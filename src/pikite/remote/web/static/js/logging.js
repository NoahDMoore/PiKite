const logs = [];
const loggerSet = new Set();

function addLogEntry(log) {
    logs.push(log);
    loggerSet.add(log.logger);
    renderLogs();
}

function getSelectedLevels() {
    return Array.from(document.querySelectorAll(".level-filter:checked"))
        .map(cb => cb.value);
}

function renderLogs() {
    const list = document.getElementById("log-entries");
    list.innerHTML = "";

    const selectedLevels = getSelectedLevels();
    const loggerFilter = document.getElementById("filter-logger").value.toLowerCase();

    const levelColors = {
        DEBUG: "grey",
        INFO: "blue",
        WARNING: "orange",
        ERROR: "red",
        CRITICAL: "red darken-3"
    };

    logs
        .filter(log => {
            // If no levels are selected, show nothing
            if (selectedLevels.length === 0) {
                return false;
            }

            // Level filter
            if (!selectedLevels.includes(log.level)) {
                return false;
            }

            // Logger filter
            if (loggerFilter && !log.logger.toLowerCase().includes(loggerFilter)) {
                return false;
            }

            return true;
        })
        .slice(-100)   // limit display size
        .reverse()     // newest first
        .forEach(log => {
            const color = levelColors[log.level] || "grey";

            const date = new Date(log.timestamp * 1000);
            const timeStr = date.toLocaleString();

            const li = document.createElement("li");
            li.className = "collection-item";

            li.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
                    <span class="log-message" style="flex: 1; min-width: 0; word-break: break-word;">${log.message}</span>
                    <span class="secondary-content" style="flex-shrink: 0; margin-left: 8px;">
                        <span class="new badge ${color}" data-badge-caption="">
                            ${log.level}
                        </span>
                    </span>
                </div>
                <div class="grey-text text-darken-1" style="font-size: 0.9em;">
                    ${timeStr} | ${log.logger}
                </div>
            `;

            // Style based on log level
            if (log.level === "CRITICAL") li.classList.add("log-critical");
            else if (log.level === "ERROR") li.classList.add("log-error");
            else if (log.level === "WARNING") li.classList.add("log-warning");
            else if (log.level === "INFO") li.classList.add("log-info");
            else if (log.level === "DEBUG") li.classList.add("log-debug");

            list.appendChild(li);
        });
}

document.getElementById("filter-logger").addEventListener("input", renderLogs);
document.querySelectorAll(".level-filter").forEach(cb => {
    cb.addEventListener("change", renderLogs);
});
document.getElementById("toggle-all").addEventListener("change", (e) => {
    const checked = e.target.checked;

    document.querySelectorAll(".level-filter").forEach(cb => {
        cb.checked = checked;
    });

    renderLogs();
});
document.querySelectorAll(".level-filter").forEach(cb => {
    cb.addEventListener("change", () => {
        const all = document.querySelectorAll(".level-filter");
        const checked = document.querySelectorAll(".level-filter:checked");

        document.getElementById("toggle-all").checked = (all.length === checked.length);

        renderLogs();
    });
});