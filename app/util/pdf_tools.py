from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from PIL import Image
import os

def save_as_pdf(image_paths, output_filename):
    if not image_paths:
        print("No images to save.")
        return
    images = [Image.open(p).convert("RGB") for p in image_paths]
    images[0].save(output_filename, save_all=True, append_images=images[1:])
    print(f"Saved PDF: {output_filename}")



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