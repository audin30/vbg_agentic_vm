import subprocess
import json
import logging
import os
from typing import Any, List, Optional, Dict
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

bridge_log = logging.getLogger("bridge")

class LocalCLIBridge(BaseChatModel):
    """
    A generic bridge that routes prompts through the Gemini CLI.
    Renamed to avoid triggering CrewAI's native Google provider regex.
    """
    # Renamed to something generic
    model_name: str = "custom-orchestrator-bridge"

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

        # Use 'gemini-2.0-flash' internally but don't tell CrewAI
        real_model = "gemini-2.0-flash"
        cmd = ["gemini", "--prompt", prompt, "--output-format", "json", "--skip-trust", "--approval-mode", "yolo", "--model", real_model]
        
        env = os.environ.copy()
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
            
            if result.returncode != 0:
                text_response = f"Error from CLI: {result.stderr}"
            else:
                output = result.stdout.strip()
                start_idx = output.rfind('{')
                if start_idx != -1:
                    try:
                        json_str = output[start_idx:]
                        balance = 0
                        end_pos = 0
                        for i, char in enumerate(json_str):
                            if char == '{': balance += 1
                            elif char == '}': balance -= 1
                            if balance == 0:
                                end_pos = i + 1
                                break
                        data = json.loads(json_str[:end_pos])
                        text_response = data.get("response", output)
                    except:
                        text_response = output
                else:
                    text_response = output if output else "No response."

        except Exception as e:
            text_response = f"Bridge Exception: {str(e)}"

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text_response))])

    @property
    def _llm_type(self) -> str:
        return "local-bridge"
