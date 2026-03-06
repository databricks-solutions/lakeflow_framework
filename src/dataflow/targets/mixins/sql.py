from __future__ import annotations

from typing import Optional

from dataflow.field import Field
from dataflow.target import TargetMeta


class SqlMixin(metaclass=TargetMeta):
    """
    Mixin that adds SQL-query support to a :class:`~dataflow.target.Target`
    subclass.

    Spec fields (``targetDetails`` keys)
    ------------------------------------
    * ``sqlPath``      — path to a ``.sql`` file containing the query
    * ``sqlStatement`` — inline SQL string

    Properties
    ----------
    rawSql:
        Returns the SQL content.  Priority: ``sqlStatement`` > file at
        ``sqlPath``.  The file is read lazily and cached.  Returns ``None``
        if neither field is set.
    """

    sqlPath: Optional[str] = Field(required=False)
    sqlStatement: Optional[str] = Field(required=False)

    def __post_init__(self) -> None:
        # Private cache — plain instance attribute, not a Field descriptor.
        self._sql_cache: Optional[str] = None
        if hasattr(super(), "__post_init__"):
            super().__post_init__()

    @property
    def rawSql(self) -> Optional[str]:
        """SQL content from ``sqlStatement`` (inline) or ``sqlPath`` (file).

        The file is read once and cached.  Returns ``None`` if neither field
        is set.
        """
        if self.sqlStatement:
            return self.sqlStatement
        if self.sqlPath and self.sqlPath.strip():
            if self._sql_cache is None:
                try:
                    with open(self.sqlPath, "r", encoding="utf-8") as fh:
                        sql = fh.read()
                    if not sql or not sql.strip():
                        raise RuntimeError(
                            f"SQL file is empty: {self.sqlPath!r}"
                        )
                    self._sql_cache = sql
                except FileNotFoundError as exc:
                    raise FileNotFoundError(
                        f"SQL file not found: {self.sqlPath!r}"
                    ) from exc
            return self._sql_cache
        return None
