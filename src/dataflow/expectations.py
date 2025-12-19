from dataclasses import dataclass, field
from typing import Dict

import utility


@dataclass(frozen=True)
class ExpectationType():
    """Constants for different types of data quality expectations."""
    EXPECT: str = "expect"
    EXPECT_OR_DROP: str = "expect_or_drop"
    EXPECT_OR_FAIL: str = "expect_or_fail"


@dataclass
class DataQualityExpectations:
    """
    Dataclass representing data quality expectations.

    Attributes:
        expectationsJson (Dict): JSON data containing the raw expectations.
        expectRules (Dict, optional): Rules for 'expect' expectations.
        expectOrDropRules (Dict, optional): Rules for 'expect_or_drop' expectations.
        expectOrFailRules (Dict, optional): Rules for 'expect_or_fail' expectations.

    Properties:
        allRules (Dict): Combines all expectation rules into a single dictionary.
    """
    expectationsJson: Dict
    expectRules: Dict = field(default_factory=dict)
    expectOrDropRules: Dict = field(default_factory=dict)
    expectOrFailRules: Dict = field(default_factory=dict)
    _all_rules: Dict = field(default_factory=dict)

    @property
    def all_rules(self) -> Dict:
        """
        Combines all expectation rules into a single dictionary.

        Returns:
            Dict: A dictionary containing all expectation rules.
        """
        return utility.merge_dicts(
            self.expectRules,
            self.expectOrDropRules,
            self.expectOrFailRules)

    def get_expectations(self) -> Dict:
        """
        Get expectations in format expected by SDP create table API's.

        Returns:
            Dict: A dictionary containing the expectation rules as expected by SDP create table API's.
        """
        return {
            "expect_all": self.expectRules if self.expectRules else {},
            "expect_all_or_drop": self.expectOrDropRules if self.expectOrDropRules else {},
            "expect_all_or_fail": self.expectOrFailRules if self.expectOrFailRules else {}
        }

    def get_expectations_as_expect_all(self) -> Dict:
        """
        Get expectations in format expected by SDP create table API's.
        Return all expectations as expect_all.

        Returns:
            Dict: A dictionary containing the expectation rules as expected by SDP create table API's.
        """
        return {
            "expect_all": self.all_rules if self.all_rules else {},
            "expect_all_or_drop": {},
            "expect_all_or_fail": {}
        }
