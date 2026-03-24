"""Crawler related tools"""
from ..factory import tool
from ..services import SearchService, FetchService


@tool(
    name="web_search",
    description="Search the internet for information. Use when you need to find latest news or answer questions that require web search.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search keywords"
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to return, default 5",
                "default": 5
            }
        },
        "required": ["query"]
    },
    category="crawler"
)
def web_search(arguments: dict) -> dict:
    """
    Web search tool

    Args:
        arguments: {
            "query": "search keywords",
            "max_results": 5
        }

    Returns:
        {"results": [...]}
    """
    query = arguments["query"]
    max_results = arguments.get("max_results", 5)

    service = SearchService()
    results = service.search(query, max_results)

    return {"results": results}


@tool(
    name="fetch_page",
    description="Fetch content from a specific webpage. Use when user needs detailed information from a webpage.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL of the webpage to fetch"
            },
            "extract_type": {
                "type": "string",
                "description": "Extraction type",
                "enum": ["text", "links", "structured"],
                "default": "text"
            }
        },
        "required": ["url"]
    },
    category="crawler"
)
def fetch_page(arguments: dict) -> dict:
    """
    Page fetch tool

    Args:
        arguments: {
            "url": "https://example.com",
            "extract_type": "text" | "links" | "structured"
        }

    Returns:
        Page content
    """
    url = arguments["url"]
    extract_type = arguments.get("extract_type", "text")

    service = FetchService()
    result = service.fetch(url, extract_type)

    return result


@tool(
    name="crawl_batch",
    description="Batch fetch multiple webpages. Use when you need to get content from multiple pages at once.",
    parameters={
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of URLs to fetch"
            },
            "extract_type": {
                "type": "string",
                "enum": ["text", "links", "structured"],
                "default": "text"
            }
        },
        "required": ["urls"]
    },
    category="crawler"
)
def crawl_batch(arguments: dict) -> dict:
    """
    Batch fetch tool

    Args:
        arguments: {
            "urls": ["url1", "url2", ...],
            "extract_type": "text"
        }

    Returns:
        {"results": [...]}
    """
    urls = arguments["urls"]
    extract_type = arguments.get("extract_type", "text")

    if len(urls) > 10:
        return {"error": "Maximum 10 pages can be fetched at once"}

    service = FetchService()
    results = service.fetch_batch(urls, extract_type)

    return {"results": results, "total": len(results)}
