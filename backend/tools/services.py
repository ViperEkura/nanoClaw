"""Tool helper services"""
from typing import List, Dict, Optional, Any
from ddgs import DDGS
import re


class SearchService:
    """Search service"""

    def __init__(self, engine: str = "duckduckgo"):
        self.engine = engine

    def search(
        self,
        query: str,
        max_results: int = 5,
        region: str = "cn-zh"
    ) -> List[dict]:
        """
        Execute search

        Args:
            query: Search keywords
            max_results: Max result count
            region: Region setting

        Returns:
            Search result list
        """
        if self.engine == "duckduckgo":
            return self._search_duckduckgo(query, max_results, region)
        else:
            raise ValueError(f"Unsupported search engine: {self.engine}")

    def _search_duckduckgo(
        self,
        query: str,
        max_results: int,
        region: str
    ) -> List[dict]:
        """DuckDuckGo search"""

        with DDGS() as ddgs:
            results = list(ddgs.text(
                query,
                max_results=max_results,
                region=region
            ))

        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")
            }
            for r in results
        ]


class FetchService:
    """Page fetch service"""

    def __init__(self, timeout: float = 30.0, user_agent: str = None):
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    def fetch(
        self,
        url: str,
        extract_type: str = "text"
    ) -> dict:
        """
        Fetch a single page

        Args:
            url: Page URL
            extract_type: Extract type (text, links, structured)

        Returns:
            Fetch result
        """
        import httpx

        try:
            resp = httpx.get(
                url,
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": self.user_agent}
            )
            resp.raise_for_status()
        except Exception as e:
            return {"error": str(e), "url": url}

        html = resp.text
        extractor = ContentExtractor(html)

        if extract_type == "text":
            return {
                "url": url,
                "text": extractor.extract_text()
            }
        elif extract_type == "links":
            return {
                "url": url,
                "links": extractor.extract_links()
            }
        else:
            return extractor.extract_structured(url)

    def fetch_batch(
        self,
        urls: List[str],
        extract_type: str = "text",
        max_concurrent: int = 5
    ) -> List[dict]:
        """
        Batch fetch pages

        Args:
            urls: URL list
            extract_type: Extract type
            max_concurrent: Max concurrent requests

        Returns:
            Result list
        """
        results = []
        for url in urls:
            results.append(self.fetch(url, extract_type))
        return results


class ContentExtractor:
    """Content extractor"""

    def __init__(self, html: str):
        self.html = html
        self._soup = None

    @property
    def soup(self):
        if self._soup is None:
            try:
                from bs4 import BeautifulSoup
                self._soup = BeautifulSoup(self.html, "html.parser")
            except ImportError:
                raise ImportError("Please install beautifulsoup4: pip install beautifulsoup4")
        return self._soup

    def extract_text(self) -> str:
        """Extract plain text"""
        # Remove script and style
        for tag in self.soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = self.soup.get_text(separator="\n", strip=True)
        # Clean extra whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def extract_links(self) -> List[dict]:
        """Extract links"""
        links = []
        for a in self.soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            if text and href and not href.startswith(("#", "javascript:")):
                links.append({"text": text, "href": href})
        return links[:50]  # Limit count

    def extract_structured(self, url: str = "") -> dict:
        """Extract structured content"""
        soup = self.soup

        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string or ""

        # Extract meta description
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "")

        return {
            "url": url,
            "title": title.strip(),
            "description": description.strip(),
            "text": self.extract_text()[:5000],  # Limit length
            "links": self.extract_links()[:20]
        }


class CalculatorService:
    """Safe calculation service"""

    ALLOWED_OPS = {
        "add", "sub", "mul", "truediv", "floordiv",
        "mod", "pow", "neg", "abs"
    }

    def evaluate(self, expression: str) -> dict:
        """
        Safely evaluate mathematical expression

        Args:
            expression: Mathematical expression

        Returns:
            Calculation result
        """
        import ast
        import operator

        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        try:
            # Parse expression
            node = ast.parse(expression, mode="eval")

            # Validate node types
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    return {"error": "Function calls not allowed"}
                if isinstance(child, ast.Name):
                    return {"error": "Variable names not allowed"}

            # Safe execution
            result = eval(
                compile(node, "<string>", "eval"),
                {"__builtins__": {}},
                {}
            )

            return {"result": result}

        except Exception as e:
            return {"error": f"Calculation error: {str(e)}"}
