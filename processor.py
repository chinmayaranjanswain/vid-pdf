"""
Vid2PDF – Core Video Processing Engine
Advanced pipeline: frame extraction, blur detection, duplicate removal,
document enhancement (deskew, perspective correction, noise removal,
CLAHE, adaptive threshold, sharpening), and 300 DPI PDF generation.
"""

import os
import math
import cv2
import numpy as np
from PIL import Image
from fpdf import FPDF
from skimage.metrics import structural_similarity as ssim


# ═══════════════════════════════════════════════════════════════════════════════
# Frame Extraction
# ═══════════════════════════════════════════════════════════════════════════════

def extract_frames(video_path, interval=1.0):
    """
    Extract frames from a video at a given interval (in seconds).
    Returns a list of (frame_index, frame_image) tuples.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0  # fallback

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = int(fps * interval)
    if frame_interval < 1:
        frame_interval = 1

    frames = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            frames.append((frame_idx, frame))

        frame_idx += 1

    cap.release()
    return frames, total_frames, fps


# ═══════════════════════════════════════════════════════════════════════════════
# Quality Filtering
# ═══════════════════════════════════════════════════════════════════════════════

def detect_blur(image, threshold=100.0):
    """
    Detect if an image is blurry using Laplacian variance.
    Returns (is_sharp, score). Higher score = sharper.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var >= threshold, laplacian_var


def filter_blurry_frames(frames, threshold=100.0):
    """
    Filter out blurry frames.
    Returns (sharp_frames, removed_count).
    """
    sharp_frames = []
    removed = 0

    for idx, frame in frames:
        is_sharp, score = detect_blur(frame, threshold)
        if is_sharp:
            sharp_frames.append((idx, frame, score))
        else:
            removed += 1

    return sharp_frames, removed


def remove_duplicates(frames, similarity_threshold=0.92):
    """
    Remove duplicate/near-duplicate frames using SSIM.
    Returns (unique_frames, removed_count).
    """
    if not frames:
        return [], 0

    unique_frames = [frames[0]]
    removed = 0

    for i in range(1, len(frames)):
        idx, frame, score = frames[i]
        prev_idx, prev_frame, prev_score = unique_frames[-1]

        # Resize for faster comparison
        h, w = 256, 256
        resized_current = cv2.resize(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (w, h)
        )
        resized_prev = cv2.resize(
            cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY), (w, h)
        )

        similarity = ssim(resized_prev, resized_current)

        if similarity < similarity_threshold:
            unique_frames.append((idx, frame, score))
        else:
            removed += 1

    return unique_frames, removed


# ═══════════════════════════════════════════════════════════════════════════════
# Step 7: Perspective Correction – Flatten page captured at an angle
# ═══════════════════════════════════════════════════════════════════════════════

def order_points(pts):
    """Order 4 points as: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]      # top-left has smallest sum
    rect[2] = pts[np.argmax(s)]      # bottom-right has largest sum
    d = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(d)]      # top-right has smallest difference
    rect[3] = pts[np.argmax(d)]      # bottom-left has largest difference
    return rect


def detect_document_contour(image):
    """
    Detect the largest quadrilateral contour (document boundary).
    Returns 4 corner points or None if not found.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection
    edges = cv2.Canny(blurred, 50, 150)

    # Dilate to close gaps in edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    # Sort by area, largest first
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    h, w = image.shape[:2]
    image_area = h * w

    for contour in contours[:5]:
        # Approximate the contour
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        # Check if it's a quadrilateral and covers significant area
        contour_area = cv2.contourArea(approx)
        if len(approx) == 4 and contour_area > image_area * 0.25:
            return approx.reshape(4, 2).astype("float32")

    return None


def perspective_correction(image):
    """
    Detect document boundaries and apply perspective transform to flatten.
    Returns corrected image or original if no document detected.
    """
    pts = detect_document_contour(image)

    if pts is None:
        return image  # No document boundary found, return original

    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    # Compute width of the new image
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))

    # Compute height of the new image
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))

    if max_width < 100 or max_height < 100:
        return image  # Too small, skip

    # Destination points
    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    # Apply perspective transform
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (max_width, max_height),
                                  flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)

    return warped


# ═══════════════════════════════════════════════════════════════════════════════
# Step 6: Auto Deskew – Correct page orientation/rotation
# ═══════════════════════════════════════════════════════════════════════════════

