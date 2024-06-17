from dataclasses import dataclass
import json
import copy

import dlt
from pyspark.sql import (
  DataFrame
)
from pyspark.sql.functions import expr
from pyspark.sql.types import (
  StructType,
  StructField,
  TimestampType
)

from constants import *
from dataflow_spec import StandardDataflowSpec, FlowDataflowSpec, DataflowSpecUtils, CDCApplyChanges
import utility as util
import api_utils as api


class StreamingView:

    def __init__(
        self,
        spark,
        view_name: str,
        source_details: dict,
        uc_enabled: bool,
        source_type: str = None,
        quarantine_rules: str = None,
        schema_json = None
    ):
        self.spark = spark
        self.view_name = view_name
        self.source_details = source_details
        self.uc_enabled = uc_enabled
        self.source_type = source_type
        if self.source_type is None and self.source_details["database"].lower() == "live":
            self.source_type = "live"
        else:
            self.source_type = "delta"
        self.quarantine_rules = quarantine_rules
        self.schema_json = schema_json

        self.view = dlt.view(
            self.__get_stream_df,
            name=self.view_name,
            comment=f"input dataset view for {self.view_name}",
        )

    def __get_stream_df(self) -> DataFrame:    
        if self.source_type== "cloudFiles":
            df = self.__get_cloudfiles_stream_df()
        elif self.source_type== "delta":
            df = self.__get_delta_stream_df()
        elif self.source_type== "kafka":
            df = self.__get_kafka_stream_df()
        elif self.source_type== "live":
            df = self.__get_live_stream_df()
        else:
            raise ValueError(f"Source format not supported: {self.source_type}")

        where_clause = self.source_details["whereClause"] \
            if "whereClause" in self.source_details else None
        if where_clause:
            where_clause_str = " ".join(where_clause)
            if len(where_clause_str.strip()) > 0:
                for where_clause in where_clause:
                    df = df.where(where_clause)

        select_exp = self.source_details["selectExp"] \
            if "selectExp" in self.source_details else None        
        if select_exp:
            df = df.selectExpr(*select_exp)
        
        if self.quarantine_rules:
            df = df.withColumn(METADATA_COLUMN_DEFINITIONS["QUARANTINE_FLAG"]["name"], expr(self.quarantine_rules))        
        return df


    def __get_cloudfiles_stream_df(self) -> DataFrame:
        """Read dlt cloud files.

        Args:
            spark (_type_): _description_
            bronze_dataflow_spec (_type_): _description_
            schema_json (_type_): _description_

        Returns:
            DataFrame: _description_
        """
        source_path = self.source_details["path"]
        reader_config_options = self.source_details["readerConfigOptions"]
        source_format = reader_config_options["cloudFiles.format"]
        reader_config_options.pop("cloudFiles.format")
        schema_json = self.schema_json

        if schema_json:
            schema = StructType.fromJson(schema_json)
            return (
                self.spark.readStream.format(source_format)
                .options(**reader_config_options)
                .schema(schema)
                .load(source_path)
            )
        else:
            return (
                self.spark.readStream.format(source_format)
                .options(**reader_config_options)
                .load(source_path)
            )


    def __get_delta_stream_df(self) -> DataFrame:
        database = self.source_details["database"]
        table = self.source_details["table"]
        table_name = f"{database}.{table}"
        table_path = self.source_details["tablePath"] \
            if "tablePath" in self.source_details else None
        cdf_enabled = self.source_details["cdfEnabled"].lower() == "true" \
            if "cdfEnabled" in self.source_details else False
        read_options = {}
        if cdf_enabled:
            read_options["readChangeFeed"] = "true"

        df = self.spark.readStream.options(**read_options).table(
            table_name
        ) if self.uc_enabled else self.spark.readStream.options(**read_options).load(
            path=table_path,
            format="delta"
        )
        # TODO: needs to be moved and cater for additional change types
        if cdf_enabled:
            df = df.where("_change_type IN ('insert')")
        return df


    def __get_live_stream_df(self) -> DataFrame:      
        return dlt.read_stream(self.source_details["table"])


