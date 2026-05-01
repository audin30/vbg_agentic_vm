import subprocess
import json
import logging
import os
from typing import Any, List, Optional, Dict
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

# Create a dedicated log for the bridge to help debugging
bridge_log = logging.getLogger("gemini_bridge")
handler = logging.FileHandler("bridge_debug.log")
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
bridge_log.addHandler(handler)
bridge_log.setLevel(logging.INFO)

class GeminiChatCLI(BaseChatModel):
    """
    A custom LangChain Chat Model that routes all prompts through the Gemini CLI.
    Inheriting from BaseChatModel ensures full compatibility with CrewAI.
    """
    model_name: str = "gemini-2.0-flash"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Convert LangChain messages to a single string for the CLI
        prompt = ""
        for m in messages:
            # We use a more distinct separator for different roles
            role = "USER" if m.type == "human" else "AGENT" if m.type == "ai" else "SYSTEM"
            prompt += f"### {role} ###\n{m.content}\n\n"

        # Build the CLI command
        # We use a longer timeout (300s) as CrewAI tasks can be complex
        cmd = ["gemini", "--prompt", prompt, "--output-format", "json", "--skip-trust", "--approval-mode", "yolo"]
        
        if self.model_name:
            cmd.extend(["--model", self.model_name])

        bridge_log.info(f"Calling Gemini CLI with prompt length: {len(prompt)}")
        
        env = os.environ.copy()
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"

        try:
            # We use a 5-minute timeout for the CLI bridge
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
            
            if result.returncode != 0:
                bridge_log.error(f"CLI Return Code {result.returncode}. Stderr: {result.stderr}")
                text_response = f"Error from Gemini CLI (Code {result.returncode}): {result.stderr}"
            else:
                output = result.stdout.strip()
                # Find the LAST JSON block (in case there's preamble)
                start_idx = output.rfind('{')
                if start_idx != -1:
                    try:
                        # Attempt to find matching closing brace if there's trailing junk
                        json_str = output[start_idx:]
                        # Simple check for balanced braces to handle trailing text
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
                        bridge_log.info("Successfully parsed JSON response from CLI.")
                    except Exception as e:
                        bridge_log.warning(f"JSON parsing failed: {str(e)}. Raw output: {output[:200]}...")
                        text_response = output
                else:
                    bridge_log.warning("No JSON block found in CLI output.")
                    text_response = output if output else "No response from CLI."

        except subprocess.TimeoutExpired:
            bridge_log.error("Gemini CLI timed out after 300s.")
            text_response = "Error: Gemini CLI request timed out. The task might be too complex for a single turn."
        except Exception as e:
            bridge_log.error(f"Bridge exception: {str(e)}")
            text_response = f"Bridge Exception: {str(e)}"

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text_response))])

    @property
    def _llm_type(self) -> str:
        return "gemini-cli-bridge"
