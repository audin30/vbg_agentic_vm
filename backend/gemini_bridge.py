import subprocess
import json
import logging
import os
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

class GeminiChatCLI:
    """
    A lightweight bridge that routes prompts through the Gemini CLI.
    Designed to be manually assigned to CrewAI agents to bypass Pydantic validation.
    """
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name

    def __call__(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        return self.predict(prompt, stop)

    def predict(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        # Build the CLI command
        cmd = ["gemini", "--prompt", prompt, "--output-format", "json", "--skip-trust", "--approval-mode", "yolo"]
        
        if self.model_name:
            cmd.extend(["--model", self.model_name])

        logger.info(f"BRIDGE - Calling Gemini CLI (model: {self.model_name})")
        
        # Ensure the subprocess inherits the trust environment variable
        env = os.environ.copy()
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
            
            if result.returncode != 0:
                logger.error(f"BRIDGE - CLI error: {result.stderr}")
                return f"Error from Gemini CLI: {result.stderr}"

            output = result.stdout.strip()
            
            # Extract JSON response
            start_idx = output.find('{')
            if start_idx != -1:
                json_part = output[start_idx:]
                try:
                    data = json.loads(json_part)
                    return data.get("response", output)
                except json.JSONDecodeError:
                    return output
            
            return output if output else "No response from Gemini CLI."

        except subprocess.TimeoutExpired:
            return "Gemini CLI request timed out."
        except Exception as e:
            return f"Exception while calling Gemini CLI: {str(e)}"
    
    # Compatibility methods for LangChain/CrewAI
    def invoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
        # Handle both string and Message list inputs
        prompt = input if isinstance(input, str) else str(input)
        response = self.predict(prompt)
        
        # Return a simple object that looks like a ChatResult if needed
        class SimpleResponse:
            def __init__(self, content):
                self.content = content
            def __str__(self):
                return self.content
        
        return SimpleResponse(response)
