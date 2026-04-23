import os
from dotenv import load_dotenv

# MUST happen before importing crew/LLM
load_dotenv()
os.environ["GEMINI_API_VERSION"] = "v1"
os.environ["GOOGLE_API_VERSION"] = "v1"

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt

# Security imports
from auth import authenticate_user, create_access_token
from crew import create_security_crew
from logger_config import logger

if not os.getenv("GEMINI_API_KEY"):
    logger.warning("GEMINI_API_KEY is not set in backend/.env. Agents will not function.")
else:
    # Set both for different library expectations
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

if not os.getenv("WINRM_USER") or not os.getenv("WINRM_PASSWORD"):
    logger.warning("WINRM credentials are not set. Remediation tasks will fail.")

if not os.getenv("MACOS_SSH_USER") or not os.getenv("MACOS_SSH_KEY_PATH"):
    logger.warning("macOS SSH credentials are not set. macOS remediation will fail.")

if not os.getenv("UBUNTU_SSH_USER") or not os.getenv("UBUNTU_SSH_KEY_PATH"):
    logger.warning("Ubuntu SSH credentials are not set. Ubuntu remediation tasks will fail.")

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/")
async def root():
    return {"message": "Security Orchestrator API is running"}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/orchestrate")
async def orchestrate(request: OrchestrationRequest, current_user: str = Depends(get_current_user)):
    logger.info(f"AUDIT - User [{current_user}] requested orchestration: {request}")
    try:
        if request.question:
            logger.info(f"AUDIT - Handling Natural Language Question: {request.question}")
            from crew import create_chat_crew
            crew = create_chat_crew(request.question)
        else:
            logger.info(f"AUDIT - Investigating {request.indicator_type}: {request.indicator}")
            crew = create_security_crew(request.indicator, request.indicator_type)
            
        result = crew.kickoff()
        logger.info("AUDIT - Orchestration cycle complete.")
        logger.info(f"AUDIT - FINAL OUTPUT: {str(result)}")
        
        return {
            "status": "success",
            "result": str(result)
        }
    except Exception as e:
        logger.error(f"AUDIT - Error during orchestration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Security Orchestrator Backend on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
