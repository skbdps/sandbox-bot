"""
Utility functions for the chatbot POC.
"""

import os
from typing import Dict, Any, List


def estimate_tokens(text: str, chars_per_token: int = 4) -> int:
    """
    Estimate token count using simple heuristic.
    
    Args:
        text: Text to estimate tokens for
        chars_per_token: Character to token ratio (default: 4)
    
    Returns:
        Estimated token count
    """
    return max(1, len(text) // chars_per_token)


def estimate_message_tokens(content: Any, chars_per_token: int = 4) -> int:
    """
    Estimate tokens for a message content (can be string or list of content blocks).
    
    Args:
        content: Message content (string or list of dicts)
        chars_per_token: Character to token ratio
    
    Returns:
        Estimated token count
    """
    if isinstance(content, str):
        return estimate_tokens(content, chars_per_token)
    
    elif isinstance(content, list):
        total = 0
        for block in content:
            if isinstance(block, dict):
                if block.get('type') == 'text':
                    total += estimate_tokens(block.get('text', ''), chars_per_token)
                elif block.get('type') == 'thinking':
                    total += estimate_tokens(block.get('thinking', ''), chars_per_token)
                elif block.get('type') == 'image':
                    # Images cost ~750 tokens
                    total += 750
                elif block.get('type') == 'document':
                    # Rough estimate for documents
                    total += 1000
        return total
    
    return 0


def estimate_file_tokens(file_path: str, file_type: str, chars_per_token: int = 4) -> int:
    """
    Estimate tokens for a file based on type and size.
    
    Args:
        file_path: Path to the file
        file_type: Type of file (pdf, txt, image, etc.)
        chars_per_token: Character to token ratio
    
    Returns:
        Estimated token count
    """
    try:
        file_size = os.path.getsize(file_path)
        
        if file_type in ['txt', 'md', 'py', 'js', 'json', 'csv']:
            # Text files: read and count
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            return estimate_tokens(text, chars_per_token)
        
        elif file_type == 'pdf':
            # PDF: rough estimate based on file size
            # Assuming ~2 bytes per token in base64
            return file_size // 2
        
        elif file_type in ['png', 'jpg', 'jpeg', 'webp']:
            # Images: fixed cost
            return 750
        
        else:
            # Unknown: conservative estimate
            return file_size // 3
    
    except Exception:
        return 1000  # Default fallback


def calculate_cost(input_tokens: int, output_tokens: int, 
                   input_cost_per_million: float, output_cost_per_million: float) -> float:
    """
    Calculate estimated API cost.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        input_cost_per_million: Cost per million input tokens
        output_cost_per_million: Cost per million output tokens
    
    Returns:
        Estimated cost in dollars
    """
    input_cost = (input_tokens / 1_000_000) * input_cost_per_million
    output_cost = (output_tokens / 1_000_000) * output_cost_per_million
    return input_cost + output_cost


def format_token_count(count: int) -> str:
    """Format token count for display"""
    if count >= 1000:
        return f"{count/1000:.1f}K"
    return str(count)


def format_cost(cost: float) -> str:
    """Format cost for display"""
    if cost < 0.01:
        return f"${cost:.4f}"
    return f"${cost:.2f}"


def get_file_type(filename: str) -> str:
    """Get file type from filename"""
    return filename.split('.')[-1].lower() if '.' in filename else 'unknown'


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def get_context_messages(messages: List[Dict], max_tokens: int, 
                         chars_per_token: int = 4) -> List[Dict]:
    """
    Get messages that fit within token limit, keeping most recent.
    
    Args:
        messages: List of message dicts with 'content' and 'role'
        max_tokens: Maximum tokens to include
        chars_per_token: Character to token ratio
    
    Returns:
        List of messages that fit in context
    """
    if not messages:
        return []
    
    context_messages = []
    total_tokens = 0
    
    # Iterate from newest to oldest
    for message in reversed(messages):
        msg_tokens = estimate_message_tokens(message.get('content', ''), chars_per_token)
        
        if total_tokens + msg_tokens > max_tokens:
            break
        
        context_messages.insert(0, message)
        total_tokens += msg_tokens
    
    return context_messages
