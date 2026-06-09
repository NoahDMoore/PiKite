var settings_select_instances = null;
const changedSettings = {};

function loadSettings(settings_update) {
    const settings_obj = JSON.parse(settings_update.settings);
    console.log(settings_obj)

    const container = document.getElementById('settings-content');
    container.innerHTML = ""; // Clear previous content
    fragment = recursivelyBuildSettings(settings_obj);
    container.appendChild(fragment);

    // Clear global changedSettings object to avoid stale changes after loading new settings
    Object.keys(changedSettings).forEach(key => delete changedSettings[key]);

    // Initialize Materialize selects
    if (M && M.FormSelect) {
        settings_select_instances = M.FormSelect.init(document.querySelectorAll('.setting-select'));
    }

    // Initialize Tooltips
    var tooltip_elems = document.querySelectorAll('.tooltipped');
    var tooltip_instances = M.Tooltip.init(tooltip_elems, {});

    document.querySelectorAll("[data-setting]").forEach(el => {
        el.addEventListener("change", handleSettingChange);

        if (el.tagName === "INPUT" && el.type !== "checkbox") {
            el.addEventListener("input", handleSettingChange);
        }
    });

    M.toast({html: 'Settings fetched from PiKite!'});
}

function recursivelyBuildSettings(group, path="") {
    const fragment = document.createDocumentFragment();

    for (const [key, value] of Object.entries(group)) {
        if (!value || typeof value !== "object") continue;
        if (["label", "description", "type"].includes(key)) continue;

        const currentPath = path ? `${path}.${key}` : key;
        const depth = path ? path.split(".").length : 0;
        const isSubsection = (depth > 0)

        if (value.type === "settings_group") {
            //console.log("Group:", currentPath);

            const {groupElement, groupContent} = createGroupElement(
                currentPath,
                value.label ?? key,
                value.description,
                subsection = isSubsection
            )

            const childGroup = recursivelyBuildSettings(value, currentPath);

            groupContent.appendChild(childGroup);
            groupElement.appendChild(groupContent);
            fragment.appendChild(groupElement);
        } else if (value.type === "setting") {
            //console.log("Setting:", currentPath);
            const setting = buildSettingInput(value, currentPath)
            fragment.appendChild(setting)
        }
    };

    return fragment
}

function createGroupElement(path, label, description, subsection=false) {
    type = Boolean
    if (subsection === true) {
        type = 'subsection'
    } else {
        type = 'card';
    }

    // Create Container
    const groupElement = document.createElement('div');
    groupElement.className = type
    groupElement.id = path.replace(".","-")

    // Group Content
    const groupContent = document.createElement('div');
    groupContent.className = `${type}-content`;

    // Title
    const groupTitle = document.createElement('div');
    groupTitle.className = 'section-title';
    groupTitle.textContent = label;
    groupContent.appendChild(groupTitle);

    // Description
    const groupDescription = document.createElement('div');
    groupDescription.className = 'section-description';
    groupDescription.textContent = description;
    groupContent.appendChild(groupDescription);

    return {groupElement, groupContent}
}

function buildSettingInput(setting, settingKey) {
    // Create container for setting
    const settingsContent = document.createElement('div');
    settingsContent.id = `setting-${settingKey}`;
    settingsContent.className = 'setting-content';

    // Label
    const label = document.createElement('label');
    label.textContent = setting.label;
    label.className = "tooltipped";
    label.dataset.position = "top";
    label.dataset.tooltip = setting.description
    settingsContent.appendChild(label);

    const options_def = setting.options

    if (options_def === undefined) {
        if (setting.data_type === "bool") {
            input = createMaterializeSwitch(setting, settingKey);
        } else {
            console.log("No options provided for setting: " + setting.label);
        }
    } else if (Array.isArray(options_def)) {
        input = createMaterializeSelect(setting, settingKey);
    } else if (Number.isFinite(options_def.min) && Number.isFinite(options_def.max)) {
        input = createMaterializeRange(setting, settingKey);
    }

    settingsContent.appendChild(input)

    return settingsContent
}

function createMaterializeSwitch(setting, settingKey) {
    currentValue = setting.current_value

    // Materialize switch
    input = document.createElement('div');
    input.className = 'switch';
    input.innerHTML = `
        <label>
            Off
            <input type="checkbox" ${currentValue === true ? "checked" : ""} data-setting="${settingKey}">
            <span class="lever"></span>
            On
        </label>
    `;

    return input
}

function createMaterializeSelect(setting, settingKey) {
    currentValue = setting.current_value

    // Materialize select
    input = document.createElement('div');
    const select = document.createElement('select');
    select.setAttribute('data-setting', settingKey);
    select.classList.add('setting-select');

    setting.options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.label || opt.value;
        if (opt.value === currentValue) option.selected = true;
        option.setAttribute('data-setting', settingKey);
        option.setAttribute('data-value', opt.value);
        select.appendChild(option);
    });

    input.appendChild(select);

    return input
}

function createMaterializeRange(setting, settingKey) {
    currentValue = setting.current_value

    // Materialize range
    input = document.createElement('p');
    input.className = "range-field";

    const range = document.createElement('input');
    range.className = "range";
    range.setAttribute('type', 'range');
    range.setAttribute('min', setting.options.min);
    range.setAttribute('max', setting.options.max);
    range.setAttribute('step', setting.options.step);
    range.setAttribute('value', parseInt(currentValue));
    range.setAttribute('data-setting', settingKey);
    input.appendChild(range)

    return input
}

function handleSettingChange(e) {
    const el = e.target;
    const key = el.dataset.setting;

    if (!key) return;

    let value;

    if (el.type === "checkbox") {
        value = el.checked;
    } else if (el.type === "range") {
        value = Number(el.value);
    } else {
        value = el.value;
    }

    changedSettings[key] = value;

    console.log("Changed:", key, value);
}