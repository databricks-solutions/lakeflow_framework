import concurrent.futures
import importlib.util
import inspect
from functools import reduce
import logging
import os
import sys
from typing import Callable, Dict, List

import json
import jsonschema as js
import yaml

from pyspark.sql import DataFrame
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType

from constants import (
    SupportedSpecFormat,
    PipelineBundleSuffixesJson,
    PipelineBundleSuffixesYaml
)


def get_format_suffixes(file_format: str, suffix_type: str) -> list:
    """Get file suffixes based on file format and suffix type.
    
    This is a centralized utility to retrieve the appropriate file suffixes
    for different configuration and specification files based on the format
    (JSON or YAML) and the type of file (substitutions, secrets, specs, etc.)."""
    suffix_map = {
        SupportedSpecFormat.JSON.value: {
            "substitutions": PipelineBundleSuffixesJson.SUBSTITUTIONS_FILE_SUFFIX,
            "secrets": PipelineBundleSuffixesJson.SECRETS_FILE_SUFFIX,
            "main_spec": PipelineBundleSuffixesJson.MAIN_SPEC_FILE_SUFFIX,
            "flow_group": PipelineBundleSuffixesJson.FLOW_GROUP_FILE_SUFFIX,
            "expectations": PipelineBundleSuffixesJson.EXPECTATIONS_FILE_SUFFIX
        },
        SupportedSpecFormat.YAML.value: {
            "substitutions": PipelineBundleSuffixesYaml.SUBSTITUTIONS_FILE_SUFFIX,
            "secrets": PipelineBundleSuffixesYaml.SECRETS_FILE_SUFFIX,
            "main_spec": PipelineBundleSuffixesYaml.MAIN_SPEC_FILE_SUFFIX,
            "flow_group": PipelineBundleSuffixesYaml.FLOW_GROUP_FILE_SUFFIX,
            "expectations": PipelineBundleSuffixesYaml.EXPECTATIONS_FILE_SUFFIX
        }
    }
    
    if file_format not in suffix_map:
        valid_formats = list(suffix_map.keys())
        raise ValueError(
            f"Invalid file format: '{file_format}'. "
            f"Valid formats are: {valid_formats}"
        )
    
    if suffix_type not in suffix_map[file_format]:
        valid_types = list(suffix_map[file_format].keys())
        raise ValueError(
            f"Invalid suffix type: '{suffix_type}'. "
            f"Valid types are: {valid_types}"
        )
    
    result = suffix_map[file_format][suffix_type]
    
    # Always return a list for consistency
    if isinstance(result, list):
        return result
    elif isinstance(result, (tuple, set)):
        return list(result)
    elif isinstance(result, str):
        return [result]
    else:
        raise TypeError(
            f"Invalid suffix type for '{suffix_type}': expected str, tuple, list, or set, "
            f"but got {type(result).__name__}"
        )
        
class JSONValidator:
    """
    A JSON schema validator class.

    Attributes:
        schema (dict): The JSON schema loaded from a file.
        base_uri (str): The base URI for resolving schema references.
        resolver (RefResolver): The JSON schema resolver.
        validator (Draft7Validator): The JSON schema validator.

    Methods:
        validate(json_data: Dict) -> List:
            Validates the provided JSON data against the loaded schema and returns a list of validation errors.
    """

    def __init__(self, schema_path: str):
        try:
            with open(schema_path, "r", encoding="utf-8") as schema_file:
                self.schema = json.load(schema_file)
        except Exception as e:
            raise ValueError(f"JSON Schema not found: {schema_path}") from e

        # Resolve references
        self.base_uri = "file://" + os.path.abspath(os.path.dirname(schema_path)) + "/"
        self.resolver = js.RefResolver(base_uri=self.base_uri, referrer=self.schema)
        self.validator = js.Draft7Validator(self.schema, resolver=self.resolver)

    def validate(self, json_data: Dict) -> List:
        """Validate the provided JSON data against the loaded schema and returns a list of validation errors."""
        return list(self.validator.iter_errors(json_data))


def add_struct_field(struct: StructType, column: Dict):
    """Add a field to a StructType schema."""  
    return struct.jsonValue()["fields"].append(column)


