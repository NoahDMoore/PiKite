var settings_select_instances = null;
const changedSettings = {};

function loadSettings(settings_update) {
    const settings = settings_update.current_settings;
    const menu = settings_update.menu_settings;

    const container = document.getElementById('settings-content');
    container.innerHTML = ''; // Clear previous content

    // Create column wrapper
    const col = document.createElement('div');
    col.className = 'col s12 m12';
    container.appendChild(col);

    // For each section (e.g., camera_settings)
    Object.entries(settings).forEach(([section, sectionSettings]) => {                
        // Create card
        const card = document.createElement('div');
        card.className = 'card';

        // Card content
        const cardContent = document.createElement('div');
        cardContent.className = 'card-content';

        // Card title
        const cardTitle = document.createElement('p');
        cardTitle.className = 'section-title';
        cardTitle.textContent = section.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

        cardContent.appendChild(cardTitle);

        // For each setting in the section
        Object.entries(sectionSettings).forEach(([setting, value]) => {
            if (menu[setting]) {
                // Create container for setting
                const settingsContent = document.createElement('div');
                settingsContent.id = `setting-${setting}`;
                settingsContent.className = 'setting-content';

                const settingInfo = menu[setting];
                const type = settingInfo.type;
                const options = settingInfo.options;

                // Label
                const label = document.createElement('label');
                label.textContent = setting.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

                // Input/select based on type
                let input;
                if (type === 'bool') {
                    // Materialize switch
                    input = document.createElement('div');
                    input.className = 'switch';
                    input.innerHTML = `
                        <label>
                            Off
                            <input type="checkbox" ${value === "True" ? "checked" : ""} data-setting="${setting}">
                            <span class="lever"></span>
                            On
                        </label>
                    `;
                } else if (options && options.length > 0) {
                    // Materialize select
                    input = document.createElement('div');
                    const select = document.createElement('select');
                    select.setAttribute('data-setting', setting);
                    select.classList.add('setting-select');

                    options.forEach(opt => {
                        const option = document.createElement('option');
                        option.value = opt.value;
                        option.textContent = opt.message || opt.value;
                        if (opt.value === value) option.selected = true;
                        option.setAttribute('data-setting', setting);
                        option.setAttribute('data-value', opt.value);
                        select.appendChild(option);
                    });

                    input.appendChild(select);
                } else {
                    // Default to text input
                    input = document.createElement('input');
                    input.type = type === 'int' || type === 'float' ? 'number' : 'text';
                    input.value = value;
                    input.setAttribute('data-setting', setting);
                }

                settingsContent.appendChild(label);
                settingsContent.appendChild(input);
                cardContent.appendChild(settingsContent);
            }
        });

        card.appendChild(cardContent);
        col.appendChild(card);
    });

    // Clear global changedSettings object to avoid stale changes after loading new settings
    Object.keys(changedSettings).forEach(key => delete changedSettings[key]);

    // Initialize Materialize selects
    if (M && M.FormSelect) {
        settings_select_instances = M.FormSelect.init(document.querySelectorAll('.setting-select'));
    }

    document.querySelectorAll("[data-setting]").forEach(el => {
        el.addEventListener("change", handleSettingChange);

        // For sliders / text inputs (real-time updates)
        if (el.tagName === "INPUT" && el.type !== "checkbox") {
            el.addEventListener("input", handleSettingChange);
        }
    });

    M.toast({html: 'Settings fetched from PiKite!'});
}

function handleSettingChange(e) {
    const el = e.target;
    const key = el.dataset.setting;

    if (!key) return;

    let value;

    if (el.type === "checkbox") {
        value = el.checked;
    } else {
        value = el.value;
    }

    changedSettings[key] = value;

    console.log("Changed:", key, value);
}