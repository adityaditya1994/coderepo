"""
LLM Factory — returns the correct LangChain chat model
based on the provider specified in config.
"""

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm(config: dict):
    """
    Build and return a LangChain chat model.

    Parameters
    ----------
    config : dict
        Full application config (from config_loader.load_config()).

    Returns
    -------
    BaseChatModel
        A LangChain chat model instance ready for .invoke() calls.
    """
    provider = config["llm"]["provider"]
    model = config["llm"]["model"]
    temp = config["llm"].get("temperature", 0.0)

    if provider == "openai":
        return ChatOpenAI(
            model=model,
            temperature=temp,
            api_key=config.get("OPENAI_API_KEY"),
        )
    elif provider == "anthropic":
        return ChatAnthropic(
            model=model,
            temperature=temp,
            api_key=config.get("ANTHROPIC_API_KEY"),
        )
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temp,
            google_api_key=config.get("GOOGLE_API_KEY"),
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