def compute_skew_angle(image):
    """
    Compute the skew angle of text in the image using Hough Line Transform.
    Returns angle in degrees.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Invert and threshold to get text as white on black
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Detect lines using probabilistic Hough transform
    lines = cv2.HoughLinesP(
        binary, rho=1, theta=np.pi / 180,
        threshold=100, minLineLength=80, maxLineGap=10
    )

    if lines is None or len(lines) == 0:
        return 0.0

    # Compute angles of all detected lines
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 == 0:
            continue
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        # Only consider near-horizontal lines (text lines)
        if abs(angle) < 30:
            angles.append(angle)

    if not angles:
        return 0.0

    # Use median angle to be robust against outliers
    median_angle = np.median(angles)
    return median_angle


def auto_deskew(image, max_angle=15.0):
    """
    Automatically correct page rotation/skew.
    Only corrects if angle is within ±max_angle degrees.
    """
    angle = compute_skew_angle(image)

    # Only correct if the angle is meaningful but not extreme
    if abs(angle) < 0.3 or abs(angle) > max_angle:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    # Rotation matrix
    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Compute new bounding dimensions after rotation
    cos = abs(M[0, 0])
    sin = abs(M[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)

    # Adjust the rotation matrix for the new center
    M[0, 2] += (new_w - w) / 2
    M[1, 2] += (new_h - h) / 2

    rotated = cv2.warpAffine(image, M, (new_w, new_h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)

    return rotated


# ═══════════════════════════════════════════════════════════════════════════════
# Step 8: Border Cropping & Shadow Removal
# ═══════════════════════════════════════════════════════════════════════════════

def crop_borders(image, margin_percent=1.0):
    """
    Detect content region and crop unnecessary borders/shadows.
    Preserves a small margin around the content.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to ignore noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Threshold: detect content (dark regions on white)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Morphological operations to connect text regions
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Find bounding box of all content
    coords = cv2.findNonZero(morph)
    if coords is None:
        return image

    x, y, w, h = cv2.boundingRect(coords)

    # Add margin
    img_h, img_w = image.shape[:2]
    margin_x = int(img_w * margin_percent / 100)
    margin_y = int(img_h * margin_percent / 100)

    x = max(0, x - margin_x)
    y = max(0, y - margin_y)
    w = min(img_w - x, w + 2 * margin_x)
    h = min(img_h - y, h + 2 * margin_y)

    # Only crop if the result is meaningful (at least 50% of original)
    if w < img_w * 0.5 or h < img_h * 0.5:
        return image

    return image[y:y+h, x:x+w]


# ═══════════════════════════════════════════════════════════════════════════════
# Step 9: Brightness Normalization
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_brightness(gray_image):
    """
    Normalize brightness for uniform lighting across the page.
    Uses morphological background estimation and division-based correction.
    """
    # Estimate background illumination using large morphological closing
    kernel_size = max(gray_image.shape[0], gray_image.shape[1]) // 10
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel_size = max(kernel_size, 51)

    # Use a large structuring element to estimate background
    bg = cv2.morphologyEx(gray_image, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                                    (kernel_size, kernel_size)))

    # Divide the image by the background to normalize illumination
    # This removes shadows and uneven lighting
    normalized = cv2.divide(gray_image, bg, scale=255)

    return normalized


# ═══════════════════════════════════════════════════════════════════════════════
# Full Image Enhancement Pipeline – Color-Preserving Clarity
# ═══════════════════════════════════════════════════════════════════════════════

def enhance_image(image, mode="enhanced"):
    """
    Clean, color-preserving enhancement for document clarity.

    - Keeps original colors intact
    - Gentle denoising without artifacts
    - CLAHE contrast on luminance only
    - Shadow/uneven lighting removal
    - Subtle sharpening for text clarity
    - No grayscale, no thresholding, no heavy filters
    """
    # Work in LAB color space: enhance Luminance, preserve A/B (color)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # ── Step 1: Gentle denoising on luminance only ──
    # Bilateral filter preserves edges (text) while smoothing noise
    l = cv2.bilateralFilter(l, 5, 30, 30)

    # ── Step 2: Brightness normalization (remove shadows) ──
    # Estimate background illumination and divide to even out lighting
    kernel_size = max(l.shape[0], l.shape[1]) // 10
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel_size = max(kernel_size, 51)

    bg = cv2.morphologyEx(l, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                                    (kernel_size, kernel_size)))
    l = cv2.divide(l, bg, scale=255)

    # ── Step 3: CLAHE contrast enhancement (luminance only) ──
    # Boosts text visibility without touching colors
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    l = clahe.apply(l)

    # ── Step 4: Subtle sharpening for text clarity ──
    # Unsharp mask with gentle parameters
    blurred = cv2.GaussianBlur(l, (0, 0), 1.2)
    l = cv2.addWeighted(l, 1.3, blurred, -0.3, 0)

    # Recombine LAB and convert back to BGR
    enhanced = cv2.merge([l, a, b])
    result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    return result



# ═══════════════════════════════════════════════════════════════════════════════
# Step 10: High-Resolution 300 DPI PDF Generation
# ═══════════════════════════════════════════════════════════════════════════════

def generate_pdf(image_paths, output_path, dpi=300):
    """
    Generate a high-resolution PDF from image files.
    Each image is placed on its own page at the specified DPI.
    Output is optimized for print at 300 DPI.
    """
    if not image_paths:
        raise ValueError("No images provided for PDF generation.")

    # Method: Use Pillow to create a proper DPI-aware PDF
    # This produces cleaner results than fpdf for image-only documents
    pil_images = []

    for img_path in image_paths:
        img = Image.open(img_path)

        # Convert to RGB if necessary (PDF doesn't support all modes)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Set DPI metadata
        img.info["dpi"] = (dpi, dpi)
        pil_images.append(img)

    if not pil_images:
        raise ValueError("No valid images for PDF generation.")

    # Save as multi-page PDF using Pillow
    first_image = pil_images[0]
    remaining = pil_images[1:] if len(pil_images) > 1 else []

    first_image.save(
        output_path,
        "PDF",
        resolution=dpi,
        save_all=True,
        append_images=remaining,
        quality=95,
    )

    return output_path


