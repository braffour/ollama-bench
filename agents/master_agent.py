import json
from .engine import ParallelExecutor, run_subagent, mcp_client


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
        print("⏳ Starting parallel execution...\n")

        executor = ParallelExecutor()

        coroutines = [
            lambda session, role=role, task=task: run_subagent(session, role, task, self.memory)
            for role, task in tasks.items()
        ]

        results = await executor.run_tasks(coroutines)

        print("\n✅ All agents completed!")
        print(f"📊 Collected {len(results)} results\n")

        # Save to memory
        for result in results:
            role = result.get("role", "unknown")
            self.memory[f"result_{role}"] = result

        # Cleanup MCP client
        await mcp_client.close()

        return results, self.memory