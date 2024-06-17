import os
import json
import jsonschema as js
from functools import reduce
import logging
import sys

from pyspark.sql import DataFrame
from pyspark.sql.types import StructType


class JSONValidator:
    def __init__(self, schema_path):

        try:
            with open(schema_path, "r") as schema_file:
                self.schema = json.load(schema_file)
        except:
            raise ValueError(f"JSON Schema not found: {schema_path}")

        # Resolve references
        self.base_uri = "file://" + os.path.abspath(os.path.dirname(schema_path)) + "/"
        self.resolver = js.RefResolver(base_uri=self.base_uri, referrer=self.schema)
        self.validator = js.Draft7Validator(self.schema, resolver=self.resolver)

    def validate(self, json_data):
        return list(self.validator.iter_errors(json_data))


def add_struct_field(struct: StructType, column: dict):
    return struct.jsonValue()["fields"].append(column)


def drop_columns(df: DataFrame, columns_to_drop: list) -> DataFrame:
    drop_column_list = []
    for column in columns_to_drop:
        if column in df.columns:
            drop_column_list.append(column)
    if len(drop_column_list) > 1:
        df = df.drop(*drop_column_list)
    return df


def get_json_from_file(file_path: str):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(f"Error loading JSON file '{file_path}': {e}")


def get_json_from_files(
    path: str, file_suffix: str = ".json", recursive: bool = False
) -> list:
    """
    Load json data from files with a specific suffix, recursively as an option.
    """

    data = {}
    if path and path.strip() and os.path.exists(path):
        if recursive:
            for root, _, filenames in os.walk(path):
                for filename in filenames:
                    if filename.endswith(file_suffix):
                        file_path = os.path.join(root, filename)
                        data[filename] = get_json_from_file(file_path)
        else:                        
            for filename in os.listdir(path):
                if filename.endswith(file_suffix):
                    file_path = os.path.join(path, filename)
                    data[filename] = get_json_from_file(file_path)
    else:
        raise ValueError(f"Path does not exist: {path}")

    return data


def list_subpaths(path):
    return [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]


def merge_dicts(*dicts):
    return reduce(lambda a, b: {**a, **b} if b is not None else a, dicts, {})

def set_logger(logger_name: str, log_level: str = "INFO"):
    logger = logging.getLogger(logger_name)
    log_level = getattr(logging, log_level, logging.INFO)
    logger.setLevel(log_level)
    console_output_handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(console_output_handler)
    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    #handler.setFormatter(formatter)
    return logger