import subprocess
import json
import logging
import os
from typing import Any, List, Mapping, Optional
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

logger = logging.getLogger(__name__)

class GeminiChatCLI(LLM):
    """
    A custom LangChain LLM that routes all prompts through the Gemini CLI.
    This allows running agents without a GEMINI_API_KEY in the environment,
    leveraging the CLI's authenticated session.
    
    Inheriting from 'LLM' (BaseLLM) ensures compatibility with Pydantic 
    validators in CrewAI and older LangChain environments.
    """
    model_name: str = "gemini-2.0-flash"

    @property
    def _llm_type(self) -> str:
        return "gemini_cli"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        # We use --approval-mode yolo to ensure it doesn't hang waiting for tool approvals
        # and --output-format json to get structured results.
        cmd = ["gemini", "--prompt", prompt, "--output-format", "json", "--skip-trust", "--approval-mode", "yolo"]
        
        if self.model_name and self.model_name != "gemini-cli":
            cmd.extend(["--model", self.model_name])

        logger.info(f"Executing Gemini CLI (model: {self.model_name})")
        
        # Ensure the subprocess inherits the trust environment variable
        env = os.environ.copy()
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
            
            if result.returncode != 0:
                logger.error(f"Gemini CLI error: {result.stderr}")
                return f"Error from Gemini CLI: {result.stderr}"

            output = result.stdout.strip()
            # Find the first JSON block (the actual response)
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

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {"model_name": self.model_name}
