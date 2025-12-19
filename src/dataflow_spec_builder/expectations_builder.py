import logging
import os
from typing import Dict

import utility

from constants import SupportedSpecFormat
from dataflow.expectations import DataQualityExpectations, ExpectationType


class DataQualityExpectationBuilder:
    """
    Builds data quality expectations from JSON/YAML files using a validation schema.
    
    Attributes:
        logger (logging.Logger): Logger instance for logging messages.
        validator (JSONValidator): JSON validator object.
        spec_file_format (str): Specification file format (json or yaml).
    
    Methods:
        get_expectation_rules(expectations: Dict, expectation_type: str, tag: str = None) -> Dict:
            Retrieves expectation rules of a specific type from expectations.
        get_expectations(path: str) -> DataQualityExpectations:
            Retrieves data quality expectations from JSON/YAML files.
    """

    def __init__(
        self,
        logger: logging.Logger,
        json_validation_schema_path: str,
        spec_file_format: str = "json"
    ):
        """Initialize the DataQualityExpectationBuilder.
        
        Args:
            logger: Logger instance for logging messages.
            json_validation_schema_path: Path to the JSON validation schema.
            spec_file_format: Specification file format (json or yaml). Defaults to "json".
            
        Raises:
            ValueError: If spec_file_format is not a valid format.
        """
        self.logger = logger
        self.validator = utility.JSONValidator(json_validation_schema_path)
        self.spec_file_format = spec_file_format.lower()

        valid_formats = [fmt.value for fmt in SupportedSpecFormat]
        if self.spec_file_format not in valid_formats:
            raise ValueError(
                f"Invalid spec file format: '{self.spec_file_format}'. "
                f"Valid formats are: {valid_formats}"
            )

    def get_expectation_rules(self, expectations: Dict, expectation_type: str, tag: str = None) -> Dict:
        """Retrieve expectation rules of a specific type from expectations.
        
        Args:
            expectations: Dictionary of expectations data.
            expectation_type: Type of expectation to retrieve (EXPECT, EXPECT_OR_DROP, EXPECT_OR_FAIL).
            tag: Optional tag to filter expectations.
            
        Returns:
            Dictionary of expectation rules mapped by name to constraint.
        """
        rules = None
        if expectation_type in expectations:
            rules = {}
            for expectation in expectations[expectation_type]:
                expectation_enabled = bool(expectation.get('enabled', True))
                if expectation_enabled:
                    if tag:
                        if expectation["tag"] == tag:
                            rules[expectation["name"]] = expectation["constraint"]
                    else:
                        rules[expectation["name"]] = expectation["constraint"]
        return rules

    def _load_single_file(self, file_path: str) -> Dict:
        """Load and validate a single expectations file."""
        self.logger.info("Loading expectations from file: %s", file_path)
        
        file_data = utility.load_config_file_auto(file_path, fail_on_not_exists=False)
        
        if not file_data:
            raise ValueError(f"Expectations file not found: {file_path}")
        
        # Validate file data
        errors = self.validator.validate(file_data)
        if errors:
            raise ValueError(f"Invalid expectations file '{file_path}': {errors}")
        
        return file_data

    def _load_directory(self, directory_path: str) -> Dict:
        """Load and validate expectations files from a directory."""
        self.logger.info("Loading expectations from directory: %s", directory_path)
        
        # Get appropriate file suffix based on spec format
        file_suffix = utility.get_format_suffixes(self.spec_file_format, "expectations")
        
        # Load all expectations files from directory
        file_data = utility.load_config_files(
            path=directory_path,
            file_format=self.spec_file_format,
            file_suffix=file_suffix,
            recursive=False
        )
        
        if not file_data:
            self.logger.warning("No expectations files found in directory: %s", directory_path)
            return {}
        
        # Validate all files and merge data
        validation_errors = {}
        merged_expectations = {}
        
        for file_path, data in file_data.items():
            errors = self.validator.validate(data)
            if errors:
                validation_errors[file_path] = errors
            else:
                merged_expectations.update(data)
        
        if validation_errors:
            raise ValueError(f"Invalid expectations files found: {validation_errors}")
        
        return merged_expectations

    def get_expectations(self, path: str) -> DataQualityExpectations:
        """Retrieve data quality expectations from JSON/YAML files."""
        if not path or path.strip() == "":
            raise ValueError("Expectations file path is not set")

        self.logger.info("Getting expectations from: %s", path)

        # Determine if path is a file or directory
        if os.path.isfile(path):
            expectations = self._load_single_file(path)
        elif os.path.isdir(path):
            expectations = self._load_directory(path)
        else:
            raise ValueError(f"Path does not exist: {path}")

        self.logger.debug("Loaded expectations: %s", expectations)
        
        return DataQualityExpectations(
            expectationsJson=expectations,
            expectRules=self.get_expectation_rules(expectations, ExpectationType.EXPECT),
            expectOrDropRules=self.get_expectation_rules(expectations, ExpectationType.EXPECT_OR_DROP),
            expectOrFailRules=self.get_expectation_rules(expectations, ExpectationType.EXPECT_OR_FAIL)
        )
