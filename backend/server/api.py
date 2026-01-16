import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .endpoints import router
from pathlib import Path
from dotenv import load_dotenv
from chainlit.utils import mount_chainlit
from fastapi.responses import RedirectResponse

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Set the root directory for Chainlit to find config and public files
project_root = Path(__file__).parent.parent.parent
os.environ["CHAINLIT_ROOT"] = str(project_root)

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
# Construct absolute path to app.py (works both locally and in Docker)
chainlit_app_path = str(Path(__file__).parent.parent.parent / "app.py")
mount_chainlit(app=app, target=chainlit_app_path, path="/chat")

@app.get("/")
async def root():
    # Redirect users immediately to the chat interface
    return RedirectResponse(url="/chat")
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
