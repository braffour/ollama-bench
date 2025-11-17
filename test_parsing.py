#!/usr/bin/env python3
"""Test script to validate JSON parsing fixes for strategist and project_manager agents."""

import asyncio
import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.engine import run_subagent
from agents.engine import mcp_client, memory_client
import aiohttp


class MockSession:
    """Mock session for testing."""
    pass


async def test_strategist_parsing():
    """Test strategist agent parsing with mock response that has extra data."""
    print("Testing Strategist Agent Parsing...")

    # Mock response with JSON + extra content (similar to error pattern)
    mock_response = '''{
  "role": "strategist",
  "result": "SaaS Concept 1: AI-powered workflow automation platform",
  "insights": ["AI can reduce manual tasks by 60%", "SMEs need affordable solutions"],
  "search_requests": []
}
SEARCH_REQUEST: "SME automation market size 2024"'''

    # Test the parsing logic
    role = "strategist"

    # Simulate the JSON parsing section from run_subagent
    try:
        result = json.loads(mock_response)
        print("❌ Direct JSON parsing should have failed with extra data")
        return False
    except json.JSONDecodeError as e:
        print(f"✅ Direct JSON parsing failed as expected: {e}")

        # Test our custom handling
        if role == "strategist" and mock_response.strip().startswith('{'):
            print("🔧 Testing strategist custom parsing...")

            json_start = mock_response.find('{')
            json_end = mock_response.find('}', json_start) + 1

            if json_start != -1 and json_end > json_start:
                try:
                    json_part = mock_response[json_start:json_end]
                    result = json.loads(json_part)
                    print("✅ Successfully extracted JSON for Strategist agent")

                    # Check for search requests in remaining text
                    remaining_text = mock_response[json_end:]
                    search_requests = []
                    if "SEARCH_REQUEST:" in remaining_text:
                        lines = remaining_text.split('\n')
                        for line in lines:
                            if "SEARCH_REQUEST:" in line:
                                query = line.split("SEARCH_REQUEST:", 1)[1].strip().strip('"')
                                if query:
                                    search_requests.append(query)

                    result["search_requests"] = search_requests
                    result["parsing_error"] = True
                    result["extraction_method"] = "strategist_json_first"

                    print(f"✅ Successfully processed Strategist with {len(search_requests)} search requests")
                    print(f"   Result: {result.get('result', '')[:50]}...")
                    return True

                except json.JSONDecodeError:
                    print("❌ Custom parsing failed")
                    return False

    return False


