import os
import yaml
import logging
import traceback
import subprocess
import tempfile
from typing import Optional
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename
from openapi_spec_validator.validation.exceptions import ValidatorDetectError
from mcp.server.fastmcp import FastMCP, Context

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the MCP server
mcp = FastMCP("OpenAPI Validator Server")

def format_validation_error(error):
    """
    Format validation errors to provide more detailed feedback.
    If the error is a ValidatorDetectError, advise on the possible missing or invalid OpenAPI version field.
    Otherwise, if the error has an 'errors' attribute (a list of issues), they are concatenated.
    Fallback to formatting the exception using traceback.
    """
    if isinstance(error, ValidatorDetectError):
        return (
            f"{str(error)}. It appears the validator could not determine the OpenAPI version. "
            "Please ensure your spec includes a valid 'openapi' (for OpenAPI 3.x) or 'swagger' (for OpenAPI 2.x) field."
        )
    
    if hasattr(error, 'errors'):
        errors = error.errors
        if isinstance(errors, list):
            return "Validation errors: " + "; ".join(str(err) for err in errors)
    
    return "".join(traceback.format_exception_only(type(error), error)).strip()

@mcp.tool()
def validate_structure(ctx: Context, spec: Optional[str] = None, file_path: Optional[str] = None, directory: Optional[str] = None) -> str:
    """
    Validates an OpenAPI specification provided as a text string, a file path, or all files in a directory.

    Parameters:
    - spec (str): The OpenAPI specification as a YAML/JSON formatted string.
    - file_path (str): The path to the OpenAPI specification file.
    - directory (str): The path to a directory containing OpenAPI specification files.

    Returns:
    - str: Validation result message.
    """
    try:
        if spec:
            try:
                spec_dict = yaml.safe_load(spec)
                if spec_dict is None:
                    return "Error: Invalid YAML/JSON content."
                base_uri = None
                validate_spec(spec_dict, base_uri=base_uri)
                logging.info("OpenAPI specification is valid.")
                return "OpenAPI specification is valid."
            except yaml.YAMLError as e:
                error_message = f"YAML parsing error: {str(e)}"
                logging.error(error_message)
                return error_message
            except Exception as e:
                error_message = f"Validation error: {format_validation_error(e)}"
                logging.error(error_message)
                return error_message

        elif file_path:
            try:
                spec_dict, base_uri = read_from_filename(file_path)
                validate_spec(spec_dict, base_uri=base_uri)
                logging.info(f"OpenAPI specification in '{file_path}' is valid.")
                return f"OpenAPI specification in '{file_path}' is valid."
            except FileNotFoundError:
                error_message = f"File not found: '{file_path}'"
                logging.error(error_message)
                return error_message
            except yaml.YAMLError as e:
                error_message = f"YAML parsing error in '{file_path}': {str(e)}"
                logging.error(error_message)
                return error_message
            except Exception as e:
                error_message = f"Validation error in '{file_path}': {format_validation_error(e)}"
                logging.error(error_message)
                return error_message

        elif directory:
            if not os.path.isdir(directory):
                logging.error(f"Error: '{directory}' is not a valid directory.")
                return f"Error: '{directory}' is not a valid directory."
            if not os.listdir(directory):
                logging.error(f"Error: The directory '{directory}' is empty.")
                return f"Error: The directory '{directory}' is empty."

            results = []
            valid_count = 0
            invalid_count = 0
            processed_count = 0
            
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(('.yaml', '.yml', '.json')):
                        processed_count += 1
                        curr_file_path = os.path.join(root, file)
                        try:
                            spec_dict, base_uri = read_from_filename(curr_file_path)
                            validate_spec(spec_dict, base_uri=base_uri)
                            results.append(f"✓ '{curr_file_path}' is valid.")
                            logging.info(f"'{curr_file_path}' is valid.")
                            valid_count += 1
                        except FileNotFoundError:
                            error_message = f"✗ File not found: '{curr_file_path}'"
                            results.append(error_message)
                            logging.error(error_message)
                            invalid_count += 1
                        except yaml.YAMLError as e:
                            error_message = f"✗ YAML parsing error in '{curr_file_path}': {str(e)}"
                            results.append(error_message)
                            logging.error(error_message)
                            invalid_count += 1
                        except Exception as e:
                            error_message = f"✗ Validation error in '{curr_file_path}': {format_validation_error(e)}"
                            results.append(error_message)
                            logging.error(error_message)
                            invalid_count += 1
                            
            if processed_count == 0:
                return f"No OpenAPI specification files found in '{directory}'."
                
            summary = f"\nSummary: {valid_count} valid, {invalid_count} invalid, {processed_count} total files processed."
            return "\n".join(results) + summary
            
        else:
            logging.error("Error: No specification data or directory provided.")
            return "Error: No specification data or directory provided."
            
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logging.error(error_message)
        return error_message

@mcp.tool()
def validate_style(ctx: Context,
                    spec_file: Optional[str] = None,
                    options_file: Optional[str] = None) -> str:
    """
    Validates the style of an OpenAPI specification using the openapi-style-validator CLI JAR.
    Launches the CLI according to the README instructions (e.g. "java -jar openapi-style-validator.jar -s spec -o options").

    Parameters:
    - spec_file (str): Path to the OpenAPI specification file.
    - options_file (str): (Optional) Path to an options JSON file for the validator.

    Returns:
    - str: Validation result message.
    """

    jar_path = os.getenv("OPENAPI_STYLE_VALIDATOR_JAR",
                         os.path.join(os.path.dirname(__file__), "tools", "openapi-style-validator-cli.jar"))
    if not os.path.exists(jar_path):
        error_message = (
            f"Error: Java style validator CLI JAR not found at {jar_path}. "
            "Please build and place it in the 'tools' directory or set the OPENAPI_STYLE_VALIDATOR_JAR environment variable."
        )
        logging.error(error_message)
        return error_message

    if not spec_file or not os.path.isfile(spec_file):
        error_message = f"Error: Spec file '{spec_file}' is not valid or does not exist. Please provide a valid OpenAPI specification file."
        logging.error(error_message)
        return error_message

    abs_spec_file = os.path.abspath(spec_file)

    java_cmd = ["java", "-jar", jar_path, "-s", abs_spec_file]

    if options_file:
        if not os.path.isfile(options_file):
            error_message = f"Error: Options file '{options_file}' does not exist. Please provide a valid options JSON file."
            logging.error(error_message)
            return error_message
        abs_options = os.path.abspath(options_file)
        java_cmd.extend(["-o", abs_options])

    # Check if Java is available.
    java_check = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if java_check.returncode != 0:
        error_message = "Error: Java runtime is not installed or not available in the system's PATH."
        logging.error(error_message)
        return error_message

    logging.info(f"Running style validation using Java on '{abs_spec_file}' with command: {' '.join(java_cmd)}")
    proc = subprocess.run(java_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if proc.returncode != 0:
        # Fallback to stdout if stderr is empty.
        error_details = proc.stderr.strip() or proc.stdout.strip() or "Unknown error"
        error_message = f"Style Validation Error: {error_details}. Please check the OpenAPI Style Validator documentation for more details."
        logging.error(error_message)
        return error_message

    logging.info("Style validation passed.")
    return proc.stdout.strip()
    
if __name__ == "__main__":
    mcp.run()
