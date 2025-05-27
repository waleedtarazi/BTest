# chat/services/langchain_service.py
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEndpoint

def get_llm_from_provider(provider):
    if provider.name.lower() == "openai":
        # Use ChatOpenAI (chat model) or OpenAI if chat not needed
        return ChatOpenAI(model=provider.model, openai_api_key=provider.api_key, temperature=0)
    #!! TODO: coher instead of HF
    
    elif provider.name.lower() == "huggingface":
        # Using Hugging Face Inference API (requires token if private)
        return HuggingFaceEndpoint(repo_id="mistralai/Mistral-Nemo-Base-2407",
                                   task="text-generation", 
                                   huggingfacehub_api_token=provider.api_key, 
                                   temperature=0,
                                   )
    else:
        raise ValueError("Unsupported LLM provider")
    

from langchain.callbacks.base import BaseCallbackHandler

class TokenUsageCallback(BaseCallbackHandler):
    def __init__(self):
        super().__init__()
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.cost = 0.0

    def on_llm_end(self, response, **kwargs):
        # LangChain output may include usage metadata under llm_output or usage_metadata
        usage = {}
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})  # ChatOpenAI puts it here
        elif hasattr(response, "usage_metadata"):
            usage = response.usage_metadata  # some models use usage_metadata

        # Extract token counts (fallback to 0 if missing)
        self.prompt_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
        self.completion_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
        self.total_tokens = usage.get("total_tokens", 0)

        # Estimate cost if using OpenAI (example rates for GPT-4/3.5)
        if usage:
            # Rates in USD per token (example: GPT-4 Turbo ~ $0.03/1K prompt, $0.06/1K completion)
            prompt_rate = 0.03/1000
            completion_rate = 0.06/1000
            self.cost = self.prompt_tokens * prompt_rate + self.completion_tokens * completion_rate

# chat/services/langchain_service.py (continued)
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType

def calc_fn(expression: str) -> str:
    """Calculate a mathematical expression."""
    try:
        # WARNING: eval is unsafe; use a safe parser in production
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"

def weather_fn(city: str) -> str:
    """Mock weather tool: returns a dummy forecast."""
    # In reality, call a weather API here
    return f"The weather in {city} is 25°C and sunny."

# Define LangChain Tool objects
calc_tool = Tool(
    name="calculator",
    func=calc_fn,
    description="Use for solving math expressions, e.g. '2 + 2'."
)
weather_tool = Tool(
    name="weather",
    func=weather_fn,
    description="Get the current weather for a given city."
)

def create_agent(llm):
    # Initialize a zero-shot agent with our tools
    return initialize_agent(
        tools=[calc_tool, weather_tool],
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # default agent type
        handle_parsing_errors=True,
        max_iterations = 4,
        early_stopping_method="generate",               # if it hits max_iterations, force a final LLM “generate” step
        verbose=True, 
    )
    
def fall_back_chat(provider):
    if provider.name.lower() == "openai":
        # Use ChatOpenAI (chat model) or OpenAI if chat not needed
        return ChatOpenAI(model=provider.model, openai_api_key=provider.api_key, temperature=0)
    elif provider.name.lower() == "huggingface":
        # Using Hugging Face Inference API (requires token if private)
        return HuggingFaceEndpoint(repo_id=provider.model,
                                   task="text-generation", 
                                   huggingfacehub_api_token=provider.api_key, 
                                   )
    else:
        raise ValueError("Unsupported LLM provider")
