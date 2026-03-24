"""Weather related tools"""
from backend.tools.factory import tool


@tool(
    name="get_weather",
    description="Get weather information for a specified city. Use when user asks about weather.",
    parameters={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City name, e.g.: 北京, 上海, 广州"
            }
        },
        "required": ["city"]
    },
    category="weather"
)
def get_weather(arguments: dict) -> dict:
    """
    Weather query tool (simulated)

    Args:
        arguments: {
            "city": "北京"
        }

    Returns:
        {
            "city": "北京",
            "temperature": 25,
            "humidity": 60,
            "description": "晴天"
        }
    """
    city = arguments["city"]
    
    # 模拟天气数据
    weather_data = {
        "北京": {"temperature": 25, "humidity": 60, "description": "晴天"},
        "上海": {"temperature": 28, "humidity": 75, "description": "多云"},
        "广州": {"temperature": 32, "humidity": 85, "description": "雷阵雨"},
        "深圳": {"temperature": 30, "humidity": 80, "description": "阴天"},
    }
    
    data = weather_data.get(city, {
        "temperature": 22,
        "humidity": 65,
        "description": "晴天"
    })
    
    return {
        "city": city,
        **data,
        "query_time": "2026-03-24 12:00:00"
    }
