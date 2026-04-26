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