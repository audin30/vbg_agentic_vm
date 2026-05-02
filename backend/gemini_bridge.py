import os
import subprocess
import json
import logging
from typing import Any, List, Optional

# Flexible imports to handle different SDK versions and environments
try:
    import google.generativeai as genai_old
    HAS_OLD_SDK = True
except ImportError:
    HAS_OLD_SDK = False

try:
    from google import genai as genai_new
    HAS_NEW_SDK = True
except ImportError:
    HAS_NEW_SDK = False

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

logger = logging.getLogger(__name__)

class LocalCLIBridge(BaseChatModel):
    """
    A unified bridge that uses Gemini API (Direct SDK) if GEMINI_API_KEY is present,
    otherwise falls back to the local Gemini CLI.
    """
    model_name: str = "gemini-2.0-flash"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        api_key = os.getenv("GEMINI_API_KEY")
        self._client = None
        self._old_model = None

        if api_key and not api_key.startswith("YOUR_"):
            logger.info("BRIDGE - Attempting to initialize Gemini SDK")
            # 1. Try Modern SDK first
            if HAS_NEW_SDK:
                try:
                    self._client = genai_new.Client(api_key=api_key)
                    logger.info("BRIDGE - Modern Gemini SDK (google-genai) initialized")
                except Exception as e:
                    logger.warning(f"BRIDGE - Modern SDK init failed: {e}")
            
            # 2. Try Old SDK if modern isn't available or failed
            if not self._client and HAS_OLD_SDK:
                try:
                    genai_old.configure(api_key=api_key)
                    self._old_model = genai_old.GenerativeModel(self.model_name)
                    logger.info("BRIDGE - Legacy Gemini SDK (google-generativeai) initialized")
                except Exception as e:
                    logger.warning(f"BRIDGE - Legacy SDK init failed: {e}")

        if not self._client and not self._old_model:
            logger.info("BRIDGE - No SDK available, using local Gemini CLI fallback")

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        
        # 1. Try Direct API (Modern)
        if self._client:
            try:
                prompt = self._format_messages(messages)
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response.text))])
            except Exception as e:
                logger.error(f"BRIDGE - Modern API Error: {str(e)}")

        # 2. Try Direct API (Legacy)
        if self._old_model:
            try:
                prompt = self._format_messages(messages)
                response = self._old_model.generate_content(prompt)
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response.text))])
            except Exception as e:
                logger.error(f"BRIDGE - Legacy API Error: {str(e)}")

        # 3. Fallback to CLI
        return self._generate_via_cli(messages)

    def _format_messages(self, messages: List[BaseMessage]) -> str:
        prompt = ""
        for m in messages:
            role = "user" if m.type == "human" else "model" if m.type == "ai" else "system"
            prompt += f"[{role}]: {m.content}\n\n"
        return prompt

    def _generate_via_cli(self, messages: List[BaseMessage]) -> ChatResult:
        prompt = ""
        for m in messages:
            role = "USER" if m.type == "human" else "AGENT" if m.type == "ai" else "SYSTEM"
            prompt += f"### {role} ###\n{m.content}\n\n"

        cmd = ["gemini", "--prompt", prompt, "--output-format", "json", "--skip-trust", "--approval-mode", "yolo", "--model", self.model_name]
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
                    text = output if output else "No response from CLI."
        except Exception as e:
            text = f"Bridge Exception: {str(e)}"

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    @property
    def _llm_type(self) -> str:
        return "gemini-unified-bridge"
