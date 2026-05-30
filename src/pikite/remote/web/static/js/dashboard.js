function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
}

function wrap360(val) {
    return (val + 360) % 360;
}

document.querySelectorAll(".step-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        const slider = document.getElementById(btn.dataset.target);
        const step = Number(btn.dataset.step);

        const min = Number(slider.min);
        const max = Number(slider.max);

        let value = Number(slider.value);

        // Wrap Pan for Continous Rotation
        if (slider.id === "pan-slider") {
            value = wrap360(value + step);
        }

        // Disable Tilt at Slider Limits
        if (slider.id === "tilt-slider") {
            value = clamp(value + step, min, max);
        }

        slider.value = value;

        slider.dispatchEvent(new Event("input"));
        slider.dispatchEvent(new Event("change"));

        updateButtonStates();
    });
});

function updateButtonStates() {
    document.querySelectorAll(".step-btn").forEach(btn => {
        const slider = document.getElementById(btn.dataset.target);
        const step = Number(btn.dataset.step);

        const min = Number(slider.min);
        const max = Number(slider.max);
        const value = Number(slider.value);

        if (slider.id === "tilt-slider") {
            const next = value + step;

            if (next < min || next > max) {
                btn.classList.add("disabled");
                btn.style.pointerEvents = "none";
            } else {
                btn.classList.remove("disabled");
                btn.style.pointerEvents = "auto";
            }
        }
    });
}

document.querySelectorAll("input[type=range]").forEach(slider => {
    slider.addEventListener("input", updateButtonStates);
});

document.querySelectorAll("#pan-slider").forEach(slider => {
    slider.addEventListener("change", () => {
        sendCommand("PAN", {angle: slider.value})
    });
});

document.querySelectorAll("#tilt-slider").forEach(slider => {
    slider.addEventListener("change", () => {
        sendCommand("TILT", {angle: slider.value})
    });
});

updateButtonStates()

// Session Info
var pikite_mode = null
status_badge = document.getElementById("status-badge");

function updateMode(info) {
    if (info.mode == "capture_loop" && pikite_mode !== "capture_loop") {
        pikite_mode = info.mode;
        sendCommand("REQUEST_SESSION_INFO");  // Request full session info when mode changes to capture loop

        status_badge.classList.remove("idle");
        status_badge.classList.add("capture");
        status_badge.dataset.badgeCaption = "Capture";

        document.getElementById("idle-controls").style.display = "none";
        document.getElementById("capture-session-controls").style.display = "block";
    }
}

function loadSessionInfo(info) {
    document.getElementById("session-start").textContent = info.session_start || "N/A";
    document.getElementById("capture-mode").textContent = info.capture_mode || "N/A";
    document.getElementById("media-type").textContent = info.media_type || "N/A";
    document.getElementById("video-length").textContent = info.video_length !== undefined ? info.video_length + "s" : "N/A";
    document.getElementById("capture-interval").textContent = info.capture_interval !== undefined ? info.capture_interval + "s" : "N/A";
    document.getElementById("altitude-interval").textContent = info.altitude_interval !== undefined ? info.altitude_interval + "s" : "N/A";
    document.getElementById("pan-tilt-mode").textContent = info.pan_tilt_mode || "N/A";
    document.getElementById("pan-tilt-interval").textContent = info.pan_tilt_interval !== undefined ? info.pan_tilt_interval + "s" : "N/A";
}

function updateSessionInfo(info) {
    document.getElementById("capture-count").textContent = info.capture_count !== undefined ? info.capture_count : "N/A";
    document.getElementById("runtime").textContent = info.runtime || "N/A";
}

function resetSessionInfo() {
    document.getElementById("session-start").textContent = "--";
    document.getElementById("capture-mode").textContent = "--";
    document.getElementById("media-type").textContent = "--";
    document.getElementById("video-length").textContent = "--";
    document.getElementById("capture-interval").textContent = "--";
    document.getElementById("altitude-interval").textContent = "--";
    document.getElementById("pan-tilt-mode").textContent = "--";
    document.getElementById("pan-tilt-interval").textContent = "--";
    document.getElementById("runtime").textContent = "--:--:--";
    document.getElementById("altitude").textContent = "--";
    document.getElementById("pan").textContent = "--";
    document.getElementById("tilt").textContent = "--";
    document.getElementById("capture-count").textContent = "--";
}

function updateAltitudeInfo(info) {
    document.getElementById("altitude").textContent = info.altitude !== undefined ? info.altitude: "N/A";
}

function updatePanTiltInfo(info) {
    document.getElementById("pan").textContent = info.pan_angle !== undefined ? info.pan_angle: "N/A";
    document.getElementById("tilt").textContent = info.tilt_angle !== undefined ? info.tilt_angle: "N/A";
}

function endCaptureSession(info) {
    pikite_mode = "menu"

    status_badge.classList.remove("capture");
    status_badge.classList.add("idle");
    status_badge.dataset.badgeCaption = "Idle";

    resetSessionInfo();

    document.getElementById("idle-controls").style.display = "block";
    document.getElementById("capture-session-controls").style.display = "none";

    sendCommand('FETCH_MEDIA_DIRS')
}

// Camera Feed

capturePreview = document.getElementById("camera-feed");
let currentPreviewUrl = null;
capture_preview_badge = document.getElementById("capture-preview-badge");

function updateCapturePreview(obj) {
    if (document.getElementById("capture-preview-enable").dataset.enable == "True") {
        if (obj instanceof Blob) {
            const blob = obj
            const newUrl = URL.createObjectURL(blob);

            capturePreview.onload = function () {
                if (currentPreviewUrl !== null) {
                    URL.revokeObjectURL(currentPreviewUrl);
                }

                currentPreviewUrl = newUrl;
            };

            capturePreview.src = newUrl;

            if (capture_preview_badge.classList.contains("last-capture")) {
                capture_preview_badge.classList.remove("last-capture");
                capture_preview_badge.classList.add("preview");
                capture_preview_badge.dataset.badgeCaption = "Live Preview";
            }

        } else if (obj.type == "last_captured_photo") {
            file_path = obj.file_path;
            capturePreview.src = file_path + "?" + new Date().getTime();

            if (capture_preview_badge.classList.contains("preview")) {
                capture_preview_badge.classList.remove("preview");
                capture_preview_badge.classList.add("last-capture");
                capture_preview_badge.dataset.badgeCaption = "Last Captured Image";
            }
        }
    }
}

function toggleCapturePreviewEnable() {
    if (document.getElementById("capture-preview-enable").dataset.enable == "True") {
        document.getElementById("capture-preview-pause").style.display = "none";
        document.getElementById("capture-preview-play").style.display = "inline-block";
        document.getElementById("capture-preview-enable").dataset.enable = "False"
    } else if (document.getElementById("capture-preview-enable").dataset.enable == "False") {
        document.getElementById("capture-preview-pause").style.display = "inline-block";
        document.getElementById("capture-preview-play").style.display = "none";
        document.getElementById("capture-preview-enable").dataset.enable = "True"
    }
}