"""
JSON to YAML Converter for Lakeflow Framework Bundles

This script provides utilities to convert Lakeflow Framework pipeline bundles from JSON format to YAML format.
It handles conversion of:
- Dataflow specifications (main specs)
- Flow group specifications  
- Data quality expectations (DQE)
- Substitution files
- Secrets files

The converter can optionally validate converted files using the validate_dataflows.py script.

Usage:
    # Convert a single JSON file to YAML with validation
    python convert_json_to_yaml.py --file path/to/file.json
    
    # Convert an entire bundle with validation
    python convert_json_to_yaml.py --bundle path/to/bundle --output path/to/output_bundle
    
    # Convert without validation
    python convert_json_to_yaml.py --bundle path/to/bundle --no-validate
    
    # Dry run to see what would be converted
    python convert_json_to_yaml.py --bundle path/to/bundle --dry-run
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import yaml


def validate_with_validation_script(target_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate dataflow files using the validate_dataflows.py script.
    
    Args:
        target_path: Path to the directory containing dataflows to validate
        
    Returns:
        Tuple of (success, error_messages)
    """
    script_dir = Path(__file__).parent
    validate_script = script_dir / "validate_dataflows.py"
    
    if not validate_script.exists():
        return False, [f"Validation script not found: {validate_script}"]
    
    try:
        # Run the validation script
        result = subprocess.run(
            [sys.executable, str(validate_script), str(target_path)],
            capture_output=True,
            text=True,
            check=False
        )
        
        # The script returns 0 for success, 1 for failure
        if result.returncode == 0:
            return True, []
        else:
            # Parse error output
            errors = result.stdout.split('\n') if result.stdout else []
            return False, errors
            
    except Exception as e:  # pylint: disable=broad-except
        return False, [f"Error running validation script: {e}"]


def update_dqe_path_extensions(data: Any) -> Any:
    """
    Recursively update dataQualityExpectationsPath extensions from .json to .yaml.
    
    This function walks through the data structure and updates any
    dataQualityExpectationsPath properties that end with .json to end with .yaml instead.
    
    Args:
        data: The data structure to update (dict, list, or primitive)
        
    Returns:
        The updated data structure
    """
    if isinstance(data, dict):
        updated_dict = {}
        for key, value in data.items():
            if key == 'dataQualityExpectationsPath' and isinstance(value, str):
                # Replace .json extension with .yaml
                if value.endswith('.json'):
                    updated_dict[key] = value[:-5] + '.yaml'
                else:
                    updated_dict[key] = value
            else:
                # Recursively process nested structures
                updated_dict[key] = update_dqe_path_extensions(value)
        return updated_dict
    elif isinstance(data, list):
        return [update_dqe_path_extensions(item) for item in data]
    else:
        return data


def json_to_yaml_basic(json_data: Dict[str, Any]) -> str:
    """
    Convert JSON data to YAML format with clean formatting.
    
    This is the most basic conversion function that handles the core transformation.
    
    Args:
        json_data: Dictionary containing the JSON data
        
    Returns:
        str: YAML formatted string
        
    Example:
        >>> data = {"key": "value", "nested": {"item": 1}}
        >>> yaml_str = json_to_yaml_basic(data)
        >>> print(yaml_str)
        key: value
        nested:
          item: 1
    """
    return yaml.dump(
        json_data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        indent=2,
        width=120
    )


def convert_json_file_to_yaml(
    input_path: str,
    output_path: str = None,
    overwrite: bool = False
) -> str:
    """
    Convert a single JSON file to YAML format.
    
    Args:
        input_path: Path to the input JSON file
        output_path: Path for the output YAML file (optional, defaults to same name with .yaml extension)
        overwrite: Whether to overwrite existing files
        
    Returns:
        str: Path to the created YAML file
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        FileExistsError: If output file exists and overwrite is False
        ValueError: If input file is not valid JSON
    """
    # Validate input file
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Read JSON file
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON file '{input_path}': {e}") from e
    
    # Update dataQualityExpectationsPath extensions from .json to .yaml
    json_data = update_dqe_path_extensions(json_data)
    
    # Determine output path
    if output_path is None:
        output_path = input_path.with_suffix('.yaml')
    else:
        output_path = Path(output_path)
    
    # Check if output file exists
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {output_path}. Use overwrite=True to replace.")
    
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert and write YAML
    yaml_content = json_to_yaml_basic(json_data)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    
    return str(output_path)


