import os
import subprocess
import json
import logging
from typing import Any, List, Optional
import google.generativeai as genai
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
        if api_key and not api_key.startswith("YOUR_"):
            logger.info("BRIDGE - Using Gemini API Key for orchestration")
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(self.model_name)
        else:
            logger.info("BRIDGE - No API key found, using local Gemini CLI fallback")
            self._model = None

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        
        # 1. Try Direct API first if available
        if self._model:
            try:
                # Convert messages to string for simplicity with GenAI SDK
                prompt = ""
                for m in messages:
                    role = "user" if m.type == "human" else "model" if m.type == "ai" else "system"
                    prompt += f"[{role}]: {m.content}\n\n"

                response = self._model.generate_content(prompt)
                text = response.text
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])
            except Exception as e:
                logger.error(f"BRIDGE - API Error, falling back to CLI: {str(e)}")

        # 2. Fallback to CLI
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
                # Find the LAST JSON block
                start_idx = output.rfind('{')
                if start_idx != -1:
                    try:
                        data = json.loads(output[start_idx:])
                        text = data.get("response", output)
                    except:
                        text = output
                else:
                    text = output if output else "No response from CLI."
        except Exception as e:
            text = f"Bridge Exception: {str(e)}"

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    @property
    def _llm_type(self) -> str:
        return "gemini-unified-bridge"
