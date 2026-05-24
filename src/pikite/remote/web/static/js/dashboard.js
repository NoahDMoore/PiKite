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
var pikite_scope = null
status_badge = document.getElementById("status-badge");

capturePreview = document.getElementById("camera-feed");

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
    if (info.scope == "CAPTURE_LOOP" && pikite_scope !== "CAPTURE_LOOP") {
        pikite_scope = info.scope;
        sendCommand("REQUEST_SESSION_INFO");  // Request full session info when scope changes to capture loop

        status_badge.classList.remove("idle");
        status_badge.classList.add("capture");
        status_badge.dataset.badgeCaption = "Capture";

        document.getElementById("idle-controls").style.display = "none";
        document.getElementById("capture-session-controls").style.display = "block";
    }

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
    pikite_scope = "MENU"

    status_badge.classList.remove("capture");
    status_badge.classList.add("idle");
    status_badge.dataset.badgeCaption = "Idle";

    resetSessionInfo();

    document.getElementById("idle-controls").style.display = "block";
    document.getElementById("capture-session-controls").style.display = "none";

    sendCommand('FETCH_MEDIA_DIRS')
}

let currentPreviewUrl = null;

function updateCapturePreview(obj) {
    if (document.getElementById("capture-preview-enable").dataset.enable == "True") {
        if (obj instanceof Blob) {
            const blob = obj
            const newUrl = URL.createObjectURL(blob);
            const preview = document.getElementById("capture-preview");

            capturePreview.onload = function () {
                if (currentPreviewUrl !== null) {
                    URL.revokeObjectURL(currentPreviewUrl);
                }

                currentPreviewUrl = newUrl;
            };

            capturePreview.src = newUrl;
        } else if (obj.type == "last_captured_photo") {
            file_path = obj.file_path;
            capturePreview.src = file_path + "?" + new Date().getTime();
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