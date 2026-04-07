/**
 * Vid2PDF – Frontend Application Logic
 * Handles file upload, SSE progress, frame preview, and PDF download.
 */

(function () {
    "use strict";

    // ─── DOM References ──────────────────────────────────────────────────────
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dropzone = $("#dropzone");
    const fileInput = $("#file-input");
    const fileInfo = $("#file-info");
    const fileName = $("#file-name");
    const fileSize = $("#file-size");
    const btnRemoveFile = $("#btn-remove-file");
    const uploadProgress = $("#upload-progress");
    const uploadProgressFill = $("#upload-progress-fill");
    const uploadProgressText = $("#upload-progress-text");
    const btnProcess = $("#btn-process");
    const btnNewSession = $("#btn-new-session");

    const sectionUpload = $("#section-upload");
    const sectionProcessing = $("#section-processing");
    const sectionResults = $("#section-results");
    const sectionError = $("#section-error");

    const overallProgressFill = $("#overall-progress-fill");
    const overallProgressLabel = $("#overall-progress-label");

    const frameGrid = $("#frame-grid");
    const btnDownload = $("#btn-download");
    const btnStartOver = $("#btn-start-over");
    const btnRetry = $("#btn-retry");
    const errorMessage = $("#error-message");

    // Stats
    const statExtracted = $("#stat-extracted");
    const statBlurRemoved = $("#stat-blur-removed");
    const statDupsRemoved = $("#stat-dups-removed");
    const statFinal = $("#stat-final");

    // ─── State ───────────────────────────────────────────────────────────────
    let selectedFile = null;
    let currentJobId = null;
    let selectedFrames = new Set();
    let totalFrames = 0;

    // ─── Utilities ───────────────────────────────────────────────────────────
    function formatFileSize(bytes) {
        if (bytes === 0) return "0 Bytes";
        const k = 1024;
        const sizes = ["Bytes", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    }

    function showSection(section) {
        [sectionUpload, sectionProcessing, sectionResults, sectionError].forEach(
            (s) => (s.style.display = "none")
        );
        section.style.display = "block";
        // Re-trigger animation
        section.style.animation = "none";
        section.offsetHeight; // force reflow
        section.style.animation = "";
    }

    function showToast(message, type = "success") {
        // Remove any existing toast
        const existing = document.querySelector(".toast");
        if (existing) existing.remove();

        const toast = document.createElement("div");
        toast.className = `toast toast--${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        requestAnimationFrame(() => {
            toast.classList.add("toast--visible");
        });

        setTimeout(() => {
            toast.classList.remove("toast--visible");
            setTimeout(() => toast.remove(), 400);
        }, 3000);
    }

    function resetStages() {
        const stages = ["extracting", "filtering", "deduplicating", "enhancing", "generating"];
        stages.forEach((stage) => {
            const el = $(`#stage-${stage}`);
            el.classList.remove("stage--active", "stage--done");
            $(`#stage-${stage}-status`).textContent = "Waiting...";
        });
        overallProgressFill.style.width = "0%";
        overallProgressLabel.textContent = "0%";
    }

    // ─── File Selection ──────────────────────────────────────────────────────
    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            fileInput.click();
        }
    });

    // Drag & drop
    ["dragenter", "dragover"].forEach((event) => {
        dropzone.addEventListener(event, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add("dropzone--active");
        });
    });

    ["dragleave", "drop"].forEach((event) => {
        dropzone.addEventListener(event, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove("dropzone--active");
        });
    });

    dropzone.addEventListener("drop", (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        const allowedExtensions = [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"];
        const ext = "." + file.name.split(".").pop().toLowerCase();

        if (!allowedExtensions.includes(ext)) {
            showToast(`Unsupported format "${ext}". Use MP4, AVI, MOV, MKV, WebM, or FLV.`, "error");
            return;
        }

        if (file.size > 200 * 1024 * 1024) {
            showToast("File is too large. Maximum size is 200MB.", "error");
            return;
        }

        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);

        dropzone.style.display = "none";
        fileInfo.style.display = "flex";
        btnProcess.style.display = "inline-flex";
    }

    btnRemoveFile.addEventListener("click", () => {
        selectedFile = null;
        fileInput.value = "";
        dropzone.style.display = "block";
        fileInfo.style.display = "none";
        btnProcess.style.display = "none";
        uploadProgress.style.display = "none";
    });

    // ─── Upload & Process ────────────────────────────────────────────────────
    btnProcess.addEventListener("click", () => {
        if (!selectedFile) return;
        uploadAndProcess();
    });

    async function uploadAndProcess() {
        btnProcess.disabled = true;
        btnProcess.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin-icon"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
            Uploading...
        `;
        uploadProgress.style.display = "block";

        try {
            // Step 1: Upload
            const formData = new FormData();
            formData.append("video", selectedFile);

            const xhr = new XMLHttpRequest();
            const uploadPromise = new Promise((resolve, reject) => {
                xhr.upload.addEventListener("progress", (e) => {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        uploadProgressFill.style.width = percent + "%";
                        uploadProgressText.textContent = `Uploading... ${percent}%`;
                    }
                });

                xhr.addEventListener("load", () => {
                    if (xhr.status === 200) {
                        resolve(JSON.parse(xhr.responseText));
                    } else {
                        try {
                            const err = JSON.parse(xhr.responseText);
                            reject(new Error(err.error || "Upload failed"));
                        } catch {
                            reject(new Error("Upload failed with status " + xhr.status));
                        }
                    }
                });

                xhr.addEventListener("error", () => reject(new Error("Network error during upload")));
                xhr.addEventListener("abort", () => reject(new Error("Upload aborted")));

                xhr.open("POST", "/api/upload");
                xhr.send(formData);
            });

            const uploadResult = await uploadPromise;
            currentJobId = uploadResult.job_id;
            uploadProgressText.textContent = "Upload complete!";

            showToast("Video uploaded successfully!", "success");

            // Step 2: Process
            await startProcessing(currentJobId);
        } catch (error) {
            showError(error.message);
        }
    }

    async function startProcessing(jobId) {
        // Switch to processing view
        showSection(sectionProcessing);
        resetStages();
        btnNewSession.style.display = "inline-flex";

        const stageOrder = ["extracting", "filtering", "deduplicating", "enhancing", "generating"];
        const stageWeights = { extracting: 30, filtering: 15, deduplicating: 15, enhancing: 25, generating: 15 };
        let completedWeight = 0;
        let currentStageKey = null;

        try {
            const response = await fetch(`/api/process/${jobId}`);

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || "Processing failed");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop(); // Keep incomplete line in buffer

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;

                    const jsonStr = line.slice(6).trim();
                    if (!jsonStr) continue;

                    try {
                        const event = JSON.parse(jsonStr);

                        if (event.stage === "error") {
                            throw new Error(event.message);
                        }

                        if (event.stage === "complete") {
                            // All done!
                            // Mark any remaining stages as done
                            stageOrder.forEach((s) => {
                                const el = $(`#stage-${s}`);
                                el.classList.remove("stage--active");
                                el.classList.add("stage--done");
                            });
                            overallProgressFill.style.width = "100%";
                            overallProgressLabel.textContent = "100%";

                            showToast("Processing complete! 🎉", "success");

                            // Small delay for satisfaction
                            await new Promise((r) => setTimeout(r, 800));

                            // Show results
                            showResults(jobId, event.stats);
                            return;
                        }

                        // Update stage UI
                        const stage = event.stage;
                        const stageEl = $(`#stage-${stage}`);
                        const statusEl = $(`#stage-${stage}-status`);

                        if (stage !== currentStageKey) {
                            // Mark previous stage as done
                            if (currentStageKey) {
                                const prevEl = $(`#stage-${currentStageKey}`);
                                prevEl.classList.remove("stage--active");
                                prevEl.classList.add("stage--done");
                                completedWeight += stageWeights[currentStageKey] || 0;
                            }
                            currentStageKey = stage;
                            stageEl.classList.add("stage--active");
                        }

                        statusEl.textContent = event.message;

                        // Update overall progress
                        const stageWeight = stageWeights[stage] || 20;
                        const stageProgress = event.percent / 100;
                        const overallPercent = Math.min(
                            Math.round(completedWeight + stageWeight * stageProgress),
                            99
                        );
                        overallProgressFill.style.width = overallPercent + "%";
                        overallProgressLabel.textContent = overallPercent + "%";
                    } catch (parseErr) {
                        if (parseErr.message && !parseErr.message.includes("JSON")) {
                            throw parseErr;
                        }
                    }
                }
            }

            // If we get here without a "complete" event, check job status
            const statusResponse = await fetch(`/api/status/${jobId}`);
            const statusData = await statusResponse.json();

            if (statusData.status === "completed" && statusData.stats) {
                stageOrder.forEach((s) => {
                    const el = $(`#stage-${s}`);
                    el.classList.remove("stage--active");
                    el.classList.add("stage--done");
                });
                overallProgressFill.style.width = "100%";
                overallProgressLabel.textContent = "100%";
                await new Promise((r) => setTimeout(r, 500));
                showResults(jobId, statusData.stats);
            } else if (statusData.status === "error") {
                throw new Error(statusData.error || "Processing failed");
            }
        } catch (error) {
            showError(error.message);
        }
    }

    // ─── Results ─────────────────────────────────────────────────────────────
    function showResults(jobId, stats) {
        showSection(sectionResults);

        // Populate stats
        statExtracted.textContent = stats.extracted_frames;
        statBlurRemoved.textContent = stats.blur_removed;
        statDupsRemoved.textContent = stats.duplicates_removed;
        statFinal.textContent = stats.final_pages;

        totalFrames = stats.final_pages;
        selectedFrames = new Set();
        for (let i = 0; i < totalFrames; i++) {
            selectedFrames.add(i);
        }

        // Render frame grid
        renderFrameGrid(jobId, totalFrames);
    }

    function renderFrameGrid(jobId, count) {
        frameGrid.innerHTML = "";

        for (let i = 0; i < count; i++) {
            const card = document.createElement("div");
            card.className = "frame-card frame-card--selected";
            card.dataset.index = i;
            card.style.animationDelay = `${i * 0.06}s`;

            card.innerHTML = `
                <img class="frame-card__image" 
                     src="/api/preview/${jobId}/${i}" 
                     alt="Page ${i + 1}" 
                     loading="lazy">
                <div class="frame-card__overlay">
                    <span class="frame-card__label">Page ${i + 1}</span>
                </div>
                <button class="frame-card__preview-btn" title="Preview Page ${i + 1}" data-preview="${i}">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"/>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                        <line x1="11" y1="8" x2="11" y2="14"/>
                        <line x1="8" y1="11" x2="14" y2="11"/>
                    </svg>
                </button>
                <div class="frame-card__check">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20,6 9,17 4,12"/></svg>
                </div>
            `;

            // Preview button click → open lightbox
            const previewBtn = card.querySelector(".frame-card__preview-btn");
            previewBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                openLightbox(i);
            });

            // Card click → toggle selection
            card.addEventListener("click", (e) => {
                if (e.target.closest(".frame-card__preview-btn")) return;
                toggleFrame(card, i);
            });

            frameGrid.appendChild(card);
        }
    }

    function toggleFrame(card, index) {
        if (selectedFrames.has(index)) {
            selectedFrames.delete(index);
            card.classList.remove("frame-card--selected");
            card.classList.add("frame-card--deselected");
        } else {
            selectedFrames.add(index);
            card.classList.add("frame-card--selected");
            card.classList.remove("frame-card--deselected");
        }

        // Update download button text
        const count = selectedFrames.size;
        btnDownload.querySelector("svg").nextSibling.textContent =
            ` Download PDF (${count} page${count !== 1 ? "s" : ""})`;

        // Disable download if no frames selected
        btnDownload.disabled = count === 0;

        // Update lightbox if open
        if (lightboxOpen && lightboxCurrentIndex === index) {
            updateLightboxSelectionUI(index);
        }
        updateLightboxThumbs();
    }

    // ─── Lightbox / Preview ─────────────────────────────────────────────────
    const lightbox = $("#lightbox");
    const lightboxBackdrop = $("#lightbox-backdrop");
    const lightboxImage = $("#lightbox-image");
    const lightboxPageLabel = $("#lightbox-page-label");
    const lightboxQualityBadge = $("#lightbox-quality-badge");
    const lightboxToggleSelect = $("#lightbox-toggle-select");
    const lightboxToggleText = $("#lightbox-toggle-text");
    const lightboxZoomIn = $("#lightbox-zoom-in");
    const lightboxZoomOut = $("#lightbox-zoom-out");
    const lightboxZoomReset = $("#lightbox-zoom-reset");
    const lightboxClose = $("#lightbox-close");
    const lightboxPrev = $("#lightbox-prev");
    const lightboxNext = $("#lightbox-next");
    const lightboxViewport = $("#lightbox-viewport");
    const lightboxStrip = $("#lightbox-strip");

    let lightboxOpen = false;
    let lightboxCurrentIndex = 0;
    let lightboxZoom = 1;
    let lightboxPanX = 0;
    let lightboxPanY = 0;
    let isDragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let dragStartPanX = 0;
    let dragStartPanY = 0;
    let zoomIndicatorTimeout = null;

    // Create zoom level indicator
    const zoomLevelEl = document.createElement("div");
    zoomLevelEl.className = "lightbox__zoom-level";
    zoomLevelEl.textContent = "100%";
    lightboxViewport.appendChild(zoomLevelEl);

    function openLightbox(index) {
        lightboxCurrentIndex = index;
        lightboxOpen = true;
        lightboxZoom = 1;
        lightboxPanX = 0;
        lightboxPanY = 0;

        lightbox.classList.add("lightbox--open");
        lightbox.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";

        updateLightboxImage(index);
        buildLightboxStrip();
        updateLightboxSelectionUI(index);
    }

    function closeLightbox() {
        lightboxOpen = false;
        lightbox.classList.remove("lightbox--open");
        lightbox.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
    }

    function updateLightboxImage(index) {
        lightboxCurrentIndex = index;

        // Load image
        lightboxImage.classList.remove("no-transition");
        lightboxImage.src = `/api/preview/${currentJobId}/${index}`;
        lightboxPageLabel.textContent = `Page ${index + 1} / ${totalFrames}`;

        // Reset zoom and pan
        lightboxZoom = 1;
        lightboxPanX = 0;
        lightboxPanY = 0;
        applyTransform();

        // Update selection state
        updateLightboxSelectionUI(index);

        // Update active thumbnail
        updateLightboxThumbs();

        // Scroll active thumb into view
        const activeThumb = lightboxStrip.querySelector(`.lightbox__thumb--active`);
        if (activeThumb) {
            activeThumb.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
        }
    }

    function updateLightboxSelectionUI(index) {
        const isSelected = selectedFrames.has(index);

        // Badge
        lightboxQualityBadge.className = "lightbox__quality-badge";
        if (isSelected) {
            lightboxQualityBadge.textContent = "✓ Selected";
            lightboxQualityBadge.classList.add("lightbox__quality-badge--selected");
        } else {
            lightboxQualityBadge.textContent = "✗ Deselected";
            lightboxQualityBadge.classList.add("lightbox__quality-badge--deselected");
        }

        // Toggle button
        lightboxToggleSelect.classList.remove("lightbox__btn--is-selected", "lightbox__btn--is-deselected");
        if (isSelected) {
            lightboxToggleSelect.classList.add("lightbox__btn--is-selected");
            lightboxToggleText.textContent = "Deselect";
        } else {
            lightboxToggleSelect.classList.add("lightbox__btn--is-deselected");
            lightboxToggleText.textContent = "Select";
        }
    }

    function buildLightboxStrip() {
        lightboxStrip.innerHTML = "";
        for (let i = 0; i < totalFrames; i++) {
            const thumb = document.createElement("div");
            thumb.className = "lightbox__thumb";
            thumb.dataset.index = i;
            if (i === lightboxCurrentIndex) thumb.classList.add("lightbox__thumb--active");
            if (!selectedFrames.has(i)) thumb.classList.add("lightbox__thumb--deselected");

            thumb.innerHTML = `<img src="/api/preview/${currentJobId}/${i}" alt="Page ${i + 1}" loading="lazy">`;
            thumb.addEventListener("click", () => updateLightboxImage(i));
            lightboxStrip.appendChild(thumb);
        }
    }

    function updateLightboxThumbs() {
        const thumbs = lightboxStrip.querySelectorAll(".lightbox__thumb");
        thumbs.forEach((thumb, i) => {
            thumb.classList.toggle("lightbox__thumb--active", i === lightboxCurrentIndex);
            thumb.classList.toggle("lightbox__thumb--deselected", !selectedFrames.has(i));
        });
    }

    // ── Zoom & Pan ──
    function applyTransform() {
        lightboxImage.style.transform = `translate(${lightboxPanX}px, ${lightboxPanY}px) scale(${lightboxZoom})`;
    }

    function setZoom(newZoom, showIndicator = true) {
        lightboxZoom = Math.max(0.25, Math.min(newZoom, 8));

        // If zooming out to fit, reset pan
        if (lightboxZoom <= 1) {
            lightboxPanX = 0;
            lightboxPanY = 0;
        }

        applyTransform();

        if (showIndicator) {
            showZoomLevel();
        }
    }

    function showZoomLevel() {
        zoomLevelEl.textContent = `${Math.round(lightboxZoom * 100)}%`;
        zoomLevelEl.classList.add("visible");
        clearTimeout(zoomIndicatorTimeout);
        zoomIndicatorTimeout = setTimeout(() => {
            zoomLevelEl.classList.remove("visible");
        }, 1200);
    }

    // Zoom buttons
    lightboxZoomIn.addEventListener("click", () => setZoom(lightboxZoom * 1.3));
    lightboxZoomOut.addEventListener("click", () => setZoom(lightboxZoom / 1.3));
    lightboxZoomReset.addEventListener("click", () => {
        lightboxPanX = 0;
        lightboxPanY = 0;
        setZoom(1);
    });

    // Scroll to zoom
    lightboxViewport.addEventListener("wheel", (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.85 : 1.18;
        setZoom(lightboxZoom * delta);
    }, { passive: false });

    // Pan (drag)
    lightboxViewport.addEventListener("mousedown", (e) => {
        if (lightboxZoom <= 1) return;
        isDragging = true;
        dragStartX = e.clientX;
        dragStartY = e.clientY;
        dragStartPanX = lightboxPanX;
        dragStartPanY = lightboxPanY;
        lightboxViewport.classList.add("is-dragging");
        lightboxImage.classList.add("no-transition");
    });

    window.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        lightboxPanX = dragStartPanX + (e.clientX - dragStartX);
        lightboxPanY = dragStartPanY + (e.clientY - dragStartY);
        applyTransform();
    });

    window.addEventListener("mouseup", () => {
        if (!isDragging) return;
        isDragging = false;
        lightboxViewport.classList.remove("is-dragging");
        lightboxImage.classList.remove("no-transition");
    });

    // Touch support for pan
    let touchStartX = 0, touchStartY = 0, touchStartPanX2 = 0, touchStartPanY2 = 0;

    lightboxViewport.addEventListener("touchstart", (e) => {
        if (lightboxZoom <= 1 || e.touches.length !== 1) return;
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        touchStartPanX2 = lightboxPanX;
        touchStartPanY2 = lightboxPanY;
        lightboxImage.classList.add("no-transition");
    }, { passive: true });

    lightboxViewport.addEventListener("touchmove", (e) => {
        if (lightboxZoom <= 1 || e.touches.length !== 1) return;
        e.preventDefault();
        lightboxPanX = touchStartPanX2 + (e.touches[0].clientX - touchStartX);
        lightboxPanY = touchStartPanY2 + (e.touches[0].clientY - touchStartY);
        applyTransform();
    }, { passive: false });

    // Double-click to toggle zoom
    lightboxViewport.addEventListener("dblclick", () => {
        if (lightboxZoom > 1.1) {
            lightboxPanX = 0;
            lightboxPanY = 0;
            setZoom(1);
        } else {
            setZoom(2.5);
        }
    });

    // ── Navigation ──
    lightboxPrev.addEventListener("click", () => {
        if (lightboxCurrentIndex > 0) {
            updateLightboxImage(lightboxCurrentIndex - 1);
        }
    });

    lightboxNext.addEventListener("click", () => {
        if (lightboxCurrentIndex < totalFrames - 1) {
            updateLightboxImage(lightboxCurrentIndex + 1);
        }
    });

    // ── Toggle Selection from Lightbox ──
    lightboxToggleSelect.addEventListener("click", () => {
        const index = lightboxCurrentIndex;
        const card = frameGrid.querySelector(`.frame-card[data-index="${index}"]`);
        if (card) {
            toggleFrame(card, index);
        }
    });

    // ── Close ──
    lightboxClose.addEventListener("click", closeLightbox);
    lightboxBackdrop.addEventListener("click", closeLightbox);

    // ── Keyboard ──
    document.addEventListener("keydown", (e) => {
        if (!lightboxOpen) return;

        switch (e.key) {
            case "Escape":
                closeLightbox();
                break;
            case "ArrowLeft":
                e.preventDefault();
                if (lightboxCurrentIndex > 0) updateLightboxImage(lightboxCurrentIndex - 1);
                break;
            case "ArrowRight":
                e.preventDefault();
                if (lightboxCurrentIndex < totalFrames - 1) updateLightboxImage(lightboxCurrentIndex + 1);
                break;
            case "+":
            case "=":
                e.preventDefault();
                setZoom(lightboxZoom * 1.3);
                break;
            case "-":
                e.preventDefault();
                setZoom(lightboxZoom / 1.3);
                break;
            case "0":
                e.preventDefault();
                lightboxPanX = 0;
                lightboxPanY = 0;
                setZoom(1);
                break;
            case " ":
                e.preventDefault();
                lightboxToggleSelect.click();
                break;
        }
    });

    // ─── Download ────────────────────────────────────────────────────────────
    btnDownload.addEventListener("click", () => {
        if (!currentJobId) return;
        if (selectedFrames.size === 0) {
            showToast("No pages selected!", "error");
            return;
        }

        // Build the download URL with selected page indices
        const sortedPages = Array.from(selectedFrames).sort((a, b) => a - b);
        const pagesParam = sortedPages.join(",");
        const downloadUrl = `/api/download/${currentJobId}?pages=${pagesParam}`;

        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = "";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        showToast(`PDF download started with ${sortedPages.length} pages!`, "success");
    });

    // ─── Error Handling ──────────────────────────────────────────────────────
    function showError(message) {
        showSection(sectionError);
        errorMessage.textContent = message;
        btnNewSession.style.display = "inline-flex";
    }

    btnRetry.addEventListener("click", resetApp);

    // ─── Start Over ──────────────────────────────────────────────────────────
    btnStartOver.addEventListener("click", resetApp);
    btnNewSession.addEventListener("click", resetApp);

    function resetApp() {
        // Cleanup server-side files
        if (currentJobId) {
            fetch(`/api/cleanup/${currentJobId}`, { method: "DELETE" }).catch(() => {});
        }

        // Close lightbox if open
        if (lightboxOpen) closeLightbox();

        // Reset state
        selectedFile = null;
        currentJobId = null;
        selectedFrames = new Set();
        totalFrames = 0;

        // Reset UI
        fileInput.value = "";
        dropzone.style.display = "block";
        fileInfo.style.display = "none";
        btnProcess.style.display = "none";
        btnProcess.disabled = false;
        btnProcess.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5,3 19,12 5,21"/></svg>
            Process Video
        `;
        uploadProgress.style.display = "none";
        uploadProgressFill.style.width = "0%";
        btnNewSession.style.display = "none";
        frameGrid.innerHTML = "";

        showSection(sectionUpload);
    }

    // ─── Cleanup on page unload ──────────────────────────────────────────────
    window.addEventListener("beforeunload", () => {
        if (currentJobId) {
            navigator.sendBeacon(`/api/cleanup/${currentJobId}`);
        }
    });

    // ─── Spin animation for loading icon ─────────────────────────────────────
    const style = document.createElement("style");
    style.textContent = `
        .spin-icon { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    `;
    document.head.appendChild(style);
})();

