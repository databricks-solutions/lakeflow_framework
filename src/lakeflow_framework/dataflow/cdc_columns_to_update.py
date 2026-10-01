"""Build the AUTO CDC ``columns_to_update`` array for lineage-only columns.

Lineage columns (for example ``meta_file_metadata``) are written on insert and
when any payload column changes. They are omitted when they are the only change
so Auto CDC leaves the current target value in place.
"""
from functools import reduce
from typing import Iterable, List, Optional, Sequence

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

from lakeflow_framework.constants import SystemColumns

COLUMNS_TO_UPDATE_COLUMN = SystemColumns.CDCColumns.COLUMNS_TO_UPDATE.value

CHANGE_TYPE_INSERT = "insert"
CHANGE_TYPE_UPDATE_PREIMAGE = "update_preimage"
CHANGE_TYPE_UPDATE_POSTIMAGE = "update_postimage"
CHANGE_TYPE_DELETE = "delete"

_CHANGE_TYPE_CANDIDATES = (
    SystemColumns.CDFColumns.CDF_CHANGE_TYPE.value,
    "meta_cdc_change_type",
)
_COMMIT_VERSION_CANDIDATES = (
    SystemColumns.CDFColumns.CDF_COMMIT_VERSION.value,
    "meta_cdc_commit_version",
)
_COMMIT_TIMESTAMP_CANDIDATES = (
    SystemColumns.CDFColumns.CDF_COMMIT_TIMESTAMP.value,
    "meta_cdc_commit_timestamp",
)

DEFAULT_IGNORE_COLUMNS = frozenset({
    SystemColumns.CDFColumns.CDF_CHANGE_TYPE.value,
    SystemColumns.CDFColumns.CDF_COMMIT_VERSION.value,
    SystemColumns.CDFColumns.CDF_COMMIT_TIMESTAMP.value,
    SystemColumns.SCD2Columns.SCD2_START_AT.value,
    SystemColumns.SCD2Columns.SCD2_END_AT.value,
    COLUMNS_TO_UPDATE_COLUMN,
    "meta_cdc_change_type",
    "meta_cdc_commit_version",
    "meta_cdc_commit_timestamp",
    "is_delete",
    "is_deleted",
})


def _unique(columns: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(col for col in columns if col))


def payload_columns(
    all_columns: Sequence[str],
    keys: Sequence[str],
    lineage_cols: Sequence[str],
    extra_ignore: Optional[Sequence[str]] = None,
) -> List[str]:
    """Columns that count as a real payload change."""
    ignore = set(DEFAULT_IGNORE_COLUMNS)
    ignore.update(keys)
    ignore.update(lineage_cols)
    if extra_ignore:
        ignore.update(extra_ignore)
    return [col for col in all_columns if col not in ignore]


def change_type_column(columns: Sequence[str]) -> Optional[str]:
    """Return the CDF change-type column if present (framework or source alias)."""
    column_set = set(columns)
    for candidate in _CHANGE_TYPE_CANDIDATES:
        if candidate in column_set:
            return candidate
    return None


def commit_timestamp_column(columns: Sequence[str]) -> Optional[str]:
    """Return the CDF commit-timestamp column if present (framework or source alias)."""
    column_set = set(columns)
    for candidate in _COMMIT_TIMESTAMP_CANDIDATES:
        if candidate in column_set:
            return candidate
    return None


def commit_version_column(columns: Sequence[str]) -> Optional[str]:
    """Return the CDF commit-version column if present (framework or source alias)."""
    column_set = set(columns)
    for candidate in _COMMIT_VERSION_CANDIDATES:
        if candidate in column_set:
            return candidate
    return None


def has_cdf_preimage_columns(columns: Sequence[str]) -> bool:
    """True when the frame can pair update preimages with postimages."""
    return change_type_column(columns) is not None and commit_version_column(columns) is not None


def columns_to_update_for_event(
    *,
    is_insert: bool,
    is_delete: bool,
    payload_changed: bool,
    payload_cols: Sequence[str],
    lineage_cols: Sequence[str],
) -> List[str]:
    """Return the column names Auto CDC should write for one event."""
    if is_insert or is_delete or payload_changed:
        return _unique([*payload_cols, *lineage_cols])
    return []


def _array_of_names(names: Sequence[str]):
    if not names:
        return F.array().cast("array<string>")
    return F.array(*[F.lit(name) for name in names])


def _any_payload_changed(payload_cols: Sequence[str], prefix: str):
    if not payload_cols:
        return F.lit(False)
    return reduce(
        lambda left, right: left | right,
        (~F.col(col).eqNullSafe(F.col(f"{prefix}{col}")) for col in payload_cols),
    )


