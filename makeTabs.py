# bash line to download a youtube video yt-dlp -f bestvideo "https://www.youtube.com/watch?v=EXAMPLE"
# run venv before doing
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
import numpy as np
import time
import os
import yt_dlp
from PIL import Image
import cv2
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Guitar tab screenshot/PDF generator")
    
    # URL or local video file
    parser.add_argument(
        "--url",
        type=str,
        help="YouTube video URL to process"
    )
    
    parser.add_argument(
        "--file",
        type=str,
        default="video2.mp4",
        help="Local video file to process (default: video2.mp4)"
    )
    
    # Optional: start/end buffers
    parser.add_argument("--start", type=float, default=5, help="Start buffer in seconds")
    parser.add_argument("--end", type=float, default=5, help="End buffer in seconds")
    
    # Optional: auto-detect threshold
    parser.add_argument("--auto-threshold", action="store_true", help="Enable auto-detect for similarity threshold")
    
    args = parser.parse_args()
    return args
    
def safe_crop(frame, roi, pad=5):
    """Safely crop region with small padding and clamped bounds."""
    h, w = frame.shape[:2]
    x, y, cw, ch = roi

    # Apply padding but clamp to frame size
    x1 = max(x - pad, 0)
    y1 = max(y - pad, 0)
    x2 = min(x + cw + pad, w)
    y2 = min(y + ch + pad, h)

    return frame[y1:y2, x1:x2]

def create_print_ready_pdf(image_paths, title_text, output_path="printable_guitar_tabs.pdf"):
    page_width, page_height = letter
    margin = 36 # 0.5 inch margin
    c = canvas.Canvas(output_path, pagesize=letter)
    bw_threshold = 180 # can be changed, everything above/below this is turned black or white
    line_spacing = 0.72

    if not image_paths:
        print("No images provided.")
        c.save()
        return

    y_cursor = page_height - margin

    # 🏷️ Draw title at top of first page
    if title_text:
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(page_width / 2, y_cursor, title_text)
        y_cursor -= 24  # leave space below title
        
    for img_path in image_paths:
        if not os.path.exists(img_path):
            print(f"Warning: {img_path} not found, skipping.")
            continue

        img = Image.open(img_path).convert("L")  # grayscale
        if bw_threshold is not None:
            # convert to pure black & white
            img = img.point(lambda p: 0 if p < bw_threshold else 255, '1')

        img_width, img_height = img.size

        # scale by width only, never upscale
        max_width = page_width - 2 * margin
        scale = min(max_width / img_width, 1.0)
        new_width = img_width * scale
        new_height = img_height * scale

        # if not enough vertical space, start new page
        if y_cursor - new_height < margin:
            c.showPage()
            y_cursor = page_height - margin

        x = (page_width - new_width) / 2
        y = y_cursor - new_height

        c.drawImage(ImageReader(img), x, y, width=new_width, height=new_height)
        y_cursor = y - line_spacing

    # finish last page
    c.save()
    print(f"Saved stacked PDF: {output_path}")
    return
    

def auto_detect_threshold(cap, fps, tab_area, sample_seconds = 30, change_threshold=5):
    x, y, w, h = tab_area
    changes = []
    prev_gray = None
    frame_count = 0
    frame_limit = int(sample_seconds * fps)

    while cap.isOpened() and frame_count < frame_limit:
        ret, frame = cap.read()
        if not ret:
            break

        cropped_gray = cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)

        if prev_gray is not None:
            diff = cv2.absdiff(prev_gray, cropped_gray)
            _, diff_thresh = cv2.threshold(diff, change_threshold, 255, cv2.THRESH_BINARY)
            change_percent = (cv2.countNonZero(diff_thresh) / diff_thresh.size) * 100
            if change_percent > 1: # only store remotely significant changes
                changes.append(change_percent)

        prev_gray = cropped_gray
        frame_count += 1

    if len(changes) < 5:
        print("Not enough data for auto-detection. Defaulting to 10%")
        return 10
    mean_change = np.mean(changes)
    std_change = np.std(changes)
    auto_threshold = round(mean_change + 2 * std_change, 2)

    print(f"Auto-detected threshold: {auto_threshold:.2f}% (mean={mean_change:.2f}, std={std_change:.2f})")
    return auto_threshold

def skip_time(video_capture, frames_to_skip, frame_count):
    for _ in range(frames_to_skip):
        video_capture.grab()
    return frame_count + frames_to_skip

