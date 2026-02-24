import json
import os

from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from constants import (
    FrameworkPaths, PipelineBundlePaths, SupportedSpecFormat, PipelineBundleSuffixesJson, PipelineBundleSuffixesYaml
)
from dataflow.dataflow_spec import DataflowSpec
import pipeline_config
from secrets_manager import SecretsManager
import utility

from .expectations_builder import DataQualityExpectationBuilder
from .spec_mapper import SpecMapper
from .template_processor import TemplateProcessor
from .transformer import SpecTransformerFactory


class DataflowSpecBuilder:
    """
    Dataflow specification builder.

    Attributes:
        LOCALISE_PATHS (Dict): Paths to localize.
        logger: Logger instance.
        dataflow_path (str): Path to the dataflow.
        framework_path (str): Path to the framework.
        filters (Dict): Filters for the dataflow.
        substitution_manager (SubstitutionManager): Substitution manager instance.
        secrets_manager (SecretsManager): Secrets manager instance.
        max_workers (int): Maximum number of worker threads for parallel file loading.
        filter_list_data_flow_ids (List[str]): List of data flow IDs to filter.
        filter_list_data_flow_groups (List[str]): List of data flow groups to filter.
        filter_list_flow_group_ids (List[str]): List of flow group IDs to filter.
        filter_list_target_tables (List[str]): List of target tables to filter.
        filter_list_files (List[str]): List of files to filter.
        main_validator: Main JSON validator.
        flow_validator: Flow JSON validator.
        dataflow_spec_version (str): Path to the dataflow spec mapping file.
        dataflow_spec_list (List): List of dataflow specifications.
        validation_errors (Dict): Dictionary of validation errors.

    Methods:
        build(): Build dataflow specifications.
    """
    
    class Keys:
        """Constants for dictionary keys for the dataflow spec JSON files, and final dataflow spec format"""
        # Core dataflow specification keys
        DATA_FLOW_ID = "dataFlowId"
        DATA_FLOW_GROUP = "dataFlowGroup"
        DATA_FLOW_TYPE = "dataFlowType"
        DATA_FLOW_VERSION = "dataFlowVersion"
        
        # Target configuration keys
        TARGET_DETAILS = "targetDetails"
        TARGET_TABLE = "targetTable"
        TABLE = "table"
        
        # Data payload key
        DATA = "data"
        
        # Flow group keys
        FLOW_GROUPS = "flowGroups"
        FLOW_GROUP_ID = "flowGroupId"
        
        # Data quality keys (from dataflow spec)
        DATA_QUALITY_EXPECTATIONS_ENABLED = "dataQualityExpectationsEnabled"
        DATA_QUALITY_EXPECTATIONS_PATH = "dataQualityExpectationsPath"
        DATA_QUALITY_EXPECTATIONS = "dataQualityExpectations"
        
        # Path keys
        LOCAL_PATH = "localPath"
        
        # Mapping keys
        GLOBAL = "global"
        
        # Template keys
        TEMPLATE = "template"
        DATAFLOW_SPEC_PARAMS = "parameterSets"
        PARAMS = "parameters"

    LOCALISE_PATHS = {
        "schemaPath": PipelineBundlePaths.SCHEMA_PATH,
        "sqlPath": PipelineBundlePaths.DML_PATH,
        "functionPath": PipelineBundlePaths.PYTHON_FUNCTION_PATH,  # For sourceType: python
    }

    def __init__(
        self,
        bundle_path: str,
        framework_path: str,
        filters: Dict,
        secrets_manager: SecretsManager,
        ignore_validation_errors: bool = False,
        dataflow_spec_version: str = None,
        max_workers: int = 10,
        spec_file_format: str = SupportedSpecFormat.JSON.value
    ):
        self.bundle_path = bundle_path
        self.framework_path = framework_path
        self.filters = filters
        self.secrets_manager = secrets_manager
        self.ignore_validation_errors = ignore_validation_errors
        self.global_dataflow_spec_version = dataflow_spec_version
        self.max_workers = max_workers
        self.spec_file_format = spec_file_format.lower()

        valid_formats = [fmt.value for fmt in SupportedSpecFormat]
        if self.spec_file_format not in valid_formats:
            raise ValueError(f"Invalid enabled format: {self.spec_file_format}. Valid formats are: {valid_formats}")

        self.dataflow_path = os.path.join(bundle_path, PipelineBundlePaths.DATAFLOWS_BASE_PATH)

        self.logger = pipeline_config.get_logger()
        self.substitution_manager = pipeline_config.get_substitution_manager()
        
        # Initialize spec mapper for version migrations
        self.spec_mapper = SpecMapper(self.framework_path, self.max_workers)
        
        # Initialize template processor
        self.template_processor = TemplateProcessor(self.bundle_path, self.framework_path)

        # Initialize filters
        self.filter_data_flow_ids = self._parse_filter(self.filters.get("data_flow_ids"))
        self.filter_data_flow_groups = self._parse_filter(self.filters.get("data_flow_groups"))
        self.filter_flow_group_ids = self._parse_filter(self.filters.get("flow_group_ids"))
        self.filter_target_tables = self._parse_filter(self.filters.get("target_tables"))
        self.filter_files = self._parse_filter(self.filters.get("files"))

        # Initialize validators
        self.main_validator = utility.JSONValidator(
            os.path.join(self.framework_path,FrameworkPaths.MAIN_SPEC_SCHEMA_PATH))
        self.flow_validator = utility.JSONValidator(
            os.path.join(self.framework_path,FrameworkPaths.FLOW_GROUP_SPEC_SCHEMA_PATH))

        # Initialize storage
        self.processed_specs: List[DataflowSpec] = []
        self.validation_errors: Dict[str, str] = {}

    def _post_init(self) -> None:
        """Post-initialization setup."""
        if not os.path.exists(self.bundle_path):
            raise FileNotFoundError(f"Path does not exist in Workspace files, or is inaccessible: {self.bundle_path}")
        if not os.path.exists(self.dataflow_path):
            raise FileNotFoundError(f"Path does not exist in Workspace files, or is inaccessible: {self.dataflow_path}")

    @staticmethod
    def _parse_filter(filter_str: Optional[str]) -> List[str]:
        """Parse a filter string into a list of lowercase, stripped values."""
        return [item.lower().strip() for item in filter_str.split(",")] if filter_str else []

    def build(self) -> List[DataflowSpec]:
        """
        Build DataflowSpec instances from configuration files.

        Returns:
            List[DataflowSpec]: List of processed dataflow specifications

        Raises:
            ValueError: If any validation errors are encountered
        """
        self.logger.info(
            "Dataflow Spec Builder - Commencing Build, Settings:\n"
            f"    Dataflow Path: {self.dataflow_path}\n"
            f"    Max Workers: {self.max_workers}\n"
            f"    Filters: {json.dumps(self.filters, indent=8)}\n"
            f"    Ignore Validation Errors: {self.ignore_validation_errors}\n"
            f"    Global Dataflow Spec Version (optional): {self.global_dataflow_spec_version}"
        )

        self.logger.info("Reading and filtering dataflow specs...")
        main_specs, flow_specs = self._read_dataflow_specs()
        main_specs = self._filter_dataflow_specs(main_specs)
        
        # Apply dataflow spec version mapping
        self.logger.info("Applying dataflow spec version mapping...")
        main_specs = self._apply_dataflow_spec_mapping(main_specs)
        flow_specs = self._apply_dataflow_spec_mapping(flow_specs)

        # Validate dataflow specs
        self.logger.info("Validating dataflow specs...")
        self._validate_dataflow_specs({**main_specs, **flow_specs})
        
        # Merge flow groups
        self.logger.info("Merging flow groups...")
        spec_payloads = self._merge_flow_groups(main_specs, flow_specs)

        # Transform dataflow specs
        self.logger.info("Transforming dataflow specs...")
        spec_payloads = self._transform_specs(spec_payloads)
        
        # Final processing of dataflow specs
        self.logger.info("Final processing of dataflow specs...")
        self._process_specs(spec_payloads)
        
        return self.processed_specs

    def _read_dataflow_specs(self) -> Dict:
        """Read dataflow specifications based on filters."""
        main_specs = {}
        flow_specs = {}
        
        def _extract_spec(spec: Dict) -> Dict:
            """Extract metadata from a dataflow specification."""
            return {
                "fileType": "main",
                self.Keys.DATA_FLOW_ID: spec.get(self.Keys.DATA_FLOW_ID, None),
                self.Keys.DATA_FLOW_GROUP: spec.get(self.Keys.DATA_FLOW_GROUP, None),
                self.Keys.DATA_FLOW_TYPE: spec.get(self.Keys.DATA_FLOW_TYPE, None),
                self.Keys.TARGET_TABLE: spec.get(self.Keys.TARGET_DETAILS, {}).get(self.Keys.TABLE, None),
                self.Keys.DATA: spec
            }

        def _validate_missing_metadata(spec: Dict) -> Dict:
            """Validate a dataflow specification for missing metadata."""
            missing_metadata = []
            if not spec.get(self.Keys.DATA_FLOW_ID):
                missing_metadata.append(self.Keys.DATA_FLOW_ID)
            if not spec.get(self.Keys.DATA_FLOW_GROUP):
                missing_metadata.append(self.Keys.DATA_FLOW_GROUP)
            if not spec.get(self.Keys.DATA_FLOW_TYPE):
                missing_metadata.append(self.Keys.DATA_FLOW_TYPE)
            return missing_metadata

        if self.filter_files:
            self.logger.info(f"Loading dataflow specifications by file filters: {self.filters}")
            # Convert filter paths to full file paths and load data
            for filter_path in self.filter_files:

                full_path = os.path.join(self.dataflow_path, filter_path)
                if not self._validate_file_path(full_path):
                    continue
                
                data = utility.load_config_file_auto(full_path, fail_on_not_exists=True)
                if data:
                    main_specs[full_path] = _extract_spec(data)

        else:
            suffixes = utility.get_format_suffixes(self.spec_file_format, "main_spec")
            suffixes.extend(utility.get_format_suffixes(self.spec_file_format, "flow_group"))

            self.logger.info(f"Loading {self.spec_file_format.upper()} dataflow specifications recursively...")
            categorized_files = utility.get_data_from_files_parallel(
                path=self.dataflow_path,
                file_format=self.spec_file_format,
                file_suffix=suffixes,
                recursive=True,
                max_workers=self.max_workers
            )
            
            main_files_data = {}
            flow_files_data = {}
            for key, value in categorized_files.items():
                # Normalize key to always be iterable
                keys_to_check = key if isinstance(key, tuple) else [key]
                if any("_main." in suffix for suffix in keys_to_check):
                    main_files_data.update(value)
                elif any("_flow." in suffix for suffix in keys_to_check):
                    flow_files_data.update(value)

            if not main_files_data:
                valid_formats = [fmt.value for fmt in SupportedSpecFormat]
                raise ValueError(
                    f"No dataflow specification files found in: {self.dataflow_path}. "
                    f"Spec format set to: {self.spec_file_format.upper()}. "
                    f"Valid formats are: {valid_formats}"
                )
            else:
                self.logger.info(f"Found {len(main_files_data)} main spec files.")
            
            # Process all specs in one pass: expand templates, extract regular specs
            main_specs = {}
            for file_path, json_data in main_files_data.items():
                if self.Keys.TEMPLATE in json_data:
                    # Template: expand and extract each resulting spec
                    expanded_specs = self.template_processor.process_template_spec(
                        file_path,
                        json_data,
                        self.spec_file_format
                    )
                    for expanded_path, expanded_json in expanded_specs.items():
                        main_specs[expanded_path] = _extract_spec(expanded_json)
                else:
                    main_specs[file_path] = _extract_spec(json_data)
            
            # Load and process flow group files if any exist
            if flow_files_data:
                flow_specs = {
                    file_path: {
                        "fileType": "flow_group",
                        self.Keys.DATA_FLOW_ID: json_data.get(self.Keys.DATA_FLOW_ID),
                        self.Keys.DATA: json_data
                    }
                    for file_path, json_data in flow_files_data.items()
                }

        metadata_validation_errors = {}
        for spec_path, spec_data in main_specs.items():
            missing_metadata = _validate_missing_metadata(spec_data)
            if missing_metadata:
                metadata_validation_errors[spec_path] = f"Missing metadata: {missing_metadata}"

        if not self.ignore_validation_errors and metadata_validation_errors:
            raise ValueError(f"Dataflow Spec Metadata Validation Errors:\n{json.dumps(metadata_validation_errors, indent=2)}")

        self.logger.info(f"Loaded {len(main_specs)} dataflow specifications.")

        return main_specs, flow_specs

    def _merge_flow_groups(self, specs: Dict, flow_groups: Dict) -> Dict:
        """Merge flow groups into the dataflow specifications."""
        for spec_path, spec_data in specs.items():
            dataflow_type = spec_data.get(self.Keys.DATA_FLOW_TYPE)
            dataflow_id = spec_data.get(self.Keys.DATA_FLOW_ID)
            if not dataflow_id or not dataflow_type:
                continue

            if dataflow_type == "flow" and dataflow_id in flow_groups:
                # Get existing flow groups from main spec
                existing_flow_groups = spec_data.get(self.Keys.FLOW_GROUPS, [])
                new_flow_groups = flow_groups[dataflow_id]
                
                # Check for duplicate flow group IDs
                existing_ids = {group.get(self.Keys.FLOW_GROUP_ID) for group in existing_flow_groups if group.get(self.Keys.FLOW_GROUP_ID)}
                new_ids = {group.get(self.Keys.FLOW_GROUP_ID) for group in new_flow_groups if group.get(self.Keys.FLOW_GROUP_ID)}
                duplicate_ids = existing_ids & new_ids
                
                if duplicate_ids:
                    message = (
                        f"Duplicate flow group IDs found for dataflow '{dataflow_id}': {duplicate_ids}. "
                        f"Flow group IDs must be unique across main spec and flow group files."
                    )
                    self.logger.error(message)
                    self.validation_errors[spec_path] = message
                    
                    if not self.ignore_validation_errors:
                        raise ValueError(message)
                
                # Merge flow groups
                self.logger.info(f"Merging flow group files for dataflow: '{dataflow_id}'. Flow Group IDs: {new_ids}")
                if not existing_flow_groups:
                    spec_data[self.Keys.FLOW_GROUPS] = new_flow_groups
                else:
                    spec_data[self.Keys.FLOW_GROUPS].extend(new_flow_groups)

        return specs

    def _filter_dataflow_specs(self, specs: Dict) -> Dict:
        """Apply filters to a dataflow specification."""
        filtered_specs = {}
        filtered_out_notifications = []
        kept_notifications = []
        for spec_path, spec_payload in specs.items():

            # Filter dataflow specs on the main filters
            if self._matches_filters(spec_payload):
                filtered_specs[spec_path] = spec_payload
                kept_notifications.append(
                    f"ID: {spec_payload.get(self.Keys.DATA_FLOW_ID)}, "
                    f"Group: {spec_payload.get(self.Keys.DATA_FLOW_GROUP)}, "
                    f"Path: {spec_path}"
                )
                # Filter flow groups if the dataflow type is flow
                if self.filter_flow_group_ids and spec_payload.get(self.Keys.DATA_FLOW_TYPE) == "flow":
                    spec_payload[self.Keys.FLOW_GROUPS] = [
                        group for group in spec_payload.get(self.Keys.FLOW_GROUPS, [])
                        if group[self.Keys.FLOW_GROUP_ID].strip().lower() in self.filter_flow_group_ids
                    ]
            else:
                filtered_out_notifications.append(
                    f"ID: {spec_payload.get(self.Keys.DATA_FLOW_ID)}, "
                    f"Group: {spec_payload.get(self.Keys.DATA_FLOW_GROUP)}, "
                    f"Path: {spec_path}"
                )

        if kept_notifications:
            self.logger.info("The following dataflow specs were kept:\n" + '\n'.join(kept_notifications) + "\n")

        if filtered_out_notifications:
            self.logger.info(
                "The following dataflow specs were filtered out:\n" + '\n'.join(filtered_out_notifications) + "\n"
            )
            
        return filtered_specs

    def _matches_filters(self, spec_payload: Dict) -> bool:
        """Check if a specification matches the current filters."""
        data_flow_id = spec_payload.get(self.Keys.DATA_FLOW_ID).lower()
        data_flow_group = spec_payload.get(self.Keys.DATA_FLOW_GROUP).lower()
        spec_has_target_table = spec_payload.get(self.Keys.TARGET_DETAILS, {}).get(self.Keys.TABLE, None) is not None
        target_table = spec_payload.get(self.Keys.TARGET_DETAILS, {}).get(self.Keys.TABLE, "").lower()

        if self.filter_data_flow_ids and data_flow_id not in self.filter_data_flow_ids:
            return False
        if self.filter_data_flow_groups and data_flow_group not in self.filter_data_flow_groups:
            return False
        if self.filter_target_tables and spec_has_target_table and target_table not in self.filter_target_tables:
            return False

        return True

    def _apply_dataflow_spec_mapping(self, specs: Dict) -> Dict:
        """Apply the dataflow spec mapping to the dataflow specs using parallel processing."""
        return self.spec_mapper.apply_mappings(
            specs,
            global_version=self.global_dataflow_spec_version,
            ignore_errors=self.ignore_validation_errors
        )

    def _validate_dataflow_specs(self, spec_payloads: Dict) -> None:
        """Validate the dataflow specifications using parallel processing."""
        if not spec_payloads:
            return

        def _validate_json(spec_item: tuple) -> tuple:
            """Validate JSON data against a schema."""
            spec_path, spec_payload = spec_item
            file_type = spec_payload.get("fileType", "main")
            json_data = spec_payload.get(self.Keys.DATA)
            if file_type == "main":
                errors = self.main_validator.validate(json_data)
            else:
                errors = self.flow_validator.validate(json_data)
            return spec_path, errors
        
        validation_errors = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all validation tasks
            future_to_path = {
                executor.submit(_validate_json, (spec_path, spec_payload)): spec_path
                for spec_path, spec_payload in spec_payloads.items()
            }
            
            # Collect results
            for future in as_completed(future_to_path):
                spec_path, errors = future.result()
                if errors:
                    validation_errors[spec_path] = errors

        self.validation_errors.update(validation_errors)
        if validation_errors:
            self.logger.warning(f"Invalid dataflow spec files found:\n{validation_errors}")
            if not self.ignore_validation_errors:
                raise ValueError(f"Invalid dataflow spec files found:\n{validation_errors}")

    def _transform_specs(self, spec_payloads: Dict) -> Dict:
        """Transform the dataflow specs using parallel processing."""
        if not spec_payloads:
            return spec_payloads

        def _transform_spec_worker(spec_item: tuple) -> tuple:
            """Worker function to transform a single spec."""
            spec_path, spec_payload = spec_item
            
            try:
                dataflow_type = spec_payload.get(self.Keys.DATA_FLOW_TYPE, "").strip().lower()
                spec_data = spec_payload.get(self.Keys.DATA)
                transformer = SpecTransformerFactory.create_transformer(dataflow_type)
                transformed_spec = transformer.transform(spec_data)
                spec_payload[self.Keys.DATA] = transformed_spec
                return spec_path, spec_payload, None
                
            except Exception as e:
                return spec_path, spec_payload, str(e)
            
        results = {}
        errors = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all transformation tasks
            future_to_path = {
                executor.submit(_transform_spec_worker, (spec_path, spec_payload)): spec_path
                for spec_path, spec_payload in spec_payloads.items()
            }
            
            # Collect results
            for future in as_completed(future_to_path):
                spec_path, spec_payload, error = future.result()
                if error:
                    errors[spec_path] = error
                    self.logger.warning(f"Failed to transform spec {spec_path}: {error}")
                results[spec_path] = spec_payload
        
        if errors and not self.ignore_validation_errors:
            self.logger.warning(f"Some specs failed during transformation: {errors}")
        
        return results

    def _process_specs(self, spec_payloads: Dict) -> None:
        """Add a processed dataflow specification."""
        for spec_path, spec_payload in spec_payloads.items():
            base_path = self._get_base_path(spec_path)
            spec_data = spec_payload.get(self.Keys.DATA)
            if isinstance(spec_data, list):
                for spec in spec_data:
                    self._process_spec_data(base_path, spec)
            else:
                self._process_spec_data(base_path, spec_data)

    def _process_spec_data(self, base_path: str, spec_data: Dict) -> None:
        """Process the dataflow specification data."""
        # Get Expectations
        spec_data = self._get_expectations(spec_data, base_path)

        # Localize paths (also sets LOCAL_PATH)
        spec_data = self._localize_paths(spec_data, base_path)

        # Substitute tokens in the dataflow spec
        spec_data = self.substitution_manager.substitute_dict(spec_data)

        # Substitute secrets in the dataflow spec with SecretValue objects
        spec_data = self.secrets_manager.substitute_secrets(spec_data)
        self.logger.info(f"Adding Dataflow Spec: {spec_data.get(self.Keys.DATA_FLOW_ID)}.")
        self.processed_specs.append(DataflowSpec(**spec_data))

    # TODO: Replace with service Locator pattern
    def _localize_paths(self, spec_data: Dict, base_path: str) -> Dict:
        """
        Convert relative paths to absolute paths in the specification with fallback logic.
        Recursively processes the entire spec structure to find and resolve all path references.
        """
        spec_data[self.Keys.LOCAL_PATH] = base_path
        self._localize_paths_recursive(spec_data, base_path, spec_data)
        return spec_data
    
    def _localize_paths_recursive(self, obj, base_path: str, root_spec_data: Dict):
        """Recursively traverse the spec structure and resolve path keys wherever they appear."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Check if this key is a simple path that needs resolution (e.g., "schemaPath")
                if key in DataflowSpecBuilder.LOCALISE_PATHS and isinstance(value, str):
                    resolved_value = self._resolve_path_value(
                        key, value, base_path, root_spec_data
                    )
                    obj[key] = resolved_value
                 
                if isinstance(value, (dict, list)):
                    self._localize_paths_recursive(value, base_path, root_spec_data)

        elif isinstance(obj, list):
            for item in obj:
                self._localize_paths_recursive(item, base_path, root_spec_data)
    
    def _resolve_path_value(self, key: str, value: str, base_path: str, root_spec_data: Dict) -> str:
        """Resolve a single path value based on its key type. Always returns normalized path."""
        if self._is_valid_absolute_path(value):
            return value
        
        if not value:
            return value
        
        # For Python function paths, use enhanced resolution with fallbacks
        if key == "functionPath":
            try:
                return self._resolve_python_function_path(value, base_path, root_spec_data)
            except FileNotFoundError:
                self.logger.error(
                    f"Python function '{value}' not found in any search location, "
                    f"keeping original path"
                )
                #TODO: pipe through to validation errors
                return os.path.normpath(value)
        else:
            # Standard path resolution
            subpath = DataflowSpecBuilder.LOCALISE_PATHS[key]
            resolved_path = os.path.normpath(
                os.path.join(base_path, PipelineBundlePaths.DATAFLOW_SPEC_PATH, subpath, value)
            )
            if os.path.exists(resolved_path):
                return resolved_path
            
            resolved_path = os.path.normpath(os.path.join(base_path, subpath, value))
            if os.path.exists(resolved_path):
                return resolved_path
            
            return resolved_path
    
    def _is_valid_absolute_path(self, path: str) -> bool:
        """Check if path is truly absolute and within our known base paths."""
        if not os.path.isabs(path):
            return False
        
        # Normalize paths for comparison (resolve symlinks, remove trailing slashes)
        normalized_path = os.path.normpath(os.path.abspath(path))
        normalized_bundle = os.path.normpath(os.path.abspath(self.bundle_path))
        normalized_framework = os.path.normpath(os.path.abspath(self.framework_path))
        
        # Check if path starts with bundle_path or framework_path
        if normalized_path.startswith(normalized_bundle):
            self.logger.debug(f"Path '{path}' is absolute within bundle path")
            return True
        
        if normalized_path.startswith(normalized_framework):
            self.logger.debug(f"Path '{path}' is absolute within framework path")
            return True
        
        # Path is absolute but not within our known locations - log warning but accept it
        # This allows for legitimate absolute paths outside our bundle/framework
        self.logger.warning(
            f"Path '{path}' is absolute but not within bundle or framework paths. "
            f"Using as-is, but this may cause issues if the path is not valid."
        )
        return True
    
    def _resolve_python_function_path(self, filename: str, base_path: str, spec_data: Dict) -> str:
        """
        Resolve Python function path with context-aware fallback logic.
        
        Search order for regular specs:
            1. base_path/python_functions/<filename>
            2. bundle_path/extensions/python_functions/<filename>
            3. framework_path/extensions/python_functions/<filename>
        
        Search order for template-generated specs (adds one additional location):
            1. base_path/python_functions/<filename>
            2. bundle_path/templates/python_functions/<filename>
            3. bundle_path/extensions/python_functions/<filename>
            4. framework_path/extensions/python_functions/<filename>
        """
        search_paths = {
            "base dataflow directory":
                os.path.join(base_path, PipelineBundlePaths.PYTHON_FUNCTION_PATH, filename),
            "templates directory":
                os.path.join(self.bundle_path, PipelineBundlePaths.TEMPLATE_PATH,
                    PipelineBundlePaths.PYTHON_FUNCTION_PATH, filename),
            "bundle extensions directory":
                os.path.join(self.bundle_path, PipelineBundlePaths.EXTENSIONS_PATH, filename),
            "framework extensions directory":
                os.path.join(self.framework_path, FrameworkPaths.EXTENSIONS_PATH, filename),
        }
        
        # Template-specific location (only for template-generated specs)
        is_template_generated = spec_data.get("tags", {}).get("_isTemplateGenerated", False)
        if not is_template_generated:
            search_paths.pop("templates directory")
        
        # Try each path in order
        for key, path in search_paths.items():
            normalized_path = os.path.normpath(path)
            if os.path.exists(normalized_path):
                self.logger.debug(f"Resolved Python function '{filename}' from {key}: {normalized_path}")
                return normalized_path
        
        spec_path = f"{base_path}/{spec_data.get(self.Keys.DATA_FLOW_ID)}"
        self.validation_errors[spec_path] = f"Python function file '{filename}' not found in any search location"
        
        return filename

    def _validate_file_path(self, path: str) -> bool:
        """Validate a file path meets all requirements."""

        if self.spec_file_format == SupportedSpecFormat.JSON.value:
            if not any(path.endswith(suffix) for suffix in PipelineBundleSuffixesJson.MAIN_SPEC_FILE_SUFFIX):
                self.validation_errors[path] = f"Invalid file filter: {path}.\nFile format must be JSON"
                return False
        elif self.spec_file_format == SupportedSpecFormat.YAML.value:
            if not any(path.endswith(suffix) for suffix in PipelineBundleSuffixesYaml.MAIN_SPEC_FILE_SUFFIX):
                self.validation_errors[path] = f"Invalid file filter: {path}.\nFile format must be YAML"
                return False

        if not os.path.exists(path):
            self.validation_errors[path] = f"File not found: {path}"
            return False

        return True

    def _get_base_path(self, file_path: str) -> str:
        """Get the base path for a file."""
        base_path = os.path.dirname(file_path)
        if base_path.endswith(PipelineBundlePaths.DATAFLOW_SPEC_PATH):
            base_path = base_path[:-len(PipelineBundlePaths.DATAFLOW_SPEC_PATH)]
            if base_path.endswith('/'):
                base_path = base_path[:-1]
        self.logger.debug(f"Base path for associated files: {base_path}")
        return base_path

    def _get_expectations(self, dataflow_spec: Dict, base_path: str) -> Dict:
        """Set the expectation validator path in the dataflow specification."""
        dqe_validator_path = os.path.join(self.framework_path,FrameworkPaths.EXPECTATIONS_SPEC_SCHEMA_PATH)
        if dataflow_spec.get(self.Keys.DATA_QUALITY_EXPECTATIONS_ENABLED, False):
            dqe_path = dataflow_spec.get(self.Keys.DATA_QUALITY_EXPECTATIONS_PATH, None)
            if dqe_path is None or dqe_path.strip() == "":
                raise ValueError("Data quality expectations path is not set in Dataflow Spec")

            dqe_path = f"{base_path}/{PipelineBundlePaths.DQE_PATH}/{dqe_path}"
            dataflow_spec[self.Keys.DATA_QUALITY_EXPECTATIONS] = (
                DataQualityExpectationBuilder(
                    self.logger,
                    dqe_validator_path,
                    self.spec_file_format
                ).get_expectations(dqe_path).__dict__)

        return dataflow_spec
