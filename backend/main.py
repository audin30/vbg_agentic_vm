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
import uuid

# Security imports
from auth import authenticate_user, create_access_token
from crew import create_security_crew
from logger_config import logger
from database.db_helper import db

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

@app.on_event("startup")
async def startup():
    await db.connect()
    logger.info("Database connection established.")

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()
    logger.info("Database connection closed.")

class OrchestrationRequest(BaseModel):
    indicator: Optional[str] = None
    indicator_type: Optional[str] = None # ip, domain, hash, cve
    question: Optional[str] = None

class TabUpdateRequest(BaseModel):
    title: str
    query_state: dict

class FeedbackRequest(BaseModel):
    action_type: str
    target: str
    decision: str
    feedback_notes: Optional[str] = None

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
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me/tabs")
async def get_user_tabs(current_user: str = Depends(get_current_user)):
    tabs = await db.get_user_tabs(current_user)
    return tabs

@app.post("/api/queries")
async def create_query(current_user: str = Depends(get_current_user)):
    tab_id = await db.save_user_tab(current_user, "New Query", {})
    return {"query_id": tab_id}

@app.put("/api/queries/{tab_id}")
async def update_query(tab_id: str, request: TabUpdateRequest, current_user: str = Depends(get_current_user)):
    await db.save_user_tab(current_user, request.title, request.query_state, tab_id)
    return {"status": "success"}

@app.delete("/api/queries/{tab_id}")
async def delete_query(tab_id: str, current_user: str = Depends(get_current_user)):
    await db.close_user_tab(current_user, tab_id)
    return {"status": "success"}

@app.post("/api/feedback")
async def save_feedback(request: FeedbackRequest, current_user: str = Depends(get_current_user)):
    await db.save_feedback(current_user, request.action_type, request.target, request.decision, request.feedback_notes)
    return {"status": "success"}

@app.get("/api/feedback/{target}")
async def get_feedback(target: str, current_user: str = Depends(get_current_user)):
    feedback = await db.get_feedback_for_target(target)
    return feedback

@app.post("/api/orchestrate")
async def orchestrate(request: OrchestrationRequest, current_user: str = Depends(get_current_user)):
    await db.log_audit(current_user, "orchestrate_start", request.dict())
    try:
        if request.question:
            from crew import create_chat_crew
            crew = create_chat_crew(request.question)
        else:
            crew = create_security_crew(request.indicator, request.indicator_type)
            
        result = await crew.kickoff_async()
        
        await db.log_audit(current_user, "orchestrate_complete", None, str(result))
        
        return {
            "status": "success",
            "result": str(result)
        }
    except Exception as e:
        await db.log_audit(current_user, "orchestrate_error", None, str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Security Orchestrator Backend on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
