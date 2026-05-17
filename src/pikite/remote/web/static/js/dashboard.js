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

updateButtonStates()

// Session Info
var pikite_scope = null

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
        sendCommand("request_session_info");  // Request full session info when scope changes to capture loop
    }

    document.getElementById("capture-count").textContent = info.capture_count !== undefined ? info.capture_count : "N/A";
    document.getElementById("runtime").textContent = info.runtime || "N/A";
}

function updateAltitudeInfo(info) {
    document.getElementById("altitude").textContent = info.altitude !== undefined ? info.altitude + "m" : "N/A";
}

function updatePanTiltInfo(info) {
    document.getElementById("pan").textContent = info.pan_angle !== undefined ? info.pan_angle + "°" : "N/A";
    document.getElementById("tilt").textContent = info.tilt_angle !== undefined ? info.tilt_angle + "°" : "N/A";
}