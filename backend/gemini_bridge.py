import subprocess
import json
import logging
import os
from typing import Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

logger = logging.getLogger(__name__)

class LocalCLIBridge(BaseChatModel):
    """
    A pure LangChain bridge that routes prompts through the local Gemini CLI.
    """
    model_name: str = "local-bridge"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt = ""
        for m in messages:
            role = "USER" if m.type == "human" else "AGENT" if m.type == "ai" else "SYSTEM"
            prompt += f"### {role} ###\n{m.content}\n\n"

        cmd = ["gemini", "--prompt", prompt, "--output-format", "json", "--skip-trust", "--approval-mode", "yolo", "--model", "gemini-2.0-flash"]
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
        return "custom"
