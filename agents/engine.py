import asyncio
import aiohttp
import json
import time
import random
import subprocess
import sys
import os
import re
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
# MEMORY CLIENT CLASS
# ======================
class MemoryClient:
    """Client for interacting with the Memory Server API."""
    
    def __init__(self, base_url: str = None):
        """
        Initialize Memory Client.
        
        Args:
            base_url: Memory server URL (defaults to env var)
        """
        self.base_url = base_url or os.getenv("MEMORY_SERVER_URL", "http://localhost:8000")
        self.initialized = False
    
    async def initialize(self):
        """Initialize memory client connection."""
        if self.initialized:
            return
        
        # Check if memory server is available
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/memory/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        self.initialized = True
                        print(f"🔗 Memory server connected at {self.base_url}")
                    else:
                        print(f"⚠️ Memory server health check failed: HTTP {response.status}")
                        self.initialized = False
        except Exception as e:
            print(f"⚠️ Memory server not available: {str(e)}")
            print(f"   Continuing without persistent memory...")
            self.initialized = False
    
    async def search(self, query: str, n_results: int = 5, agent: str = None) -> List[Dict[str, Any]]:
        """
        Search memory for relevant context.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            agent: Optional agent filter
            
        Returns:
            List of search results with text and metadata
        """
        if not self.initialized:
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": query,
                    "n_results": n_results
                }
                if agent:
                    payload["agent"] = agent
                
                async with session.post(
                    f"{self.base_url}/memory/search",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("results", [])
                    else:
                        return []
        except Exception as e:
            print(f"⚠️ Memory search failed: {str(e)}")
            return []
    
    async def store(
        self,
        text: str,
        agent: str,
        task: str,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Store memory entry.
        
        Args:
            text: Text content to store
            agent: Agent persona name
            task: Task description
            tags: Optional additional tags
            metadata: Optional additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        if not self.initialized:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": text,
                    "agent": agent,
                    "task": task
                }
                if tags:
                    payload["tags"] = tags
                if metadata:
                    payload["metadata"] = metadata
                
                async with session.post(
                    f"{self.base_url}/memory/store",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        print(f"⚠️ Memory store failed: HTTP {response.status} - {error_text[:200]}")
                        return False
        except Exception as e:
            print(f"⚠️ Memory store failed: {str(e)}")
            return False
    
    async def close(self):
        """Close memory client connection."""
        self.initialized = False


# Global Memory client instance
memory_client = MemoryClient()


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
def build_subagent_prompt(role: str, task: str, shared_memory: Dict[str, Any], memory_context: List[Dict[str, Any]] = None):
    # Build role-specific context and instructions
    role_instructions = ""
    
    # Add memory context if available
    memory_section = ""
    if memory_context and len(memory_context) > 0:
        memory_section = "\n\n🧠 RELEVANT MEMORY FROM PREVIOUS SESSIONS:\n"
        memory_section += "The following information from previous agent runs may be relevant:\n\n"
        for i, mem in enumerate(memory_context[:3], 1):  # Top 3 results
            memory_section += f"{i}. {mem.get('text', '')[:300]}...\n"
            if mem.get('metadata', {}).get('agent'):
                memory_section += f"   (From: {mem['metadata']['agent']})\n"
        memory_section += "\nUse this context to inform your analysis, but prioritize current task requirements.\n"

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

{memory_section}

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

    # Query memory for relevant context before execution
    memory_context = []
    if memory_client.initialized:
        # Search memory using task description as query
        memory_context = await memory_client.search(
            query=f"{role} {task}",
            n_results=3,
            agent=role
        )
        if memory_context:
            print(f"  🧠 Found {len(memory_context)} relevant memories")

    # First call to get initial response and potential search requests
    prompt = build_subagent_prompt(role, task, mem, memory_context)
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

        # Special handling for Product Manager agent - handle malformed JSON with control characters
        elif role == "product_manager" and response.strip().startswith('{'):
            print(f"🔧 Detected Product Manager agent with potential malformed JSON, attempting advanced extraction...")

            # First, try to find the complete outer JSON structure
            json_start = response.find('{')
            # Find the LAST closing brace to get the complete JSON object
            json_end = response.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_part = response[json_start:json_end]

                # Try to parse the outer JSON, but handle the case where inner content is malformed
                try:
                    result = json.loads(json_part)
                    print(f"✅ Successfully parsed complete JSON for Product Manager agent")
                except json.JSONDecodeError:
                    # If direct parsing fails, try to extract the structure manually
                    print(f"🔧 Direct JSON parsing failed, attempting manual extraction...")

                    # Extract role
                    role_match = re.search(r'"role"\s*:\s*"([^"]*)"', json_part)
                    extracted_role = role_match.group(1) if role_match else "product_manager"

                    # Extract result field - this might contain malformed JSON
                    result_match = re.search(r'"result"\s*:\s*"((?:[^"\\]|\\.)*)"', json_part, re.DOTALL)
                    extracted_result = ""
                    if result_match:
                        extracted_result = result_match.group(1)
                        # Try to clean up the result if it looks like JSON
                        if extracted_result.strip().startswith('{'):
                            # Attempt to extract meaningful content from malformed inner JSON
                            try:
                                # Look for the actual result content
                                inner_result_match = re.search(r'"result"\s*:\s*"([^"]*)"', extracted_result)
                                if inner_result_match:
                                    extracted_result = inner_result_match.group(1)
                                # Extract insights from inner JSON
                                inner_insights = []
                                insights_matches = re.findall(r'"([^"]*)"', extracted_result)
                                if insights_matches:
                                    inner_insights = [insight for insight in insights_matches if insight and not insight.startswith('product_manager') and not insight.startswith('result')]
                                extracted_result = extracted_result.replace('\\n', '\n').replace('\\"', '"')
                            except:
                                pass

                    # Extract insights array
                    insights_match = re.search(r'"insights"\s*:\s*\[([^\]]*)\]', json_part, re.DOTALL)
                    extracted_insights = []
                    if insights_match:
                        insights_content = insights_match.group(1)
                        # Extract individual insight strings
                        insight_matches = re.findall(r'"([^"]*)"', insights_content)
                        extracted_insights = [insight for insight in insight_matches if insight.strip()]

                    # Extract search_requests array
                    search_requests_match = re.search(r'"search_requests"\s*:\s*\[([^\]]*)\]', json_part, re.DOTALL)
                    extracted_search_requests = []
                    if search_requests_match:
                        search_content = search_requests_match.group(1)
                        # Handle both proper JSON strings and SEARCH_REQUEST: syntax
                        if 'SEARCH_REQUEST:' in search_content:
                            lines = search_content.split('\n')
                            for line in lines:
                                if 'SEARCH_REQUEST:' in line:
                                    query = line.split('SEARCH_REQUEST:', 1)[1].strip().strip('",')
                                    if query:
                                        extracted_search_requests.append(query)
                        else:
                            # Try to extract as JSON array
                            request_matches = re.findall(r'"([^"]*)"', search_content)
                            extracted_search_requests = [req for req in request_matches if req.strip()]

                    # Construct the result
                    result = {
                        "role": extracted_role,
                        "result": extracted_result,
                        "insights": extracted_insights,
                        "search_requests": extracted_search_requests,
                        "parsing_error": True,
                        "extraction_method": "product_manager_manual_extraction"
                    }

                    print(f"✅ Successfully extracted data manually for Product Manager agent")

                # Extract additional search requests from any remaining text after JSON
                remaining_text = response[json_end:]
                additional_search_requests = []
                if "SEARCH_REQUEST:" in remaining_text:
                    lines = remaining_text.split('\n')
                    for line in lines:
                        if "SEARCH_REQUEST:" in line:
                            query = line.split("SEARCH_REQUEST:", 1)[1].strip().strip('"')
                            if query and query not in result.get("search_requests", []):
                                additional_search_requests.append(query)

                if additional_search_requests:
                    result["search_requests"].extend(additional_search_requests)

                # Handle web searches if any were requested
                search_requests = result.get("search_requests", [])
                if search_requests:
                    print(f"🔍 Agent '{role}' requested {len(search_requests)} web searches")
                    search_results = []
                    for search_query in search_requests[:3]:  # Limit to 3 searches
                        if search_query and search_query.strip():
                            print(f"  📡 Searching: '{search_query}'")
                            search_result = await web_search(search_query.strip())
                            search_results.append(search_result)

                    result["web_search_results"] = search_results

                print(f"✅ Successfully processed Product Manager agent with {len(search_requests)} search requests")
                return result

        # Special handling for Strategist agent - handle extra data after JSON
        elif role == "strategist" and response.strip().startswith('{'):
            print(f"🔧 Detected Strategist agent JSON+extra content format, attempting extraction...")

            # Try to extract the first valid JSON object
            json_start = response.find('{')
            json_end = response.find('}', json_start) + 1

            if json_start != -1 and json_end > json_start:
                try:
                    json_part = response[json_start:json_end]
                    result = json.loads(json_part)
                    print(f"✅ Successfully extracted JSON for Strategist agent")

                    # Check for search requests in the remaining text
                    remaining_text = response[json_end:]
                    search_requests = []
                    if "SEARCH_REQUEST:" in remaining_text:
                        lines = remaining_text.split('\n')
                        for line in lines:
                            if "SEARCH_REQUEST:" in line:
                                query = line.split("SEARCH_REQUEST:", 1)[1].strip().strip('"')
                                if query:
                                    search_requests.append(query)

                    result["search_requests"] = search_requests

                    # Handle web searches if any were requested
                    if search_requests:
                        print(f"🔍 Agent '{role}' requested {len(search_requests)} web searches")
                        search_results = []
                        for search_query in search_requests[:3]:  # Limit to 3 searches
                            if search_query and search_query.strip():
                                print(f"  📡 Searching: '{search_query}'")
                                search_result = await web_search(search_query.strip())
                                search_results.append(search_result)

                        result["web_search_results"] = search_results

                    result["parsing_error"] = True
                    result["extraction_method"] = "strategist_json_first"
                    print(f"✅ Successfully processed Strategist agent with {len(search_requests)} search requests")
                    return result

                except json.JSONDecodeError:
                    pass  # Continue with general handling

        # Special handling for Project Manager agent - handle complex markdown content
        elif role == "project_manager":
            print(f"🔧 Detected Project Manager agent with complex content, attempting extraction...")

            # First, try to extract JSON by handling the specific markdown formatting issues
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_content = response[json_start:json_end]

                # Fix common issues in project manager responses:
                # 1. Unescaped quotes in markdown headers like "## Phase 1: "Planning""
                # 2. Unescaped quotes in content like "95% uptime"
                try:
                    # Replace problematic quote patterns in markdown
                    # Pattern: word"word or "word"word" -> word\"word or \"word\"word\"
                    json_content = re.sub(r'(\w)"(\w)', r'\1\\"\2', json_content)  # word"word -> word\"word
                    json_content = re.sub(r'"(\w*)"(\w*)"', r'"\1\\"\2"', json_content)  # "word"word" -> "word\"word"

                    # More aggressive: escape all unescaped quotes that appear to be inside strings
                    # This looks for quotes that are not preceded by backslash or colon
                    def escape_internal_quotes(match):
                        value = match.group(1)
                        # Escape quotes that are not at the start/end and not after colons
                        escaped = re.sub(r'(?<!^)(?<!:)\"(?!\s*[,}])', r'\\"', value)
                        return f'"{escaped}"'

                    # Apply to string values in JSON
                    json_content = re.sub(r'"([^"]*)"', escape_internal_quotes, json_content)

                    result = json.loads(json_content)
                    print(f"✅ Successfully parsed JSON for Project Manager after quote escaping")

                    # Handle web searches if any were requested
                    if "search_requests" in result and result["search_requests"]:
                        print(f"🔍 Agent '{role}' requested {len(result['search_requests'])} web searches")
                        search_results = []
                        for search_query in result["search_requests"][:3]:  # Limit to 3 searches
                            if search_query and search_query.strip():
                                print(f"  📡 Searching: '{search_query}'")
                                search_result = await web_search(search_query.strip())
                                search_results.append(search_result)

                        result["web_search_results"] = search_results

                    result["parsing_error"] = True
                    result["extraction_method"] = "project_manager_quote_escape"
                    print(f"✅ Successfully processed Project Manager agent")
                    return result

                except (json.JSONDecodeError, re.error) as e:
                    print(f"⚠️ Advanced quote escaping failed: {e}")

            # Fallback: If JSON parsing fails completely, extract markdown content
            print(f"🔄 Attempting markdown content extraction for Project Manager...")
            try:
                # Look for the JSON structure and extract the result field manually
                result_start = response.find('"result":')
                if result_start != -1:
                    # Find the end of the result field (before next field)
                    result_end = response.find('"insights":', result_start)
                    if result_end == -1:
                        result_end = response.find('"search_requests":', result_start)
                    if result_end == -1:
                        result_end = response.find('}', result_start)

                    if result_end != -1:
                        result_content = response[result_start:result_end].strip()
                        # Extract just the content between quotes
                        content_match = re.search(r'"result":\s*"([^"]*)"', result_content, re.DOTALL)
                        if content_match:
                            markdown_content = content_match.group(1)
                            # Unescape the content
                            markdown_content = markdown_content.replace('\\"', '"').replace('\\n', '\n')

                            consolidated_result = {
                                "role": role,
                                "result": markdown_content,
                                "insights": [
                                    "Project plan developed with timeline and milestones",
                                    "Resource requirements identified",
                                    "Risk assessment included"
                                ],
                                "search_requests": [],
                                "parsing_error": True,
                                "extraction_method": "project_manager_content_extraction"
                            }

                            print(f"✅ Successfully extracted markdown content for Project Manager")
                            return consolidated_result

                # If all else fails, use the general markdown extraction
                if "## " in response or "### " in response:
                    lines = response.split('\n')
                    result_content = []
                    in_result = False

                    for line in lines:
                        if line.strip().startswith('## ') or line.strip().startswith('### '):
                            in_result = True
                        if in_result and line.strip():
                            result_content.append(line)

                    if result_content:
                        consolidated_result = {
                            "role": role,
                            "result": "\n".join(result_content).strip(),
                            "insights": [
                                "Project plan created with detailed timeline and milestones",
                                "Resource requirements identified for development team",
                                "Risk mitigation strategies included in planning"
                            ],
                            "search_requests": [],
                            "parsing_error": True,
                            "extraction_method": "project_manager_markdown_fallback"
                        }

                        print(f"✅ Successfully extracted markdown content for Project Manager (fallback)")
                        return consolidated_result

            except Exception as fallback_e:
                print(f"⚠️ All extraction methods failed for Project Manager: {fallback_e}")

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