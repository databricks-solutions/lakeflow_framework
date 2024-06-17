"""Dataflow Spec related utilities."""
import os
from constants import *
from dataclasses import dataclass
import utility


@dataclass
class StandardDataflowSpec:
    """A schema to hold a dataflow spec used for defining standard flows."""

    dataFlowId: str
    dataFlowGroup: str
    dataFlowType: str
    sourceSystem: str
    sourceType: str
    sourceDetails: dict
    targetFormat: str
    targetDetails: dict
    cdcApplyChanges: str = None
    dataQualityExpectationsEnabled: str = None
    quarantineMode: str = None
    quarantineTargetDetails: dict = None
    localPath: str = None


@dataclass
class FlowDataflowSpec:
    """A schema to hold a dataflow spec used for defining flows (append or change)."""

    dataFlowId: str
    dataFlowGroup: str
    dataFlowType: str
    targetFormat: str
    targetDetails: dict
    flowGroups: list
    cdcApplyChanges: str = None
    dataQualityExpectationsEnabled: str = None
    quarantineMode: str = None
    quarantineTargetDetails: dict = None
    localPath: str = None


@dataclass
class CDCApplyChanges:
    """CDC ApplyChanges structure."""

    keys: list
    sequence_by: str
    where: str
    ignore_null_updates: bool
    apply_as_deletes: str
    apply_as_truncates: str
    column_list: list
    except_column_list: list
    scd_type: str
    track_history_column_list: list
    track_history_except_column_list: list


class DataflowSpecUtils:
    """A collection of methods for working with DataflowSpec."""

    cdc_applychanges_api_mandatory_attributes = ["keys", "sequence_by", "scd_type"]
    cdc_applychanges_api_attributes = [
        "keys",
        "sequence_by",
        "where",
        "ignore_null_updates",
        "apply_as_deletes",
        "apply_as_truncates",
        "column_list",
        "except_column_list",
        "scd_type",
        "track_history_column_list",
        "track_history_except_column_list",
    ]
    cdc_applychanges_api_attributes_defaults = {
        "where": None,
        "ignore_null_updates": False,
        "apply_as_deletes": None,
        "apply_as_truncates": None,
        "column_list": None,
        "except_column_list": None,
        "track_history_column_list": None,
        "track_history_except_column_list": None,
    }


    @staticmethod
    def get_dataflow_specs(
        bundle_path: str,
        framework_path: str,
        bundle_tables: str = None # TODO: bundle_tables to be comma separated list of table subfolders, to allow selectively executing tables in a bundle
    ):

        main_val_schema_path = f"{framework_path}/{MAIN_SPEC_SCHEMA_PATH}"
        main_validator = utility.JSONValidator(main_val_schema_path)
        flow_val_schema_path = f"{framework_path}/{FLOW_GROUP_SPEC_SCHEMA_PATH}"
        flow_validator = utility.JSONValidator(flow_val_schema_path)
        
        main_file_suffix = MAIN_SPEC_FILE_SUFFIX
        flow_file_suffix = FLOW_GROUP_FILE_SUFFIX

        dataflow_spec_list = []
        validation_errors = {}
        if os.path.exists(bundle_path): 
            subpaths = utility.list_subpaths(bundle_path)
            for subpath in subpaths:
                base_path = f"{bundle_path}/{subpath}"
                path = f"{base_path}/dataFlowSpec/"
                json_files = utility.get_json_from_files(path, file_suffix=main_file_suffix)
                if len(json_files) == 1:
                    for json_file, json_data in json_files.items():
                        errors = main_validator.validate(json_data)
                        if errors:
                            validation_errors[json_file] = errors
                        else:
                            dataflow_spec = json_data
                            if dataflow_spec["dataFlowType"] == "flow": 
                                json_files = utility.get_json_from_files(path, file_suffix=flow_file_suffix, recursive=True)
                                if json_files:
                                    flow_groups = []
                                    for json_file, json_data in json_files.items():
                                        errors = flow_validator.validate(json_data)
                                        if errors:
                                            validation_errors[json_file] = errors
                                        else:
                                            flow_groups.append(json_data)
                                    dataflow_spec["flowGroups"] = flow_groups
                                    dataflow_spec["localPath"] = base_path
                                    dataflow_spec_list.append(FlowDataflowSpec(**dataflow_spec))

                            elif dataflow_spec["dataFlowType"] == "standard":
                                dataflow_spec["localPath"] = base_path
                                dataflow_spec_list.append(StandardDataflowSpec(**dataflow_spec))

                    if validation_errors:
                        raise ValueError(f"Invalid dataflow spec files found: {validation_errors}")

        return dataflow_spec_list


    @staticmethod
    def get_cdc_apply_changes(json_cdc_apply_changes) -> CDCApplyChanges:
        """Get CDC Apply changes metadata."""
        payload_keys = json_cdc_apply_changes.keys()
        missing_cdc_payload_keys = set(DataflowSpecUtils.cdc_applychanges_api_attributes).difference(payload_keys)
        if set(DataflowSpecUtils.cdc_applychanges_api_mandatory_attributes) - set(payload_keys):
            missing_mandatory_attr = set(DataflowSpecUtils.cdc_applychanges_api_mandatory_attributes) - set(
                payload_keys
            )
            raise Exception(f"mandatory missing keys= {missing_mandatory_attr} for merge info")
        else:
            for missing_cdc_payload_key in missing_cdc_payload_keys:
                json_cdc_apply_changes[missing_cdc_payload_key] = DataflowSpecUtils.cdc_applychanges_api_attributes_defaults[
                    missing_cdc_payload_key
                ]
        if json_cdc_apply_changes["where"].strip() == '':
            json_cdc_apply_changes["where"] = None
        return CDCApplyChanges(**json_cdc_apply_changes)


    @staticmethod
    def get_expectations_from_json(
        path: str,
        framework_path: str
    ):
        validator = utility.JSONValidator(f"{framework_path}/{EXPECTATIONS_SPEC_SCHEMA_PATH}")
        validation_errors = {}
        expectations = {}
        if os.path.exists(path): 
            json_files = utility.get_json_from_files(path, file_suffix=".json")
            if json_files:
                for json_file, json_data in json_files.items():
                    errors = validator.validate(json_data)
                    if errors:
                        validation_errors[json_file] = errors
                    else:
                        expectations.update(json_data)
            else:
                raise ValueError(f"No files found in expectations file path: {path}")

            if validation_errors:
                raise ValueError(f"Invalid dataflow spec files found: {validation_errors}")
        
        else:
            raise ValueError(f"Expectations file path not found: {path}")

        return expectations


    @staticmethod
    def get_expectation_rules(expectations: dict, type: str, tag: str = None):
        """
            loads data quality rules from a table
            :param tag: tag to match
            :return: dictionary of rules that matched the tag
        """
        rules = None
        if type in expectations:
            rules = {}
            for expectation in expectations[type]:
                if "enabled" not in expectation or \
                    ("enabled" in expectation and eval("expectation['enabled'] == 'true'")):
                    if tag:
                        if expectation["tag"] == tag:
                            rules[expectation["name"]] = expectation["constraint"]
                    else:
                        rules[expectation["name"]] = expectation["constraint"]
        return rules