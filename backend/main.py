import os
import sys
from datetime import timedelta

# --- ABSOLUTE LOCKDOWN (MUST BE FIRST) ---
os.environ["CREWAI_TELEMETRY_OPTOUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["OPENAI_API_KEY"] = "sk-no-network-allowed-local-bridge-only"
os.environ["OPENAI_API_BASE"] = "http://localhost:9999/v1" 
# -----------------------------------------

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
import uuid
import asyncio
from fastapi.responses import StreamingResponse
import logging

# App specific
from auth import authenticate_user, create_access_token, get_current_user
from database.db_helper import db
from logger_config import logger
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    logger.info("Database connection established.")
    yield
    await db.disconnect()
    logger.info("Database connection closed.")

app = FastAPI(title="Security Orchestrator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas ---

class OrchestrationRequest(BaseModel):
    indicator: Optional[str] = None
    indicator_type: Optional[str] = None
    question: Optional[str] = None

class TabStateUpdate(BaseModel):
    title: str
    query_state: dict

class FeedbackRequest(BaseModel):
    action_type: str
    target: str
    decision: str
    feedback_notes: Optional[str] = None

# --- Endpoints ---

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token({"sub": user}), "token_type": "bearer"}

@app.get("/api/users/me/tabs")
async def get_tabs(current_user: str = Depends(get_current_user)):
    return await db.get_user_tabs(current_user)

@app.post("/api/queries")
async def create_query(current_user: str = Depends(get_current_user)):
    query_id = await db.save_user_tab(current_user, "New Investigation", {})
    return {"query_id": query_id}

@app.put("/api/queries/{query_id}")
async def update_query(query_id: str, update: TabStateUpdate, current_user: str = Depends(get_current_user)):
    await db.save_user_tab(current_user, update.title, update.query_state, query_id)
    return {"status": "success"}

@app.delete("/api/queries/{query_id}")
async def delete_query(query_id: str, current_user: str = Depends(get_current_user)):
    await db.close_user_tab(current_user, query_id)
    return {"status": "success"}

@app.post("/api/feedback")
async def post_feedback(feedback: FeedbackRequest, current_user: str = Depends(get_current_user)):
    await db.save_feedback(current_user, feedback.action_type, feedback.target, feedback.decision, feedback.feedback_notes)
    return {"status": "success"}

@app.get("/api/feedback/{target}")
async def get_feedback(target: str, current_user: str = Depends(get_current_user)):
    return await db.get_feedback_for_target(target)

@app.post("/api/orchestrate")
async def orchestrate(request: OrchestrationRequest, current_user: str = Depends(get_current_user)):
    async def event_generator():
        try:
            yield "event: thought\ndata: Activating local security agents...\n\n"
            from crew import create_chat_crew, create_security_crew
            crew = create_chat_crew(request.question) if request.question else create_security_crew(request.indicator, request.indicator_type)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crew.kickoff)
            yield f"data: {str(result)}\n\n"
        except Exception as e:
            logger.error(f"Orchestration Error: {str(e)}")
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/")
async def root():
    return {"message": "Security Orchestrator API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