def load_video(video_path, start_time):
    # load video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Error: Unable to open video file '{video_path}'.")
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    start_frame = int(fps * start_time)
    if start_frame >= total_frames:
        raise ValueError(f"Start time {start_time}s exceeds video length.")
    # Move the video to the desired timestamp
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    ret, frame = cap.read()
    if not ret:
        raise IOError("Error: Could not read frame after seeking.")
    return cap, fps, frame

def select_tab_area(frame):
    tab_area = cv2.selectROI("Select Tab Area", frame, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()
    return tab_area

def get_similarity_threshold(cap, fps, tab_area, start_time = 5):
    auto_detect = input("Auto-detect threshold? (y/n): ").lower().startswith("y")
    if auto_detect:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_time)
        threshold = auto_detect_threshold(cap, fps, tab_area, 30) # 30 is the hard coded number of seconds we scan to find the threshold
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_time) # reset so that this function leaves cap unchanged
    else:
        threshold = float(input("Enter manual similarity threshold (e.g., 15): ") or 15)
    return threshold

def capture_tab_frames(cap, fps, tab_area, similarity_threshold, end_time):
    image_paths = []
    frame_count = 0
    prev_cropped_gray = None
    change_threshold = 5  # pixel intensity threshold for per-pixel changes
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    end_frame = total_frames - int(end_time * fps)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Video ended")
            break

        # Stop before chosen end time
        current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        if current_frame >= end_frame:
            print("Reached defined end point — stopping early.")
            break
        
        # continue processing
        x, y, w, h = tab_area
        cropped = safe_crop(frame, tab_area)
        cropped_gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

        if prev_cropped_gray is not None:
            diff = cv2.absdiff(prev_cropped_gray, cropped_gray)
            _, diff_thresh = cv2.threshold(diff, change_threshold, 255, cv2.THRESH_BINARY)
            change_percent = (cv2.countNonZero(diff_thresh) / diff_thresh.size) * 100

            if change_percent > similarity_threshold:
                path = f"tab_screenshots/frame_{frame_count}.png"
                cv2.imwrite(path, cropped)
                image_paths.append(path)
                print(f"Saved frame {frame_count} ({change_percent:.2f}% change)")
                prev_cropped_gray = cropped_gray
        else:
            # Save first frame
            path = f"tab_screenshots/frame_{frame_count}.png"
            cv2.imwrite(path, cropped)
            image_paths.append(path)
            prev_cropped_gray = cropped_gray
            print(f"Saved first frame {frame_count}")

        frame_count += 1

    return image_paths

def save_as_pdf(image_paths, output_filename):
    if not image_paths:
        print("No images to save.")
        return
    images = [Image.open(p).convert("RGB") for p in image_paths]
    images[0].save(output_filename, save_all=True, append_images=images[1:])
    print(f"Saved PDF: {output_filename}")

def skip_edges(cap, fps, start_offset=5, end_offset=5):
    """Returns (start_frame, end_frame) adjusted for fade-in/out."""
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    start_frame = int(start_offset * fps)
    end_frame = total_frames - int(end_offset * fps)
    return start_frame, end_frame

def main():
    args = parse_args()
    # If URL is provided, use yt-dlp to download
    if args.url:
        ydl_opts = {
            "format": "bestvideo",
            "outtmpl": "temp_video.%(ext)s"
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(args.url)
            video_path = ydl.prepare_filename(info)
            video_title = info.get("title", "Unknown Title")
            print(f"✅ Downloaded: {video_title}")
    else:
        video_path = args.file or 'video2.mp4'
        video_title = None

    # 1. Load video and select region
    cap, fps, frame = load_video(video_path, start_time=5)
    tab_area = select_tab_area(frame)

    # 2. Create output folder
    os.makedirs("tab_screenshots", exist_ok=True)

    # 3. Detect or set similarity threshold
    cap.set(cv2.CAP_PROP_POS_FRAMES, fps * 5)
    similarity_threshold = get_similarity_threshold(cap, fps, tab_area)

    # 4. Capture tab frames
    image_paths = capture_tab_frames(cap, fps, tab_area, similarity_threshold, end_time=5) # TODO: eventually want both end time and start time to have user input
    print(image_paths)
    # 5. Save all images to a PDF
    if image_paths:
        create_print_ready_pdf(image_paths, video_title)
    save_as_pdf(image_paths, "guitar_tabs.pdf")

    cap.release()
    cv2.destroyAllWindows()

main()
