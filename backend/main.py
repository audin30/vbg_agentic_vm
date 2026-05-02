import os
os.environ["CREWAI_TELEMETRY_OPTOUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["OPENAI_API_KEY"] = "sk-local-bridge-no-key-required"

from dotenv import load_dotenv
load_dotenv()

# Rest of the imports
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt
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

class OrchestrationRequest(BaseModel):
    indicator: Optional[str] = None
    indicator_type: Optional[str] = None
    question: Optional[str] = None

@app.post("/api/orchestrate")
async def orchestrate(request: OrchestrationRequest, current_user: str = Depends(get_current_user)):
    await db.log_audit(current_user, "orchestrate_start", request.dict())
    
    async def event_generator():
        try:
            yield "event: thought\ndata: Initializing local security agents...\n\n"
            
            from crew import create_chat_crew, create_security_crew
            if request.question:
                crew = create_chat_crew(request.question)
            else:
                crew = create_security_crew(request.indicator, request.indicator_type)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crew.kickoff)
            
            final_result = str(result)
            await db.log_audit(current_user, "orchestrate_complete", None, final_result)
            yield f"data: {final_result}\n\n"
            
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
