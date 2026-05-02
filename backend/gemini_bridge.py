import os
import subprocess
import json
import logging
from typing import Any, List, Optional

# Late imports to ensure environment is fully loaded
def get_sdk():
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

class LocalCLIBridge(BaseChatModel):
    """
    A unified bridge that uses Gemini API if GEMINI_API_KEY is present,
    otherwise falls back to the local Gemini CLI.
    """
    # Using a generic name to prevent CrewAI from trying to use its native provider
    model_name: str = "orchestrator-core-engine"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._api_key = os.getenv("GEMINI_API_KEY")
        self._real_model = "gemini-2.0-flash"
        self._client = None
        self._sdk_type = None

        if self._api_key and not self._api_key.startswith("YOUR_"):
            sdk, sdk_type = get_sdk()
            if sdk_type == "modern":
                try:
                    self._client = sdk.Client(api_key=self._api_key)
                    self._sdk_type = "modern"
                    logger.info("BRIDGE - Gemini API (Modern SDK) ready")
                except Exception as e:
                    logger.warning(f"BRIDGE - Modern SDK init error: {e}")
            elif sdk_type == "legacy":
                try:
                    sdk.configure(api_key=self._api_key)
                    self._client = sdk.GenerativeModel(self._real_model)
                    self._sdk_type = "legacy"
                    logger.info("BRIDGE - Gemini API (Legacy SDK) ready")
                except Exception as e:
                    logger.warning(f"BRIDGE - Legacy SDK init error: {e}")

        if not self._client:
            logger.info("BRIDGE - No API SDK available, using local Gemini CLI fallback")

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        
        # 1. Try API first
        if self._client:
            try:
                prompt = self._format_prompt(messages)
                if self._sdk_type == "modern":
                    response = self._client.models.generate_content(
                        model=self._real_model,
                        contents=prompt
                    )
                    text = response.text
                else: # legacy
                    response = self._client.generate_content(prompt)
                    text = response.text
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])
            except Exception as e:
                logger.error(f"BRIDGE - API Execution Error: {str(e)}")

        # 2. Fallback to CLI
        return self._generate_via_cli(messages)

    def _format_prompt(self, messages: List[BaseMessage]) -> str:
        formatted = ""
        for m in messages:
            role = "user" if m.type == "human" else "model" if m.type == "ai" else "system"
            formatted += f"[{role}]: {m.content}\n\n"
        return formatted

    def _generate_via_cli(self, messages: List[BaseMessage]) -> ChatResult:
        prompt = ""
        for m in messages:
            role = "USER" if m.type == "human" else "AGENT" if m.type == "ai" else "SYSTEM"
            prompt += f"### {role} ###\n{m.content}\n\n"

        cmd = ["gemini", "--prompt", prompt, "--output-format", "json", "--skip-trust", "--approval-mode", "yolo", "--model", self._real_model]
        env = os.environ.copy()
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
            if result.returncode != 0:
                text = f"Error from CLI: {result.stderr}"
            else:
                output = result.stdout.strip()
                start_idx = output.rfind('{')
                if start_idx != -1:
                    data = json.loads(output[start_idx:])
                    text = data.get("response", output)
                else:
                    text = output if output else "No response."
        except Exception as e:
            text = f"Bridge Exception: {str(e)}"

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    @property
    def _llm_type(self) -> str:
        return "local-bridge"
