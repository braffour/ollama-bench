"""Metadata tagging system and default tags for agent personas."""
from typing import List, Dict

# Default tags for each agent persona
AGENT_DEFAULT_TAGS: Dict[str, List[str]] = {
    "researcher": ["research", "market_analysis", "data_gathering", "insights"],
    "strategist": ["strategy", "saas_concepts", "business_model", "planning"],
    "product_manager": ["product", "requirements", "user_personas", "metrics"],
    "architect": ["architecture", "technical_design", "system_design", "infrastructure"],
    "project_manager": ["project", "timeline", "resources", "planning"],
    "namer": ["branding", "naming", "creative", "brand_names"],
    "copywriter": ["marketing", "copy", "messaging", "content"]
}

# Valid agent personas
VALID_AGENTS = list(AGENT_DEFAULT_TAGS.keys())


def get_default_tags(agent: str) -> List[str]:
    """
    Get default tags for an agent persona.
    
    Args:
        agent: Agent persona name
        
    Returns:
        List of default tags
    """
    return AGENT_DEFAULT_TAGS.get(agent, [])


def validate_agent(agent: str) -> bool:
    """
    Validate that agent is a valid persona.
    
    Args:
        agent: Agent persona name
        
    Returns:
        True if valid, False otherwise
    """
    return agent in VALID_AGENTS


def build_tags(agent: str, topic: str = None, output_type: str = None, utility: str = None) -> List[str]:
    """
    Build complete tag list for a memory entry.
    
    Args:
        agent: Agent persona name
        topic: Optional topic tag
        output_type: Optional output type tag
        utility: Optional utility tag
        
    Returns:
        Complete list of tags including defaults
    """
    tags = get_default_tags(agent).copy()
    
    if topic:
        tags.append(f"topic:{topic}")
    if output_type:
        tags.append(f"output_type:{output_type}")
    if utility:
        tags.append(f"utility:{utility}")
    
    return tags

