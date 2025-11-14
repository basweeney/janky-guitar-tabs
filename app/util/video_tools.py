import os
import cv2
import numpy as np

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

def skip_edges(cap, fps, start_offset=5, end_offset=5):
    """Returns (start_frame, end_frame) adjusted for fade-in/out."""
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    start_frame = int(start_offset * fps)
    end_frame = total_frames - int(end_offset * fps)
    return start_frame, end_frame

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
    auto_threshold = round(mean_change + 1.5 * std_change, 2)

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
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if start_frame >= total_frames:
        raise ValueError(f"Start time {start_time}s exceeds video length.")
    # Move the video to the desired timestamp
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    ret, frame = cap.read()
    if not ret:
        raise IOError("Error: Could not read frame after seeking.")
    return cap, fps, frame, frame_width, frame_height

def select_tab_area(frame, roi=None, frame_width=None, frame_height=None, iframe_size=None):
    # scale the iframe roi to the actual video frame size
    if iframe_size is not None and frame_width is not None and frame_height is not None:
        iframe_width, iframe_height = iframe_size
        x_scale = frame_width / iframe_width
        y_scale = frame_height / iframe_height
        roi = {
            'x': int(roi.x * x_scale),
            'y': int(roi.y * y_scale),
            'width': int(roi.width * x_scale),
            'height': int(roi.height * y_scale)
        }

    if roi is not None:
        # ROI is passed as {x, y, width, height} from frontend
        tab_area = (roi['x'], roi['y'], roi['width'], roi['height'])
    else:
        # Fallback: manual selection (or a default value)
        tab_area = cv2.selectROI("Select Tab Area", frame, fromCenter=False, showCrosshair=True)
        cv2.destroyAllWindows()
    print("selected tab area:", tab_area)
    return tab_area

def get_similarity_threshold(cap, fps, tab_area, start_time = 3):
    auto_detect = input("Auto-detect threshold? (y/n): ").lower().startswith("y")
    if auto_detect:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_time)
        threshold = auto_detect_threshold(cap, fps, tab_area, 10) # 10 is the hard coded number of seconds we scan to find the threshold
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_time) # reset so that this function leaves cap unchanged
    else:
        threshold = float(input("Enter manual similarity threshold (e.g., 15): ") or 15)
    print(f"Using similarity threshold: {threshold}%")
    return threshold

def reset_cap_position(cap, fps, start_time):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps * start_time))
    return cap

def capture_tab_frames(cap, fps, tab_area, similarity_threshold, end_time):
    os.makedirs("tab_screenshots", exist_ok=True)
    image_paths = []
    frame_count = 0
    prev_cropped_gray = None
    change_threshold = 5  # pixel intensity threshold for per-pixel changes
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    end_frame = total_frames - int(end_time * fps)
    print("began processing video")
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