def drop_columns(df: DataFrame, columns_to_drop: List) -> DataFrame:
    """Drop columns from a DataFrame."""
    drop_column_list = []
    for column in columns_to_drop:
        if column in df.columns:
            drop_column_list.append(column)
    if drop_column_list:
        df = df.drop(*drop_column_list)
    return df


def load_config_file(file_path: str, file_format: str = "json", fail_on_not_exists: bool = True) -> Dict:
    """Load JSON or YAML data from a file."""
    if not os.path.exists(file_path):
        if fail_on_not_exists:
            raise ValueError(f"Path does not exist: {file_path}")
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            if file_format == "json":
                return json.load(file)
            elif file_format == "yaml":
                return yaml.safe_load(file)
            else:
                raise ValueError(f"Invalid file format: {file_format}. Only 'json' and 'yaml' are supported.")
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Error loading JSON file '{file_path}': {e.msg} at line {e.lineno}, column {e.colno}"
            ) from e
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error loading YAML file '{file_path}': {e}")


def load_config_files(
    path: str, 
    file_format: str = "json",
    file_suffix: str | List[str] = None,
    recursive: bool = False
) -> Dict:
    """Load configuration data from files with a specific suffix."""
    if file_suffix is None:
        file_suffix = f".{file_format}"
    
    data = {}
    if not path or path.strip() == "" or not os.path.exists(path):
        raise ValueError(f"Path does not exist: {path}")
    
    file_suffix_list = [file_suffix] if isinstance(file_suffix, str) else file_suffix
    
    if recursive:
        for root, _, filenames in os.walk(path):
            for filename in filenames:
                if any(filename.endswith(suffix) for suffix in file_suffix_list):
                    file_path = os.path.join(root, filename)
                    data[file_path] = load_config_file(file_path, file_format)
    else:
        for filename in os.listdir(path):
            if any(filename.endswith(suffix) for suffix in file_suffix_list):
                file_path = os.path.join(path, filename)
                data[file_path] = load_config_file(file_path, file_format)
    
    return data


