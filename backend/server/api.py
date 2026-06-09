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

# Set the root directory for Chainlit to find config and public files
project_root = Path(__file__).parent.parent.parent
os.environ["CHAINLIT_ROOT"] = str(project_root)

app = FastAPI(title="CRS ADK Backend API")

# API routes live under /api/ so Chainlit can be mounted at root without conflicts
app.include_router(router, prefix="/api")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check (kept at root level for container orchestration)
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "CRS ADK Backend API"}

# Mount Chainlit at root so HF Spaces iframe loads it directly (no redirect chain)
chainlit_app_path = str(Path(__file__).parent.parent.parent / "app.py")
mount_chainlit(app=app, target=chainlit_app_path, path="/")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
