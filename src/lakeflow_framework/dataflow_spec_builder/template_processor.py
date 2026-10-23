import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Tuple

from lakeflow_framework.constants import FrameworkPaths, PipelineBundlePaths, SupportedSpecFormat
import lakeflow_framework.pipeline_config as pipeline_config
import lakeflow_framework.utility as utility


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
        max_workers (int): Worker threads for expanding parameter sets
        logger: Logger instance for tracking template processing
        
    Note:
        Template definitions are cached after first load. The template file is loaded
        once per ``process_template_spec`` call; parameter-set expansion may run in
        parallel and never writes the template cache from worker threads.
    """

    class DefinitionKeys:
        """Constants for dictionary keys for the template dataflow spec JSON files"""
        TEMPLATE = "template"
        PARAMETER_DEFINITIONS = "parameters"
        DATA_FLOW_ID = "dataFlowId"
        PARAM_TYPE = "type"
        PARAM_REQUIRED = "required"
        PARAM_DEFAULT = "default"
        FOR_EACH = "$for_each"
        FOR_EACH_AS = "as"
        FOR_EACH_NODE = "node"
        FOR_EACH_VALUE = "value"

    class SpecKeys:
        """Constants for dictionary keys for the template dataflow spec JSON files"""
        TEMPLATE_NAME = "template"
        GLOBAL_DEFAULTS = "global_defaults"
        # Legacy camelCase spelling, still accepted for backward compatibility.
        GLOBAL_DEFAULTS_LEGACY = "globalDefaults"
        PARAMETER_SETS = "parameter_sets"
        # Legacy camelCase spelling, still accepted for backward compatibility.
        PARAMETER_SETS_LEGACY = "parameterSets"
        DATA_FLOW_ID = "dataFlowId"
        TAGS = "tags"
        TAG_IS_TEMPLATE_GENERATED = "_isTemplateGenerated"
        TAG_TEMPLATE_NAME = "_templateName"
    
    def __init__(self, bundle_path: str, framework_path: str, max_workers: int = 1):
        """Initialize the template processor."""
        self.bundle_path = bundle_path
        self.framework_path = framework_path
        self.max_workers = max(1, int(max_workers))
        self.logger = pipeline_config.get_logger()
        # ${param.<key>} or ${<loop_alias>.<dotted.path>}
        self._pattern = re.compile(
            r'\$\{(param|[a-zA-Z_][a-zA-Z0-9_]*)\.([^}]+)\}'
        )
        
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
        dataflow_spec_params = template_spec.get(
            self.SpecKeys.PARAMETER_SETS,
            template_spec.get(self.SpecKeys.PARAMETER_SETS_LEGACY, []),
        )
        global_defaults = self._resolve_global_defaults(template_spec, file_path)
        
        # Validate template spec structure
        if not template_name:
            error_msg = "Template name must be provided in template spec"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        if not dataflow_spec_params:
            error_msg = f"Dataflow specs must be provided for template: {template_name}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Load template content and validate against schema (main thread only —
        # workers must not write _template_cache).
        template_definition = self._get_template_definition(template_name, spec_file_format)
        
        # Get and validate parameter definitions
        param_definitions = self._get_template_parameters(template_definition, template_name)
        spec_template = template_definition.get(self.DefinitionKeys.TEMPLATE, {})

        processed_specs = self._expand_parameter_sets(
            file_path=file_path,
            template_name=template_name,
            parameter_sets=dataflow_spec_params,
            param_definitions=param_definitions,
            spec_template=spec_template,
            global_defaults=global_defaults,
        )
        
        self.logger.info(
            f"Successfully generated {len(processed_specs)} specs from template '{template_name}'"
        )
        
        return processed_specs

    def _resolve_global_defaults(self, template_spec: Dict, file_path: str) -> Dict:
        """Return shared defaults from snake_case or legacy camelCase key."""
        if self.SpecKeys.GLOBAL_DEFAULTS in template_spec:
            global_defaults = template_spec.get(self.SpecKeys.GLOBAL_DEFAULTS)
            key_label = self.SpecKeys.GLOBAL_DEFAULTS
        elif self.SpecKeys.GLOBAL_DEFAULTS_LEGACY in template_spec:
            global_defaults = template_spec.get(self.SpecKeys.GLOBAL_DEFAULTS_LEGACY)
            key_label = self.SpecKeys.GLOBAL_DEFAULTS_LEGACY
        else:
            return {}

        if global_defaults is None:
            return {}
        if not isinstance(global_defaults, dict):
            error_msg = (
                f"'{key_label}' must be an object when provided "
                f"(template spec: {file_path})"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        return global_defaults

    def _expand_parameter_sets(
        self,
        file_path: str,
        template_name: str,
        parameter_sets: list,
        param_definitions: Dict,
        spec_template: Dict,
        global_defaults: Dict | None = None,
    ) -> Dict[str, Dict]:
        """Expand each parameter set into a concrete spec, optionally in parallel."""
        shared_defaults = global_defaults or {}
        if self.max_workers == 1 or len(parameter_sets) <= 1:
            processed_specs = {}
            for params in parameter_sets:
                spec_key, generated_spec = self._expand_one_parameter_set(
                    file_path,
                    template_name,
                    params,
                    param_definitions,
                    spec_template,
                    shared_defaults,
                )
                processed_specs[spec_key] = generated_spec
            return processed_specs

        processed_specs = {}
        workers = min(self.max_workers, len(parameter_sets))
        self.logger.debug(
            "Expanding %s parameter sets for template '%s' with %s workers",
            len(parameter_sets),
            template_name,
            workers,
        )
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    self._expand_one_parameter_set,
                    file_path,
                    template_name,
                    params,
                    param_definitions,
                    spec_template,
                    shared_defaults,
                )
                for params in parameter_sets
            ]
            for future in as_completed(futures):
                spec_key, generated_spec = future.result()
                processed_specs[spec_key] = generated_spec
        return processed_specs

    def _expand_one_parameter_set(
        self,
        file_path: str,
        template_name: str,
        params: Dict,
        param_definitions: Dict,
        spec_template: Dict,
        global_defaults: Dict | None = None,
    ) -> Tuple[str, Dict]:
        """Validate one parameter set and generate its concrete spec."""
        # Per-set keys override global_defaults; template definition defaults
        # still apply afterward for any remaining optional params.
        merged_params = {**(global_defaults or {}), **params}
        dataflow_id = merged_params.get(self.SpecKeys.DATA_FLOW_ID)
        spec_key = f'{file_path}#template_{template_name}_{dataflow_id}'

        processed_params = self._validate_and_apply_defaults(
            merged_params, param_definitions, spec_key
        )

        try:
            generated_spec = self._generate_spec(spec_template, processed_params)

            tags = generated_spec.get(self.SpecKeys.TAGS, {})
            tags[self.SpecKeys.TAG_IS_TEMPLATE_GENERATED] = True
            tags[self.SpecKeys.TAG_TEMPLATE_NAME] = template_name
            generated_spec[self.SpecKeys.TAGS] = tags

            self.logger.debug(f"Generated spec from template: '{spec_key}'")
            return spec_key, generated_spec
        except Exception as e:
            error_msg = f"Failed to generate spec from template '{spec_key}': {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e
    
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
        # List params referenced only via $for_each (not ${param.*}) still count as used
        unique_placeholders |= self._collect_for_each_list_names(template_content)
        
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
    
    def _collect_for_each_list_names(self, obj) -> set:
        """Return list-parameter names referenced by ``$for_each`` markers."""
        names: set = set()
        if isinstance(obj, dict):
            if self.DefinitionKeys.FOR_EACH in obj:
                list_name = obj[self.DefinitionKeys.FOR_EACH]
                if isinstance(list_name, str) and list_name:
                    names.add(list_name)
            for value in obj.values():
                names |= self._collect_for_each_list_names(value)
        elif isinstance(obj, list):
            for item in obj:
                names |= self._collect_for_each_list_names(item)
        return names

    def _generate_spec(self, obj, params: Dict, loop_bindings: Dict | None = None):
        """Recursively process a value, expanding ``$for_each`` and placeholders."""
        bindings = loop_bindings or {}

        if isinstance(obj, dict):
            if self.DefinitionKeys.FOR_EACH in obj:
                # Property-value form: replace this object with an expanded array
                return self._expand_for_each(
                    obj, params, bindings, fragment_key=self.DefinitionKeys.FOR_EACH_VALUE
                )
            result = {
                self._generate_spec(k, params, bindings): self._generate_spec(
                    v, params, bindings
                )
                for k, v in obj.items()
            }
            if non_string_keys := [k for k in result.keys() if not isinstance(k, str)]:
                error_msg = f"Dictionary keys must be strings, found: {non_string_keys}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            return result

        if isinstance(obj, list):
            result = []
            for item in obj:
                if isinstance(item, dict) and self.DefinitionKeys.FOR_EACH in item:
                    # Array-element form: splice N cloned fragments into the list
                    result.extend(
                        self._expand_for_each(
                            item,
                            params,
                            bindings,
                            fragment_key=self.DefinitionKeys.FOR_EACH_NODE,
                        )
                    )
                else:
                    result.append(self._generate_spec(item, params, bindings))
            return result

        if isinstance(obj, str):
            return self._replace_string_placeholders(obj, params, bindings)

        return obj

    def _expand_for_each(
        self,
        marker: Dict,
        params: Dict,
        loop_bindings: Dict,
        fragment_key: str,
    ) -> list:
        """Expand a ``$for_each`` marker into a list of generated fragments.

        Array-element form (``fragment_key=\"node\"``): each item becomes a nodespec
        node spliced into ``nodes``. Property-value form (``fragment_key=\"value\"``):
        each item becomes an element of an array property (e.g. ``sources``).
        Nested ``$for_each`` is not supported in v1.
        """
        if loop_bindings:
            error_msg = (
                "Nested '$for_each' is not supported; expand one list at a time"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        list_name = marker.get(self.DefinitionKeys.FOR_EACH)
        alias = marker.get(self.DefinitionKeys.FOR_EACH_AS, "item")
        if not isinstance(list_name, str) or not list_name:
            error_msg = "'$for_each' must be a non-empty string naming a list parameter"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        if not isinstance(alias, str) or not alias or alias == "param":
            error_msg = (
                f"'$for_each' 'as' must be a non-empty alias other than 'param' "
                f"(got {alias!r})"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        if fragment_key not in marker:
            form_hint = (
                "use 'node' when $for_each is a list element"
                if fragment_key == self.DefinitionKeys.FOR_EACH_NODE
                else "use 'value' when $for_each is a property value"
            )
            error_msg = (
                f"'$for_each' marker missing '{fragment_key}' fragment ({form_hint})"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        unexpected = set(marker.keys()) - {
            self.DefinitionKeys.FOR_EACH,
            self.DefinitionKeys.FOR_EACH_AS,
            fragment_key,
        }
        if unexpected:
            error_msg = (
                f"'$for_each' marker has unexpected keys: {sorted(unexpected)}"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        items = params.get(list_name)
        if items is None:
            error_msg = (
                f"'$for_each' list parameter '{list_name}' not found in params"
            )
            self.logger.error(error_msg)
            raise KeyError(error_msg)
        if not isinstance(items, list):
            error_msg = (
                f"'$for_each' parameter '{list_name}' must be a list, "
                f"got {type(items).__name__}"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        fragment = marker[fragment_key]
        expanded = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                error_msg = (
                    f"'$for_each' items in '{list_name}' must be objects "
                    f"(item {index} is {type(item).__name__})"
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            expanded.append(
                self._generate_spec(fragment, params, {alias: item})
            )
        return expanded

    def _replace_string_placeholders(
        self, text: str, params: Dict, loop_bindings: Dict | None = None
    ):
        """Replace ``${param.*}`` / ``${alias.*}`` placeholders in a string value."""
        bindings = loop_bindings or {}

        def resolve(match: re.Match):
            return self._resolve_placeholder_match(match, params, bindings)

        # Full replacement: entire string is a single placeholder (preserves type)
        if (m := self._pattern.fullmatch(text)):
            return resolve(m)

        # Partial replacement: string contains placeholders
        if self._pattern.search(text):
            return self._pattern.sub(lambda m: str(resolve(m)), text)

        return text

    def _resolve_placeholder_match(
        self, match: re.Match, params: Dict, loop_bindings: Dict
    ):
        """Resolve one ``${root.path}`` match to a concrete value."""
        root, path = match.group(1), match.group(2)
        if root == "param":
            return self._get_param_value(path, params)
        if root in loop_bindings:
            return self._get_nested_value(loop_bindings[root], path, root)
        error_msg = (
            f"Unknown placeholder root '{root}' in '${{{root}.{path}}}'; "
            f"expected 'param' or a $for_each alias"
        )
        self.logger.error(error_msg)
        raise KeyError(error_msg)

    def _get_nested_value(self, obj: Any, dotted_path: str, alias: str):
        """Walk ``dotted_path`` through a loop-item object."""
        current = obj
        for part in dotted_path.split("."):
            if not isinstance(current, dict) or part not in current:
                error_msg = (
                    f"Path '{dotted_path}' not found on $for_each alias '{alias}'"
                )
                self.logger.error(error_msg)
                raise KeyError(error_msg)
            current = current[part]
        return current

    def _get_param_value(self, param_key: str, params: Dict):
        """Get a parameter value from the params dictionary."""
        if param_key not in params:
            error_msg = f"Parameter '{param_key}' not found in params"
            self.logger.error(error_msg)
            raise KeyError(error_msg)
        return params[param_key]
