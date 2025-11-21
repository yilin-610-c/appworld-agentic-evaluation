"""Utility functions for parsing XML-like tags from messages."""
import re
from typing import Dict


def parse_tags(str_with_tags: str) -> Dict[str, str]:
    """Parse XML-like tags from a string.
    
    Example:
        "<task>Do something</task>" -> {"task": "Do something"}
    """
    tags = re.findall(r"<(.*?)>(.*?)</\1>", str_with_tags, re.DOTALL)
    return {tag: content.strip() for tag, content in tags}


