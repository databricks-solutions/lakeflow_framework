import json
import os
import re
from typing import Dict, Any

from constants import FrameworkPaths, PipelineBundlePaths, SupportedSpecFormat
import pipeline_config
import utility


class TemplateProcessor:
    """
    Handles template file loading and expansion into concrete dataflow specs.
    
    This processor is responsible for:
    - Loading template definition files from the file system (with caching)
    - Finding and validating parameter placeholders
    - Expanding templates with provided parameter sets
    - Generating multiple concrete specs from a single template definition
    
    Attributes:
        bundle_path (str): Path to the pipeline bundle containing templates
        framework_path (str): Path to the framework containing schemas
        logger: Logger instance for tracking template processing
        
    Note:
        Templates definitionsare cached after first load to optimize performance when
        the same template is used multiple times.
    """

    class DefinitionKeys:
        """Constants for dictionary keys for the template dataflow spec JSON files"""
        TEMPLATE = "template"
        PARAMETER_DEFINITIONS = "parameters"
        DATA_FLOW_ID = "dataFlowId"
        PARAM_TYPE = "type"
        PARAM_REQUIRED = "required"
        PARAM_DEFAULT = "default"

    class SpecKeys:
        """Constants for dictionary keys for the template dataflow spec JSON files"""
        TEMPLATE_NAME = "template"
        PARAMETER_SETS = "parameterSets"
        DATA_FLOW_ID = "dataFlowId"
        TAGS = "tags"
        TAG_IS_TEMPLATE_GENERATED = "_isTemplateGenerated"
        TAG_TEMPLATE_NAME = "_templateName"
    
    def __init__(self, bundle_path: str, framework_path: str):
        """Initialize the template processor."""
        self.bundle_path = bundle_path
        self.framework_path = framework_path
        self.logger = pipeline_config.get_logger()
        self._pattern = re.compile(r'\$\{param\.([^}]+)\}')
        
        # Initialize cache for loaded templates
        self._template_cache: Dict[str, Dict] = {}
        
        # Initialize validators for template definitions and template specs
        self.template_definition_validator = utility.JSONValidator(
            os.path.join(self.framework_path, FrameworkPaths.TEMPLATE_DEFINITION_SPEC_SCHEMA_PATH)
        )
        self.template_spec_validator = utility.JSONValidator(
            os.path.join(self.framework_path, FrameworkPaths.TEMPLATE_SPEC_SCHEMA_PATH)
        )

    def process_template_spec(
        self,
        file_path: str,
        template_spec: Dict,
        spec_file_format: str = SupportedSpecFormat.JSON.value
    ) -> Dict[str, Dict]:
        """
        Process a template spec into multiple concrete specs based on provided parameters.
        
        Takes a template definition that includes:
        - A template name referencing a template file
        - A list of parameter sets
        
        Returns a dictionary where each key is a unique identifier and each value
        is a fully expanded concrete spec with all parameters substituted.
        
        Args:
            file_path: Path to the original template spec file (used for tracking)
            template_spec: Dictionary containing a template dataflow spec
            
        Returns:
            Dict[str, Dict]: Dictionary mapping unique identifiers to expanded specs
            
        Raises:
            ValueError: If template name is missing, no parameters provided, or parameters are invalid
            FileNotFoundError: If the referenced template file cannot be found
            KeyError: If a required parameter is missing from a parameter set
        """
        # Validate template definition against schema
        validation_errors = self.template_spec_validator.validate(template_spec)
        if validation_errors:
            error_msg = f"Template definition validation failed for {file_path}:\n{validation_errors}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        template_name = template_spec.get(self.SpecKeys.TEMPLATE_NAME)
        dataflow_spec_params = template_spec.get(self.SpecKeys.PARAMETER_SETS, [])
        
        # Validate template spec structure
        if not template_name:
            error_msg = "Template name must be provided in template spec"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        if not dataflow_spec_params:
            error_msg = f"Dataflow specs must be provided for template: {template_name}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Load template content and validate against schema
        template_definition = self._get_template_definition(template_name, spec_file_format)
        
        # Get and validate parameter definitions
        param_definitions = self._get_template_parameters(template_definition, template_name)
        
        # Generat Spec for each parameter set
        processed_specs = {}
        spec_template = template_definition.get(self.DefinitionKeys.TEMPLATE, {})
        for params in dataflow_spec_params:
            dataflow_id = params.get(self.SpecKeys.DATA_FLOW_ID)
            spec_key = f'{file_path}#template_{template_name}_{dataflow_id}'
            
            # Validate and apply defaults to parameters
            processed_params = self._validate_and_apply_defaults(
                params, param_definitions, spec_key
            )
            
            # Generate Spec with this parameter set
            try:
                generated_spec = self._generate_spec(spec_template, processed_params)
                
                # Explicitly mark this spec as template-generated for downstream processing
                tags = generated_spec.get(self.SpecKeys.TAGS, {})
                tags[self.SpecKeys.TAG_IS_TEMPLATE_GENERATED] = True
                tags[self.SpecKeys.TAG_TEMPLATE_NAME] = template_name
                generated_spec[self.SpecKeys.TAGS] = tags
                
                # Add spec
                processed_specs[spec_key] = generated_spec
                self.logger.debug(f"Generated spec from template: '{spec_key}'")
            except Exception as e:
                error_msg = f"Failed to generate spec from template '{spec_key}': {str(e)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg) from e
        
        self.logger.info(
            f"Successfully generated {len(processed_specs)} specs from template '{template_name}'"
        )
        
        return processed_specs
    
    def _get_template_definition(self, template_name: str, spec_file_format: str) -> Dict:
        """Load a template file from the file system with caching."""
        if template_name in self._template_cache:
            self.logger.debug(f"Using cached template definition: {template_name}")
            return self._template_cache[template_name]
        
        base_path = os.path.join(
            self.bundle_path, 
            PipelineBundlePaths.TEMPLATE_PATH,
            template_name
        )
        template_path = self._resolve_template_path(base_path, spec_file_format)
        if not template_path:
            error_msg = f"Template not found: {base_path} for format: {spec_file_format.upper()}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        template_definition = utility.load_config_file(template_path, spec_file_format, True)
        template_validation_errors = self.template_definition_validator.validate(template_definition)
        if template_validation_errors:
            error_msg = f"Template file validation failed for template '{template_name}':\n{template_validation_errors}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.logger.info(f"Loaded template definition '{template_name}' from: {template_path}")
        self._template_cache[template_name] = template_definition
        
        return template_definition
    
    def _resolve_template_path(self, base_path: str, spec_file_format: str) -> str | None:
        """Resolve the full path to a template file, handling both .yaml and .yml extensions."""        
        # For YAML format, check both .yaml and .yml extensions
        if spec_file_format in ('yaml', 'yml'):
            for ext in ('yaml', 'yml'):
                file_path = f"{base_path}.{ext}"
                if os.path.exists(file_path):
                    return file_path
            return None
        
        # For other formats (e.g., JSON), use the format directly
        file_path = f"{base_path}.{spec_file_format}"
        if os.path.exists(file_path):
            return file_path
        
        return None
    
    def clear_cache(self) -> None:
        """Clear the template cache. Used for testing or when templates need to be reloaded from disk after being modified."""
        cache_size = len(self._template_cache)
        self._template_cache.clear()
        self.logger.info(f"Cleared template cache ({cache_size} templates)")
    
    def get_cache_info(self) -> Dict[str, int]:
        """Get information about the template cache. Used for testing or when templates need to be reloaded from disk after being modified."""
        return {
            "cached_templates": len(self._template_cache),
            "template_names": list(self._template_cache.keys())
        }
    
    def _get_template_parameters(self, template_definition: Dict, template_name: str) -> Dict:
        """Get parameter definitions from template and validate against template content."""
        param_definitions = template_definition.get(self.DefinitionKeys.PARAMETER_DEFINITIONS, {})
        
        if not param_definitions:
            error_msg = f"Template '{template_name}' contains no parameters"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        if "dataFlowId" not in param_definitions:
            error_msg = f"Template '{template_name}' must declare 'dataFlowId' parameter"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Extract template content and find all parameter placeholders used in it
        template_content = template_definition.get(self.DefinitionKeys.TEMPLATE, {})
        template_string = json.dumps(template_content)
        param_placeholders = re.findall(r'\$\{param\.([^}]+)\}', template_string)
        unique_placeholders = set(param_placeholders)
        
        # Validate all placeholders have definitions
        undefined_params = unique_placeholders - set(param_definitions.keys())
        if undefined_params:
            error_msg = f"Template '{template_name}' uses undefined parameters: {sorted(undefined_params)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Warn about unused parameter definitions
        unused_params = set(param_definitions.keys()) - unique_placeholders
        if unused_params:
            self.logger.warning(
                f"Template '{template_name}' has unused parameter definitions: {sorted(unused_params)}"
            )
        
        self.logger.debug(
            f"Template '{template_name}' parameter definitions: {json.dumps(param_definitions, indent=4)}"
        )
        
        return param_definitions
    
    def _validate_and_apply_defaults(
        self,
        params: Dict,
        param_definitions: Dict,
        spec_key: str
    ) -> Dict:
        """Validate provided parameters against definitions and apply defaults."""
        processed_params = {}
        missing_required = []
        
        for param_name, param_def in param_definitions.items():
            param_type = param_def.get(self.DefinitionKeys.PARAM_TYPE)
            is_required = param_def.get(self.DefinitionKeys.PARAM_REQUIRED, True)
            default_value = param_def.get(self.DefinitionKeys.PARAM_DEFAULT, None)
            
            if param_name in params:
                param_value = params[param_name]
                if not self._validate_parameter_type(param_value, param_type):
                    error_msg = (
                        f"Error validating parameter '{param_name}' in spec '{spec_key}': "
                        f"Expected type '{param_type}', got '{type(param_value).__name__}'"
                    )
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)
                processed_params[param_name] = param_value

            else:
                if is_required:
                    missing_required.append(param_name)
                elif default_value is not None:
                    try:
                        processed_params[param_name] = default_value
                        self.logger.debug(
                            f"Applied default value for parameter '{param_name}': {default_value}"
                        )
                    except ValueError as e:
                        error_msg = f"Error applying default value for parameter '{param_name}' in spec '{spec_key}': {str(e)}"
                        self.logger.error(error_msg)
                        raise ValueError(error_msg) from e
                # If not required and no default, skip it
        
        if missing_required:
            error_msg = f"Generated spec '{spec_key}' is missing required parameters: {missing_required}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        return processed_params
    
    def _validate_parameter_type(
        self,
        param_value: Any,
        expected_type: str
    ) -> bool:
        """Validate a parameter value matches its declared type."""
        type_map = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "list": list,
            "object": dict
        }
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return False
            
        return isinstance(param_value, expected_python_type)
    
    def _generate_spec(self, obj, params: Dict):
        """Recursively process a value, replacing parameter placeholders."""
        if isinstance(obj, dict):
            result = {
                self._generate_spec(k, params): self._generate_spec(v, params) 
                for k, v in obj.items()
            }
            # Validate all keys are strings
            if non_string_keys := [k for k in result.keys() if not isinstance(k, str)]:
                error_msg = f"Dictionary keys must be strings, found: {non_string_keys}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            return result
        
        if isinstance(obj, list):
            return [self._generate_spec(item, params) for item in obj]
        
        if isinstance(obj, str):
            return self._replace_string_placeholders(obj, params)
        
        return obj
    
    def _replace_string_placeholders(self, text: str, params: Dict):
        """Replace parameter placeholders in a string value."""
        # Full replacement: entire string is a single placeholder
        if (m := self._pattern.fullmatch(text)):
            return self._get_param_value(m.group(1), params)
        
        # Partial replacement: string contains placeholders
        if self._pattern.search(text):
            return self._pattern.sub(
                lambda m: str(self._get_param_value(m.group(1), params)), 
                text
            )
        
        return text
    
    def _get_param_value(self, param_key: str, params: Dict):
        """Get a parameter value from the params dictionary."""
        if param_key not in params:
            error_msg = f"Parameter '{param_key}' not found in params"
            self.logger.error(error_msg)
            raise KeyError(error_msg)
        return params[param_key]
