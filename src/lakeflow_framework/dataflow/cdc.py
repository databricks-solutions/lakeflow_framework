from dataclasses import dataclass, field
from typing import List, Optional

from pyspark import pipelines as dp
from pyspark.sql import functions as F
import pyspark.sql.types as T

import lakeflow_framework.pipeline_config as pipeline_config

from .enums import TargetConfigFlags
from .features import Features


def get_operational_metadata_columns(
    features: Optional[Features] = None,
    target_config_flags: Optional[List[str]] = None
) -> List[str]:
    """Return the operational metadata columns the framework adds to a flow's rows.

    Mirrors the condition used when the columns are added at read time: the feature is enabled,
    an operational metadata schema is configured and the target does not disable it.

    Args:
        features: The dataflow features. When not provided, no columns are returned.
        target_config_flags: The target config flags.

    Returns:
        List[str]: The operational metadata column names, or an empty list.
    """
    schema = pipeline_config.get_operational_metadata_schema()
    if features is None or not features.operationalMetadataEnabled or not schema:
        return []
    if target_config_flags and TargetConfigFlags.DISABLE_OPERATIONAL_METADATA in target_config_flags:
        return []
    return [column.name for column in schema.fields]


def exclude_from_scd2_history(
    scd_type: str,
    track_history_column_list: Optional[List[str]],
    track_history_except_column_list: Optional[List[str]],
    columns: List[str],
    except_column_list: Optional[List[str]] = None
) -> Optional[List[str]]:
    """Add columns to track_history_except_column_list for SCD2 flows that track every column.

    Operational metadata changes on every load (e.g. a load timestamp), so tracking it makes
    SCD Type 2 open a new version for every re-delivered row, even when no business column changed.

    Args:
        scd_type: The SCD type ("1" or "2").
        track_history_column_list: Explicitly tracked columns. When set, it is left to decide.
        track_history_except_column_list: Columns already excluded from history tracking.
        columns: Columns to exclude from history tracking.
        except_column_list: Columns not written to the target; these are not added.

    Returns:
        Optional[List[str]]: The track_history_except_column_list to pass to the SDP API.
    """
    if str(scd_type) != "2" or track_history_column_list or not columns:
        return track_history_except_column_list
    result = list(track_history_except_column_list or [])
    not_written = set(except_column_list or [])
    result.extend(column for column in columns if column not in result and column not in not_written)
    return result


@dataclass
class CDCSettings:
    """
    CDC Settings for the SDP auto CDC API.

    Attributes:
        keys (List): List of keys.
        sequence_by (str): Sequence by column.
        scd_type (str): SCD type.
        where (str, optional): Where clause.
        ignore_null_updates (bool, optional): Ignore null updates flag.
        apply_as_deletes (str, optional): Apply as deletes flag.
        apply_as_truncates (str, optional): Apply as truncates flag.
        column_list (List, optional): List of columns.
        except_column_list (List, optional): List of columns to exclude.
        track_history_column_list (List, optional): List of columns to track history.
        track_history_except_column_list (List, optional): List of columns to exclude from history tracking.
    """
    keys: List
    sequence_by: str
    scd_type: str
    where: str = None
    ignore_null_updates: bool = False
    apply_as_deletes: str = None
    apply_as_truncates: str = None
    column_list: List = field(default_factory=list)
    except_column_list: List = field(default_factory=list)
    track_history_column_list: List = field(default_factory=list)
    track_history_except_column_list: List = field(default_factory=list)
    sequence_by_data_type: T.DataType = None

    def __post_init__(self):
        if self.scd_type == "2":
            # TODO: implement dynamic sequence by type
            self.sequence_by_data_type = T.TimestampType()


class CDCFlow:
    """
    A class to create a CDC flow.
    """
    def __init__(self, settings: CDCSettings):
        
        self.settings = settings
        self.apply_as_deletes = self.settings.apply_as_deletes
        self.apply_as_truncates = self.settings.apply_as_truncates
        self.column_list = self.settings.column_list
        self.except_column_list = self.settings.except_column_list
        self.keys = self.settings.keys
        self.sequence_by = self.settings.sequence_by
        self.scd_type = self.settings.scd_type
        self.track_history_column_list = self.settings.track_history_column_list
        self.track_history_except_column_list = self.settings.track_history_except_column_list
        self.where = self.settings.where
        self.ignore_null_updates = self.settings.ignore_null_updates

    def create(
            self,
            target_table: str,
            source_view_name: str,
            flow_name: Optional[str] = None,
            additional_except_columns: Optional[List[str]] = None,
            run_once: bool = False,
            features: Optional[Features] = None,
            target_config_flags: Optional[List[str]] = None
    ) -> None:
        """Create CDC flow.
        
        Args:
            logger: Logger instance for logging operations
            target_table: Name of the target table
            source_view_name: Name of the source view
            flow_name: Optional name for the flow
            additional_except_columns: Additional columns to exclude
            run_once: Whether to run the flow only once
            features: The dataflow features; used to exclude operational metadata from SCD2 history
            target_config_flags: The target config flags
        """
        logger = pipeline_config.get_logger()
        logger.debug("CDC API: passed cdc_settings: %s", self.settings)
        
        additional_except_columns = additional_except_columns or []
        logger.debug("CDC API: passed additional_except_columns: %s", additional_except_columns)

        # Handle apply_as_deletes expression
        apply_as_deletes = F.expr(self.apply_as_deletes) if self.apply_as_deletes else None
        logger.debug("CDC API: apply_as_deletes: %s", apply_as_deletes)

        # Handle apply_as_truncates expression
        apply_as_truncates = F.expr(self.apply_as_truncates) if self.apply_as_truncates else None
        logger.debug("CDC API: apply_as_truncates: %s", apply_as_truncates)

        # Handle except columns
        except_column_list = self.except_column_list.copy() if self.except_column_list else []
        if additional_except_columns:
            except_column_list.extend(additional_except_columns)
        # CDCAPI throws error on empty list, so set to None if list empty
        except_column_list = except_column_list if except_column_list else None
        logger.debug("CDC API: except_column_list: %s", except_column_list)

        # Operational metadata changes on every load, so SCD2 must not version rows on it
        track_history_except_column_list = exclude_from_scd2_history(
            scd_type=self.scd_type,
            track_history_column_list=self.track_history_column_list,
            track_history_except_column_list=self.track_history_except_column_list,
            columns=get_operational_metadata_columns(features, target_config_flags),
            except_column_list=except_column_list
        )
        logger.debug("CDC API: track_history_except_column_list: %s", track_history_except_column_list)

        dp.create_auto_cdc_flow(
            flow_name=flow_name,
            target=target_table,
            once=run_once,
            source=source_view_name,
            keys=self.keys,
            sequence_by=self.sequence_by,
            where=self.where.strip() if self.where and self.where.strip() else None,
            ignore_null_updates=self.ignore_null_updates,
            apply_as_deletes=apply_as_deletes,
            apply_as_truncates=apply_as_truncates,
            column_list=self.column_list,
            except_column_list=except_column_list,
            stored_as_scd_type=self.scd_type,
            track_history_column_list=self.track_history_column_list,
            track_history_except_column_list=track_history_except_column_list
        )