class SqlView:

    def __init__(
        self,
        spark,
        view_name: str,
        view_details: dict,
        sql_root_path: str,
        sql_tokens: dict
    ):
        self.spark = spark
        self.view_details = view_details
        self.sql_path = f'{sql_root_path}/{view_details["sqlPath"]}'
        self.view_name = view_name
        self.sql_tokens = sql_tokens
        self.sql = self.__get_sql_from_file()
        
        dlt.view(
            self.__get_sql_df,
            name=self.view_name,
            comment=f"input dataset view for {self.view_name}",
        )


    def __get_sql_from_file(self):
        try:
            with open(self.sql_path, "r") as f:
                transform_sql = f.read()
            for token in self.sql_tokens:
                transform_sql = transform_sql.replace(token, self.sql_tokens[token])
        except Exception as e:
            raise Exception(f"Error loading sql file: {self.sql_path} - {e}")
        
        if transform_sql:
            return transform_sql
        raise Exception(f"Sql file empty or error: {self.sql_path}")

    def __get_sql_df(self) -> DataFrame:
        return self.spark.sql(self.sql)
    

class DltPipeline:

    def __init__(self, spark, framework_path: str, dataflow_spec: dataclass, logger):
        
        self.spark = spark
        uc_enabled_str = spark.conf.get("spark.databricks.unityCatalog.enabled", "False")
        uc_enabled_str = uc_enabled_str.lower()
        self.uc_enabled = True if uc_enabled_str == "true" else False
        self.dataflow_spec = dataflow_spec
        self.logger = logger

        self.local_path = dataflow_spec.localPath
        self.schema_path = f"{dataflow_spec.localPath}/{SCHEMA_PATH}"
        self.dml_path = f"{dataflow_spec.localPath}/{DML_PATH}"
        self.dqe_path = f"{dataflow_spec.localPath}/{DQE_PATH}"

        self.target_table = dataflow_spec.targetDetails["table"]
        self.table_properties = dataflow_spec.targetDetails["tableProperties"] \
            if "tableProperties" in dataflow_spec.targetDetails else None
        self.partition_cols = [x.strip() for x in dataflow_spec.targetDetails["partitionColumns"]] \
            if "partitionColumns" in dataflow_spec.targetDetails else None
        self.target_path = dataflow_spec.targetDetails["tablePath"] if "tablePath" in dataflow_spec.targetDetails else None
        
        # Init Schema
        self.schema_json = util.get_json_from_file(f"{self.schema_path}/{dataflow_spec.targetDetails['schemaPath']}")
        self.base_schema_struct = StructType.fromJson(self.schema_json)
        self.schema_struct = copy.deepcopy(self.base_schema_struct)

        # Init CDC Apply Changes settings
        # TODO: implement better handling of applychanges format
        if dataflow_spec.cdcApplyChanges:
            self.cdc_apply_changes = DataflowSpecUtils.get_cdc_apply_changes(dataflow_spec.cdcApplyChanges)        

            # TODO: implement dynamic sequence by type
            self.sequenced_by_data_type = TimestampType()

            if self.cdc_apply_changes.except_column_list:
                modified_schema = StructType([])
                if self.schema_struct:
                    for field in self.schema_struct.fields:
                        if field.name not in self.cdc_apply_changes.except_column_list:
                            modified_schema.add(field)
                    self.schema_struct = modified_schema

            if self.cdc_apply_changes.scd_type == "2":
                self.schema_struct.add(StructField(SCD2_COLUMN_NAMES["SCD2_START_AT"], self.sequenced_by_data_type))
                self.schema_struct.add(StructField(SCD2_COLUMN_NAMES["SCD2_END_AT"], self.sequenced_by_data_type))
        else:
            self.cdc_apply_changes = None

        # Init Expectations
        self.expectations_enabled = eval("dataflow_spec.dataQualityExpectationsEnabled == 'true'") if dataflow_spec.dataQualityExpectationsEnabled else False
        self.expect_rules = None
        self.expect_or_drop_rules = None
        self.expect_or_fail_rules = None
        if self.expectations_enabled:
            self.expectations_json = DataflowSpecUtils.get_expectations_from_json(self.dqe_path, framework_path)
            self.expect_rules = DataflowSpecUtils.get_expectation_rules(self.expectations_json, "expect")
            self.expect_or_drop_rules = DataflowSpecUtils.get_expectation_rules(self.expectations_json, "expect_or_drop")
            self.expect_or_fail_rules = DataflowSpecUtils.get_expectation_rules(self.expectations_json, "expect_or_fail")

        # Init Quarantine
        self.quarantine_mode = dataflow_spec.quarantineMode
        self.quarantine_enabled = self.quarantine_mode and self.quarantine_mode != "off"
        self.quarantine_rules = None
        if self.quarantine_enabled:
            self.all_rules = util.merge_dicts(self.expect_rules , self.expect_or_drop_rules, self.expect_or_fail_rules)
            self.quarantine_rules = "NOT({0})".format(" AND ".join(self.all_rules.values()))
            self.expect_rules = self.all_rules if self.quarantine_mode == "flag" else None
            self.expect_or_drop_rules = self.all_rules if self.quarantine_mode == "table" else None
            self.expect_or_fail_rules = None
            
            if self.quarantine_mode == "flag":
                self.schema_struct = util.add_struct_field(self.schema_struct, METADATA_COLUMN_DEFINITIONS["QUARANTINE_FLAG"])
            
            if self.quarantine_mode == "table":
                self.quarantine_table = self.dataflow_spec.quarantineTargetDetails["table"] \
                    if "table" in self.dataflow_spec.quarantineTargetDetails else f"{self.target_table}_quarantine"
                self.quarantine_partition_columns = [x.strip() for x in dataflow_spec.quarantineTargetDetails["partitionColumns"]] \
                    if "partitionColumns" in dataflow_spec.quarantineTargetDetails else None
                self.quarantine_path = dataflow_spec.quarantineTargetDetails["path"] \
                    if "path" in dataflow_spec.quarantineTargetDetails else None


    def call_apply_changes(
        self,
        target_table: str,
        source_view_name: str,
        cdc_apply_changes: CDCApplyChanges,
        flow_name: str = None,
        additional_except_columns: list[str] = [],
    ):
        """CDC Apply Changes against dataflowspec."""
        if cdc_apply_changes is None:
            raise Exception("cdcApplychanges is None! ")
        self.logger.debug(f"  - passed cdc_apply_changes: {cdc_apply_changes}")
        self.logger.debug(f"  - passed additional_except_columns: {additional_except_columns}")

        apply_as_deletes = None
        if cdc_apply_changes.apply_as_deletes:
            apply_as_deletes = expr(cdc_apply_changes.apply_as_deletes)
        self.logger.debug(f"  - apply_as_deletes: {apply_as_deletes}")

        apply_as_truncates = None
        if cdc_apply_changes.apply_as_truncates:
            apply_as_truncates = expr(cdc_apply_changes.apply_as_truncates)
        self.logger.debug(f"  - apply_as_truncates: {apply_as_truncates}")
        
        except_column_list = []
        if cdc_apply_changes.except_column_list and len(cdc_apply_changes.except_column_list) > 0:
            except_column_list.extend(cdc_apply_changes.except_column_list)
        # TODO: Tech debt investigate with engineering whether there is a way to pass/change columns at run time.
        # replace additional_except_column logic with below if possible in future.
        #for column in RESERVED_COLUMN_NAMES.values():
        #    if column in source_view_columns:
        #        except_column_list.append(column)
        if len(additional_except_columns) > 0:
            except_column_list.extend(additional_except_columns)
        if self.quarantine_enabled:
            except_column_list.append(METADATA_COLUMN_DEFINITIONS["QUARANTINE_FLAG"]["name"])
        if len(except_column_list) == 0:
            except_column_list = None
        self.logger.debug(f"  - except_column_list: {except_column_list}")

        dlt.apply_changes(
            target=target_table,
            flow_name=flow_name,
            source=source_view_name,
            keys=cdc_apply_changes.keys,
            sequence_by=cdc_apply_changes.sequence_by,
            where=cdc_apply_changes.where,
            ignore_null_updates=eval("cdc_apply_changes.ignore_null_updates == 'true'"),
            apply_as_deletes=apply_as_deletes,
            apply_as_truncates=apply_as_truncates,
            column_list=cdc_apply_changes.column_list,
            except_column_list=except_column_list,
            stored_as_scd_type=cdc_apply_changes.scd_type,
            track_history_column_list=cdc_apply_changes.track_history_column_list,
            track_history_except_column_list=cdc_apply_changes.track_history_except_column_list
        )

    def create_quarantine_table(self):
        self.logger.debug(f"  - Creating Quarantine Table: {self.quarantine_table}")
        schema = util.add_struct_field(self.base_schema_struct, METADATA_COLUMN_DEFINITIONS["QUARANTINE_FLAG"])
        @dlt.table(
            name=self.quarantine_table,
            table_properties=self.table_properties,
            partition_cols=self.partition_cols,
            path=self.target_path,
            schema=schema
        )
        def quarantined_rows():
            quarantine_column = METADATA_COLUMN_DEFINITIONS["QUARANTINE_FLAG"]["name"]
            df = self.spark.readStream.table(f"live.{self.view_name}").where(f"{quarantine_column} = 1")
            df = util.drop_columns(df, CDF_COLUMN_NAMES.values())
            return df


