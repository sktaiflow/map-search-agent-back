from .chat import Message as ChatMessage, ChatRequest, ChatResponse


class InvokeRequest:
    """Temporary InvokeRequest model for compatibility"""
    def __init__(self, id=None, user_message="", thread_id=None):
        self.id = id
        self.user_message = user_message
        self.thread_id = thread_id


__all__ = ["ChatMessage", "ChatRequest", "ChatResponse", "InvokeRequest"]