"""
LLM Factory — returns the correct LangChain chat model
based on the provider specified in config.
"""


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
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=temp,
            api_key=config.get("OPENAI_API_KEY"),
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            temperature=temp,
            api_key=config.get("ANTHROPIC_API_KEY"),
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temp,
            google_api_key=config.get("GOOGLE_API_KEY"),
        )
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        base_url = config["llm"].get("base_url", "http://localhost:11434")
        return ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temp,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

