import os
import subprocess
import json
import logging
from typing import Any, List, Optional

# Flexible imports for Gemini SDK
def get_gemini_sdk():
    try:
        from google import genai
        return genai, "modern"
    except ImportError:
        try:
            import google.generativeai as genai
            return genai, "legacy"
        except ImportError:
            return None, None

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

logger = logging.getLogger(__name__)

class SecurityHubLLM(BaseChatModel):
    """
    A custom security-focused LLM bridge that uses Gemini Cloud API 
    with a local Gemini CLI fallback.
    """
    model_name: str = "security-hub-engine"
    
    # Use regular attributes but initialize them in a way that avoids Pydantic issues
    # In Pydantic v2 / LangChain, we can often just set them in __init__
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use object.__setattr__ to bypass Pydantic's __setattr__ if necessary
        object.__setattr__(self, "_sdk_instance", None)
        object.__setattr__(self, "_sdk_type", None)
        object.__setattr__(self, "_target_model", "models/gemini-flash-latest")

        api_key = os.getenv("GEMINI_API_KEY")

        if api_key and not api_key.startswith("YOUR_"):
            sdk, sdk_type = get_gemini_sdk()
            if sdk_type == "modern":
                try:
                    object.__setattr__(self, "_sdk_instance", sdk.Client(api_key=api_key))
                    object.__setattr__(self, "_sdk_type", "modern")
                    logger.info("SECURITY-HUB-LLM: Cloud API (Modern) ready")
                except Exception as e:
                    logger.warning(f"SECURITY-HUB-LLM: Modern SDK init failed: {e}")
            elif sdk_type == "legacy":
                try:
                    sdk.configure(api_key=api_key)
                    object.__setattr__(self, "_sdk_instance", sdk.GenerativeModel(self._target_model))
                    object.__setattr__(self, "_sdk_type", "legacy")
                    logger.info("SECURITY-HUB-LLM: Cloud API (Legacy) ready")
                except Exception as e:
                    logger.warning(f"SECURITY-HUB-LLM: Legacy SDK init failed: {e}")

        if not getattr(self, "_sdk_instance", None):
            logger.info("SECURITY-HUB-LLM: Cloud API unavailable, using Local CLI fallback")

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        
        sdk_instance = getattr(self, "_sdk_instance", None)
        sdk_type = getattr(self, "_sdk_type", None)
        target_model = getattr(self, "_target_model", "models/gemini-flash-latest")

        # 1. Try Cloud API
        if sdk_instance:
            try:
                prompt = self._format_chat_prompt(messages)
                if sdk_type == "modern":
                    response = sdk_instance.models.generate_content(
                        model=target_model,
                        contents=prompt
                    )
                    text = response.text
                else: # legacy
                    response = sdk_instance.generate_content(prompt)
                    text = response.text
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])
            except Exception as e:
                logger.error(f"SECURITY-HUB-LLM: Cloud API Error: {str(e)}")

        # 2. Local Fallback
        return self._run_local_cli(messages)

    def _format_chat_prompt(self, messages: List[BaseMessage]) -> str:
        formatted = ""
        for m in messages:
            role = "user" if m.type == "human" else "model" if m.type == "ai" else "system"
            formatted += f"[{role.upper()}]: {m.content}\n\n"
        return formatted

    def _run_local_cli(self, messages: List[BaseMessage]) -> ChatResult:
        target_model = getattr(self, "_target_model", "models/gemini-flash-latest")
        prompt = ""
        for m in messages:
            role = "USER" if m.type == "human" else "AGENT" if m.type == "ai" else "SYSTEM"
            prompt += f"### {role} ###\n{m.content}\n\n"

        cmd = ["gemini", "--prompt", prompt, "--output-format", "json", "--skip-trust", "--approval-mode", "yolo", "--model", target_model]
        env = os.environ.copy()
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
            if result.returncode != 0:
                text = f"Local Engine Error: {result.stderr}"
            else:
                output = result.stdout.strip()
                start_idx = output.rfind('{')
                if start_idx != -1:
                    data = json.loads(output[start_idx:])
                    text = data.get("response", output)
                else:
                    text = output if output else "No local response."
        except Exception as e:
            text = f"Local Engine Exception: {str(e)}"

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    @property
    def _llm_type(self) -> str:
        return "security-hub-orchestrator"
