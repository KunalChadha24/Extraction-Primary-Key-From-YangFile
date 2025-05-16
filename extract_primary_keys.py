#!/usr/bin/env python3
"""
Script to extract primary keys from YANG files in a ZIP archive.
"""

import argparse
import os
import re
import tempfile
import zipfile
import json
import logging
import io

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_yang_files(zip_path, temp_dir):
    """
    Extract YANG files from ZIP archive to a temporary directory.
    Returns a list of extracted YANG file paths that match the pattern <version>-<yangTableName>.yang
    """
    yang_files = []
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # List all files in the ZIP
        all_files = zip_ref.namelist()
        logger.debug(f"All files in ZIP: {all_files}")
        
        # Filter for YANG files with the pattern <version>-<yangTableName>.yang
        pattern = re.compile(r'.*-.*\.yang$')
        for file_path in all_files:
            if pattern.match(file_path) and not file_path.endswith('/'):
                # Skip files that are just <version>.yang (no hyphen)
                base_name = os.path.basename(file_path)
                if '-' in base_name:
                    # Extract the file
                    zip_ref.extract(file_path, temp_dir)
                    yang_files.append(os.path.join(temp_dir, file_path))
                    logger.info(f"Extracted: {file_path}")
    
    logger.info(f"Total extracted YANG files: {len(yang_files)}")
    return yang_files

def extract_keys_using_regex(yang_file_path):
    """
    Parse a YANG file using regex to extract tables (lists) and their primary keys.
    Returns a dictionary with tables as keys and primary keys as values.
    """
    tables_and_keys = {}
    
    try:
        with open(yang_file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Find all list definitions and their keys
        list_pattern = r'list\s+(\w+)\s*{[^{]*?key\s+"([^"]+)"'
        matches = re.finditer(list_pattern, content, re.DOTALL)
        
        for match in matches:
            table_name = match.group(1)
            key_value = match.group(2).strip()
            
            # Handle multiple keys (space-separated)
            keys = key_value.split()
            if len(keys) == 1:
                tables_and_keys[table_name] = keys[0]
            else:
                tables_and_keys[table_name] = keys
                
            logger.debug(f"Found table: {table_name}, key(s): {keys}")
    
    except Exception as e:
        logger.error(f"Error parsing {yang_file_path}: {str(e)}")
    
    logger.info(f"Extracted {len(tables_and_keys)} tables from {os.path.basename(yang_file_path)}")
    return tables_and_keys

def extract_primary_keys_from_zip(zip_path):
    """
    Extract primary keys from all YANG files in a ZIP archive.
    Returns a dictionary with tables as keys and primary keys as values.
    """
    all_tables_and_keys = {}
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract YANG files from ZIP
        yang_files = extract_yang_files(zip_path, temp_dir)
        
        if not yang_files:
            logger.warning("No YANG files found matching the pattern <version>-<yangTableName>.yang")
            # Let's try to extract and examine a sample file to debug
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                all_files = zip_ref.namelist()
                for file_path in all_files:
                    if file_path.endswith('.yang') and not file_path.endswith('/'):
                        logger.info(f"Examining sample file: {file_path}")
                        with zip_ref.open(file_path) as f:
                            content = f.read(500)  # Read first 500 bytes
                            logger.info(f"Sample content: {content}")
                        break
        
        # Parse each YANG file
        for yang_file in yang_files:
            logger.info(f"Parsing: {yang_file}")
            try:
                tables_and_keys = extract_keys_using_regex(yang_file)
                # Update the main dictionary
                all_tables_and_keys.update(tables_and_keys)
            except Exception as e:
                logger.error(f"Error parsing {yang_file}: {str(e)}")
    
    return all_tables_and_keys

def main():
    """Main function to parse command line arguments and extract primary keys."""
    parser = argparse.ArgumentParser(description='Extract primary keys from YANG files in a ZIP archive.')
    parser.add_argument('zip_file', help='Path to the ZIP file containing YANG files')
    parser.add_argument('--output', '-o', help='Output file path (JSON format)', default=None)
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Extract primary keys
    try:
        primary_keys = extract_primary_keys_from_zip(args.zip_file)
        
        # Output the results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(primary_keys, f, indent=2)
            logger.info(f"Results saved to {args.output}")
        else:
            print(json.dumps(primary_keys, indent=2))
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())