"""Unit tests for shared DDL schema parsing helpers (#132, #133, #139)."""

from __future__ import annotations

from lakeflow_framework.dataflow._ddl_parsing import (
    ddl_column_name,
    parse_ddl_text,
    struct_from_ddl_column_lines,
)


class TestParseDdlText:
    def test_drops_blank_lines_and_comments(self):
        """Blank lines must not leak into DDL (#139)."""
        text = "`a` STRING,\n\n`b` INT\n-- ignored\n"
        columns, constraints = parse_ddl_text(text)
        assert columns == ["`a` STRING", "`b` INT"]
        assert constraints == []

    def test_separates_constraints(self):
        text = "id INT,\nname STRING,\nCONSTRAINT pk PRIMARY KEY (id)\n"
        columns, constraints = parse_ddl_text(text)
        assert columns == ["id INT", "name STRING"]
        assert constraints == ["CONSTRAINT pk PRIMARY KEY (id)"]


class TestDdlColumnName:
    def test_plain_and_backticked_names(self):
        assert ddl_column_name("id INT") == "id"
        assert ddl_column_name("`customer_id` STRING") == "customer_id"
        assert ddl_column_name("extra string") == "extra"


class TestStructFromDdlColumnLines:
    def test_builds_structtype(self):
        struct = struct_from_ddl_column_lines(["id INT", "name STRING"])
        assert struct is not None
        assert struct.fieldNames() == ["id", "name"]

    def test_empty_returns_none(self):
        assert struct_from_ddl_column_lines([]) is None
