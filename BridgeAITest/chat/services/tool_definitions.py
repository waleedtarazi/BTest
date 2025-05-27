from langchain_core.tools import tool
from pydantic import BaseModel, Field

class GetWeatherInput(BaseModel):
    location: str = Field(description="The city and state, e.g., San Francisco, CA")

@tool("get_current_weather", args_schema=GetWeatherInput)
def get_current_weather(location: str) -> str:
    """Get the current weather in a given location."""
    # This is a dummy function. In a real app, you'd call a weather API.
    if "tokyo" in location.lower():
        return "It's 24°C and sunny in Tokyo."
    elif "london" in location.lower():
        return "It's 15°C and cloudy in London."
    else:
        return f"Sorry, I don't have weather information for {location}."

class SearchInternetInput(BaseModel):
    query: str = Field(description="The search query to find information on the internet.")

@tool("search_internet", args_schema=SearchInternetInput)
def search_internet(query: str) -> str:
    """Searches the internet for the given query. Returns a summary of findings."""
    # Dummy implementation
    return f"Search results for '{query}': Based on current trends, the topic is very popular."

# List of all available tools
ALL_TOOLS = [get_current_weather, search_internet]