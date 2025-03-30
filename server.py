import os
import yaml
from typing import Optional
from openapi_spec_validator import validate_spec, OpenAPIValidationError
from openapi_spec_validator.readers import read_from_filename
from mcp.server.fastmcp import FastMCP, Context

# Initialize the MCP server
mcp = FastMCP("OpenAPI Validator Server")

@mcp.tool()
def validate_openapi_spec(ctx: Context, spec: Optional[str] = None, file_path: Optional[str] = None) -> str:
    """
    Validates an OpenAPI specification provided as a text string or a file path.

    Parameters:
    - spec (str): The OpenAPI specification as a YAML/JSON formatted string.
    - file_path (str): The path to the OpenAPI specification file.

    Returns:
    - str: Validation result message.
    """
    try:
        if spec:
            # Load the specification from the provided text
            spec_dict = yaml.safe_load(spec)
            base_uri = None
        elif file_path:
            # Load the specification from the provided file path
            spec_dict, base_uri = read_from_filename(file_path)
        else:
            return "Error: No specification data provided."

        # Validate the specification
        validate_spec(spec_dict, base_uri=base_uri)
        return "OpenAPI specification is valid."
    except OpenAPIValidationError as e:
        return f"Validation Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
