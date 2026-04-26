var materialboxed_instances = null;

function loadMediaSessionDirectories(media_dirs_update) {
    media_session_dirs = media_dirs_update.media_dirs;

    const container = document.getElementById('media-header');
    container.innerHTML = ''; // Clear previous content

    // Create card
    const card = document.createElement('div');
    card.className = 'card';

    // Card content
    const cardContent = document.createElement('div');
    cardContent.className = 'card-content';

    // Card title
    const cardTitle = document.createElement('div');
    cardTitle.className = 'section-title';
    cardTitle.textContent = "PiKite Media Gallery";
    cardContent.appendChild(cardTitle);

    if (media_session_dirs.length === 0) {
        const noMediaMsg = document.createElement('p');
        noMediaMsg.textContent = "No media sessions found.";
        cardContent.appendChild(noMediaMsg);
    } else {
        const selectContainer = document.createElement('div');
        selectContainer.className = 'input-field';
        cardContent.appendChild(selectContainer);

        const label = document.createElement('label');
        label.textContent = "Select a media session to view its contents:";
        selectContainer.appendChild(label);

        input = document.createElement('div');
        const select = document.createElement('select');
        select.id = 'media-session-select';

        defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select a media session';
        select.appendChild(defaultOption);

        media_session_dirs.forEach(dir => {
            const option = document.createElement('option');
            option.value = dir.path;
            var mode = ""
            if (dir.mode == "STILL") {
                mode = "Photo"
            } else if (dir.mode == "VIDEO") {
                mode = "Video"
            }
            option.textContent = dir.name + " - [" + mode + "]";
            option.setAttribute('data-mode', dir.mode);
            select.appendChild(option);
        });

        input.appendChild(select);
        selectContainer.appendChild(input);
    }

    card.appendChild(cardContent);
    container.appendChild(card);

    // Initialize Materialize selects
    if (M && M.FormSelect) {
        media_dir_select_instance = M.FormSelect.init(document.querySelectorAll('#media-session-select'));
    }

    document.querySelectorAll("#media-session-select").forEach(el => {
        el.addEventListener("change", fetch_images);
    });
}

function fetch_images(e) {
    const el = e.target;
    const path = el.value;
    const mode = el.selectedOptions[0].dataset.mode;

    args = {path: path, mode: mode};
    sendCommand('FETCH_MEDIA', args);
}

function loadMedia(media_file_paths) {
    file_paths = media_file_paths.file_paths;

    const container = document.getElementById('media-content');
    container.innerHTML = ''; // Clear previous content

    for (const file_path of file_paths) {
        const image = document.createElement('img');
        image.classList.add("materialboxed", "col", "m4", "s12");
        image.src = file_path;
        image.loading = "lazy"
        image.dataset.caption = file_path

        container.appendChild(image);
    }

    var elems = document.querySelectorAll('.materialboxed');
    var materialboxed_instances = M.Materialbox.init(elems);
}