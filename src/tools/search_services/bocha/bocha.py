import logging
import httpx
import json
import os
import time
from typing import Dict, Any, Tuple, List, Optional

logger = logging.getLogger(__name__)

class BochaAPI:
    """Bocha API wrapper class providing web search functionality."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Bocha API client.

        Reads API key from BOCHA_API_KEY environment variable if not provided.

        Args:
            api_key: Optional API key. If not provided, reads from environment.
        """
        self.api_key = api_key or os.getenv('BOCHA_API_KEY')
        if not self.api_key:
            raise ValueError("BOCHA_API_KEY not found in environment variables")
        self.base_url = "https://api.bochaai.com/v1"
        self.ai_search_endpoint = f"{self.base_url}/ai-search"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        self.stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "total_results": 0
        }

        logger.debug("Bocha API client initialized (using AI Search endpoint).")

    async def _make_request(self, query: str, count: int = 10, freshness: Optional[str] = None, answer: bool = False) -> dict:
        """
        Send AI Search request to Bocha API (POST).

        Args:
            query: Search query
            count: Number of results to return
            freshness: Time range filter parameter
            answer: Whether to request LLM-generated answer (default False)

        Returns:
            API response as JSON dictionary
        """
        payload_dict = {
            "query": query,
            "count": count,
            "answer": answer,
            "stream": False
        }

        # Add freshness parameter if provided and not "noLimit"
        if freshness and freshness != "noLimit":
            payload_dict["freshness"] = freshness

        payload = json.dumps(payload_dict)

        logger.debug(f"Bocha AI Search POST request URL: {self.ai_search_endpoint}")
        logger.debug(f"Bocha AI Search POST request body: {payload}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.ai_search_endpoint, headers=self.headers, data=payload)
            response.raise_for_status()
            json_response = response.json()

            if json_response.get("code") != 200:
                error_msg = f"Bocha API returned business error: Code={json_response.get('code')}, Msg={json_response.get('msg')}"
                logger.error(error_msg)
                return {"error": error_msg}

            logger.debug("Bocha AI Search request successful.")
            return json_response

        except httpx.HTTPStatusError as e:
            logger.error(f"Bocha API HTTP error: {e.response.status_code} - {e.response.text}", exc_info=True)
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except httpx.TimeoutException as e:
            logger.error(f"Bocha API request timeout: {e}", exc_info=True)
            return {"error": f"Request timeout: {e}"}
        except httpx.RequestError as e:
            logger.error(f"Bocha API request failed: {e}", exc_info=True)
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Bocha API response JSON: {e}", exc_info=True)
            return {"error": f"Unable to parse API response: {e}"}

    async def web_search(self, query: str, count: int = 10, freshness: Optional[str] = None, answer: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Execute AI Search and return detailed results (with artifact support).

        Args:
            query: Search query
            count: Number of results to return
            freshness: Time range filter parameter
                - "noLimit": No time limit (default)
                - "oneDay": Within one day
                - "oneWeek": Within one week
                - "oneMonth": Within one month
                - "oneYear": Within one year
                - "YYYY-MM-DD..YYYY-MM-DD": Date range
                - "YYYY-MM-DD": Specific date
            answer: Whether to request LLM-generated answer (default False)

        Returns:
            Tuple[List[Dict[str, Any]], Dict[str, Any]]:
            - First element: Detailed results list with all fields (for building content and artifact)
            - Second element: Raw response metadata (query, response_time, conversation_id, etc.)
        """
        self.stats["total_searches"] += 1
        logger.info(f"Executing Bocha AI search: {query[:50]}... (freshness={freshness}, answer={answer})")

        # Track response time
        start_time = time.time()
        data = await self._make_request(query, count, freshness, answer)
        response_time = time.time() - start_time

        detailed_results_list = []
        image_results_list = []

        if "error" in data:
            logger.warning(f"Bocha AI search returned error: {data['error']}")
            return detailed_results_list, {
                "query": query,
                "response_time": response_time,
                "error": data["error"]
            }

        try:
            messages = data.get("messages", [])

            # Parse webpage results from messages[0]
            webpage_msg = next((m for m in messages if m.get("content_type") == "webpage"), None)
            if webpage_msg:
                webpage_content = json.loads(webpage_msg["content"])
                results = webpage_content.get("value", [])

                for item in results:
                    detailed_results_list.append({
                        "type": "webpage",
                        "title": item.get('name', ''),
                        "url": item.get('url', ''),
                        "summary": item.get('summary', ''),
                        "snippet": item.get('snippet', ''),
                        "site_name": item.get('siteName', ''),
                        "site_icon": item.get('siteIcon', ''),
                        "publish_time": item.get('datePublished', ''),
                        "id": item.get('id', '')
                    })

            # Parse image results from messages[1]
            image_msg = next((m for m in messages if m.get("content_type") == "image"), None)
            if image_msg:
                try:
                    image_content = json.loads(image_msg["content"])
                    images = image_content.get("value", [])

                    for img in images:
                        image_results_list.append({
                            "type": "image",
                            "content_url": img.get('contentUrl', ''),
                            "thumbnail_url": img.get('thumbnailUrl', ''),
                            "host_page_url": img.get('hostPageUrl', ''),
                            "host_page_display_url": img.get('hostPageDisplayUrl', ''),
                            "width": img.get('width', 0),
                            "height": img.get('height', 0)
                        })
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Failed to parse image results: {e}")

            # Combine webpage and image results
            all_results = detailed_results_list + image_results_list

            result_count = len(all_results)
            self.stats["total_results"] += result_count
            if result_count > 0:
                self.stats["successful_searches"] += 1
            logger.info(f"Bocha AI search successful, returned {len(detailed_results_list)} webpages and {len(image_results_list)} images.")

            # Return results and metadata
            metadata = {
                "query": query,
                "response_time": round(response_time, 2),
                "total_results": result_count,
                "conversation_id": data.get("conversation_id", ""),
                "log_id": data.get("log_id", "")
            }

            return all_results, metadata

        except (AttributeError, KeyError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing Bocha AI Search response structure: {e}", exc_info=True)
            logger.debug(f"Raw messages field: {data.get('messages')}")
            return detailed_results_list, {
                "query": query,
                "response_time": response_time,
                "error": str(e)
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get API call statistics.

        Returns:
            Dictionary containing call statistics
        """
        success_rate = (self.stats["successful_searches"] / self.stats["total_searches"] * 100) if self.stats["total_searches"] > 0 else 0

        return {
            "total_searches": self.stats["total_searches"],
            "successful_searches": self.stats["successful_searches"],
            "total_results": self.stats["total_results"],
            "success_rate": f"{success_rate:.2f}%"
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "total_results": 0
        }
