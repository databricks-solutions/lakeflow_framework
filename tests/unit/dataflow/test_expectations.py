"""Unit tests for DataQualityExpectations."""

from __future__ import annotations

from lakeflow_framework.dataflow.expectations import DataQualityExpectations


class TestDataQualityExpectations:
    def test_all_rules_merges_rule_groups(self):
        expectations = DataQualityExpectations(
            expectationsJson={},
            expectRules={"a": "a IS NOT NULL"},
            expectOrDropRules={"b": "b > 0"},
            expectOrFailRules={"c": "c = 'ok'"},
        )
        assert expectations.all_rules == {
            "a": "a IS NOT NULL",
            "b": "b > 0",
            "c": "c = 'ok'",
        }

    def test_get_expectations_splits_by_sdp_type(self):
        expectations = DataQualityExpectations(
            expectationsJson={},
            expectRules={"a": "a IS NOT NULL"},
            expectOrDropRules={"b": "b > 0"},
            expectOrFailRules={"c": "c = 'ok'"},
        )
        assert expectations.get_expectations() == {
            "expect_all": {"a": "a IS NOT NULL"},
            "expect_all_or_drop": {"b": "b > 0"},
            "expect_all_or_fail": {"c": "c = 'ok'"},
        }

    def test_get_expectations_uses_empty_dicts_for_missing_groups(self):
        expectations = DataQualityExpectations(
            expectationsJson={},
            expectRules={"a": "a IS NOT NULL"},
        )
        result = expectations.get_expectations()
        assert result["expect_all_or_drop"] == {}
        assert result["expect_all_or_fail"] == {}

    def test_get_expectations_as_expect_all_flattens_rules(self):
        expectations = DataQualityExpectations(
            expectationsJson={},
            expectRules={"a": "a IS NOT NULL"},
            expectOrDropRules={"b": "b > 0"},
        )
        assert expectations.get_expectations_as_expect_all() == {
            "expect_all": {
                "a": "a IS NOT NULL",
                "b": "b > 0",
            },
            "expect_all_or_drop": {},
            "expect_all_or_fail": {},
        }

    def test_get_expectations_as_expect_all_empty_when_no_rules(self):
        expectations = DataQualityExpectations(expectationsJson={})
        assert expectations.get_expectations_as_expect_all() == {
            "expect_all": {},
            "expect_all_or_drop": {},
            "expect_all_or_fail": {},
        }
