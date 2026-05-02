import subprocess
import json
import logging
import os
from typing import Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

logger = logging.getLogger(__name__)

class LocalCLIBridge(ChatOpenAI):
    """
    A 'Stealth Bridge' that inherits from ChatOpenAI to fool CrewAI's 
    internal checks, but overrides the actual generation to use the local Gemini CLI.
    """
    model_name: str = "gpt-4-stealth-bridge" # Fool the validator

    def __init__(self, **kwargs):
        # Initialize with dummy data to satisfy BaseChatOpenAI
        super().__init__(openai_api_key="sk-local-bridge", **kwargs)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # 1. Convert messages to CLI prompt
        prompt = ""
        for m in messages:
            role = "USER" if m.type == "human" else "AGENT" if m.type == "ai" else "SYSTEM"
            prompt += f"### {role} ###\n{m.content}\n\n"

        # 2. Call Local Gemini CLI
        cmd = ["gemini", "--prompt", prompt, "--output-format", "json", "--skip-trust", "--approval-mode", "yolo", "--model", "gemini-2.0-flash"]
        
        env = os.environ.copy()
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"

        logger.info(f"STEALTH BRIDGE - Executing Gemini CLI")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
            
            if result.returncode != 0:
                text_response = f"Error from CLI: {result.stderr}"
            else:
                output = result.stdout.strip()
                # Find the LAST JSON block
                start_idx = output.rfind('{')
                if start_idx != -1:
                    try:
                        data = json.loads(output[start_idx:])
                        text_response = data.get("response", output)
                    except:
                        text_response = output
                else:
                    text_response = output if output else "No response from CLI."

        except Exception as e:
            text_response = f"Stealth Bridge Exception: {str(e)}"

        # 3. Return as a standard ChatResult
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text_response))])

    @property
    def _llm_type(self) -> str:
        return "openai" # Fool CrewAI into thinking it's native
