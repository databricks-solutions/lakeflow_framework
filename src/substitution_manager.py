import re
import os
from typing import Dict, Any, Optional, Pattern, List
from functools import cached_property

import utility
import pipeline_config

class SubstitutionManager():
    """
    Manages token substitutions in strings and nested dictionaries.
    
    This class handles token replacements in configuration files, supporting both
    framework-level and pipeline-level substitutions with optional additional tokens.
    
    Attributes:
        framework_substitutions_path (str): Path to framework substitutions JSON
        pipeline_substitutions_path (str): Path to pipeline substitutions JSON
        additional_tokens (Optional[Dict[str, str]]): Optional dictionary of additional token replacements
    
    Methods:
        substitute_string(input_string: str) -> str:
            Substitute tokens in a string.

        substitute_dict(input_dict: Dict[str, Any]) -> Dict[str, Any]:
            Substitute tokens in a nested dictionary.
    """
    
    # Compiled regex patterns for token substitution
    DEFAULT_TOKEN_PATTERN: Pattern = re.compile(r'\{(\w+)\}')
    
    def __init__(
        self,
        framework_substitutions_paths: List[str],
        pipeline_substitutions_paths: List[str],
        additional_tokens: Optional[Dict[str, str]] = None
    ):
        """Initialize the SubstitutionManager.
        
        Args:
            framework_substitutions_paths: List of paths to framework substitutions files.
            pipeline_substitutions_paths: List of paths to pipeline substitutions files.
            additional_tokens: Optional dictionary of additional token replacements
        """
        if not framework_substitutions_paths or not pipeline_substitutions_paths:
            raise ValueError("Framework and pipeline substitution paths must be provided as a list.")
            
        self.framework_substitutions_paths = framework_substitutions_paths
        self.pipeline_substitutions_paths = pipeline_substitutions_paths
        self.additional_tokens = additional_tokens or {}

        self.logger = pipeline_config.get_logger()

        self._substitutions_config = self._load_substitution_config()

    def _load_file(self, paths: List[str], config_type: str) -> Dict[str, Any]:
        """Load a single substitution file from a list of possible paths."""
        existing_files = [path for path in paths if os.path.exists(path)]
        
        if len(existing_files) > 1:
            raise ValueError(f"Multiple {config_type} substitutions files found. Only one is allowed: {existing_files}")
        
        if len(existing_files) == 1:
            file_path = existing_files[0]
            self.logger.info("Retrieving %s substitutions from: %s", config_type, file_path)
            return utility.load_config_file_auto(file_path, False) or {}
        
        self.logger.warning("No %s substitutions file found.", config_type)
        return {}

    def _load_substitution_config(self) -> Dict[str, Any]:
        """Load and merge framework and pipeline substitutions."""
        framework_subs = self._load_file(self.framework_substitutions_paths, "framework")
        pipeline_subs = self._load_file(self.pipeline_substitutions_paths, "pipeline")
        
        return utility.merge_dicts_recursively(pipeline_subs, framework_subs)

    @cached_property
    def tokens(self) -> Dict[str, str]:
        """Get merged tokens with additional tokens applied."""
        tokens = self._substitutions_config.get('tokens', {})
        if self.additional_tokens:
            tokens = utility.merge_dicts_recursively(tokens, self.additional_tokens)

        # Apply substitutions to token values themselves
        return {
            k: self._substitute_tokens_in_string(v, tokens)
            for k, v in tokens.items()
        }

    @cached_property
    def prefix_suffix_rules(self) -> Dict[str, Dict[str, str]]:
        """Get prefix/suffix rules with tokens substituted."""
        rules = self._substitutions_config.get('prefix_suffix', {})
            
        # Apply substitutions to prefix/suffix values
        return {
            k: {
                rule_k: self._substitute_tokens_in_string(rule_v, self.tokens)
                for rule_k, rule_v in v.items()
            }
            for k, v in rules.items()
        }

    def substitute_string(self, input_string: str, additional_tokens: Optional[Dict[str, Any]] = None) -> str:
        """Substitute tokens in a string.
        
        Args:
            input_string: String containing tokens to replace
            additional_tokens: Optional dictionary of additional token replacements.
                Dictionary values will be converted to strings, with nested dictionaries being JSON serialized.
            
        Returns:
            str: String with all tokens substituted
        """
        if not isinstance(input_string, str):
            raise TypeError(f"Expected string input, got {type(input_string)}")
        
        tokens = self.tokens
        if additional_tokens:
            tokens = utility.merge_dicts_recursively(self.tokens.copy(), additional_tokens)

        return self._substitute_tokens_in_string(input_string, tokens)

    def substitute_dict(self, data: Any) -> Any:
        """
        Substitute tokens and apply prefix/suffix rules to a string or dictionary.
        
        Args:
            data: The data to process (dict, list, or string)

        Returns:
            Processed data with tokens references replaced by their values
        """
        result = self._substitute_tokens(data)
        result = self._apply_prefix_suffix(result)
        return result

    def _substitute_tokens_in_string(
        self, 
        value: str, 
        tokens: Dict[str, str], 
        pattern: Optional[Pattern] = None
    ) -> str:
        """Replace tokens in a string using regex substitution."""
        if not isinstance(value, str):
            return value
            
        def replace_token(match):
            token = match.group(1)
            if token in self.additional_tokens:
                return self.additional_tokens[token]
            elif token in tokens:
                return tokens[token]
            return match.group(0)
            
        return (pattern or self.DEFAULT_TOKEN_PATTERN).sub(replace_token, value)

    def _substitute_tokens(self, data: Any) -> Any:
        """Substitute tokens in a string or dictionary"""
        if isinstance(data, dict):
            return {k: self._substitute_tokens(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_tokens(item) for item in data]
        elif isinstance(data, str):
            return self._substitute_tokens_in_string(data, self.tokens, self.DEFAULT_TOKEN_PATTERN)
        else:
            return data

    def _apply_prefix_suffix(self, data: Any) -> Any:
        """Apply prefix/suffix rules to a string or dictionary."""
        def apply_value(key: str, value: Any) -> Any:
            if isinstance(value, str) and key in self.prefix_suffix_rules:
                rules = self.prefix_suffix_rules[key]
                if 'prefix' in rules:
                    value = rules['prefix'] + value
                if 'suffix' in rules:
                    value = value + rules['suffix']
            return value

        if isinstance(data, dict):
            return {k: apply_value(k, v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._apply_prefix_suffix(item) for item in data]
        else:
            return data