class FlowsPipeline(DltPipeline):
    
    def __init__(self, spark, framework_path: str, dataflow_spec: dataclass, logger):
        
        super().__init__(spark, framework_path, dataflow_spec, logger)
        if not isinstance(dataflow_spec, FlowDataflowSpec):
            raise Exception("Dataflow not supported!")
        self.views = {}


    def create_append_flow(
            self,
            flow_name: str,
            flow_type: str,
            flow_details: dict,
            sql_tokens: dict
    ):  
        target_table = flow_details["targetTable"]
        if flow_type == "append_sql":
            sql_path = f'{self.dml_path}/{flow_details["sqlPath"]}'
            with open(sql_path, "r") as f:
                transform_sql = f.read()
            for token in sql_tokens:
                transform_sql = transform_sql.replace(token, sql_tokens[token])

            @dlt.append_flow(
                name=flow_name,
                target=target_table)
            def flow_transform():
                df = self.spark.sql(transform_sql)
                df = util.drop_columns(df, CDF_COLUMN_NAMES.values())
                return df
        
        elif flow_type == "append_view":
            source_view_name = f'live.{flow_details["sourceView"]}'

            @dlt.append_flow(
                name=flow_name,
                target=target_table)
            def flow_transform():
                df = self.spark.readStream.table(source_view_name)
                if "column_prefix" in flow_details.keys():
                    prefix = f"{flow_details['column_prefix'].lower()}_"
                    column_prefix_exceptions = flow_details["column_prefix_exceptions"]
                    column_prefix_exceptions.append(SCD2_COLUMN_NAMES["SCD2_START_AT"])
                    column_prefix_exceptions.append(SCD2_COLUMN_NAMES["SCD2_END_AT"])
                    df = df.select([df[col].alias(prefix + col)
                                    if col not in column_prefix_exceptions
                                    else df[col] for col in df.columns])
                df = util.drop_columns(df, CDF_COLUMN_NAMES.values())
                return df


    def create_dataflow(self):
        self.logger.info(f"Flow ID: {self.dataflow_spec.dataFlowId}\nFlow Group: {self.dataflow_spec.dataFlowGroup}\nTarget Table: {self.target_table}")
        self.logger.info(f"Creating Target Table: {self.target_table}")
        dlt.create_streaming_table(
            name=self.target_table,
            table_properties=self.table_properties,
            partition_cols=self.partition_cols,
            path=self.target_path,
            schema=self.schema_struct,
            expect_all=self.expect_rules,
            expect_all_or_drop=self.expect_or_drop_rules,
            expect_all_or_fail=self.expect_or_fail_rules,
        )

        self.logger.info(f"Creating FlowGroups...")
        for flowGroup in self.dataflow_spec.flowGroups:
            self.logger.info(f"Creating Flow Group: {flowGroup['flowGroup']}")
            targets = flowGroup["targets"]
            sql_tokens = flowGroup["sqlTokens"]

            self.logger.info(f"  - Creating Tables...")
            for table_name in targets.keys():
                table_details = targets[table_name]
                if table_details["type"] == "ST":
                    dlt.create_streaming_table(
                        name=table_name,
                        #table_properties=flow['tableProperties'],
                        #schema=struct_schema,
                    )
                elif table_details["type"] == "MV":
                    # TODO: handle MV's
                    break
                self.logger.debug(f"    - Created Table: {table_name}, type: {table_details['type']}")

            self.logger.info(f"  - Creating Flows...")
            flows = flowGroup['flows']
            for flow_name in flows:
                self.logger.info(f"    - Creating Flow: {flow_name}")
                flow_config = flows[flow_name]
                flow_type = flow_config['flowType']
                flow_details = flow_config["flowDetails"]
                views = flow_config['views'] if 'views' in flow_config else []

                self.logger.debug(f"    - Creating Views...")
                for view_name in views:
                    view_config = views[view_name]
                    view_type = view_config["viewType"]
                    view_details = view_config["viewDetails"]

                    self.logger.debug(f"      - Creating View: {view_name}, type: {view_type}")
                    if view_type == "stream":
                        self.views[view_name] = StreamingView(self.spark, view_name, view_details, self.uc_enabled)
                    elif view_type == "sql":
                        self.views[view_name] = SqlView(self.spark, view_name, view_details, self.dml_path, sql_tokens)
                
                if flow_type.startswith('append'):
                    self.logger.debug(f"    - Creating Append Flow: {flow_name}")
                    self.create_append_flow(flow_name, flow_type, flow_details, sql_tokens)

                elif flow_type == 'merge':
                    self.logger.debug(f"    - Creating Merge Flow: {flow_name}")
                    target_table = flow_details['targetTable']
                    source_view_name = flow_details['sourceView']
                    cdc_apply_changes = (self.cdc_apply_changes 
                                         if target_table == self.target_table 
                                         else DataflowSpecUtils.get_cdc_apply_changes(targets[target_table]["cdcApplyChanges"]))
                    
                    additional_except_columns = []
                    cdf_enabled = views[source_view_name]["viewDetails"]["cdfEnabled"].lower() == "true" \
                        if "cdfEnabled" in views[source_view_name]["viewDetails"] else False
                    if cdf_enabled:
                        additional_except_columns.extend(CDF_COLUMN_NAMES.values())
                    self.call_apply_changes(target_table, source_view_name, cdc_apply_changes, flow_name, additional_except_columns)

        if self.quarantine_enabled and self.quarantine_mode == "table":
            self.create_quarantine_table() 


