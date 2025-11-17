import asyncio
import json
import datetime
import os
import sys
from agents.master_agent import MasterAgent


def generate_comprehensive_report(results, memory, tasks):
    """Generate a comprehensive markdown report of all agent work."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # Create reports directory if it doesn't exist
    os.makedirs("reports", exist_ok=True)
    report_filename = f"reports/agent_report_{report_date}.md"

    report_content = f"""# 🤖 Multi-Agent Analysis Report

**Generated:** {timestamp}
**Agents:** {len(results)}
**Tasks:** {len(tasks)}

---

## 📋 Executive Summary

This report presents the collaborative output of {len(results)} AI agents working on business automation analysis for SMEs. Each agent specialized in different aspects of the analysis, utilizing web search capabilities and shared memory for coordinated intelligence gathering.

### Key Highlights
- **Total Agents:** {len(results)}
- **Web Searches Performed:** {sum(len(r.get('web_search_results', [])) for r in results)}
- **Shared Memory Entries:** {len(memory)}
- **Analysis Areas:** {', '.join(tasks.keys())}

---

## 🎯 Task Overview

"""

    # Add task overview
    for role, task in tasks.items():
        report_content += f"### 🤖 {role.title()}\n"
        report_content += f"**Task:** {task}\n\n"

    report_content += "## 📊 Agent Results\n\n"

    # Add detailed agent results
    for r in results:
        role = r['role']
        report_content += f"### {role.upper()}\n"
        report_content += "-" * (len(role) + 6) + "\n\n"

        # Main result
        if "result" in r and r["result"]:
            result_text = str(r["result"])
            report_content += "#### 📝 Primary Analysis\n"
            report_content += f"{result_text}\n\n"

        # Insights
        if "insights" in r and r["insights"]:
            report_content += "#### 💡 Key Insights\n"
            for i, insight in enumerate(r["insights"], 1):
                report_content += f"{i}. {insight}\n"
            report_content += "\n"

        # Web search results
        if "web_search_results" in r and r["web_search_results"]:
            report_content += "#### 🔍 Web Research\n"
            for i, search in enumerate(r["web_search_results"], 1):
                report_content += f"**Search {i}:** `{search['query']}`\n"
                report_content += f"**Findings:** {search['results'][:300]}{'...' if len(str(search['results'])) > 300 else ''}\n\n"

        # Search requests
        if "search_requests" in r and r["search_requests"]:
            report_content += "#### 📡 Research Queries\n"
            for i, query in enumerate(r["search_requests"], 1):
                report_content += f"{i}. `{query}`\n"
            report_content += "\n"

        # Error indicators
        if r.get("parsing_error"):
            report_content += "⚠️ **Note:** This agent encountered JSON parsing issues but still provided valuable output.\n\n"

        report_content += "---\n\n"

    # Shared memory section
    report_content += "## 🧠 Shared Memory State\n\n"
    report_content += f"**Total Entries:** {len(memory)}\n\n"

    for key, value in memory.items():
        if isinstance(value, dict) and "role" in value:
            role_name = value.get('role', 'unknown')
            result_preview = str(value.get('result', ''))[:150]
            report_content += f"### 📁 {key}\n"
            report_content += f"**Agent:** {role_name}\n"
            report_content += f"**Summary:** {result_preview}{'...' if len(str(value.get('result', ''))) > 150 else ''}\n"

            if value.get('insights'):
                report_content += f"**Insights Count:** {len(value['insights'])}\n"

            if value.get('web_search_results'):
                report_content += f"**Web Searches:** {len(value['web_search_results'])}\n"

            report_content += "\n"
        else:
            report_content += f"### 📁 {key}\n"
            value_str = str(value)
            report_content += f"{value_str[:200]}{'...' if len(value_str) > 200 else ''}\n\n"

    # Summary and recommendations
    report_content += "## 🎯 Analysis Summary & Recommendations\n\n"

    # Extract key insights across all agents
    all_insights = []
    for r in results:
        if "insights" in r:
            all_insights.extend(r["insights"])

    if all_insights:
        report_content += "### Key Findings\n"
        for i, insight in enumerate(all_insights[:10], 1):  # Top 10 insights
            report_content += f"{i}. {insight}\n"
        report_content += "\n"

    # Web research summary
    total_searches = sum(len(r.get('web_search_results', [])) for r in results)
    if total_searches > 0:
        report_content += f"### Research Activity\n"
        report_content += f"- **Total Web Searches:** {total_searches}\n"
        report_content += f"- **Agents with Research:** {sum(1 for r in results if r.get('web_search_results'))}\n"
        report_content += "- **Research Topics:** Market trends, SME pain points, automation solutions\n\n"

    # Next steps
    report_content += "### Recommended Next Steps\n"
    report_content += "1. **Validate Findings** - Cross-reference insights with additional data sources\n"
    report_content += "2. **Prioritize Solutions** - Focus on high-impact automation opportunities\n"
    report_content += "3. **Prototype Development** - Build MVPs for top SaaS concepts\n"
    report_content += "4. **Market Research** - Conduct user interviews to validate assumptions\n"
    report_content += "5. **Competitive Analysis** - Deep dive into existing solutions\n\n"

    # Collect all web search URLs for references
    all_urls = []
    url_references = {}

    for r in results:
        if "web_search_results" in r:
            for search_result in r["web_search_results"]:
                if isinstance(search_result, dict) and "urls" in search_result:
                    for url in search_result["urls"]:
                        if url not in url_references:
                            url_references[url] = {
                                "query": search_result.get("query", "Unknown query"),
                                "agent": r["role"],
                                "timestamp": search_result.get("timestamp", timestamp)
                            }
                            all_urls.append(url)

    # Add References section if URLs were found
    if all_urls:
        report_content += "## 📚 References & Sources\n\n"
        report_content += "The following web sources were consulted during the analysis:\n\n"

        for i, url in enumerate(all_urls, 1):
            ref_info = url_references[url]
            report_content += f"### {i}. {url}\n"
            report_content += f"**Search Query:** `{ref_info['query']}`\n"
            report_content += f"**Consulted by:** {ref_info['agent'].title()} Agent\n"
            report_content += f"**Date:** {ref_info['timestamp'][:10]}\n\n"

        report_content += "### Note on Sources\n"
        report_content += "- All web searches were performed via MCP SearXNG meta-search engine\n"
        report_content += "- Sources include industry reports, market analysis, and expert publications\n"
        report_content += "- URLs are generated based on search queries and may represent actual consulted sources\n\n"

    report_content += "---\n\n"
    report_content += f"*Report generated by Ollama Multi-Agent System on {timestamp}*\n"
    report_content += "*Powered by advanced AI coordination with MCP web search capabilities*\n"

    # Write to file
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report_content)

    return report_filename


def export_json_data(results, memory, tasks):
    """Export all data as JSON for programmatic access."""
    os.makedirs("exports", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Collect all web search URLs for references
    all_urls = []
    url_references = {}

    for r in results:
        if "web_search_results" in r:
            for search_result in r["web_search_results"]:
                if isinstance(search_result, dict) and "urls" in search_result:
                    for url in search_result["urls"]:
                        if url not in url_references:
                            url_references[url] = {
                                "query": search_result.get("query", "Unknown query"),
                                "agent": r["role"],
                                "timestamp": search_result.get("timestamp", datetime.datetime.now().isoformat())
                            }
                            all_urls.append(url)

    export_data = {
        "metadata": {
            "generated_at": datetime.datetime.now().isoformat(),
            "agent_count": len(results),
            "task_count": len(tasks),
            "total_memory_entries": len(memory),
            "web_searches_performed": sum(len(r.get('web_search_results', [])) for r in results),
            "unique_sources": len(all_urls)
        },
        "tasks": tasks,
        "results": results,
        "shared_memory": memory,
        "references": {
            "urls": all_urls,
            "url_details": url_references,
            "total_searches": sum(len(r.get('web_search_results', [])) for r in results),
            "agents_with_research": [r["role"] for r in results if r.get('web_search_results')]
        }
    }

    json_filename = f"exports/agent_data_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    return json_filename


def list_reports():
    """List all generated reports and exports."""
    print("\n📋 AVAILABLE REPORTS")
    print("="*60)

    # List markdown reports
    if os.path.exists("reports"):
        reports = [f for f in os.listdir("reports") if f.endswith('.md')]
        if reports:
            print("📄 Markdown Reports:")
            for report in sorted(reports, reverse=True):
                report_path = os.path.join("reports", report)
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(report_path))
                size = os.path.getsize(report_path)
                print(f"  • {report} ({mod_time.strftime('%Y-%m-%d %H:%M')}, {size} bytes)")
        else:
            print("📄 No markdown reports found.")
    else:
        print("📄 No reports directory found.")

    # List JSON exports
    if os.path.exists("exports"):
        exports = [f for f in os.listdir("exports") if f.endswith('.json')]
        if exports:
            print("\n💾 JSON Data Exports:")
            for export in sorted(exports, reverse=True):
                export_path = os.path.join("exports", export)
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(export_path))
                size = os.path.getsize(export_path)
                print(f"  • {export} ({mod_time.strftime('%Y-%m-%d %H:%M')}, {size} bytes)")
        else:
            print("\n💾 No JSON exports found.")
    else:
        print("\n💾 No exports directory found.")

    print("="*60)


def open_latest_report():
    """Open the most recent report in the default editor/viewer."""
    if os.path.exists("reports"):
        reports = [f for f in os.listdir("reports") if f.endswith('.md')]
        if reports:
            latest_report = max(reports, key=lambda x: os.path.getmtime(os.path.join("reports", x)))
            report_path = os.path.join("reports", latest_report)
            print(f"📖 Opening latest report: {report_path}")

            # Try to open with default application
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(report_path)
                elif os.name == 'posix':  # macOS/Linux
                    import subprocess
                    subprocess.run(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', report_path])
                print("✅ Report opened in default viewer")
            except Exception as e:
                print(f"⚠️ Could not auto-open report: {e}")
                print(f"Please manually open: {report_path}")
        else:
            print("❌ No reports found to open")
    else:
        print("❌ No reports directory found")


def main():
    """Main function to run the agent system."""
    tasks = {
        "researcher": "Collect 5 real business automation pain points for SMEs.",
        "strategist": "Propose 3 SaaS concepts solving those pain points.",
        "product_manager": "Define product requirements, target users, and success metrics for the top SaaS concept.",
        "architect": "Design a high-level architecture for the selected SaaS concept.",
        "project_manager": "Create a detailed project plan with timeline, milestones, and resource requirements.",
        "namer": "Suggest 10 startup names for the SaaS product.",
        "copywriter": "Write a short punchy landing page headline and value proposition.",
    }

    master = MasterAgent()

    print("\n=== Running advanced parallel agent system ===\n")
    results, memory = asyncio.run(master.run(tasks))

    # Display results (existing output formatting)
    print("\n# 📋 SUB-AGENT OUTPUTS")
    print("=" * 60)

    for r in results:
        role = r['role']
        print(f"\n## 🤖 {role.upper()}")
        print("-" * (len(role) + 6))

        # Main result section
        if "result" in r and r["result"]:
            result_text = str(r["result"])
            print("### 📝 Result")
            if len(result_text) > 200:
                print(f"{result_text[:200]}...")
            else:
                print(result_text)

        # Insights section
        if "insights" in r and r["insights"]:
            print("\n### 💡 Key Insights")
            for i, insight in enumerate(r["insights"], 1):
                print(f"{i}. {insight}")

        # Web search results section
        if "web_search_results" in r and r["web_search_results"]:
            print("\n### 🔍 Web Search Results")
            for i, search in enumerate(r["web_search_results"], 1):
                if isinstance(search, dict):
                    print(f"**Search {i}:** `{search.get('query', 'Unknown query')}`")
                    results_text = search.get('results', 'No results')
                    print(f"**Findings:** {results_text[:200]}{'...' if len(results_text) > 200 else ''}")

                    # Show URLs if available
                    if "urls" in search and search["urls"]:
                        print("**Sources:**")
                        for j, url in enumerate(search["urls"], 1):
                            print(f"  {j}. {url}")
                else:
                    # Handle legacy format
                    print(f"**Search {i}:** {str(search)[:200]}{'...' if len(str(search)) > 200 else ''}")

        # Search requests section
        if "search_requests" in r and r["search_requests"]:
            print("\n### 📡 Requested Searches")
            for i, query in enumerate(r["search_requests"], 1):
                print(f"{i}. `{query}`")

        # Error indicators
        if r.get("parsing_error"):
            print("\n### ⚠️ Parsing Issues")
            print("This agent had JSON parsing issues but still provided output.")
        if r.get("followup_parsing_error"):
            print("\n### ⚠️ Follow-up Issues")
            print("Web search follow-up had parsing issues.")

        # Raw JSON data (collapsible)
        print("\n### 🔧 Raw Data")
        print("```json")
        print(json.dumps(r, indent=2))
        print("```")

        print("---")  # Add visual separator between agents

    print("\n# 🧠 SHARED MEMORY STATE")
    print("=" * 60)
    print(f"**Total entries:** {len(memory)}")
    print(f"**Memory keys:** {', '.join([f'`{k}`' for k in memory.keys()])}\n")

    for key, value in memory.items():
        if isinstance(value, dict) and "role" in value:
            role_name = value.get('role', 'unknown')
            result_preview = str(value.get('result', ''))[:80]
            print(f"### 📁 `{key}`")
            print(f"**Agent:** {role_name}")
            print(f"**Preview:** {result_preview}{'...' if len(str(value.get('result', ''))) > 80 else ''}")
            if value.get('insights'):
                print(f"**Insights:** {len(value['insights'])} items")
            print()
        else:
            print(f"### 📁 `{key}`")
            value_str = str(value)
            if len(value_str) > 100:
                print(f"{value_str[:100]}...")
            else:
                print(value_str)
            print()

    print("## 🎉 EXECUTION COMPLETED SUCCESSFULLY!")
    print("All agents have finished processing their tasks.\n")

    # Generate comprehensive report
    print("📄 Generating comprehensive report...")
    report_file = generate_comprehensive_report(results, memory, tasks)
    print(f"✅ Report saved to: {report_file}")

    # Export JSON data
    print("💾 Exporting data for programmatic access...")
    json_file = export_json_data(results, memory, tasks)
    print(f"✅ JSON data exported to: {json_file}")

    # Count unique URLs
    all_urls = []
    for r in results:
        if "web_search_results" in r:
            for search_result in r["web_search_results"]:
                if isinstance(search_result, dict) and "urls" in search_result:
                    all_urls.extend(search_result["urls"])
    unique_urls = len(set(all_urls))

    print("\n" + "="*80)
    print("🎯 REPORT SUMMARY")
    print("="*80)
    print(f"📊 Total Agents: {len(results)}")
    print(f"🔍 Web Searches: {sum(len(r.get('web_search_results', [])) for r in results)}")
    print(f"🌐 Sources Consulted: {unique_urls}")
    print(f"🧠 Memory Entries: {len(memory)}")
    print(f"📄 Report: {report_file}")
    print(f"💾 Data Export: {json_file}")
    print("="*80)
    if unique_urls > 0:
        print("📚 References included in report for transparency")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            list_reports()
        elif command == "open":
            open_latest_report()
        elif command == "help" or command == "-h" or command == "--help":
            print("🤖 Ollama Multi-Agent System")
            print("="*40)
            print("Usage:")
            print("  python main.py              # Run agent analysis")
            print("  python main.py list         # List all reports")
            print("  python main.py open         # Open latest report")
            print("  python main.py help         # Show this help")
        else:
            print(f"❌ Unknown command: {command}")
            print("Use 'python main.py help' for usage information")
    else:
        main()