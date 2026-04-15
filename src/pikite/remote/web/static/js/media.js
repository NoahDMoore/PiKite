function loadMediaSessionDirectories(media_dirs_update) {
    media_session_dirs = media_dirs_update.media_dirs;

    const container = document.getElementById('media-content');
    container.innerHTML = ''; // Clear previous content

    // Create column wrapper
    const col = document.createElement('div');
    col.className = 'col s12 m12';
    container.appendChild(col);

    // Create card
    const card = document.createElement('div');
    card.className = 'card';

    // Card content
    const cardContent = document.createElement('div');
    cardContent.className = 'card-content';

    // Card title
    const cardTitle = document.createElement('p');
    cardTitle.className = 'section-title';
    cardTitle.textContent = "PiKite Media Gallery";
    cardContent.appendChild(cardTitle);

    if (media_session_dirs.length === 0) {
        const noMediaMsg = document.createElement('p');
        noMediaMsg.textContent = "No media sessions found.";
        cardContent.appendChild(noMediaMsg);
    } else {
        const label = document.createElement('label');
        label.textContent = "Select a media session to view its contents:";
        cardContent.appendChild(label);

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
            option.textContent = dir.name;
            select.appendChild(option);
        });

        input.appendChild(select);
        cardContent.appendChild(input);
    }

    card.appendChild(cardContent);
    col.appendChild(card);

    // Initialize Materialize selects
    if (M && M.FormSelect) {
        media_dir_select_instance = M.FormSelect.init(document.querySelectorAll('#media-session-select'));
    }
}