class StandardPipeline(DltPipeline):
    
    def __init__(self, spark, framework_path: str, dataflow_spec: dataclass, logger):
        super().__init__(spark, framework_path, dataflow_spec, logger)
        if not isinstance(dataflow_spec, StandardDataflowSpec):
            raise Exception("Dataflow not supported!")
        self.source_type = dataflow_spec.sourceType
        self.source_details = dataflow_spec.sourceDetails
        self.view_name = dataflow_spec.sourceDetails["viewName"]
        self.cdf_enabled = self.source_details["cdfEnabled"] if "cdfEnabled" in self.source_details else False
        

    def get_stream_from_view(self):
        df = self.spark.readStream.table(f"live.{self.view_name}")
        df = util.drop_columns(df, RESERVED_COLUMN_NAMES.values())
        return df


    def create_dataflow(self):
        self.logger.info(f"Flow ID: {self.dataflow_spec.dataFlowId}\nFlow Group: {self.dataflow_spec.dataFlowGroup}\nTarget Table: {self.target_table}")
        self.logger.debug(f"Creating View: {self.view_name}")
        source_view = StreamingView(self.spark, self.view_name, self.source_details, self.uc_enabled, self.source_type, quarantine_rules=self.quarantine_rules)
        if self.quarantine_enabled and self.quarantine_mode == "table":
            self.logger.debug(f"Creating Quarantine Table: {self.quarantine_table}")
            self.create_quarantine_table() 
            
        if self.cdc_apply_changes:
            self.logger.debug(f"Creating Target Table (Apply Changes Branch): {self.target_table}")
            dlt.create_streaming_table(
                name=self.target_table,
                table_properties=self.table_properties,
                partition_cols=self.partition_cols,
                path=self.target_path,
                schema=self.schema_struct,
                expect_all=self.expect_rules,
                expect_all_or_drop=self.expect_or_drop_rules,
                expect_all_or_fail=self.expect_or_fail_rules,
            )
            
            additional_except_columns = []
            if self.cdf_enabled:
                additional_except_columns.extend(CDF_COLUMN_NAMES.values())
            self.logger.debug(f"Calling Apply Changes: {self.view_name} --> {self.target_table}")
            self.call_apply_changes(self.target_table, self.view_name, self.cdc_apply_changes, additional_except_columns=additional_except_columns)

        else:
            self.logger.debug(f"Creating Target Table (Append Branch): {self.target_table}")
            table = dlt.table(
                self.get_stream_from_view,
                name=self.target_table,
                table_properties=self.table_properties,
                partition_cols=self.partition_cols,
                path=self.target_path,
                # TODO: add comment=<property>
            )
            if self.expectations_enabled:
                self.logger.debug(f"  - Adding Expectations...")
                table_with_expectations = None
                if self.expect_rules:
                    table_with_expectations = dlt.expect_all(self.expect_rules)(table)
                if self.expect_or_drop_rules:
                    table_with_expectations = dlt.expect_all_or_drop(self.expect_or_drop_rules)(table_with_expectations) \
                        if table_with_expectations else dlt.expect_all_or_drop(self.expect_or_drop_rules)(table)
                if self.expect_or_fail_rules:
                    table_with_expectations = dlt.expect_all_or_fail(self.expect_or_fail_rules)(table_with_expectations) \
                        if table_with_expectations else dlt.expect_all_or_fail(self.expect_or_fail_rules)(table)