def get_file_type_and_new_name(file_path: Path) -> Tuple[str, str]:
    """
    Determine the file type and generate the appropriate YAML filename.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Tuple of (file_type, new_filename) where file_type is one of:
        'main_spec', 'flow_group', 'expectations', 'secrets', 'substitutions', 'other'
    """
    filename = file_path.name
    
    # Check for main spec files
    if filename.endswith('_main.json'):
        base_name = filename[:-len('_main.json')]
        return 'main_spec', f"{base_name}_main.yaml"
    
    # Check for flow group files
    if filename.endswith('_flow.json'):
        base_name = filename[:-len('_flow.json')]
        return 'flow_group', f"{base_name}_flow.yaml"
    
    # Check for secrets files
    if filename.endswith('_secrets.json'):
        base_name = filename[:-len('_secrets.json')]
        return 'secrets', f"{base_name}_secrets.yaml"
    
    # Check for substitutions files
    if filename.endswith('_substitutions.json'):
        base_name = filename[:-len('_substitutions.json')]
        return 'substitutions', f"{base_name}_substitutions.yaml"
    
    # Check for expectations files (in expectations directory)
    if 'expectations' in str(file_path.parent) or filename.endswith('_dqe.json'):
        base_name = filename[:-len('.json')]
        return 'expectations', f"{base_name}_expectations.yaml"
    
    # Other JSON files - typically schemas, don't convert
    return 'other', filename


