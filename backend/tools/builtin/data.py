"""Data processing related tools"""
from ..factory import tool
from ..services import CalculatorService


@tool(
    name="calculator",
    description="Perform mathematical calculations. Supports basic arithmetic: addition, subtraction, multiplication, division, power, modulo, etc.",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression, e.g.: (2 + 3) * 4, 2 ** 10, 100 / 7"
            }
        },
        "required": ["expression"]
    },
    category="data"
)
def calculator(arguments: dict) -> dict:
    """
    Calculator tool

    Args:
        arguments: {
            "expression": "2 + 3 * 4"
        }

    Returns:
        {"result": 14}
    """
    expression = arguments["expression"]
    service = CalculatorService()
    return service.evaluate(expression)


@tool(
    name="text_process",
    description="Process text content, supports counting, format conversion and other operations.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to process"
            },
            "operation": {
                "type": "string",
                "description": "Operation type",
                "enum": ["count", "lines", "words", "upper", "lower", "reverse"]
            }
        },
        "required": ["text", "operation"]
    },
    category="data"
)
def text_process(arguments: dict) -> dict:
    """
    Text processing tool

    Args:
        arguments: {
            "text": "text content",
            "operation": "count" | "lines" | "words" | ...
        }

    Returns:
        Processing result
    """
    text = arguments["text"]
    operation = arguments["operation"]

    operations = {
        "count": lambda t: {"count": len(t)},
        "lines": lambda t: {"lines": len(t.splitlines())},
        "words": lambda t: {"words": len(t.split())},
        "upper": lambda t: {"result": t.upper()},
        "lower": lambda t: {"result": t.lower()},
        "reverse": lambda t: {"result": t[::-1]}
    }

    if operation not in operations:
        return {"error": f"Unknown operation: {operation}"}

    return operations[operation](text)


@tool(
    name="json_process",
    description="Process JSON data, supports parsing, formatting, extraction and other operations.",
    parameters={
        "type": "object",
        "properties": {
            "json_string": {
                "type": "string",
                "description": "JSON string"
            },
            "operation": {
                "type": "string",
                "description": "Operation type",
                "enum": ["parse", "format", "keys", "validate"]
            }
        },
        "required": ["json_string", "operation"]
    },
    category="data"
)
def json_process(arguments: dict) -> dict:
    """
    JSON processing tool

    Args:
        arguments: {
            "json_string": '{"key": "value"}',
            "operation": "parse" | "format" | "keys" | "validate"
        }

    Returns:
        Processing result
    """
    import json

    json_string = arguments["json_string"]
    operation = arguments["operation"]

    try:
        if operation == "validate":
            json.loads(json_string)
            return {"valid": True}

        data = json.loads(json_string)

        if operation == "parse":
            return {"data": data}
        elif operation == "format":
            return {"result": json.dumps(data, indent=2, ensure_ascii=False)}
        elif operation == "keys":
            if isinstance(data, dict):
                return {"keys": list(data.keys())}
            return {"error": "JSON root element is not an object"}
        else:
            return {"error": f"Unknown operation: {operation}"}

    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {str(e)}"}
