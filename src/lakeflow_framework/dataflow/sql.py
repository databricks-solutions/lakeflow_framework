from dataclasses import dataclass


@dataclass
class SqlMixin:
    """
    SQL Mixin class that provides SQL path and statement handling.

    Attributes:
        sqlPath (str): Path to the SQL file.
        sqlStatement (str): SQL statement to execute.

    Properties:
        rawSql (str): Lazily loaded raw SQL content from the SQL file.
    """
    sqlPath: str = None
    sqlStatement: str = None
    _sql: str = None

    @property
    def rawSql(self) -> str:
        """
        Returns the SQL content from either sqlStatement or sqlPath.
        If sqlStatement is provided, it is returned directly.
        Otherwise, the content from the file at sqlPath is loaded lazily.
        """
        if self.sqlStatement:
            return self.sqlStatement
        if self.sqlPath and self.sqlPath.strip() != "":
            if self._sql is None:
                try:
                    with open(self.sqlPath, "r", encoding="utf-8") as f:
                        sql = f.read()
                        if sql is None or sql.strip() == "":
                            raise RuntimeError(f"Sql file empty or error: {self.sqlPath}")
                        self._sql = sql
                except FileNotFoundError as e:
                    raise FileNotFoundError(f"Error loading sql file: {self.sqlPath} - {e}") from e
        else:
            raise ValueError("Sql path and sql statement are None or empty.")
        return self._sql

