import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .endpoints import router
from pathlib import Path
from dotenv import load_dotenv
from chainlit.utils import mount_chainlit
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
app = FastAPI(title="CRS ADK Backend API")
app.include_router(router)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint for Cloud Run
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy", "service": "CRS ADK Backend API"}

# MOUNT CHAINLIT
# target: path to your chainlit python file relative to the working directory
mount_chainlit(app=app, target="app.py", path="/chat")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
