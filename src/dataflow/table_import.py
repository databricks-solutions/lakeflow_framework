from pyspark import pipelines as dp
from typing import Any

from constants import SystemColumns
from dataflow.sources.factory import SourceFactory
import pipeline_config
from pyspark.sql import functions as F

from .cdc import CDCFlow, CDCSettings
from .dataflow_config import DataFlowConfig
from .enums import Mode, SourceType
from .view import View


# TODO: Limited to streaming at the moment, fix for Batch
def create_table_import_flow(
    source_details: Any,
    target_table_name: str,
    cdc_settings: CDCSettings = None,
    dataflow_config: DataFlowConfig = None
):
    """Create a table import flow."""
    spark = pipeline_config.get_spark()
    logger = pipeline_config.get_logger()
    logger.info("Creating Run Once Flow: %s", source_details)
    
    source_details_dict = source_details.copy()
    source_details = SourceFactory.create(SourceType.DELTA, source_details_dict)
    view_name = f"v_import_{source_details.table}"
    flow_name = f"f_import_{source_details.table}"
    scd2_columns = [column.value for column in SystemColumns.SCD2Columns]
    additional_except_columns = getattr(source_details, 'exceptColumns', [])

    # Create Flows for table being imported
    if not cdc_settings:
        logger.info(f"Table Import: Append Only: Creating source view: {view_name}")
        View(
            viewName=view_name,
            mode=Mode.BATCH,
            sourceType=SourceType.DELTA,
            sourceDetails=source_details_dict
        ).create_view(
            dataflow_config=dataflow_config
        )

        logger.info(f"Table Import: Creating append flow: {flow_name}")
        # If not CDC create append flow for table being imported
        @dp.append_flow(name=f"f_import_append_{source_details.table}", target=target_table_name, once=True)
        def flow_migrate_table():
            return spark.read.table(view_name)

    else:
        # If SCD Type 2
        logger.info(f"Table Import: CDC: Creating source view: {view_name}")
        View(
            viewName=view_name,
            mode=Mode.STREAM,
            sourceType=SourceType.DELTA,
            sourceDetails=source_details_dict
        ).create_view(
            dataflow_config=dataflow_config
        )

        cdc_settings_with_deletes = None
        if cdc_settings.scd_type == "2":
            logger.debug(f"Table Import: Handling SCD Type 2")

            is_deleted_column = "is_deleted"
            start_at_column = SystemColumns.SCD2Columns.SCD2_START_AT.value
            end_at_column = SystemColumns.SCD2Columns.SCD2_END_AT.value
            watermark_column = "WATERMARK_COLUMN"
            exclude_columns = [is_deleted_column, watermark_column, *scd2_columns]
            cdc_settings_with_deletes = CDCSettings(
                scd_type=cdc_settings.scd_type,
                keys=cdc_settings.keys,
                sequence_by=SystemColumns.SCD2Columns.SCD2_START_AT.value,
                apply_as_deletes=f"{is_deleted_column} = true",
                ignore_null_updates=cdc_settings.ignore_null_updates,
                except_column_list= (
                    list(set(cdc_settings.except_column_list.copy().extend(*exclude_columns)))
                    if cdc_settings.except_column_list
                    else [is_deleted_column, *scd2_columns]
                )
            )
            
            # Create view for table being imported with deletes
            logger.debug(f"Table Import: Creating view to handle soft deletes / closed records: {view_name}")
            view_with_deletes_name = f"{view_name}_with_deletes"
            @dp.view(name=view_with_deletes_name)
            def view_with_deletes():
                # Read stream and add arbitrary watermark to allow grouping and aggregation
                df = (spark.readStream.table(view_name)
                    .withColumn(is_deleted_column, F.lit(False))
                    .withColumn(watermark_column, F.lit('2000-01-01').cast("timestamp"))
                )
                df_closed_rows = (df
                    .withWatermark(watermark_column, "10 minutes")
                    .groupBy(
                        *cdc_settings_with_deletes.keys,
                        F.window(watermark_column, "10 minutes")
                    )
                    .agg(
                        F.max_by(F.struct("*"), start_at_column).alias("max_row")
                    )
                    .select("max_row.*")
                    .withColumn(start_at_column, F.col(end_at_column))
                    .withColumn(is_deleted_column, F.lit(True))
                    
                    .where(F.col(end_at_column).isNotNull())
                )

                return df.unionAll(df_closed_rows).drop(watermark_column)

        CDCFlow(
            cdc_settings_with_deletes
            if cdc_settings_with_deletes
            else cdc_settings
        ).create(
            target_table=target_table_name,
            source_view_name=view_name if cdc_settings.scd_type != "2" else view_with_deletes_name,
            flow_name=flow_name,
            additional_except_columns=additional_except_columns,
            run_once=True
        )
