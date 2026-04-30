try:
    from crewai.agent import Agent
    import pydantic
    print(f"Pydantic version: {pydantic.__version__}")
    
    # Check the type hint for 'llm' in crewai.Agent
    from typing import get_type_hints
    hints = get_type_hints(Agent)
    print(f"Agent.llm type hint: {hints.get('llm')}")
    
    # Try to see where BaseLLM is imported from in crewai
    import crewai
    print(f"CrewAI file: {crewai.__file__}")
    
    try:
        from langchain_core.language_models.llms import LLM as LLM1
        from langchain.llms.base import LLM as LLM2
        print("langchain_core.language_models.llms.LLM is available")
        print("langchain.llms.base.LLM is available")
    except ImportError as e:
        print(f"Import error: {e}")

except Exception as e:
    print(f"Error: {e}")
