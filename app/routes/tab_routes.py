from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Body
from pydantic import BaseModel
import os
import subprocess
from app.util.video_tools import load_video, select_tab_area, capture_tab_frames, auto_detect_threshold
from app.util.pdf_tools import create_print_ready_pdf


router = APIRouter(prefix="/tabs", tags=["tabs"])
templates = Jinja2Templates(directory="app/templates")

class TabRequest(BaseModel):
    youtube_url: str
    start_buffer : int
    end_buffer : int

@router.get("/", response_class=HTMLResponse)
async def show_form(request: Request):
    """Show a simple upload form."""
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/fetch_video_info")
def fetch_video_info(request: TabRequest):
    youtube_url = request.youtube_url
    video_id = youtube_url.split("watch?v=")[1]  # simple regex or split
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    return {"video_id": video_id, "thumbnail_url": thumbnail_url}

@router.post("/process_video", response_class=HTMLResponse)
def create_tabs(request: TabRequest = Body(...)):
    print("Received request:", request)
    video_url = request.youtube_url
    video_path = os.path.join("app", "static", "video.mp4")

    # Step 1: Download video using yt-dlp
    try:
        subprocess.run(["yt-dlp", "-f", "bestvideo", "-o", video_path, video_url], check=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading video: {e}")

    # Step 2: Process video
    try:
        cap, fps, frame = load_video(video_path, start_time=5)
        tab_area = select_tab_area(frame)  # TODO: automate ROI later
        threshold = auto_detect_threshold(cap, fps, tab_area)
        image_paths = capture_tab_frames(cap, fps, tab_area, threshold, end_time=5)
        create_print_ready_pdf(image_paths, title_text="Guitar Tabs", output_path=os.path.join("app", "static", "output.pdf"))
        cap.release()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video processing failed: {e}")

    from fastapi.responses import FileResponse
    return {"message": "PDF ready!", "output": "output.pdf"}
    
