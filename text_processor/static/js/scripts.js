function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    const openSidebarBtn = document.getElementById('openSidebarBtn');

    if (!sidebar || !overlay || !openSidebarBtn) {
        console.error("Sidebar, Overlay, or Button not found!");
        return;
    }

    sidebar.classList.toggle('open');
    overlay.style.display = sidebar.classList.contains('open') ? 'block' : 'none';
    openSidebarBtn.classList.toggle('hidden', sidebar.classList.contains('open'));
}

document.addEventListener('click', (event) => {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    const openSidebarBtn = document.getElementById('openSidebarBtn');

    if (sidebar.classList.contains('open') && 
        !sidebar.contains(event.target) && 
        !openSidebarBtn.contains(event.target)) {
        toggleSidebar();
    }
});

document.addEventListener('keydown', (event) => {
    const sidebar = document.getElementById('sidebar');
    if (event.key === 'Escape' && sidebar.classList.contains('open')) {
        toggleSidebar();
    }
});


async function selectFolder() {
    try {
        // Открываем диалог выбора папки
        const handle = await window.showDirectoryPicker();

        if (handle) {
            // Получаем полный путь к папке
            const folderPath = await getFullPath(handle);
            document.getElementById('folder-path').value = folderPath;
        }
    } catch (error) {
        console.error("Ошибка при выборе папки:", error);
    }
}

// Функция для получения полного пути к папке
async function getFullPath(handle) {
    const roots = await navigator.storage.getDirectory();
    const fullPath = await resolveHandle(roots, handle);
    return fullPath;
}

// Рекурсивная функция для разрешения пути
async function resolveHandle(root, handle) {
    let current = root;
    let pathParts = [];

    while (current !== handle) {
        const entries = await current.entries();
        for await (const [name, entry] of entries) {
            if (entry === handle) {
                pathParts.push(name);
                current = entry;
                break;
            }
            if (entry.kind === 'directory') {
                pathParts.push(name);
                current = entry;
                break;
            }
        }
    }

    return '/' + pathParts.join('/');
}