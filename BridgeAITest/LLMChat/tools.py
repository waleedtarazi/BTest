from typing import Dict, Any, List
from langchain_core.tools import BaseTool, tool
from datetime import datetime

class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool_instance: BaseTool) -> None:
        """Register a new tool."""
        self._tools[tool_instance.name] = tool_instance
    
    def get_tool(self, name: str) -> BaseTool:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[BaseTool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def __getitem__(self, key: str) -> BaseTool:
        return self._tools[key]

# Initialize the global tool registry
TOOL_REGISTRY = ToolRegistry()

# Example tools (you can add more as needed)
@tool
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b

@tool
def get_current_time() -> str:
    """Get the current time in ISO format."""
    return datetime.now().isoformat()

@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    # Implement actual web search logic here
    return f"Searching for: {query}"

@tool
def calculate(expression: str) -> float:
    """Evaluate a mathematical expression."""
    # Note: In production, you'd want to add safety checks
    return eval(expression)

# Register the tools
TOOL_REGISTRY.register(add)
TOOL_REGISTRY.register(get_current_time)
TOOL_REGISTRY.register(search_web)
TOOL_REGISTRY.register(calculate)

# You can add more tools here as needed
