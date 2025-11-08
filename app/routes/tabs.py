from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import subprocess
from app.util.video_tools import load_video, select_tab_area, capture_tab_frames, auto_detect_threshold
from app.util.pdf_tools import create_print_ready_pdf

router = APIRouter(prefix="/tabs", tags=["tabs"])

class TabRequest(BaseModel):
    youtube_url: str

@router.post("/")
def create_tabs(request: TabRequest):
    video_url = request.youtube_url
    video_path = "video.mp4"

    # Step 1: Download video using yt-dlp
    try:
        subprocess.run(["yt-dlp", "-f", "best", "-o", video_path, video_url], check=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading video: {e}")

    # Step 2: Process video
    try:
        cap, fps, frame = load_video(video_path, start_time=5)
        tab_area = select_tab_area(frame)  # TODO: automate ROI later
        threshold = auto_detect_threshold(cap, fps, tab_area)
        image_paths = capture_tab_frames(cap, fps, tab_area, threshold, end_time=5)
        create_print_ready_pdf(image_paths, title_text="Guitar Tabs", output_path="output.pdf")
        cap.release()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video processing failed: {e}")

    return {"message": "Guitar tabs PDF created successfully", "output": "output.pdf"}
