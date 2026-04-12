from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import voice, vision, parse, inventory
import os

app = FastAPI(title="Speak Snap Store", description="AI-Powered Inventory Management")

# CORS for React frontend
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(vision.router, prefix="/api/vision", tags=["Vision"])
app.include_router(parse.router, prefix="/api/parse", tags=["Parse"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])

@app.get("/")
def root():
    return {"message": "Speak Snap Store API", "status": "active", "version": "2.0"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)