# ═══════════════════════════════════════════════════════════════════════════════
# Full Processing Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def process_video(video_path, output_dir, progress_callback=None):
    """
    Full processing pipeline:
    1. Extract frames from video
    2. Filter blurry frames
    3. Remove duplicate frames
    4. Enhance each frame:
       a. Perspective correction (flatten angled pages)
       b. Auto deskew (correct rotation)
       c. Crop borders & shadows
       d. Grayscale conversion
       e. Noise reduction (median filter)
       f. Brightness normalization
       g. CLAHE contrast enhancement
       h. Adaptive thresholding
       i. Gentle sharpening
    5. Generate 300 DPI print-ready PDF

    progress_callback(stage, percent, message) is called to report progress.
    Returns stats dictionary.
    """

    def report(stage, percent, message):
        if progress_callback:
            progress_callback(stage, percent, message)

    # Create output directories
    frames_dir = os.path.join(output_dir, "frames")
    enhanced_dir = os.path.join(output_dir, "enhanced")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(enhanced_dir, exist_ok=True)

    # ── Stage 1: Extract frames ──
    report("extracting", 0, "Starting frame extraction...")
    frames, total_frames, fps = extract_frames(video_path, interval=1.0)
    report("extracting", 100,
           f"Extracted {len(frames)} frames from video "
           f"({total_frames} total at {fps:.1f} FPS)")

    if not frames:
        raise ValueError("No frames could be extracted from the video.")

    # ── Stage 2: Filter blurry frames ──
    report("filtering", 0, "Detecting and removing blurry frames...")
    sharp_frames, blur_removed = filter_blurry_frames(frames, threshold=80.0)
    report("filtering", 100,
           f"Removed {blur_removed} blurry frames, "
           f"{len(sharp_frames)} sharp frames remaining")

    if not sharp_frames:
        raise ValueError(
            "All frames were detected as blurry. Try a clearer video."
        )

    # ── Stage 3: Remove duplicates ──
    report("deduplicating", 0, "Removing duplicate frames...")
    unique_frames, dup_removed = remove_duplicates(
        sharp_frames, similarity_threshold=0.92
    )
    report("deduplicating", 100,
           f"Removed {dup_removed} duplicate frames, "
           f"{len(unique_frames)} unique pages remaining")

    if not unique_frames:
        raise ValueError("No unique frames found after filtering.")

    # ── Stage 4: Enhance images (full pipeline) ──
    report("enhancing", 0, "Starting document enhancement...")
    enhanced_paths = []
    total = len(unique_frames)

    for i, (idx, frame, score) in enumerate(unique_frames):
        # Save original frame for preview
        frame_path = os.path.join(frames_dir, f"frame_{i:04d}.jpg")
        cv2.imwrite(frame_path, frame)

        # Sub-step a: Perspective correction
        corrected = perspective_correction(frame)

        # Sub-step b: Auto deskew
        deskewed = auto_deskew(corrected)

        # Sub-step c: Crop borders & shadows
        cropped = crop_borders(deskewed)

        # Sub-steps d–i: Full enhancement pipeline
        enhanced = enhance_image(cropped, mode="enhanced")

        # Save enhanced image as high-quality PNG for PDF generation
        enhanced_path = os.path.join(enhanced_dir, f"enhanced_{i:04d}.png")
        cv2.imwrite(enhanced_path, enhanced,
                    [cv2.IMWRITE_PNG_COMPRESSION, 3])
        enhanced_paths.append(enhanced_path)

        percent = int((i + 1) / total * 100)
        step_desc = f"Enhanced page {i + 1}/{total}"
        if i == 0:
            step_desc += " (perspective → deskew → crop → enhance)"
        report("enhancing", percent, step_desc)

    # ── Stage 5: Generate 300 DPI PDF ──
    report("generating", 0, "Generating 300 DPI print-ready PDF...")
    pdf_path = os.path.join(output_dir, "output.pdf")
    generate_pdf(enhanced_paths, pdf_path, dpi=300)
    report("generating", 100,
           f"PDF generated with {len(enhanced_paths)} pages at 300 DPI!")

    # Return stats
    stats = {
        "total_video_frames": total_frames,
        "extracted_frames": len(frames),
        "blur_removed": blur_removed,
        "duplicates_removed": dup_removed,
        "final_pages": len(unique_frames),
        "pdf_path": pdf_path,
        "frame_paths": [
            os.path.join(frames_dir, f"frame_{i:04d}.jpg")
            for i in range(len(unique_frames))
        ],
    }

    return stats
