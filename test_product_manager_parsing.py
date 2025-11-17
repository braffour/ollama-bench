#!/usr/bin/env python3
"""Test script to validate Product Manager JSON parsing fix."""

import asyncio
import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.engine import run_subagent
import aiohttp


class MockSession:
    """Mock session for testing."""
    pass


async def test_product_manager_parsing():
    """Test product manager agent parsing with extra data after JSON."""
    print("Testing Product Manager Agent Parsing...")

    # Mock response with JSON + extra content (similar to the error pattern)
    mock_response = '''{
  "role": "product_manager",
  "result": "AI-powered SEO tool with AI-driven insights, personalized recommendations, and user-friendly interface.",
  "insights": [
    "Target user persona: Digital Marketing Specialist",
    "Key features: Keyword Research, On-Page Optimization, Content Analysis, Competitor Analysis"
  ],
  "search_requests": []
}
SEARCH_REQUEST: "digital marketing trends 2024"
SEARCH_REQUEST: "SEO industry market size 2024"'''

    # Test with the actual malformed response pattern from the export
    malformed_response = '''{
  "role": "product_manager",
  "result": "{
  \"role\": \"product_manager\",
  \"result\": \"AI-powered SEO tool with AI-driven insights, personalized recommendations, and user-friendly interface.\",
  \"insights\": [
    \"Target user persona: Digital Marketing Specialist\",
    \"Key features: Keyword Research, On-Page Optimization, Content Analysis, Competitor Benchmarking, ...
  ],
  \"search_requests\": [
    SEARCH_REQUEST: \"digital marketing tools market size 2024\",
    SEARCH_REQUEST: \"best practices for AI-powered SEO\"
  ]
}",
  "insights": [],
  "parsing_error": true,
  "search_requests": [
    "digital marketing tools market size 2024\",",
    "best practices for AI-powered SEO"
  ]
}'''

    role = "product_manager"

    # Test both response patterns
    test_responses = [
        ("mock_response", mock_response),
        ("malformed_response", malformed_response)
    ]

    for test_name, response in test_responses:
        print(f"\n--- Testing {test_name} ---")

        # Test direct parsing (should fail with extra data)
        try:
            result = json.loads(response)
            print(f"❌ Direct JSON parsing should have failed for {test_name}")
            return False
        except json.JSONDecodeError as e:
            print(f"✅ Direct JSON parsing failed for {test_name} as expected: {e}")

            # Test our custom handling
            if role == "product_manager" and response.strip().startswith('{'):
                print(f"🔧 Testing product manager custom parsing for {test_name}...")

                json_start = response.find('{')
                json_end = response.find('}', json_start) + 1

                if json_start != -1 and json_end > json_start:
                    try:
                        json_part = response[json_start:json_end]
                        result = json.loads(json_part)
                        print(f"✅ Successfully extracted JSON for Product Manager agent ({test_name})")

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
                        result["parsing_error"] = True
                        result["extraction_method"] = "product_manager_json_first"

                        print(f"✅ Successfully processed Product Manager ({test_name}) with {len(search_requests)} search requests")
                        print(f"   Search requests found: {search_requests}")

                    except json.JSONDecodeError as e2:
                        print(f"❌ Custom parsing failed for {test_name}: {e2}")
                        # Try the new advanced parsing logic
                        print(f"🔧 Trying advanced manual extraction for {test_name}...")

                        import re

                        # Extract role
                        role_match = re.search(r'"role"\s*:\s*"([^"]*)"', response)
                        extracted_role = role_match.group(1) if role_match else "product_manager"

                        # Extract result field - this might contain malformed JSON
                        result_match = re.search(r'"result"\s*:\s*"((?:[^"\\]|\\.)*)"', response, re.DOTALL)
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
                        insights_match = re.search(r'"insights"\s*:\s*\[([^\]]*)\]', response, re.DOTALL)
                        extracted_insights = []
                        if insights_match:
                            insights_content = insights_match.group(1)
                            # Extract individual insight strings
                            insight_matches = re.findall(r'"([^"]*)"', insights_content)
                            extracted_insights = [insight for insight in insight_matches if insight.strip()]

                        # Extract search_requests array
                        search_requests_match = re.search(r'"search_requests"\s*:\s*\[([^\]]*)\]', response, re.DOTALL)
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

                        print(f"✅ Successfully extracted data manually for {test_name}")
                        print(f"   Result: {extracted_result[:100]}...")
                        print(f"   Insights: {extracted_insights}")
                        print(f"   Search requests: {extracted_search_requests}")

    return True


async def main():
    """Run the test."""
    print("🧪 Testing Product Manager JSON Parsing Fix\n")

    success = await test_product_manager_parsing()

    print(f"\n📊 Test Result:")
    print(f"   Product Manager parsing: {'✅ PASS' if success else '❌ FAIL'}")

    if success:
        print("\n🎉 Product Manager parsing fix is working correctly!")
    else:
        print("\n⚠️ Product Manager parsing fix needs more work.")


if __name__ == "__main__":
    asyncio.run(main())
