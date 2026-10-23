from dataclasses import dataclass, field
from typing import List, Optional

from pyspark import pipelines as dp
from pyspark.sql import functions as F
import pyspark.sql.types as T

import lakeflow_framework.pipeline_config as pipeline_config


def _empty_to_none(value):
    """AUTO CDC rejects empty lists; coerce them to None so they are not passed."""
    if value is None:
        return None
    if isinstance(value, list) and not value:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


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
        ignore_null_updates_column_list (List, optional): Columns that ignore incoming nulls.
        ignore_null_updates_except_column_list (List, optional): Columns that apply explicit nulls.
        apply_as_deletes (str, optional): Apply as deletes flag.
        apply_as_truncates (str, optional): Apply as truncates flag.
        column_list (List, optional): List of columns.
        except_column_list (List, optional): List of columns to exclude.
        track_history_column_list (List, optional): List of columns to track history.
        track_history_except_column_list (List, optional): List of columns to exclude from history tracking.
        columns_to_update (str, optional): Source column holding per-row columns to write.
    """
    keys: List
    sequence_by: str
    scd_type: str
    where: str = None
    ignore_null_updates: bool = False
    ignore_null_updates_column_list: List = field(default_factory=list)
    ignore_null_updates_except_column_list: List = field(default_factory=list)
    apply_as_deletes: str = None
    apply_as_truncates: str = None
    column_list: List = field(default_factory=list)
    except_column_list: List = field(default_factory=list)
    track_history_column_list: List = field(default_factory=list)
    track_history_except_column_list: List = field(default_factory=list)
    columns_to_update: str = None
    sequence_by_data_type: T.DataType = None

    def __post_init__(self):
        self.ignore_null_updates_column_list = _empty_to_none(
            self.ignore_null_updates_column_list
        ) or []
        self.ignore_null_updates_except_column_list = _empty_to_none(
            self.ignore_null_updates_except_column_list
        ) or []
        self.columns_to_update = _empty_to_none(self.columns_to_update)

        if self.scd_type == "2":
            # TODO: implement dynamic sequence by type
            self.sequence_by_data_type = T.TimestampType()

        has_ignore_column_list = bool(self.ignore_null_updates_column_list)
        has_ignore_except_list = bool(self.ignore_null_updates_except_column_list)
        if has_ignore_column_list and has_ignore_except_list:
            raise ValueError(
                "Set ignore_null_updates_column_list or "
                "ignore_null_updates_except_column_list, not both."
            )

        if self.columns_to_update and (
            self.ignore_null_updates or has_ignore_column_list or has_ignore_except_list
        ):
            raise ValueError(
                "columns_to_update cannot be combined with ignore_null_updates, "
                "ignore_null_updates_column_list, or ignore_null_updates_except_column_list."
            )


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
        self.ignore_null_updates_column_list = self.settings.ignore_null_updates_column_list
        self.ignore_null_updates_except_column_list = self.settings.ignore_null_updates_except_column_list
        self.columns_to_update = self.settings.columns_to_update

    def create(
            self,
            target_table: str,
            source_view_name: str,
            flow_name: Optional[str] = None,
            additional_except_columns: Optional[List[str]] = None,
            run_once: bool = False
    ) -> None:
        """Create CDC flow.
        
        Args:
            logger: Logger instance for logging operations
            target_table: Name of the target table
            source_view_name: Name of the source view
            flow_name: Optional name for the flow
            additional_except_columns: Additional columns to exclude
            run_once: Whether to run the flow only once
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
        if self.columns_to_update and self.columns_to_update not in except_column_list:
            except_column_list.append(self.columns_to_update)

        # CDCAPI throws error on empty list, so set to None if list empty
        except_column_list = except_column_list if except_column_list else None
        logger.debug("CDC API: except_column_list: %s", except_column_list)

        cdc_kwargs = {
            "flow_name": flow_name,
            "target": target_table,
            "once": run_once,
            "source": source_view_name,
            "keys": self.keys,
            "sequence_by": self.sequence_by,
            "where": self.where.strip() if self.where and self.where.strip() else None,
            "ignore_null_updates": self.ignore_null_updates,
            "apply_as_deletes": apply_as_deletes,
            "apply_as_truncates": apply_as_truncates,
            "column_list": self.column_list,
            "except_column_list": except_column_list,
            "stored_as_scd_type": self.scd_type,
            "track_history_column_list": self.track_history_column_list,
            "track_history_except_column_list": self.track_history_except_column_list,
        }
        # Newer AUTO CDC args — only pass when set so older runtimes stay compatible.
        ignore_null_updates_column_list = _empty_to_none(self.ignore_null_updates_column_list)
        ignore_null_updates_except_column_list = _empty_to_none(
            self.ignore_null_updates_except_column_list
        )
        if ignore_null_updates_column_list:
            cdc_kwargs["ignore_null_updates_column_list"] = ignore_null_updates_column_list
        if ignore_null_updates_except_column_list:
            cdc_kwargs["ignore_null_updates_except_column_list"] = (
                ignore_null_updates_except_column_list
            )
        if self.columns_to_update:
            cdc_kwargs["columns_to_update"] = self.columns_to_update

        dp.create_auto_cdc_flow(**cdc_kwargs)