def _with_cdf_preimage_columns_to_update(
    df: DataFrame,
    keys: Sequence[str],
    lineage_cols: Sequence[str],
    payload_cols: Sequence[str],
    change_col: str,
) -> DataFrame:
    """Pair pre/post images inside each streaming microbatch.

    Window and stream-stream joins are not usable here: Spark rejects
    non-time windows on streams, and a left stream-stream join buffers
    inserts that never find a preimage.
    """
    commit_col = commit_version_column(df.columns)
    write_cols = _unique([*payload_cols, *lineage_cols])
    key_cols = list(keys)
    payload = list(payload_cols)
    result_col = COLUMNS_TO_UPDATE_COLUMN
    preimage_type = CHANGE_TYPE_UPDATE_PREIMAGE
    insert_type = CHANGE_TYPE_INSERT
    delete_type = CHANGE_TYPE_DELETE
    out_schema = T.StructType(
        list(df.schema.fields)
        + [T.StructField(COLUMNS_TO_UPDATE_COLUMN, T.ArrayType(T.StringType()), False)]
    )
    empty_columns = [field.name for field in out_schema.fields]

    def _assign(pdf_iter):
        import pandas as pd

        def values_differ(left, right):
            left_na = left is None or (isinstance(left, float) and pd.isna(left))
            right_na = right is None or (isinstance(right, float) and pd.isna(right))
            if left_na and right_na:
                return False
            if left_na or right_na:
                return True
            return left != right

        yielded = False
        for pdf in pdf_iter:
            if pdf is None or pdf.empty:
                continue
            apply = pdf.loc[pdf[change_col] != preimage_type].copy()
            if apply.empty:
                continue
            pre_cols = key_cols + [commit_col] + payload
            pre = pdf.loc[pdf[change_col] == preimage_type, pre_cols]
            if payload:
                pre = pre.rename(columns={col: f"__pre_{col}" for col in payload})
            if pre.empty:
                apply[result_col] = [list(write_cols)] * len(apply)
                yield apply
                yielded = True
                continue

            merged = apply.merge(
                pre,
                on=key_cols + [commit_col],
                how="left",
                indicator=True,
            )

            def cols_for(row):
                if row[change_col] in (insert_type, delete_type):
                    return list(write_cols)
                if row["_merge"] == "left_only":
                    return list(write_cols)
                if any(values_differ(row[col], row[f"__pre_{col}"]) for col in payload):
                    return list(write_cols)
                return []

            merged[result_col] = merged.apply(cols_for, axis=1)
            merged = merged.drop(
                columns=["_merge"] + [f"__pre_{col}" for col in payload],
                errors="ignore",
            )
            yield merged
            yielded = True
        if not yielded:
            yield pd.DataFrame(columns=empty_columns)

    return df.mapInPandas(_assign, schema=out_schema)


def _with_target_columns_to_update(
    df: DataFrame,
    target_df: DataFrame,
    keys: Sequence[str],
    lineage_cols: Sequence[str],
    payload_cols: Sequence[str],
) -> DataFrame:
    current = target_df
    end_at = SystemColumns.SCD2Columns.SCD2_END_AT.value
    if end_at in current.columns:
        current = current.where(F.col(end_at).isNull())

    tgt_aliases = [F.col(key).alias(f"__tgt_key_{key}") for key in keys]
    tgt_aliases.extend(F.col(col).alias(f"__tgt_{col}") for col in payload_cols)
    current = current.select(*tgt_aliases)

    join_on = [df[key] == current[f"__tgt_key_{key}"] for key in keys]
    joined = df.join(current, on=join_on, how="left")
    payload_changed = _any_payload_changed(payload_cols, "__tgt_")
    is_insert = F.col(f"__tgt_key_{keys[0]}").isNull()
    change_col = change_type_column(df.columns)
    is_delete = F.col(change_col) == CHANGE_TYPE_DELETE if change_col else F.lit(False)

    write_cols = _unique([*payload_cols, *lineage_cols])
    return (
        joined.withColumn(
            COLUMNS_TO_UPDATE_COLUMN,
            F.when(
                is_insert | is_delete | payload_changed,
                _array_of_names(write_cols),
            ).otherwise(_array_of_names([])),
        ).drop(
            *[f"__tgt_key_{key}" for key in keys],
            *[f"__tgt_{col}" for col in payload_cols],
        )
    )


def build_columns_to_update(
    df: DataFrame,
    keys: Sequence[str],
    lineage_cols: Sequence[str],
    extra_ignore: Optional[Sequence[str]] = None,
    target_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Attach ``__columns_to_update`` using CDF preimages, else a target snapshot.

    When neither comparison source is available, every row writes payload plus
    lineage columns (same as not using this feature).
    """
    lineage_cols = _unique(lineage_cols)
    extra_ignore = _unique(extra_ignore or [])
    payload_cols = payload_columns(df.columns, keys, lineage_cols, extra_ignore)
    write_cols = _unique([*payload_cols, *lineage_cols])

    if has_cdf_preimage_columns(df.columns):
        return _with_cdf_preimage_columns_to_update(
            df,
            keys=keys,
            lineage_cols=lineage_cols,
            payload_cols=payload_cols,
            change_col=change_type_column(df.columns),
        )

    if target_df is not None:
        return _with_target_columns_to_update(
            df,
            target_df=target_df,
            keys=keys,
            lineage_cols=lineage_cols,
            payload_cols=payload_cols,
        )

    return df.withColumn(COLUMNS_TO_UPDATE_COLUMN, _array_of_names(write_cols))