def convert_bundle(
    source_bundle_path: str,
    target_bundle_path: str,
    overwrite: bool = False,
    convert_schemas: bool = False,
    validate: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Convert an entire Lakeflow Framework bundle from JSON to YAML format with optional validation.
    
    This function:
    1. Copies the entire bundle structure to a new location
    2. Converts all relevant JSON files to YAML format:
       - Dataflow specifications (*_main.json -> *_main.yaml)
       - Flow group specifications (*_flow.json -> *_flow.yaml)
       - Data quality expectations (*_dqe.json -> *_expectations.yaml)
       - Substitution files (*_substitutions.json -> *_substitutions.yaml)
       - Secrets files (*_secrets.json -> *_secrets.yaml)
    3. Removes the original JSON files
    4. Optionally validates converted files using validate_dataflows.py
    
    Args:
        source_bundle_path: Path to the source bundle directory
        target_bundle_path: Path to the target bundle directory
        overwrite: Whether to overwrite existing target bundle
        convert_schemas: Whether to convert schema JSON files (default: False, as schemas typically stay JSON)
        validate: Whether to validate converted files using validate_dataflows.py (default: True)
        dry_run: If True, only print what would be done without making changes
        
    Returns:
        Dict containing conversion statistics:
        {
            'copied_files': int,
            'converted_files': int,
            'removed_files': int,
            'validation_errors': int,
            'errors': List[str],
            'converted_by_type': {
                'main_spec': int,
                'flow_group': int,
                'expectations': int,
                'secrets': int,
                'substitutions': int
            }
        }
    """
    source_path = Path(source_bundle_path)
    target_path = Path(target_bundle_path)
    
    # Validation
    if not source_path.exists():
        raise FileNotFoundError(f"Source bundle not found: {source_path}")
    
    if target_path.exists():
        if not overwrite:
            raise FileExistsError(
                f"Target bundle already exists: {target_path}. Use overwrite=True to replace."
            )
        if not dry_run:
            shutil.rmtree(target_path)
    
    # Initialize statistics
    stats = {
        'copied_files': 0,
        'converted_files': 0,
        'removed_files': 0,
        'validation_errors': 0,
        'errors': [],
        'converted_by_type': {
            'main_spec': 0,
            'flow_group': 0,
            'expectations': 0,
            'secrets': 0,
            'substitutions': 0,
            'other': 0
        }
    }
    
    print(f"{'[DRY RUN] ' if dry_run else ''}Converting bundle from {source_path} to {target_path}")
    
    # Step 1: Copy the entire bundle
    print(f"{'[DRY RUN] ' if dry_run else ''}Copying bundle structure...")
    if not dry_run:
        shutil.copytree(source_path, target_path)
    
    # Step 2: Find and convert JSON files
    print(f"{'[DRY RUN] ' if dry_run else ''}Scanning for JSON files to convert...")
    
    # Walk through the target directory
    json_files_to_convert = []
    for root, _, files in os.walk(target_path if not dry_run else source_path):
        for file in files:
            if file.endswith('.json'):
                file_path = Path(root) / file
                relative_path = file_path.relative_to(target_path if not dry_run else source_path)
                
                # Determine file type
                file_type, new_filename = get_file_type_and_new_name(file_path)
                
                # Skip schema files unless explicitly requested
                if file_type == 'other' and not convert_schemas:
                    continue
                
                json_files_to_convert.append((file_path, file_type, new_filename, relative_path))
    
    print(f"Found {len(json_files_to_convert)} JSON files to convert")
    
    # Step 3: Convert files
    for file_path, file_type, new_filename, relative_path in json_files_to_convert:
        try:
            print(f"  Converting: {relative_path} -> {new_filename}")
            
            if not dry_run:
                # Read JSON
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                # Update dataQualityExpectationsPath extensions from .json to .yaml
                json_data = update_dqe_path_extensions(json_data)
                
                # Convert to YAML
                yaml_content = json_to_yaml_basic(json_data)
                
                # Write YAML file
                yaml_path = file_path.parent / new_filename
                with open(yaml_path, 'w', encoding='utf-8') as f:
                    f.write(yaml_content)
                
                # Remove original JSON file
                file_path.unlink()
                
                stats['converted_files'] += 1
                stats['removed_files'] += 1
                stats['converted_by_type'][file_type] += 1
            else:
                stats['converted_files'] += 1
                stats['converted_by_type'][file_type] += 1
                
        except ValueError as e:
            error_msg = f"Conversion error in {relative_path}: {str(e)}"
            print(f"  ERROR: {error_msg}")
            stats['errors'].append(error_msg)
        except Exception as e:  # pylint: disable=broad-except
            error_msg = f"Error converting {relative_path}: {str(e)}"
            print(f"  ERROR: {error_msg}")
            stats['errors'].append(error_msg)
    
    # Step 4: Validate using validate_dataflows.py if requested
    if validate and not dry_run:
        print("\n" + "="*80)
        print("Validating converted files...")
        print("="*80)
        
        validation_success, validation_errors = validate_with_validation_script(target_path)
        
        if not validation_success:
            stats['validation_errors'] = 1
            if validation_errors:
                print("\nValidation output:")
                for error in validation_errors:
                    if error.strip():
                        print(error)
                stats['errors'].extend(validation_errors)
        else:
            print("✓ All dataflow files validated successfully")
    
    # Print summary
    print("\n" + "="*80)
    print("Conversion Summary:")
    print("="*80)
    print(f"Files converted: {stats['converted_files']}")
    print(f"  - Main specs: {stats['converted_by_type']['main_spec']}")
    print(f"  - Flow groups: {stats['converted_by_type']['flow_group']}")
    print(f"  - Expectations: {stats['converted_by_type']['expectations']}")
    print(f"  - Secrets: {stats['converted_by_type']['secrets']}")
    print(f"  - Substitutions: {stats['converted_by_type']['substitutions']}")
    if convert_schemas:
        print(f"  - Other (schemas, etc.): {stats['converted_by_type']['other']}")
    print(f"Files removed: {stats['removed_files']}")
    if validate:
        if stats['validation_errors'] > 0:
            print("Validation: FAILED")
        else:
            print("Validation: PASSED")
    if stats['errors']:
        print(f"\nErrors encountered: {len(stats['errors'])}")
        # Don't print all the errors here as they were already printed above
    print("="*80)
    
    return stats


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Lakeflow Framework bundles from JSON to YAML format with optional validation"
    )
    
    # Add arguments
    parser.add_argument(
        '--file',
        type=str,
        help='Convert a single JSON file to YAML'
    )
    parser.add_argument(
        '--bundle',
        type=str,
        help='Path to source bundle directory to convert'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Path to output location (for --file or --bundle)'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing files/directories'
    )
    parser.add_argument(
        '--convert-schemas',
        action='store_true',
        help='Also convert schema JSON files (by default they are skipped)'
    )
    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip validation (validation using validate_dataflows.py is enabled by default)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.file and not args.bundle:
        parser.error("Either --file or --bundle must be specified")
    
    if args.file and args.bundle:
        parser.error("Cannot specify both --file and --bundle")
    
    try:
        if args.file:
            # Convert single file
            output_path = convert_json_file_to_yaml(
                args.file,
                args.output,
                args.overwrite
            )
            print(f"Successfully converted: {args.file} -> {output_path}")
            
        elif args.bundle:
            # Convert bundle
            if not args.output:
                # Default output is source + "_yaml" suffix
                source_path = Path(args.bundle)
                args.output = str(source_path.parent / f"{source_path.name}_yaml")
            
            stats = convert_bundle(
                args.bundle,
                args.output,
                args.overwrite,
                args.convert_schemas,
                validate=not args.no_validate,
                dry_run=args.dry_run
            )
            
            if not args.dry_run:
                print(f"\nBundle successfully converted to: {args.output}")
            else:
                print("\nDry run complete. No files were modified.")
            
            # Exit with error code if there were errors
            if stats['errors']:
                sys.exit(1)
                
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        # Expected errors with clear messages
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-except
        # Unexpected errors
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()