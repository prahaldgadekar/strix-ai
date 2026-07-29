from __future__ import annotations
from strix.types import StrixResponse, ToolResult

class ResponseGenerator:
    """Formats and processes responses before sending to the user."""
    
    def __init__(self, conversation_memory, persistent_memory):
        self.conversation_memory = conversation_memory
        self.persistent_memory = persistent_memory
        print("[STRIX ResponseGenerator] Initialized")
        
    def format(self, response: StrixResponse) -> StrixResponse:
        """Post-process response text."""
        if response.text:
            response.text = response.text.strip()
        return response
        
    def save_to_memory(self, response: StrixResponse, session_id: str = None):
        """Save assistant response to memory backends."""
        if self.conversation_memory and response.text:
            self.conversation_memory.save("assistant", response.text)
            
    def format_tool_result(self, result: ToolResult) -> str:
        """Format tool output for display."""
        if not result.success:
            return f"❌ Error: {result.error}"
        return f"✅ Tool execution successful.\nOutput:\n{result.output}"
        
    def format_stream(self, generator, callback=None):
        """Wrap a token generator to save the final assembled text."""
        full_text = ""
        for chunk in generator:
            full_text += chunk
            if callback:
                callback(chunk)
            yield chunk
        
        response = StrixResponse(text=full_text)
        self.save_to_memory(self.format(response))
