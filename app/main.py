from app.util.video_tools import *
from app.util.pdf_tools import *
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import tabs

app = FastAPI(title="Guitar Tabs Generator")

# Allow frontend access (adjust domains later if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(tabs.router)

@app.get("/")
def root():
    return {"message": "Welcome to the Guitar Tabs API"}
