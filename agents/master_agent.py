import json
from .engine import ParallelExecutor, run_subagent, mcp_client, memory_client


class MasterAgent:
    def __init__(self):
        self.memory = {}
        # MCP client is initialized globally in engine.py

    def update_memory(self, key, value):
        self.memory[key] = value

    async def run(self, tasks: dict):
        """
        tasks = {
           "researcher": "Collect market insights about automation SaaS",
           "namer": "Generate 10 brand names for the platform",
           "architect": "Design high-level architecture for multi-agent workflow execution"
        }
        """
        print(f"\n🤖 Initializing {len(tasks)} agents...")
        print("📋 Agents:", ", ".join(tasks.keys()))
        print("🔗 Setting up MCP web search capabilities...")
        await mcp_client.initialize()
        print("🧠 Initializing memory server...")
        await memory_client.initialize()
        print("⏳ Starting parallel execution...\n")

        executor = ParallelExecutor()

        coroutines = [
            lambda session, role=role, task=task: run_subagent(session, role, task, self.memory)
            for role, task in tasks.items()
        ]

        results = await executor.run_tasks(coroutines)

        print("\n✅ All agents completed!")
        print(f"📊 Collected {len(results)} results\n")

        # Save to local memory
        for result in results:
            role = result.get("role", "unknown")
            self.memory[f"result_{role}"] = result
        
        # Store results in persistent memory server
        if memory_client.initialized:
            print("💾 Storing results in persistent memory...")
            for result in results:
                role = result.get("role", "unknown")
                task = tasks.get(role, "Unknown task")
                
                # Extract text content for storage
                text_content = ""
                if "result" in result:
                    text_content += str(result["result"])
                if "insights" in result and result["insights"]:
                    text_content += "\n\nInsights:\n" + "\n".join(result["insights"])
                
                if text_content:
                    # Store in memory server
                    await memory_client.store(
                        text=text_content,
                        agent=role,
                        task=task,
                        metadata={
                            "has_web_search": bool(result.get("web_search_results")),
                            "insights_count": len(result.get("insights", [])),
                            "search_requests_count": len(result.get("search_requests", []))
                        }
                    )
            print("✅ Memory storage completed\n")

        # Cleanup clients
        await mcp_client.close()
        await memory_client.close()

        return results, self.memory