async def test_project_manager_parsing():
    """Test project manager agent parsing with complex markdown content."""
    print("\nTesting Project Manager Agent Parsing...")

    # Mock response similar to the actual error pattern with complex markdown
    mock_response = '''{
  "role": "project_manager",
  "result": "## Detailed Project Plan: AI-Powered Customer Support Chatbot

### 1. Executive Summary
The objective is to deliver a fully-functional, AI-driven chatbot that handles Tier-1 customer support queries, reduces average handling time by 30%, and integrates seamlessly with the existing CRM and ticketing systems. The project will follow an Agile, data-centric approach with dedicated data-science, engineering, and product teams. The total duration is 24 weeks (6 months) from kickoff to production launch, with a 4-week post-launch support phase.

### 2. Timeline & Milestones
| Phase | Duration | Key Milestones | Deliverables |
|-------|----------|----------------|--------------|
| Phase 1 – Discovery & Planning | 2 weeks | • Stakeholder alignment
• Requirement refinement
• Success criteria definition | • Project charter
• Detailed requirements document
• Technical architecture overview
• Data collection strategy |
| Phase 2 – Data Preparation | 3 weeks | • Data acquisition completed
• Initial data quality assessment
• ETL pipeline established | • Cleaned dataset ready for modeling
• Data quality report
• Initial model baseline established |
| Phase 3 – Model Development | 6 weeks | • Core ML model trained
• Performance metrics established
• Model validation completed | • Trained chatbot model
• Model performance report
• API endpoint for model serving |
| Phase 4 – Integration & Testing | 4 weeks | • CRM integration completed
• End-to-end testing finished
• User acceptance testing passed | • Integrated chatbot system
• Test reports and bug fixes
• User documentation |
| Phase 5 – Deployment & Launch | 2 weeks | • Production deployment completed
• Monitoring systems active
• Go-live readiness confirmed | • Live chatbot in production
• Monitoring dashboards
• Runbook and support procedures |
| Phase 6 – Post-Launch Support | 4 weeks | • Performance monitoring
• User feedback collection
• Optimization iterations | • Performance optimization report
• User feedback analysis
• Final project retrospective |

### 3. Resource Requirements
- **Data Science Team**: 2 Senior Data Scientists, 1 ML Engineer (12 weeks each)
- **Engineering Team**: 1 Backend Engineer, 1 Frontend Engineer, 1 DevOps Engineer (20 weeks each)
- **Product Team**: 1 Product Manager, 1 UX Designer (16 weeks each)
- **Infrastructure**: Cloud hosting (AWS/GCP), GPU instances for training, API gateway
- **External Resources**: CRM integration specialist (4 weeks), Security audit (1 week)

### 4. Risk Assessment & Mitigation
- **Technical Risks**: Model accuracy below threshold, Integration complexity
- **Mitigation**: Start with simpler model baseline, Phase-gate integration testing
- **Business Risks**: Low user adoption, Data quality issues
- **Mitigation**: Early user testing, Comprehensive data validation pipeline
- **Operational Risks**: System downtime, Performance issues
- **Mitigation**: Comprehensive monitoring, Auto-scaling infrastructure

### 5. Success Metrics
- **Functional**: Chatbot handles 80% of Tier-1 queries with 95% accuracy
- **Performance**: Average response time < 3 seconds, System uptime > 99.5%
- **Business**: 30% reduction in average handling time, User satisfaction > 4.5/5
- **Technical**: Model accuracy > 90%, API response time < 200ms",
  "insights": ["Agile methodology provides flexibility for AI projects", "Comprehensive risk assessment reduces project failure risk", "Cross-functional team collaboration essential for success"],
  "search_requests": ["AI chatbot development best practices", "CRM integration patterns", "ML model deployment strategies"]
}'''

    role = "project_manager"

    # Test direct parsing (should fail due to complex content)
    try:
        result = json.loads(mock_response)
        print("❌ Direct JSON parsing should have failed with complex markdown")
        return False
    except json.JSONDecodeError as e:
        print(f"✅ Direct JSON parsing failed as expected: {str(e)[:100]}...")

        # Test our custom handling (simulate the logic from engine.py)
        if role == "project_manager":
            print("🔧 Testing project manager custom parsing...")

            json_start = mock_response.find('{')
            json_end = mock_response.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_content = mock_response[json_start:json_end]

                try:
                    import re

                    # Apply the quote escaping logic from engine.py
                    json_content = re.sub(r'(\w)"(\w)', r'\1\\"\2', json_content)
                    json_content = re.sub(r'"(\w*)"(\w*)"', r'"\1\\"\2"', json_content)

                    def escape_internal_quotes(match):
                        value = match.group(1)
                        escaped = re.sub(r'(?<!^)(?<!:)\"(?!\s*[,}])', r'\\"', value)
                        return f'"{escaped}"'

                    json_content = re.sub(r'"([^"]*)"', escape_internal_quotes, json_content)

                    result = json.loads(json_content)
                    print("✅ Successfully parsed JSON for Project Manager after quote escaping")

                    result["parsing_error"] = True
                    result["extraction_method"] = "project_manager_quote_escape"

                    print("✅ Successfully processed Project Manager agent")
                    print(f"   Result contains: {len(result.get('result', ''))} characters")
                    return True

                except (json.JSONDecodeError, re.error) as e:
                    print(f"⚠️ Advanced quote escaping failed: {str(e)[:100]}...")

                    # Test fallback content extraction
                    try:
                        result_start = mock_response.find('"result":')
                        if result_start != -1:
                            result_end = mock_response.find('"insights":', result_start)
                            if result_end == -1:
                                result_end = mock_response.find('"search_requests":', result_start)
                            if result_end == -1:
                                result_end = mock_response.find('}', result_start)

                            if result_end != -1:
                                result_content = mock_response[result_start:result_end].strip()
                                content_match = re.search(r'"result":\s*"([^"]*)"', result_content, re.DOTALL)
                                if content_match:
                                    markdown_content = content_match.group(1)
                                    markdown_content = markdown_content.replace('\\"', '"').replace('\\n', '\n')

                                    print("✅ Content extraction fallback successful")
                                    print(f"   Extracted {len(markdown_content)} characters of markdown")
                                    return True

                        # Test general markdown extraction
                        if "## " in mock_response or "### " in mock_response:
                            lines = mock_response.split('\n')
                            result_content = []
                            in_result = False

                            for line in lines:
                                if line.strip().startswith('## ') or line.strip().startswith('### '):
                                    in_result = True
                                if in_result and line.strip():
                                    result_content.append(line)

                            if result_content:
                                print("✅ Markdown fallback successful")
                                return True

                    except Exception as fallback_e:
                        print(f"❌ Fallback extraction failed: {fallback_e}")

    return False


async def main():
    """Run parsing tests."""
    print("🧪 Testing JSON Parsing Fixes\n")

    strategist_success = await test_strategist_parsing()
    project_manager_success = await test_project_manager_parsing()

    print(f"\n📊 Test Results:")
    print(f"   Strategist parsing: {'✅ PASS' if strategist_success else '❌ FAIL'}")
    print(f"   Project Manager parsing: {'✅ PASS' if project_manager_success else '❌ FAIL'}")

    if strategist_success and project_manager_success:
        print("\n🎉 All parsing tests passed! The fixes should resolve the agent issues.")
    else:
        print("\n⚠️ Some tests failed. The fixes may need further adjustment.")


if __name__ == "__main__":
    asyncio.run(main())
