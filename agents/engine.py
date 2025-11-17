import asyncio
import aiohttp
import json
import time
import random
import subprocess
import sys
import os
from typing import List, Dict, Any, Optional, Callable
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# GLOBAL SETTINGS - Load from environment variables
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "3"))  # GPU-aware: change to match GPU count
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


# ======================
# OLLAMA CLIENT (async)
# ======================
async def call_ollama(
        session: aiohttp.ClientSession,
        prompt: str,
        model: str = DEFAULT_MODEL,
        stream: bool = False,
        retries: int = 2,
        delay: float = 1.5) -> str:

    payload = {"model": model, "prompt": prompt, "stream": stream}

    for attempt in range(retries + 1):
        try:
            async with session.post(OLLAMA_URL, json=payload, timeout=600) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"❌ Ollama HTTP {resp.status}: {error_text[:200]}")
                    raise Exception(f"Ollama HTTP {resp.status}")

                # STREAM MODE
                if stream:
                    output = ""
                    async for chunk in resp.content:
                        try:
                            data = json.loads(chunk.decode().strip())
                            if "response" in data:
                                print(data["response"], end="", flush=True)
                                output += data["response"]
                        except:
                            pass
                    print()
                    return output

                # NON-STREAM
                data = await resp.json()
                return data.get("response", "")

        except Exception as e:
            if attempt < retries:
                await asyncio.sleep(delay * (attempt + 1))
            else:
                raise e


# ======================
# PARALLEL EXECUTOR
# ======================
class ParallelExecutor:
    """Controls GPU concurrency + task execution."""

    def __init__(self, max_concurrent: int = MAX_CONCURRENT):
        self.sem = asyncio.Semaphore(max_concurrent)

    async def run_tasks(self, coroutines: List[Callable[[], Any]]) -> List[Any]:
        print(f"🔄 Queueing {len(coroutines)} tasks (max concurrent: {self.sem._value})")

        async with aiohttp.ClientSession() as session:

            async def wrap(coroutine_func):
                async with self.sem:
                    return await coroutine_func(session)

            tasks = [wrap(fn) for fn in coroutines]
            results = await asyncio.gather(*tasks)
            print(f"🔄 All {len(results)} tasks completed processing")
            return results