class DltPipelineBuilder:

    def __init__(
        self,
        spark,
        dbutils,
        config: dict
    ):
        log_level = config["log_level"] if "log_level" in config else "INFO"
        self.logger = util.set_logger("DltFramework", log_level)
        self.logger.info(f"Initializing Pipeline...")
        # Check for mandatory configs
        mandatory_configs = ["framework_path", "bundle_path", "workspace_host"]
        missing_keys = []
        for key in mandatory_configs:
            if key not in config or config[key] is None or config[key].strip() == '':
                missing_keys.append(key)
        if len(missing_keys) > 0:
            raise Exception(f"Following config parameters missing or not set: {missing_keys}")
        
        # Set core attributes
        self.spark = spark
        self.dbutils = dbutils
        self.context = self.dbutils.entry_point.getDbutils().notebook().getContext()
        self.config = config
        self.bundle_path = config["bundle_path"]
        self.framework_path = config["framework_path"]
        self.workspace_host = config["workspace_host"]
        self.pipeline_name = config["pipeline_name"]

        # Get framwork global config
        self.global_config = util.get_json_from_file(f"{self.framework_path}/config/global.json")
        self.api_connections = self.global_config["api_connections"] if "api_connections" in self.global_config else None

        # Get dataflow_specs from bundle and build Pipeline
        self.dataflows_path = f"{config['bundle_path']}/{DATAFLOWS_BASE_PATH}"
        self.logger.info(f"Retrieving Dataflow Specs From: {self.dataflows_path}")
        self.dataflow_specs = DataflowSpecUtils.get_dataflow_specs(self.dataflows_path, self.framework_path)
        if self.dataflow_specs is None or len(self.dataflow_specs) == 0:
            raise Exception(f"No dataflow_specs were found in or loaded from: {self.dataflows_path}")
        
        self.logger.info(f"Processing Dataflow Specs...")
        for dataflow_spec in self.dataflow_specs:
            if isinstance(dataflow_spec, FlowDataflowSpec):
                FlowsPipeline(self.spark, self.framework_path, dataflow_spec, self.logger).create_dataflow()
            elif isinstance(dataflow_spec, StandardDataflowSpec):
                StandardPipeline(self.spark, self.framework_path, dataflow_spec, self.logger).create_dataflow()
            else:
                raise Exception("Dataflow not supported!")
        
        # Get pipeline config from bundle
        self.config_path = f"{self.bundle_path}/{PIPELINE_CONFIGS_PATH}"
        self.logger.info(f"Retrieving Pipeline Config From: {self.dataflows_path}")
        self.pipeline_config = None
        self.pipeline_config = util.get_json_from_file(f"{self.config_path}/{self.pipeline_name}.json")

        # Process Pipeline Config
        if self.pipeline_config:
            self.logger.info(f"Processing Pipeline Config...")
            if "event_hooks" in self.pipeline_config:
                self.logger.info(f"  - Creating Event Hooks...")
                self.event_hooks = self.pipeline_config["event_hooks"]
                self.__configure_event_hooks()
    

    def __configure_event_hooks(self):
        event_configs = self.event_hooks
            
        @dlt.on_event_hook
        def pipeline_hooks(event):
            try:
                if "progress_events" in event_configs:
                    self.logger.debug(f"    - Creating Pipeline Status Based Events...")
                    for config in event_configs["progress_events"]:
                        if (
                            event['event_type'] == 'update_progress' and
                            event['details']['update_progress']['state'].upper() == config["state"].upper()
                        ):
                            for action in config["actions"]:
                                type = action["type"]
                                if type == "api_call":
                                    self.__set_api_event(action)
            except Exception as e:
                self.logger.info(f"Error in DLT event hook config: {e}")
    

    def __set_api_event(self, action: dict):
        api_connections = self.api_connections
        if api_connections:
            api_connection_name = action["api_connection_name"] 
            if api_connection_name in api_connections:
                api_config = api_connections[api_connection_name]
                api_connection_type = api_config["type"]
                if api_connection_type == "databricks_sql_statements_api":
                    self.__log_dbsql(api_config, action["payload"])
                else:
                    raise ValueError(f"Api connection type unknown: {api_connection_type}")
            else:
                raise ValueError(f"API connection \"{api_connection_name}\" missing from global config.")
        else:
            raise ValueError("API connections not configured in global config, or global config missing.")


    def __log_dbsql(self, config: dict, payload: str):
        data = json.loads(payload)
        values = []
        for val in data.values():
            if isinstance(val, str):
                values.append(f"'{val}'")
            else:
                values.append(str(val))

        sql = f"""INSERT INTO {config["schema"]}.{config["table"]} ({', '.join(data.keys())})
                VALUES ({', '.join(values)})"""

        payload = {
            "warehouse_id": config["warehouse_id"],
            "statement": sql,
            "wait_timeout": "0s"
        }

        token = self.context.apiToken().get()
        api.call_statement_api(self.workspace_host, token, payload)