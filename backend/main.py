import os
from dotenv import load_dotenv

# MUST happen before importing crew/LLM
load_dotenv()
os.environ["GEMINI_API_VERSION"] = "v1"
os.environ["GOOGLE_API_VERSION"] = "v1"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from crew import create_security_crew

if not os.getenv("GEMINI_API_KEY"):
    print("WARNING: GEMINI_API_KEY is not set in backend/.env. Agents will not function.")
else:
    # Set both for different library expectations
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

if not os.getenv("WINRM_USER") or not os.getenv("WINRM_PASSWORD"):
    print("WARNING: WINRM credentials are not set. Remediation tasks will fail.")

if not os.getenv("MACOS_SSH_USER") or not os.getenv("MACOS_SSH_KEY_PATH"):
    print("WARNING: macOS SSH credentials are not set. macOS remediation will fail.")

if not os.getenv("UBUNTU_SSH_USER") or not os.getenv("UBUNTU_SSH_KEY_PATH"):
    print("WARNING: Ubuntu SSH credentials are not set. Ubuntu remediation tasks will fail.")

app = FastAPI(title="Security Orchestrator API")

# Add CORS Middleware to allow Electron to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OrchestrationRequest(BaseModel):
    indicator: Optional[str] = None
    indicator_type: Optional[str] = None # ip, domain, hash, cve
    question: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Security Orchestrator API is running"}

@app.post("/api/orchestrate")
async def orchestrate(request: OrchestrationRequest):
    print(f"Received request: {request}")
    try:
        if request.question:
            print(f"Handling question: {request.question}")
            from crew import create_chat_crew
            crew = create_chat_crew(request.question)
        else:
            print(f"Investigating {request.indicator_type}: {request.indicator}")
            crew = create_security_crew(request.indicator, request.indicator_type)
            
        result = crew.kickoff()
        print("Orchestration complete.")
        
        return {
            "status": "success",
            "result": str(result)
        }
    except Exception as e:
        print(f"Error during orchestration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("Starting Security Orchestrator Backend on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
