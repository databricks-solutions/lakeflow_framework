# Validation helper functions for Lakeflow Framework sample pipelines
from pyspark.sql import DataFrame, SparkSession
from typing import List, Dict, Any, Optional


class ValidationResult:
    """Represents the result of a validation check."""
    
    def __init__(self, test_name: str, passed: bool, message: str, details: Optional[Dict] = None):
        self.test_name = test_name
        self.passed = passed
        self.message = message
        self.details = details or {}
    
    def __repr__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status}: {self.test_name} - {self.message}"


class ValidationRunner:
    """Runs validation checks and tracks results."""
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.results: List[ValidationResult] = []
    
    def validate_row_count(self, table_name: str, expected_count: int, description: str = "") -> ValidationResult:
        """Validate that a table has the expected row count."""
        try:
            actual_count = self.spark.table(table_name).count()
            passed = actual_count == expected_count
            message = f"Expected {expected_count} rows, got {actual_count}"
            if description:
                message = f"{description}: {message}"
            result = ValidationResult(f"Row Count: {table_name}", passed, message, {"expected": expected_count, "actual": actual_count})
        except Exception as e:
            result = ValidationResult(f"Row Count: {table_name}", False, f"Error: {str(e)}")
        self.results.append(result)
        print(result)
        return result

    def validate_min_row_count(self, table_name: str, min_count: int, description: str = "") -> ValidationResult:
        """Validate that a table has at least the minimum row count."""
        try:
            actual_count = self.spark.table(table_name).count()
            passed = actual_count >= min_count
            message = f"Expected at least {min_count} rows, got {actual_count}"
            if description:
                message = f"{description}: {message}"
            result = ValidationResult(f"Min Row Count: {table_name}", passed, message, {"min_expected": min_count, "actual": actual_count})
        except Exception as e:
            result = ValidationResult(f"Min Row Count: {table_name}", False, f"Error: {str(e)}")
        self.results.append(result)
        print(result)
        return result

    def validate_active_scd2_count(self, table_name: str, expected_count: int, end_column: str = "__END_AT") -> ValidationResult:
        """Validate count of active (current) SCD2 records."""
        try:
            df = self.spark.table(table_name)
            actual_count = df.filter(f"{end_column} IS NULL").count()
            passed = actual_count == expected_count
            message = f"Expected {expected_count} active records, got {actual_count}"
            result = ValidationResult(f"Active SCD2 Records: {table_name}", passed, message, {"expected": expected_count, "actual": actual_count})
        except Exception as e:
            result = ValidationResult(f"Active SCD2 Records: {table_name}", False, f"Error: {str(e)}")
        self.results.append(result)
        print(result)
        return result

    def validate_closed_scd2_count(self, table_name: str, expected_count: int, end_column: str = "__END_AT") -> ValidationResult:
        """Validate count of closed (historical) SCD2 records."""
        try:
            df = self.spark.table(table_name)
            actual_count = df.filter(f"{end_column} IS NOT NULL").count()
            passed = actual_count == expected_count
            message = f"Expected {expected_count} closed records, got {actual_count}"
            result = ValidationResult(f"Closed SCD2 Records: {table_name}", passed, message, {"expected": expected_count, "actual": actual_count})
        except Exception as e:
            result = ValidationResult(f"Closed SCD2 Records: {table_name}", False, f"Error: {str(e)}")
        self.results.append(result)
        print(result)
        return result

    def validate_min_closed_scd2_count(self, table_name: str, min_count: int, end_column: str = "__END_AT") -> ValidationResult:
        """Validate that at least min_count closed SCD2 records exist."""
        try:
            df = self.spark.table(table_name)
            actual_count = df.filter(f"{end_column} IS NOT NULL").count()
            passed = actual_count >= min_count
            message = f"Expected at least {min_count} closed records, got {actual_count}"
            result = ValidationResult(f"Min Closed SCD2 Records: {table_name}", passed, message, {"min_expected": min_count, "actual": actual_count})
        except Exception as e:
            result = ValidationResult(f"Min Closed SCD2 Records: {table_name}", False, f"Error: {str(e)}")
        self.results.append(result)
        print(result)
        return result

    def validate_values_exist(self, table_name: str, column: str, expected_values: List[Any], description: str = "") -> ValidationResult:
        """Validate that specific values exist in a column."""
        try:
            df = self.spark.table(table_name)
            actual_values = [row[column] for row in df.select(column).distinct().collect()]
            missing = [v for v in expected_values if v not in actual_values]
            passed = len(missing) == 0
            message = f"All expected values found" if passed else f"Missing values: {missing}"
            if description:
                message = f"{description}: {message}"
            result = ValidationResult(f"Values Exist: {table_name}.{column}", passed, message, {"expected": expected_values, "missing": missing})
        except Exception as e:
            result = ValidationResult(f"Values Exist: {table_name}.{column}", False, f"Error: {str(e)}")
        self.results.append(result)
        print(result)
        return result

    def validate_column_value(self, table_name: str, filter_condition: str, column: str, expected_value: Any, description: str = "") -> ValidationResult:
        """Validate a specific column value for filtered rows."""
        try:
            df = self.spark.table(table_name)
            filtered = df.filter(filter_condition)
            if filtered.count() == 0:
                result = ValidationResult(f"Column Value: {table_name}", False, f"No rows found for filter: {filter_condition}")
            else:
                actual_value = filtered.select(column).first()[0]
                passed = actual_value == expected_value
                message = f"Expected '{expected_value}', got '{actual_value}'"
                if description:
                    message = f"{description}: {message}"
                result = ValidationResult(f"Column Value: {table_name}.{column}", passed, message)
        except Exception as e:
            result = ValidationResult(f"Column Value: {table_name}.{column}", False, f"Error: {str(e)}")
        self.results.append(result)
        print(result)
        return result

    def validate_quarantine_count(self, quarantine_table: str, expected_count: int) -> ValidationResult:
        """Validate quarantine table row count."""
        return self.validate_row_count(quarantine_table, expected_count, "Quarantine records")

    def _get_column_paths_to_check(self, df: "DataFrame", column_spec: str) -> List[str]:
        """
        Resolve a column specification to a list of column paths to check.
        
        Supports:
        - Simple column: "CUSTOMER_ID" -> ["CUSTOMER_ID"]
        - Nested column with dot notation: "meta_load_details.record_insert_timestamp" -> ["meta_load_details.record_insert_timestamp"]
        - All fields in a struct: "meta_load_details.*" -> ["meta_load_details.field1", "meta_load_details.field2", ...]
        
        Args:
            df: The DataFrame to inspect schema from
            column_spec: The column specification string
            
        Returns:
            List of fully qualified column paths to check
        """
        from pyspark.sql.types import StructType
        
        # Handle wildcard for struct expansion
        if column_spec.endswith(".*"):
            struct_name = column_spec[:-2]  # Remove .*
            
            # Navigate to the struct in the schema
            schema = df.schema
            parts = struct_name.split(".")
            current_type = None
            
            for i, part in enumerate(parts):
                field = schema[part] if i == 0 else current_type[part]
                current_type = field.dataType
            
            if not isinstance(current_type, StructType):
                raise ValueError(f"Column '{struct_name}' is not a struct type, cannot use wildcard")
            
            return [f"{struct_name}.{field.name}" for field in current_type.fields]
        
        # Handle simple or dot-notation column
        return [column_spec]

    def validate_column_not_null(
        self, 
        table_name: str, 
        columns: "str | List[str]", 
        description: str = ""
    ) -> ValidationResult:
        """
        Validate that column(s) do not contain null values.
        
        This is a generic validation that works with:
        - Simple columns: "CUSTOMER_ID"
        - Nested columns with dot notation: "meta_load_details.record_insert_timestamp"
        - All fields in a struct using wildcard: "meta_load_details.*"
        - Multiple columns as a list: ["col1", "meta_load_details.field1", "nested.*"]
        
        Args:
            table_name: The fully qualified table name
            columns: Column specification - can be:
                - A single column name: "CUSTOMER_ID"
                - A nested column path: "meta_load_details.record_insert_timestamp"
                - A struct with wildcard to check all fields: "meta_load_details.*"
                - A list of any combination of the above
            description: Optional description for the validation
        
        Returns:
            ValidationResult indicating if all specified columns have non-null values
            
        Examples:
            # Check a single column
            v.validate_column_not_null("schema.table", "CUSTOMER_ID")
            
            # Check a nested field
            v.validate_column_not_null("schema.table", "meta_load_details.record_insert_timestamp")
            
            # Check all fields in a struct
            v.validate_column_not_null("schema.table", "meta_load_details.*")
            
            # Check multiple columns at once
            v.validate_column_not_null("schema.table", ["CUSTOMER_ID", "meta_load_details.*"])
        """
        try:
            from pyspark.sql import functions as F
            
            df = self.spark.table(table_name)
            
            # Normalize columns to a list
            if isinstance(columns, str):
                column_specs = [columns]
            else:
                column_specs = columns
            
            # Resolve all column specs to actual column paths
            all_column_paths = []
            for spec in column_specs:
                try:
                    paths = self._get_column_paths_to_check(df, spec)
                    all_column_paths.extend(paths)
                except Exception as e:
                    result = ValidationResult(
                        f"Column Not Null: {table_name}",
                        False,
                        f"Error resolving column spec '{spec}': {str(e)}"
                    )
                    self.results.append(result)
                    print(result)
                    return result
            
            # Check each column for null values
            null_columns = []
            null_counts = {}
            
            for col_path in all_column_paths:
                null_count = df.filter(F.col(col_path).isNull()).count()
                if null_count > 0:
                    null_columns.append(col_path)
                    null_counts[col_path] = null_count
            
            passed = len(null_columns) == 0
            
            if passed:
                message = f"All {len(all_column_paths)} column(s) have non-null values"
            else:
                null_details = ", ".join([f"{c}({null_counts[c]} nulls)" for c in null_columns])
                message = f"Found null values in: {null_details}"
            
            if description:
                message = f"{description}: {message}"
            
            # Create a display name for the columns being checked
            col_display = ", ".join(column_specs) if len(column_specs) <= 3 else f"{len(column_specs)} columns"
            
            result = ValidationResult(
                f"Column Not Null: {table_name} [{col_display}]",
                passed,
                message,
                {"columns_checked": all_column_paths, "null_columns": null_columns, "null_counts": null_counts}
            )
        except Exception as e:
            col_display = columns if isinstance(columns, str) else ", ".join(columns[:3])
            result = ValidationResult(
                f"Column Not Null: {table_name} [{col_display}]",
                False,
                f"Error: {str(e)}"
            )
        
        self.results.append(result)
        print(result)
        return result

    def print_summary(self):
        """Print validation summary and raise AssertionError if any tests failed."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        
        print("\n" + "="*60)
        print(f"VALIDATION SUMMARY: {passed}/{total} tests passed")
        print("="*60)
        
        if failed > 0:
            print("\nFailed Tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.test_name}: {r.message}")
            raise AssertionError(f"{failed} validation(s) failed!")
        else:
            print("\n✅ All validations passed!")

