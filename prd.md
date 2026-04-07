📄 Product Requirements Document (PRD)
🧾 Project Name: Vid2PDF – Smart Video to Document Converter
1. 📌 Overview

Vid2PDF is a web-based application that converts a video of handwritten or printed notes into a high-quality, readable PDF document.

Instead of manually capturing images page-by-page, users can upload a video containing multiple pages. The system intelligently processes the video to extract only the best-quality frames, removes duplicates, enhances readability, and compiles them into a structured PDF.

2. 🎯 Objective
Reduce manual effort in digitizing notes
Automatically extract readable pages from videos
Generate clean, organized PDFs
Provide a fast and user-friendly experience
3. 👥 Target Users
Students (school, college, coaching)
Teachers sharing notes
Content creators (study material)
Professionals digitizing documents
4. 💡 Problem Statement

Currently:

Students receive notes in video format (WhatsApp, Telegram, etc.)
Extracting pages manually is time-consuming and inefficient
Screenshots often result in blurry or duplicate images

👉 There is no simple tool that:

Automatically selects clear frames
Removes duplicates
Converts to PDF in one click
5. 🚀 Solution

Vid2PDF solves this by:

Processing video frame-by-frame
Detecting and selecting high-quality, readable frames
Filtering out blurred and duplicate images
Enhancing images for clarity
Generating a clean PDF document
6. 🔑 Key Features
🔹 Core Features
Video Upload (MP4, AVI, MOV)
Frame Extraction
Blur Detection & Removal
Duplicate Frame Removal
Image Enhancement (contrast, thresholding)
PDF Generation
Download Option
🔹 Advanced Features (Optional / Future Scope)
OCR (convert images → searchable text)
Auto page detection & cropping
Orientation correction (rotate pages automatically)
Real-time preview of selected pages
Cloud storage & history
Mobile-friendly version
7. ⚙️ Functional Requirements
7.1 Video Upload
User can upload a video file
System validates file format and size
7.2 Frame Extraction
Extract frames at fixed intervals (e.g., 1 frame/sec)
Store frames temporarily
7.3 Quality Filtering
Detect blurry frames using variance method
Remove low-quality images
7.4 Duplicate Removal
Compare frames using similarity metrics
Remove repeated pages
7.5 Image Processing
Convert to grayscale
Apply thresholding for clarity
Crop document area (if detected)
7.6 PDF Generation
Convert selected images into ordered PDF
Allow user to download final file
8. 🖥️ Non-Functional Requirements
Performance
Process a 2–5 minute video within 30–60 seconds
Scalability
Should support multiple users (future cloud deployment)
Usability
Simple UI (upload → process → download)
Compatibility
Works on desktop and mobile browsers
Security
Uploaded files should not be stored permanently
9. 🧱 System Architecture
Frontend
User Interface (Upload + Preview + Download)
Tech: HTML, CSS, JavaScript / React
Backend
Video processing engine
Frame filtering logic
PDF generator

Tech:

Python (OpenCV, PIL, NumPy)
Flask / FastAPI
Storage
Temporary storage for:
Uploaded videos
Extracted frames
Output PDF
10. 🔄 User Flow
User opens website
Uploads video
Clicks “Process”
System:
Extracts frames
Filters quality
Removes duplicates
Enhances images
PDF is generated
User downloads PDF
11. 📊 Success Metrics
PDF generation success rate
Processing time
User satisfaction
Accuracy of frame selection (clear vs blurry)
12. ⚠️ Constraints & Risks
Poor video quality → bad output
Heavy processing → slower performance
Lighting and camera movement issues
Large file size handling
13. 🛣️ Future Enhancements
AI-based page detection (YOLO, CNN)
Text recognition (OCR-based searchable PDF)
Mobile app version
Multi-language support
Cloud sync & sharing
14. 📅 Milestones (Suggested)
Phase	Task	Duration
Phase 1	Basic frame extraction + PDF	3–5 days
Phase 2	Blur detection + filtering	3 days
Phase 3	Duplicate removal	2–3 days
Phase 4	UI Development	4–6 days
Phase 5	Testing & Optimization	3 days
15. 🏁 Conclusion

Vid2PDF is a practical, real-world solution that simplifies document digitization from videos. It combines computer vision and automation to deliver a seamless user experience and has strong potential for further expansion using AI.