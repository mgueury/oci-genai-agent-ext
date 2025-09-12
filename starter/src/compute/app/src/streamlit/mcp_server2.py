import sys
import json
import logging

# Set up basic logging to a file for debugging, as stdout is used for communication.
logging.basicConfig(filename='mcp_server.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_weather(location: str, unit: str = "celsius"):
    """
    Get the current weather for a specific location.
    """
    if "new york" in location.lower():
        return f"The weather in New York is 15 degrees {unit} and sunny."
    elif "london" in location.lower():
        return f"The weather in London is 10 degrees {unit} and cloudy."
    else:
        return f"Sorry, I don't have weather information for {location}."

def send_email(recipient: str, subject: str, body: str):
    """
    Sends an email to a recipient.
    """
    # This is a dummy function for demonstration.
    logging.info(f"Simulating email send to {recipient}")
    return f"Email successfully sent to {recipient} with subject '{subject}'."

# --- Tool Registry ---
TOOLS = {
    "get_weather": {
        "function": get_weather,
        "description": "Get the current weather for a specific location.",
        "parameters": [
            {"name": "location", "type": "string", "description": "The city and state, e.g. San Francisco, CA", "required": True},
            {"name": "unit", "type": "string", "description": "The unit of temperature, 'celsius' or 'fahrenheit'", "required": False}
        ]
    },
    "send_email": {
        "function": send_email,
        "description": "Sends an email to a given recipient with a subject and body.",
        "parameters": [
            {"name": "recipient", "type": "string", "description": "The email address of the recipient.", "required": True},
            {"name": "subject", "type": "string", "description": "The subject of the email.", "required": True},
            {"name": "body", "type": "string", "description": "The body content of the email.", "required": True}
        ]
    }
}

def list_tools():
    """Prepares the list of tools for the client."""
    tool_list = []
    for name, details in TOOLS.items():
        tool_list.append({
            "name": name,
            "description": details["description"],
            "parameters": details["parameters"]
        })
    return tool_list

def call_tool(name, arguments):
    """Calls a tool by name with given arguments."""
    if name not in TOOLS:
        return {"error": f"Tool '{name}' not found."}

    tool_info = TOOLS[name]
    func = tool_info["function"]

    try:
        result = func(**arguments)
        return result
    except Exception as e:
        logging.error(f"Error calling tool {name}: {e}")
        return {"error": f"An error occurred while executing the tool: {str(e)}"}

def main():
    """Main loop to listen for JSON-RPC requests on stdin."""
    logging.info("MCP Server started and listening on stdin.")
    for line in sys.stdin:
        try:
            logging.info(f"Received raw request: {line.strip()}")
            request = json.loads(line)
            request_id = request.get("id")

            response = {"jsonrpc": "2.0", "id": request_id}

            method = request.get("method")
            if method == "mcp.list_tools":
                response["result"] = list_tools()
            elif method == "mcp.call_tool":
                params = request.get("params", {})
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                response["result"] = call_tool(tool_name, tool_args)
            else:
                response["error"] = {"code": -32601, "message": "Method not found"}

            json_response = json.dumps(response)
            logging.info(f"Sending response: {json_response}")
            print(json_response, flush=True)

        except json.JSONDecodeError:
            logging.error(f"Failed to decode JSON: {line.strip()}")
            error_response = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
            print(json.dumps(error_response), flush=True)
        except Exception as e:
            logging.error(f"An unexpected error occurred in main loop: {e}")

if __name__ == "__main__":
    main()
