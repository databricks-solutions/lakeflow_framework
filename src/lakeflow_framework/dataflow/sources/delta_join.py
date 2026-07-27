from dataclasses import dataclass
from typing import List
import re

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from .base import BaseSource, ReadConfig
from .delta import SourceDelta


@dataclass(kw_only=True)
class DeltaTable(SourceDelta):
    """
    Source details for Delta tables that need to be joined in stream-stream or stream-static scenarios.

    Attributes:
        alias (str): Table alias.
        joinMode (str): The type of join if streaming ["stream", "static"].
    """
    alias: str
    joinMode: str


@dataclass
class DeltaJoin:
    """
    Join details of Delta tables that need to be joined.

    Attributes:
        joinType (str): Type of join e.g. ["left", "inner"].
        condition (str): Condition expressed in SQL syntax e.g. "a.id = b.id".

    Methods:
        get_table_aliases() -> List[str]: Get table aliases from the join condition.
    """
    joinType: str
    condition: str

    def get_table_aliases(self) -> List[str]:
        """Get table aliases from the join condition."""
        pattern = r'(\b\w+)\.'  # Matches word characters before a dot
        matches = re.findall(pattern, self.condition)

        # not using set to de-dupe as it disrupts the order of the aliases
        aliases = []
        for match in matches:
            if match not in aliases:  # Add alias if not already in the list
                aliases.append(match)
        return aliases


@dataclass(kw_only=True)
class SourceDeltaJoin(BaseSource):
    """
    Source details for Delta tables that need to be joined in stream-stream or stream-static scenarios.

    Attributes:
        sources (list): List of delta table sources.
        joins (list): List of joins.
        selectExp (List[str], optional): List of select expressions.
        whereClause (List[str], optional): List of WHERE clauses.

    Methods:
        get_sources() -> List[SourceDeltaTable]: Get source details for Delta tables.
        get_joins() -> List[SourceDeltaJoin]: Get join details for Delta tables.
    """
    sources: List
    joins: List

    def get_sources(self) -> List[DeltaTable]:
        """Get source details for Delta tables."""
        return [DeltaTable(**item) for item in self.sources]

    def get_joins(self) -> List[DeltaJoin]:
        """Get join details for Delta tables."""
        return [DeltaJoin(**item) for item in self.joins]

    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        """Ingest data from a Delta table based on configured options and return a DataFrame."""
        dfs_to_join = {}
        for source in self.get_sources():
            read_config.mode = "batch" if source.joinMode == "static" else source.joinMode
            df = source.read_source(read_config)
            dfs_to_join[source.alias] = df.alias(source.alias)

        final_df = None
        used_aliases = set()
        for join in self.get_joins():
            aliases = join.get_table_aliases()

            missing_aliases = [alias for alias in aliases if alias not in dfs_to_join]
            if missing_aliases:
                raise ValueError(f"Missing DataFrames for aliases: {missing_aliases}")

            # Determine DataFrames to join; start with the first two if final_df is not initialized
            if final_df is None:
                df1, df2 = (dfs_to_join[aliases[0]], dfs_to_join[aliases[1]])
                final_df = df1.join(df2, on=F.expr(join.condition), how=join.joinType)
                used_aliases.update(aliases)
            else:
                # Join each remaining alias that hasn't been used yet
                for alias in aliases:
                    if alias not in used_aliases:
                        df = dfs_to_join[alias]
                        final_df = final_df.join(df, on=F.expr(join.condition), how=join.joinType)
                        used_aliases.add(alias)

        if final_df is None:
            raise ValueError("No joins could be performed. Please check the join configuration.")
            
        return final_df
