"""Chat utility functions"""

from app.schemas import ChatMessage


def langchain_to_chat_message(message) -> ChatMessage:
    """Convert LangChain message to ChatMessage"""
    # Simple conversion - adjust based on actual LangChain message structure
    if hasattr(message, 'content') and hasattr(message, 'type'):
        role = "assistant" if message.type == "ai" else "user"
        return ChatMessage(role=role, content=str(message.content))
    
    # Fallback for simple string messages
    return ChatMessage(role="assistant", content=str(message))