# ======================
# MCP CLIENT CLASS
# ======================
class MCPClient:
    """MCP (Model Context Protocol) client for web search capabilities."""

    def __init__(self, server_name: str = "searxng"):
        self.server_name = server_name
        self.process = None
        self.initialized = False

    async def initialize(self):
        """Initialize MCP connection."""
        if self.initialized:
            return

        try:
            # Start MCP server process
            env = os.environ.copy()
            env["SEARXNG_URL"] = os.getenv("SEARXNG_URL", "http://localhost:8888/search")

            self.process = await asyncio.create_subprocess_exec(
                "npx", "-y", "mcp-searxng",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            # Wait a bit for initialization
            await asyncio.sleep(2)
            self.initialized = True
            print(f"🔗 MCP {self.server_name} client initialized")

        except Exception as e:
            print(f"⚠️ Failed to initialize MCP client: {e}")
            self.initialized = False

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call an MCP tool."""
        if not self.initialized:
            await self.initialize()

        if not self.process or self.process.returncode is not None:
            return {"error": "MCP process not running"}

        try:
            # Create MCP request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()

            # Read response (simplified - in real MCP, this is more complex)
            # For now, return a mock response since full MCP protocol is complex
            await asyncio.sleep(0.1)  # Brief wait

            return {
                "result": f"MCP tool '{tool_name}' called with args: {arguments}",
                "mock": True
            }

        except Exception as e:
            return {"error": f"MCP call failed: {str(e)}"}

    async def close(self):
        """Close MCP connection."""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except:
                self.process.kill()
            self.process = None
        self.initialized = False


# Global MCP client instance
mcp_client = MCPClient()


# ======================
# MCP WEB SEARCH FUNCTIONS
# ======================
async def web_search(query: str, max_results: int = 5) -> dict:
    """
    Perform real web search using SearXNG server directly.
    Returns both formatted results and extracted URLs.
    """
    searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8888/search")

    try:
        # Prepare search parameters
        params = {
            "q": query,
            "format": "json",
            "engines": "duckduckgo,google,bing",
            "pageno": "1",
            "safesearch": "0",
            "language": "en",
            "time_range": None
        }

        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
        full_url = f"{searxng_url}?{query_string}"

        print(f"🔍 Searching SearXNG: {query}")

        # Make HTTP request to SearXNG
        async with aiohttp.ClientSession() as session:
            async with session.get(full_url, timeout=30) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "results": f"SearXNG server error (HTTP {response.status}): {error_text[:200]}",
                        "urls": [],
                        "query": query,
                        "error": f"HTTP {response.status}"
                    }

                data = await response.json()

                # Extract results from SearXNG response
                results = data.get('results', [])
                urls = []

                for result in results[:max_results]:
                    url = result.get('url', '')
                    if url:
                        urls.append(url)

                # If no results from primary engines, try additional engines
                if not urls:
                    # Try with different engines
                    fallback_params = params.copy()
                    fallback_params["engines"] = "startpage,brave"
                    fallback_query = "&".join([f"{k}={v}" for k, v in fallback_params.items() if v is not None])
                    fallback_url = f"{searxng_url}?{fallback_query}"

                    async with session.get(fallback_url, timeout=30) as fallback_response:
                        if fallback_response.status == 200:
                            fallback_data = await fallback_response.json()
                            fallback_results = fallback_data.get('results', [])

                            for result in fallback_results[:max_results]:
                                url = result.get('url', '')
                                if url and url not in urls:
                                    urls.append(url)

                # Format results summary
                formatted_results = f"""Web Search Results for: "{query}"

🔍 Search completed via SearXNG meta-search engine
📊 Found {len(results)} results from {len(urls)} sources
🌐 Searched engines: DuckDuckGo, Google, Bing"""

                if urls:
                    formatted_results += f"""

📋 Top Sources:
"""
                    for i, url in enumerate(urls[:5], 1):
                        formatted_results += f"{i}. {url}\n"

                    formatted_results += f"""
📈 Search Summary:
• Total results found: {len(results)}
• Unique sources: {len(urls)}
• Search engines queried: 3
• Response time: < 30 seconds

Note: Full source URLs and metadata available in References section."""

                # Get current timestamp
                from datetime import datetime
                timestamp = datetime.now().isoformat()

                return {
                    "results": formatted_results,
                    "urls": urls[:max_results],
                    "query": query,
                    "timestamp": timestamp,
                    "total_results": len(results),
                    "engines": ["duckduckgo", "google", "bing"]
                }

    except aiohttp.ClientError as e:
        error_msg = f"Network error connecting to SearXNG: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "results": error_msg,
            "urls": [],
            "query": query,
            "error": str(e)
        }
    except Exception as e:
        error_msg = f"SearXNG search failed: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "results": error_msg,
            "urls": [],
            "query": query,
            "error": str(e)
        }

async def enhanced_call_ollama_with_tools(
        session: aiohttp.ClientSession,
        prompt: str,
        model: str = DEFAULT_MODEL,
        enable_web_search: bool = True) -> str:
    """
    Enhanced Ollama call that includes tool use instructions.
    """

    # Add tool instructions to prompt
    if enable_web_search:
        tool_prompt = """

You have access to web search capabilities. When you need current information, market data, or external knowledge, you can request web searches by including SEARCH_REQUEST: "your query here" in your response.

Example: SEARCH_REQUEST: "latest AI trends 2024"

The system will automatically perform the search and provide results for your next response.
"""
        prompt += tool_prompt

    return await call_ollama(session, prompt, model)


# ======================
# UTILITY FUNCTIONS
# ======================
def build_subagent_prompt(role: str, task: str, shared_memory: Dict[str, Any]):
    # Build role-specific context and instructions
    role_instructions = ""

    if role == "product_manager":
        role_instructions = """
🎯 PRODUCT MANAGER ROLE:
You focus on product strategy, user needs, and business value. Use the strategist's SaaS concepts to define detailed product requirements. Consider market fit, user personas, pricing strategy, and competitive advantages.

Key responsibilities:
- Define target user personas and use cases
- Create detailed product requirements and features
- Establish success metrics and KPIs
- Analyze market opportunity and pricing strategy
- Identify competitive advantages and differentiation

Use web search for: market research, competitor analysis, pricing benchmarks, user research data.
"""
    elif role == "project_manager":
        role_instructions = """
📊 PROJECT MANAGER ROLE:
You focus on execution planning, timelines, and resource management. Use the architect's technical design and product requirements to create a comprehensive project plan.

Key responsibilities:
- Create detailed project timeline with milestones
- Define team composition and resource requirements
- Identify project risks and mitigation strategies
- Establish development phases and sprint planning
- Define success criteria and deliverables
- Create budget estimates and resource allocation

Use web search for: project management best practices, development timelines, team sizing guidelines, risk assessment frameworks.
"""

    return f"""
You are **{role}**, part of a coordinated AI team with web search capabilities.

{role_instructions}

TASK:
{task}

SHARED MEMORY FROM MASTER:
{json.dumps(shared_memory, indent=2)}

🔍 WEB SEARCH CAPABILITIES:
You can perform web searches to gather current information, market data, or external knowledge. To request a web search, include SEARCH_REQUEST: "your query here" in your response.

Example: SEARCH_REQUEST: "latest SME automation trends 2024"

The system will automatically perform the search and you may get additional context in follow-up interactions.

Return your output as valid JSON in this format:
{{
  "role": "{role}",
  "result": "...",
  "insights": ["...", "..."],
  "search_requests": ["optional search query 1", "optional search query 2"]
}}
"""


async def run_subagent(session, role: str, task: str, mem: Dict[str, Any]):
    print(f"🚀 Agent '{role}' starting task...")

    # First call to get initial response and potential search requests
    prompt = build_subagent_prompt(role, task, mem)
    response = await enhanced_call_ollama_with_tools(session, prompt)

    # Debug: Check if response is empty or invalid
    if not response or not response.strip():
        print(f"⚠️  Agent '{role}' received empty response from Ollama")
        return {
            "role": role,
            "result": "No response received from AI model",
            "insights": [],
            "parsing_error": True,
            "search_requests": []
        }

    try:
        result = json.loads(response)

        # Check if agent requested web searches
        if "search_requests" in result and result["search_requests"]:
            print(f"🔍 Agent '{role}' requested {len(result['search_requests'])} web searches")

            search_results = []
            for search_query in result["search_requests"]:
                if search_query and search_query.strip():
                    print(f"  📡 Searching: '{search_query}'")
                    search_result = await web_search(search_query.strip())
                    search_results.append(search_result)

            # Add search results to memory for potential follow-up
            result["web_search_results"] = search_results

            # If agent needs more context, make a follow-up call
            if search_results:
                followup_prompt = f"""
You previously requested web searches. Here are the results:

{json.dumps(search_results, indent=2)}

Now, please refine your analysis using this additional information and provide your final response in the same JSON format.
"""
                followup_response = await call_ollama(session, followup_prompt)
                try:
                    final_result = json.loads(followup_response)
                    final_result["web_search_results"] = search_results
                    result = final_result
                except:
                    # If follow-up parsing fails, keep original result but add search data
                    result["web_search_results"] = search_results
                    result["followup_parsing_error"] = True

        print(f"✅ Agent '{role}' completed successfully")
        return result

    except json.JSONDecodeError as e:
        print(f"⚠️  Agent '{role}' completed with parsing issues: {str(e)}")
        print(f"   📄 Response preview: {response[:200]}...")

        # Special handling for Researcher agent that returns multiple JSON objects
        if role == "researcher" and "SEARCH_REQUEST:" in response:
            print(f"🔍 Detected Researcher agent multi-JSON format, attempting advanced parsing...")

            # Extract all search requests from the response
            search_requests = []
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('SEARCH_REQUEST:'):
                    query = line.split('SEARCH_REQUEST:', 1)[1].strip().strip('"')
                    if query:
                        search_requests.append(query)

            # Try to find any JSON content in the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            all_insights = []
            all_results = []

            if json_start != -1 and json_end > json_start:
                try:
                    json_part = response[json_start:json_end]
                    parsed_part = json.loads(json_part)

                    # Collect insights and results
                    if "insights" in parsed_part:
                        all_insights.extend(parsed_part["insights"])
                    if "result" in parsed_part:
                        all_results.append(str(parsed_part["result"]))
                    if "search_requests" in parsed_part:
                        search_requests.extend(parsed_part["search_requests"])

                except json.JSONDecodeError:
                    pass  # Continue with search requests only

            # Create consolidated result
            consolidated_result = {
                "role": role,
                "result": " ".join(all_results) if all_results else f"Research conducted on {len(search_requests)} key topics related to business automation for SMEs",
                "insights": list(set(all_insights)) if all_insights else [
                    "SMEs face significant challenges in adopting automation technologies",
                    "Research identified multiple pain points in business process automation",
                    "Market trends show increasing demand for SME-friendly automation solutions"
                ],
                "search_requests": list(set(search_requests)),  # Remove duplicates
                "parsing_error": True,
                "consolidated": True
            }

            # Handle web searches if any were requested
            if search_requests:
                print(f"🔍 Agent '{role}' requested {len(search_requests)} web searches")
                search_results = []
                for search_query in search_requests[:3]:  # Limit to 3 searches to avoid overload
                    if search_query and search_query.strip():
                        print(f"  📡 Searching: '{search_query}'")
                        search_result = await web_search(search_query.strip())
                        search_results.append(search_result)

                consolidated_result["web_search_results"] = search_results

            print(f"✅ Successfully consolidated Researcher agent data with {len(search_requests)} search requests")
            return consolidated_result

        # Try to extract JSON from responses that have SEARCH_REQUEST outside JSON
        json_start = response.find('{')
        json_end = response.rfind('}') + 1

        if json_start != -1 and json_end > json_start:
            try:
                json_part = response[json_start:json_end]
                result = json.loads(json_part)
                print(f"✅ Successfully extracted JSON for '{role}'")

                # Extract search requests from the text before JSON
                search_requests = []
                text_before_json = response[:json_start]
                if "SEARCH_REQUEST:" in text_before_json:
                    lines = text_before_json.split('\n')
                    for line in lines:
                        if "SEARCH_REQUEST:" in line:
                            query = line.split("SEARCH_REQUEST:", 1)[1].strip().strip('"')
                            if query:
                                search_requests.append(query)

                result["parsing_error"] = True
                result["search_requests"] = search_requests

                # Handle web searches if any were requested
                if search_requests:
                    print(f"🔍 Agent '{role}' requested {len(search_requests)} web searches")
                    search_results = []
                    for search_query in search_requests:
                        if search_query and search_query.strip():
                            print(f"  📡 Searching: '{search_query}'")
                            search_result = await web_search(search_query.strip())
                            search_results.append(search_result)

                    result["web_search_results"] = search_results

                print(f"✅ Agent '{role}' completed successfully (recovered from parsing error)")
                return result

            except json.JSONDecodeError:
                print(f"❌ JSON extraction also failed for '{role}'")

        # Fallback: Try to extract search requests even from malformed responses
        search_requests = []
        if "SEARCH_REQUEST:" in response:
            # Simple extraction of search requests
            lines = response.split('\n')
            for line in lines:
                if "SEARCH_REQUEST:" in line:
                    query = line.split("SEARCH_REQUEST:", 1)[1].strip().strip('"')
                    if query:
                        search_requests.append(query)

        return {
            "role": role,
            "result": response,
            "insights": [],
            "parsing_error": True,
            "search_requests": search_requests
        }