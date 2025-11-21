from fastapi.responses import FileResponse, RedirectResponse
from app.util.video_tools import *
from app.util.pdf_tools import *
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import tab_routes
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, HTTPException, Request

app = FastAPI(title="Guitar Tabs Generator")

# TODO
# This will be a big todo list for the app
# add user titling and automatic titling based on youtube title to output pdf
# use AWS to set up user accounts and store their generated tabs
# allow users to download their generated pdfs from their account page
# add header, about, instuctions pages to improve site usability and look

# Allow frontend access (adjust domains later if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (like CSS, JS)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="app/templates")

# Register routes
app.include_router(tab_routes.router)

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico")

@app.get("/")
def root(request: Request):
    return RedirectResponse(url="/tabs/")
