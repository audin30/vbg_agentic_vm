import subprocess
import json
import logging
from typing import Any, List, Mapping, Optional, Union
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

logger = logging.getLogger(__name__)

class GeminiChatCLI(BaseChatModel):
    """
    A custom LangChain ChatModel that routes all prompts through the Gemini CLI.
    This allows running agents without a GEMINI_API_KEY in the environment.
    """
    model_name: str = "gemini-cli"

    @property
    def _llm_type(self) -> str:
        return "gemini_cli_chat"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Convert messages to a single prompt for the CLI
        prompt_parts = []
        for m in messages:
            if isinstance(m, SystemMessage):
                prompt_parts.append(f"System: {m.content}")
            elif isinstance(m, HumanMessage):
                prompt_parts.append(f"User: {m.content}")
            elif isinstance(m, AIMessage):
                prompt_parts.append(f"Assistant: {m.content}")
            else:
                prompt_parts.append(f"{m.type}: {m.content}")
        
        full_prompt = "\n".join(prompt_parts)
        
        # We use --approval-mode yolo to ensure it doesn't hang waiting for tool approvals
        # and --output-format json to get structured results.
        # Note: --yolo and --approval-mode are mutually exclusive in newer CLI versions.
        cmd = ["gemini", "--prompt", full_prompt, "--output-format", "json", "--skip-trust", "--approval-mode", "yolo"]
        
        if self.model_name and self.model_name != "gemini-cli":
            cmd.extend(["--model", self.model_name])

        logger.info(f"Executing Gemini CLI for chat (messages: {len(messages)}, model: {self.model_name})")
        
        # Ensure the subprocess inherits the trust environment variable
        env = os.environ.copy()
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
            
            if result.returncode != 0:
                logger.error(f"Gemini CLI error: {result.stderr}")
                text = f"Error from Gemini CLI: {result.stderr}"
            else:
                output = result.stdout.strip()
                # Find the first JSON block (the actual response)
                start_idx = output.find('{')
                if start_idx != -1:
                    json_part = output[start_idx:]
                    try:
                        data = json.loads(json_part)
                        text = data.get("response", output)
                    except json.JSONDecodeError:
                        text = output
                else:
                    text = output if output else "No response from Gemini CLI."

        except subprocess.TimeoutExpired:
            text = "Gemini CLI request timed out."
        except Exception as e:
            text = f"Exception while calling Gemini CLI: {str(e)}"

        message = AIMessage(content=text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {"model_name": self.model_name}