def load_config_file_auto(file_path: str, fail_on_not_exists: bool = True) -> Dict:
    """Load JSON or YAML data from a file with automatic format detection.
    
    The file format is automatically detected based on the file extension:
    - .json -> JSON format
    - .yaml, .yml -> YAML format
    
    Args:
        file_path: Path to the configuration file
        fail_on_not_exists: Whether to raise an error if file doesn't exist
        
    Returns:
        Dict containing the loaded configuration data
        
    Raises:
        ValueError: If file extension is not recognized or path doesn't exist
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.json':
        file_format = 'json'
    elif file_ext in ('.yaml', '.yml'):
        file_format = 'yaml'
    else:
        raise ValueError(
            f"Unable to detect file format from extension '{file_ext}'. "
            f"Supported extensions: .json, .yaml, .yml"
        )
    
    return load_config_file(file_path, file_format, fail_on_not_exists)


# TODO: Legacy wrapper around load_config_file. Remove this in a future release.
def get_json_from_file(file_path: str, fail_on_not_exists: bool = True) -> Dict:
    """Load JSON data from a file."""
    return load_config_file(file_path, "json", fail_on_not_exists)


# TODO: Legacy wrapper around load_config_files. Remove this in a future release.
def get_json_from_files(path: str, file_suffix: str | List[str] = ".json", recursive: bool = False) -> Dict:
    """Load JSON data from files that have a specific suffix."""
    return load_config_files(path, "json", file_suffix, recursive)


# TODO: Legacy wrapper around load_config_file. Remove this in a future release.
def get_yaml_from_file(file_path: str, fail_on_not_exists: bool = True) -> Dict:
    """Load YAML data from a file."""
    return load_config_file(file_path, "yaml", fail_on_not_exists)


# TODO: Legacy wrapper around load_config_files. Remove this in a future release.
def get_yaml_from_files(path: str, file_suffix: str | List[str] = ".yaml", recursive: bool = False) -> Dict:
    """Load YAML data from files with a specific suffix."""
    return load_config_files(path, "yaml", file_suffix, recursive)


def get_data_from_files_parallel(
    path: str, 
    file_format: str,
    file_suffix: str | List[str], 
    recursive: bool = False, 
    max_workers: int = 10
) -> Dict:
    """
    Load data from JSON or YAML files that have a specific suffix using parallel processing.
    
    Args:
        path: Directory path to search for files
        file_format: File format to load. ["json", "yaml"]
        file_suffix: File suffixes to filter by e.g. ".json" or ["_main.json", "_flow.json"]
        recursive: Whether to search recursively in subdirectories
        max_workers: Maximum number of worker threads for parallel loading
        
    Returns:
        Dict mapping file suffix to a list of file paths to their loaded JSON data
    
    Example output:
        {
            ".json": {
                "/path/to/file1.json": {
                    "data": {
                        "key": "value"
                    }
                },
                "/path/to/file2.json": {
                    "data": {
                        "key": "value"
                    }
                }
            }
        }
        
    Raises:
        ValueError: If the path doesn't exist
    """
    def _discover_files(path: str, file_suffix: str | List[str], recursive: bool) -> List[str]:
        file_path_list = []
        if recursive:
            for root, _, filenames in os.walk(path):
                for filename in filenames:
                    if filename.endswith(file_suffix):
                        file_path_list.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(path):
                if filename.endswith(file_suffix):
                    file_path_list.append(os.path.join(path, filename))

        return file_path_list

    def load_single_file(file_path):
        try:
            return file_path, load_config_file(file_path, file_format), None
        except Exception as e:
            return file_path, None, str(e)

    # Validate path
    if not path or path.strip() == "" or not os.path.exists(path):
        raise ValueError(f"Path does not exist: {path}")

    file_suffix_list = [file_suffix] if isinstance(file_suffix, str) else file_suffix
    file_paths = {}
    data = {}
    errors = {}
    for suffix in file_suffix_list:
        file_paths[suffix] = _discover_files(path, suffix, recursive)
    
    for file_suffix, file_paths in file_paths.items():
        print(f"Loading {file_suffix} files...")
        print(f"File paths: {file_paths}")
        data[file_suffix] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(load_single_file, file_path): file_path
                for file_path in file_paths
            }
            
            for future in concurrent.futures.as_completed(future_to_path):
                file_path, file_data, error = future.result()
                if error:
                    errors[file_path] = error
                    print(f"Warning: Failed to load {file_path}: {error}")
                elif file_data is not None:
                    data[file_suffix][file_path] = file_data
    
    if errors:
        print(f"Warning: {len(errors)} files failed to load.")
        for file_path, error in errors.items():
            print(f"Warning: {file_path}: {error}")

    return data


def get_pipeline_update_id(spark: SparkSession) -> str:
    """
    Get the pipeline update id from the spark conf.
    This is only populated post initialisation of the pipeline, by an event hook in DltPipelineBuilder.
    
    Args:
        spark (SparkSession): The Spark session to use for the pipeline.

    Returns:
        str: The pipeline update id.
    """
    return spark.conf.get("pipeline.pipeline_update_id", None)


def get_table_versions(spark, source_view_dict: Dict[str, str]) -> DataFrame:
    """Get table versions from a Spark DataFrame."""
    df_list = []
    for view_name, source_table in source_view_dict.items():
        sql = f"DESCRIBE HISTORY {source_table} LIMIT 1"
        select_expr = [
            f"'{view_name}' AS viewName",
            f"'{source_table}' AS tableName",
            "version"
        ]
        df = spark.sql(sql).selectExpr(select_expr)
        df_list.append(df)
    return reduce(DataFrame.unionAll, df_list) if len(df_list) > 1 else df_list[0]


def load_python_function(
    python_function_path: str,
    function_name: str,
    required_params: List[str] = None
) -> Callable:
    """Load and validate a Python function from a file."""
    if required_params is None:
        required_params = []
    
    spec = importlib.util.spec_from_file_location("module", python_function_path)
    if not spec or not spec.loader:
        raise ImportError(f"Could not load Python function from {python_function_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Validate function exists
    if not hasattr(module, function_name):
        raise AttributeError(
            f"Python function file '{python_function_path}' must contain a "
            f"'{function_name}' function with parameters: {', '.join(required_params)}"
        )

    function = getattr(module, function_name)
    if not callable(function):
        raise TypeError(f"'{function_name}' in '{python_function_path}' is not callable")

    # Inspect signature
    sig = inspect.signature(function)
    func_params = list(sig.parameters.keys())
    missing_params = [p for p in required_params if p not in func_params]
    if missing_params:
        raise ValueError(
            f"Function '{function_name}' in '{python_function_path}' is missing "
            f"required parameters: {', '.join(missing_params)}"
        )

    return function


def load_python_function_from_module(
    python_module: str,
    required_params: List[str] = None
) -> Callable:
    """
    Load and validate a Python function from an extension module.
    
    The module must be importable via sys.path (typically from the extensions directory
    which is added to sys.path during pipeline initialization).
    
    Args:
        python_module: Module and function reference in format 'module_name.function_name'
                      (e.g., 'transforms.customer_source' or 'my_module.sub.get_data')
        required_params: List of required parameter names for validation
        
    Returns:
        The callable function from the module
        
    Raises:
        ValueError: If python_module format is invalid
        ImportError: If module cannot be imported
        AttributeError: If function is not found in module
        TypeError: If the attribute is not callable
    """
    if required_params is None:
        required_params = []
    
    # Parse module and function name
    if "." not in python_module:
        raise ValueError(
            f"Invalid pythonModule format: '{python_module}'. "
            f"Expected format: 'module_name.function_name' (e.g., 'transforms.get_df')"
        )
    
    # Split on last dot to get module path and function name
    module_path, function_name = python_module.rsplit(".", 1)
    
    # Import the module
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        raise ImportError(
            f"Could not import module '{module_path}' for pythonModule '{python_module}'. "
            f"Ensure the module exists in the extensions directory. Original error: {e}"
        ) from e
    
    # Get the function
    if not hasattr(module, function_name):
        raise AttributeError(
            f"Module '{module_path}' does not contain function '{function_name}'. "
            f"Available attributes: {[a for a in dir(module) if not a.startswith('_')]}"
        )
    
    function = getattr(module, function_name)
    if not callable(function):
        raise TypeError(
            f"'{function_name}' in module '{module_path}' is not callable"
        )
    
    # Validate required parameters
    if required_params:
        sig = inspect.signature(function)
        func_params = list(sig.parameters.keys())
        missing_params = [p for p in required_params if p not in func_params]
        if missing_params:
            raise ValueError(
                f"Function '{function_name}' in module '{module_path}' is missing "
                f"required parameters: {', '.join(missing_params)}"
            )
    
    return function


def list_sub_paths(path: str) -> List[str]:
    """List subdirectories in a given directory path."""
    return [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]


def merge_dicts(*dicts: Dict) -> Dict:
    """Merge dictionaries into a single dictionary."""
    return reduce(lambda a, b: {**a, **b} if b is not None else a, dicts, {})


def merge_dicts_recursively(d1: Dict, d2: Dict) -> Dict:
    """Recursively merges two dictionaries. Keys in d1 take precedence over d2."""
    d = d1.copy()

    for key in d2:
        if key in d1:
            if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                d[key] = merge_dicts_recursively(d1[key], d2[key])
        else:
            d[key] = d2[key]

    return d


def replace_dict_key_value(spec: Dict, target_key: str, new_value: str) -> Dict:
    """Replace values of a specific key in a nested dictionary."""
    if isinstance(spec, dict):
        for key, value in spec.items():
            if key == target_key:
                if spec[key] is not None and spec[key].strip() != "":
                    spec[key] = f"{new_value}/{spec[key]}"
            elif isinstance(value, dict) or isinstance(value, list):
                replace_dict_key_value(value, target_key, new_value)
    elif isinstance(spec, list):
        for item in spec:
            replace_dict_key_value(item, target_key, new_value)
    return spec


def set_logger(logger_name: str, log_level: str = "INFO") -> logging.Logger:
    """Set up and return a logger with a specified name and log level."""
    logger = logging.getLogger(logger_name)
    log_level = getattr(logging, log_level, logging.INFO)
    logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicate logging
    if logger.hasHandlers():
        logger.handlers.clear()

    # Add a new handler
    console_output_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_output_handler.setFormatter(formatter)
    logger.addHandler(console_output_handler)

    return logger
