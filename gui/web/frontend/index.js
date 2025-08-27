import { filesize } from "https://esm.sh/filesize";
import { loadTranslations, setLanguage, t } from './i18n.js';

let languages = []
let allIsoCodes = []
// --- Language Mapping Elements ---
const useDifferentLanguagesCheckbox = document.getElementById('use-different-languages');
const languageMappingContainer = document.getElementById('language-mapping-container');
const languageMappingRows = document.getElementById('language-mapping-rows');
const addMappingBtn = document.getElementById('add-language-mapping');

const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const uploadPrompt = document.getElementById('upload-prompt');
const sunIcon = document.getElementById('sun-icon');
const moonIcon = document.getElementById('moon-icon');
let selectedFiles = [];
let availableVideos = {};

// Elements for file browser modal
const fileBrowserModal = document.getElementById('file-browser-modal');
const availableVideosContainer = document.getElementById('available-videos-container');
const closeFileBrowserBtn = document.getElementById('close-file-browser');
const closeFileBrowserBtn2 = document.getElementById('close-file-browser-2');
const modalFileUploadInput = document.getElementById('modal-file-upload');

// const pauseButton = document.getElementById('pause-button');
// const resumeButton = document.getElementById('resume-button');
const cancelButton = document.getElementById('cancel-button');

// let isPaused = false;
let isCancelled = false;
let pollTimeoutId = null;


document.addEventListener('DOMContentLoaded', async () => {
    // Set default language and load translations
    const userLanguage = 'de'; // or get from user settings
    loadTranslations(userLanguage).then(() => {
        // Apply translations to the DOM
        applyTranslations();
    }).catch(error => {
        console.error(`Error loading translations for ${userLanguage}:`, error);
    });
    setLanguage(userLanguage);

    // --- DOM Elements ---
    const brightnessSlider = document.getElementById('brightness-slider');
    const brightnessValue = document.getElementById('brightness-value');
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const convertButton = document.getElementById('convert-button');
    

    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', () => {
            const isDarkMode = document.documentElement.classList.toggle('dark');
            localStorage.setItem('darkMode', isDarkMode);
            applyDarkMode(isDarkMode);
            setTheme(isDarkMode ? 'Dark' : 'Light'); // Save theme preference
        });
    }

    // On page load, check for saved preference and apply it
    const savedMode = localStorage.getItem('darkMode') === 'true';
    applyDarkMode(savedMode);

    // --- File Handling Logic ---
    if (fileInput) {
        const dropZone = fileInput.parentElement;

        // We listen on the label, not the hidden input itself
        dropZone.addEventListener('click', (e) => {
            // Only open modal if not clicking a delete button or inside the file list
            if (e.target.closest('.delete-file-btn') || e.target.closest('#file-list')) return;
            e.preventDefault();
            if (fileBrowserModal) {
                fileBrowserModal.classList.remove('hidden');
            }
        });

        // --- Drag and Drop Logic ---
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            // Optional: Add a class to give visual feedback
            if (uploadPrompt) uploadPrompt.classList.add('border-blue-500', 'dark:border-blue-400');
        });

        dropZone.addEventListener('dragleave', (e) => {
            // Optional: Remove the visual feedback class
            if (uploadPrompt) uploadPrompt.classList.remove('border-blue-500', 'dark:border-blue-400');
        });

        dropZone.addEventListener('drop', async (e) => {
            e.preventDefault();
            // Optional: Remove the visual feedback class
            if (uploadPrompt) uploadPrompt.classList.remove('border-blue-500', 'dark:border-blue-400');
            
            if (e.dataTransfer.files.length > 0) {
                await uploadFiles(e.dataTransfer.files);
                // Refresh file list after upload
                await fetchVideos();
            }
        });
    }
    
    // --- NEU: Event-Listener zum Schließen des Modals ---
    if (closeFileBrowserBtn) {
        closeFileBrowserBtn.addEventListener('click', () => fileBrowserModal.classList.add('hidden'));
    }
    if (closeFileBrowserBtn2) {
        closeFileBrowserBtn2.addEventListener('click', () => fileBrowserModal.classList.add('hidden'));
    }

    if (modalFileUploadInput) {
        modalFileUploadInput.addEventListener('change', async (e) => {
            if (e.target.files.length > 0) {
                await uploadFiles(e.target.files);
                // Refresh file list after upload
                await fetchVideos();
            }
        });
    }

    // --- Slider Logic ---
    if (brightnessSlider) {
        brightnessSlider.addEventListener('input', (e) => {
            if (brightnessValue) brightnessValue.textContent = `${e.target.value}%`;
        });
    }

    // --- Language Mapping Logic ---
    // Await the languages before setting up the rest of the logic
    await fetchLanguages();
    // Await the IsoCodes before setting up the rest of the logic
    await fetchIsoCodes();

    if (useDifferentLanguagesCheckbox) {
        useDifferentLanguagesCheckbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                languageMappingContainer.classList.remove('hidden');
                if (languageMappingRows.children.length === 0) {
                    addMappingRow(); // Add one row by default
                }
            } else {
                languageMappingContainer.classList.add('hidden');
            }
        });
    }

    if (addMappingBtn) {
        addMappingBtn.addEventListener('click', addMappingRow);
    }
    
    if(convertButton) {
        convertButton.addEventListener('click', startConversion);
    }

    // if(pauseButton) pauseButton.addEventListener('click', pauseConversion);
    // if(resumeButton) resumeButton.addEventListener('click', resumeConversion);
    if(cancelButton) cancelButton.addEventListener('click', cancelConversion);

    // Fetch initial data
    getVersion();
    getTheme();
    fetchVideos();
});

// --- Dark Mode Logic ---
const applyDarkMode = (isDark) => {
    if (isDark) {
        document.documentElement.classList.add('dark');
        if (sunIcon) sunIcon.classList.add('hidden');
        if (moonIcon) moonIcon.classList.remove('hidden');
    } else {
        document.documentElement.classList.remove('dark');
        if (sunIcon) sunIcon.classList.remove('hidden');
        if (moonIcon) moonIcon.classList.add('hidden');
    }
};

function handleFiles(files) {
    if (!files.length) return;

    const newFilesToAdd = [];
    for (const newFile of files) {
        const isDuplicate = selectedFiles.some(existingFile =>
            existingFile.name === newFile.name && existingFile.size === newFile.size
        );

        if (!isDuplicate) {
            newFilesToAdd.push(newFile);
        }
    }

    selectedFiles = [...selectedFiles, ...newFilesToAdd];
    renderFileList(); // Call a new function to render the list
}

function renderFileList() {
    if (fileList) fileList.innerHTML = '';

    if (selectedFiles.length > 0) {
        if (uploadPrompt) uploadPrompt.classList.add('hidden');
        if (fileList) fileList.classList.remove('hidden');
    } else {
        if (uploadPrompt) uploadPrompt.classList.remove('hidden');
        if (fileList) fileList.classList.add('hidden');
    }

    selectedFiles.forEach((file, index) => {
        const truncatedName = truncateMiddle(file.name, 48);
        
        const fileElement = document.createElement('div');
        fileElement.className = 'flex items-center justify-between bg-white dark:bg-slate-700 p-2 rounded-md border border-slate-200 dark:border-slate-600 mb-2';
        fileElement.innerHTML = `
            <div class="flex items-center overflow-hidden" title="${file.name}">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4 text-slate-500 dark:text-slate-400">
                    <path fill-rule="evenodd" d="M1 3.5A1.5 1.5 0 0 1 2.5 2h11A1.5 1.5 0 0 1 15 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 12.5v-9Zm1.5.25a.25.25 0 0 1 .25-.25h1.5a.25.25 0 0 1 .25.25v1a.25.25 0 0 1-.25.25h-1.5a.25.25 0 0 1-.25-.25v-1Zm3.75-.25a.25.25 0 0 0-.25.25v3.5c0 .138.112.25.25.25h3.5a.25.25 0 0 0 .25-.25v-3.5a.25.25 0 0 0-.25-.25h-3.5ZM6 8.75a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.5a.25.25 0 0 1-.25.25h-3.5a.25.25 0 0 1-.25-.25v-3.5Zm5.75-5.25a.25.25 0 0 0-.25.25v1c0 .138.112.25.25.25h1.5a.25.25 0 0 0 .25-.25v-1a.25.25 0 0 0-.25-.25h-1.5ZM2.5 11.25a.25.25 0 0 1 .25-.25h1.5a.25.25 0 0 1 .25.25v1a.25.25 0 0 1-.25.25h-1.5a.25.25 0 0 1-.25-.25v-1Zm9.25-.25a.25.25 0 0 0-.25.25v1c0 .138.112.25.25.25h1.5a.25.25 0 0 0 .25-.25v-1a.25.25 0 0 0-.25-.25h-1.5ZM2.5 8.75a.25.25 0 0 1 .25-.25h1.5a.25.25 0 0 1 .25.25v1a.25.25 0 0 1-.25.25h-1.5a.25.25 0 0 1-.25-.25v-1Zm9.25-.25a.25.25 0 0 0-.25.25v1c0 .138.112.25.25.25h1.5a.25.25 0 0 0 .25-.25v-1a.25.25 0 0 0-.25-.25h-1.5ZM2.5 6.25A.25.25 0 0 1 2.75 6h1.5a.25.25 0 0 1 .25.25v1a.25.25 0 0 1-.25.25h-1.5a.25.25 0 0 1-.25-.25v-1ZM11.75 6a.25.25 0 0 0-.25.25v1c0 .138.112.25.25.25h1.5a.25.25 0 0 0 .25-.25v-1a.25.25 0 0 0-.25-.25h-1.5Z" clip-rule="evenodd" />
                </svg>
                <span class="ml-3 text-sm text-slate-700 dark:text-slate-200">${truncatedName}</span>
            </div>
            <div class="flex items-center">
                <span class="text-xs text-slate-500 dark:text-slate-400 flex-shrink-0 ml-2">${filesize(file.size)}</span>
                <button class="delete-file-btn ml-3 p-1 rounded-full text-slate-400 hover:text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors duration-200" data-index="${index}" title="Datei entfernen">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
                        <path fill-rule="evenodd" d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14Zm2.78-4.22a.75.75 0 0 0 0-1.06L9.06 8l1.72-1.72a.75.75 0 0 0-1.06-1.06L8 6.94l-1.72-1.72a.75.75 0 0 0-1.06 1.06L6.94 8l-1.72 1.72a.75.75 0 1 0 1.06 1.06L8 9.06l1.72 1.72a.75.75 0 0 0 1.06 0Z" clip-rule="evenodd" />
                    </svg>
                </button>
            </div>
            `;
        if (fileList) fileList.appendChild(fileElement);
    });

    document.querySelectorAll('.delete-file-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            const indexToDelete = parseInt(e.currentTarget.dataset.index);
            deleteFile(indexToDelete);
        });
    });
}

function deleteFile(index) {
    if (index > -1 && index < selectedFiles.length) {
        const deletedFile = selectedFiles.splice(index, 1)[0];
        renderFileList();
        const fileElement = document.querySelector(`.file-item[data-path="${deletedFile.name}"]`);
        if (fileElement) {
            fileElement.classList.remove('font-bold');
        }
    }
}

function truncateMiddle(text, maxLength) {
    if (text.length <= maxLength) {
        return text;
    }
    const half = Math.floor(maxLength / 2) - 2; // -2 for the ellipsis
    return `${text.substring(0, half)}...${text.substring(text.length - half)}`;
}

async function uploadFiles(files) {
    console.log('Uploading files:', Array.from(files).map(f => f.name));
    const formData = new FormData();
    for (const file of files) {
        formData.append('files[]', file);
    }

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        if (!response.ok) {
            console.error('File upload failed:', response.statusText);
        }
    } catch (error) {
        console.error('Error uploading files:', error);
    }
}

// --- Fetch Languages ---
const fetchLanguages = async () => {
    try {
        const response = await fetch('/userLanguages');
        if (!response.ok) {
            throw new Error(`Language fetching failed: ${response.statusText}`);
        }
        languages = await response.json();
    } catch (error) {
        console.error("Failed to fetch languages:", error);
    }
};

const fetchIsoCodes = async () => {
    try {
        const response = await fetch('/isoCodes');
        if (!response.ok) {
            throw new Error(`Iso Codes fetching failed: ${response.statusText}`);
        }

        allIsoCodes = await response.json();
    } catch (error) {
        console.error("Failed to fetch Iso Codes:", error);
    }
}

const createLanguageSelect = (name, all_langs = false) => {
    const select = document.createElement('select');
    select.name = name;
    select.className = "w-full sm:w-auto flex-1 px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500";
    var langs;

    if (all_langs) {
        langs = allIsoCodes;
    } else {
        langs = languages;
    }

    langs.forEach((code) => {
        const option = document.createElement('option');
        option.value = code;
        option.textContent = code;
        select.appendChild(option);
    });
    return select;
};

const addMappingRow = () => {
    // TODO: fix padding
    const row = document.createElement('div');
    row.className = 'flex items-center gap-2 animate-fade-in';

    const insteadOfText = document.createElement('span');
    insteadOfText.textContent = t('Instead of');
    insteadOfText.className = 'text-slate-600 dark:text-slate-300';

    const fromSelect = createLanguageSelect('from_lang', true);

    const useText = document.createElement('span');
    useText.textContent = t('use');
    useText.className = 'text-slate-600 dark:text-slate-300';

    const toSelect = createLanguageSelect('to_lang');

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'p-1 text-slate-400 hover:text-red-500 dark:hover:text-red-400 rounded-full hover:bg-slate-200 dark:hover:bg-slate-700';
    deleteBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /></svg>';
    deleteBtn.onclick = () => {
        if (languageMappingRows.children.length > 1) {
            row.remove();
            showOrHideDelButtons(Array.from(languageMappingRows.children));
        }
    }

    row.append(insteadOfText, fromSelect, useText, toSelect, deleteBtn);
    languageMappingRows.appendChild(row);

    showOrHideDelButtons(Array.from(languageMappingRows.children));
};

function getVersion() {
    fetch('/version')
        .then(response => response.text())
        .then(version => {
            const versionElement = document.getElementById('help-version');
            if (versionElement) {
                versionElement.textContent = `${version}`;
            }
        })
        .catch(error => console.error('Error fetching version:', error));
}

function getTheme() {
    fetch('/theme')
        .then(response => response.text())
        .then(theme => {
            // select theme in the dropdown
            const themeSelect = document.getElementById('popup-theme');
            if (themeSelect) {
                themeSelect.value = theme;
            }
            // apply dark mode based on the theme
            applyDarkMode(theme === 'dark');
        })
        .catch(error => console.error('Error fetching theme:', error));

    // print response.text to console
    fetch('/theme')
        .then(response => response.text())
        .then(theme => console.log('Current theme:', theme))
        .catch(error => console.error('Error fetching theme:', error));
}

function setTheme(theme) {
    fetch('/theme', {
        method: 'POST',
        headers: {
            'Content-Type': 'text/plain'
        },
        body: theme
    })
        .then(response => {
            if (!response.ok) {
                console.error('Failed to set theme:', response.statusText);
            }
        })
        .catch(error => console.error('Error setting theme:', error));
}

// --- Conversion and Progress Logic ---
async function getConversionStatus() {
    const response = await fetch('/conversionStatus');
}

async function startConversion() {
    const convertButton = document.getElementById('convert-button');
    // const pauseButton = document.getElementById('pause-button');
    const cancelButton = document.getElementById('cancel-button');
    const progressSection = document.getElementById('progress-section');
    const currentFileProgressBar = document.getElementById('current-file-progress-bar');
    const totalProgressBar = document.getElementById('total-progress-bar');
    const currentFileLabel = document.getElementById('current-file-label');
    const totalProgressLabel = document.getElementById('total-progress-label');

    if (selectedFiles.length === 0) {
        alert(t('Please select at least one file.'));
        return;
    }

    // Reset state for a new run
    // isPaused = false;
    isCancelled = false;

    // --- UI Update: Start Process ---
    progressSection.classList.remove('hidden');
    convertButton.classList.add('hidden'); // Hide the start button
    convertButton.disabled = true;
    // pauseButton.classList.remove('hidden');
    cancelButton.classList.remove('hidden');
    
    // Reset progress bars and labels
    currentFileProgressBar.style.width = '0%';
    totalProgressBar.style.width = '0%';
    totalProgressLabel.textContent = '0%';
    currentFileLabel.textContent = t('Preparing...');
    totalProgressBar.classList.remove('bg-red-500');
    totalProgressBar.classList.add('bg-green-500');

    const settings = {
        files: selectedFiles.map(file => file.name),
        format: document.getElementById('subtitle-format').value,
        brightness: document.getElementById('brightness-slider').value,
        edit: document.getElementById('edit-before-muxing').checked,
        saveImages: document.getElementById('save-pgs-images').checked,
        keepFiles: document.getElementById('keep-original-mkv').checked,
        keepOldSubs: document.getElementById('keep-copy-old').checked,
        keepNewSubs: document.getElementById('keep-copy-new').checked,
        useDiffLang: document.getElementById('use-different-languages').checked,
        diffLangs: Array.from(document.querySelectorAll('#language-mapping-rows > div')).map(row => ({
            from: row.querySelector('select[name="from_lang"]').value,
            to: row.querySelector('select[name="to_lang"]').value
        }))
    };

    try {
        const response = await fetch('/convert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to start conversion.');
        }

        // Start polling for status updates
        pollStatus();

    } catch (error) {
        console.error('Error starting conversion:', error);
        handleConversionEnd(false, error.message);
    }
}

function pollStatus() {
    // if (isPaused || isCancelled) {
    if (isCancelled) {
        return; // Stop polling if paused or cancelled
    }

    const currentFileProgressBar = document.getElementById('current-file-progress-bar');
    const totalProgressBar = document.getElementById('total-progress-bar');
    const currentFileLabel = document.getElementById('current-file-label');
    const totalProgressLabel = document.getElementById('total-progress-label');

    fetch('/conversionStatus')
        .then(res => {
            if (!res.ok) throw new Error('Polling request failed.');
            return res.json();
        })
        .then(status => {
            if (isCancelled) return; // Check again in case cancel was clicked during fetch

            const totalFiles = status.file_counter || selectedFiles.length;
            const finishedFiles = status.finished_files_counter || 0;
            const jobProgress = status.job_progress || 0;

            currentFileProgressBar.style.width = `${jobProgress}%`;

            if (finishedFiles < selectedFiles.length) {
                const currentFile = selectedFiles[finishedFiles];
                currentFileLabel.textContent = `${t('Processing')} ${truncateMiddle(currentFile.name, 40)}...`;
            }

            const totalPercentageBasedOnFiles = totalFiles > 0 ? (finishedFiles / totalFiles) * 100 : 0;
            const partialProgressOfCurrentFile = (1 / totalFiles) * jobProgress;
            const totalPercentage = Math.round(totalPercentageBasedOnFiles + partialProgressOfCurrentFile);

            totalProgressBar.style.width = `${totalPercentage}%`;
            totalProgressLabel.textContent = `${totalPercentage}%`;

            if (status.is_finished || (status.finished_files_counter !== undefined && status.finished_files_counter === status.file_counter)) {
                handleConversionEnd(true);
            } else {
                pollTimeoutId = setTimeout(pollStatus, 500);
            }
        })
        .catch(err => {
            console.error('Error during polling:', err);
            handleConversionEnd(false, t('A critical error occurred during polling.'));
        });
}

// function pauseConversion() {
//     isPaused = true;
//     document.getElementById('pause-button').classList.add('hidden');
//     document.getElementById('resume-button').classList.remove('hidden');
//     // Optional: Send pause signal to backend if it supports it
//     // fetch('/pauseConversion', { method: 'POST' });
// }

// function resumeConversion() {
//     isPaused = false;
//     document.getElementById('resume-button').classList.add('hidden');
//     document.getElementById('pause-button').classList.remove('hidden');
//     // fetch('/pauseConversion', { method: 'POST' });
//     // Restart polling
//     pollStatus(); 
// }

function cancelConversion() {
    isCancelled = true;
    clearTimeout(pollTimeoutId); // Stop any scheduled polling

    // Reset UI
    const convertButton = document.getElementById('convert-button');
    const progressSection = document.getElementById('progress-section');
    convertButton.classList.remove('hidden'); // Show the start button again
    convertButton.disabled = false;
    // document.getElementById('pause-button').classList.add('hidden');
    // document.getElementById('resume-button').classList.add('hidden');
    document.getElementById('cancel-button').classList.add('hidden');
    progressSection.classList.add('hidden');
    
    // Send cancel signal to backend
    fetch('/cancelConversion', { method: 'POST' });
}

function handleConversionEnd(success, message = '') {
    const convertButton = document.getElementById('convert-button');
    const progressSection = document.getElementById('progress-section');
    const currentFileLabel = document.getElementById('current-file-label');
    const totalProgressBar = document.getElementById('total-progress-bar');
    
    if (success) {
        currentFileLabel.textContent = t('Conversion successful!');
        document.getElementById('current-file-progress-bar').style.width = '100%';
        totalProgressBar.style.width = '100%';
        document.getElementById('total-progress-label').textContent = '100%';
    } else {
        currentFileLabel.textContent = message || t('Conversion failed.');
        totalProgressBar.classList.replace('bg-green-500', 'bg-red-500');
    }

    convertButton.classList.remove('hidden'); // Show the start button again
    convertButton.disabled = false;
    // document.getElementById('pause-button').classList.add('hidden');
    // document.getElementById('resume-button').classList.add('hidden');
    document.getElementById('cancel-button').classList.add('hidden');

    setTimeout(() => {
        progressSection.classList.add('hidden');
        totalProgressBar.classList.replace('bg-red-500', 'bg-green-500'); // Reset color for next run
    }, 5000);
}

function applyTranslations() {
    document.querySelectorAll('[i18n]').forEach(element => {
        const key = element.getAttribute('i18n');
        element.textContent = t(key);
    });
}

function showOrHideDelButtons(rows) {
    rows.forEach((row) => {
        const deleteBtn = row.querySelector('button');
        if (rows.length === 1) {
            deleteBtn.classList.add('hidden');
        } else {
            deleteBtn.classList.remove('hidden');
        }
    });
}

const fetchVideos = async () => {
    try {
        const response = await fetch('/files');
        if (!response.ok) {
            throw new Error(`File fetching failed: ${response.statusText}`);
        }
        const data = await response.json();
        if (data && typeof data === 'object' && !Array.isArray(data)) {
            availableVideos = data;
            if (availableVideosContainer) {
                renderAvailableVideos(availableVideos, availableVideosContainer);
            }
        } else {
            console.error("Unexpected data structure for videos:", data);
            availableVideos = {};
        }
    } catch (error) {
        console.error("Failed to fetch videos:", error);
        availableVideos = {};
    }
};

function renderAvailableVideos(node, container, filePath = '') {
    container.innerHTML = '';
    const ul = document.createElement('ul');
    ul.className = 'space-y-1';
    for (const key in node) {
        const fullPath = filePath ? `${filePath}/${key}` : key;
        const li = document.createElement('li');
        const isDirectory = typeof node[key] === 'object' && node[key] !== null && !node[key].size;
        if (isDirectory) {
            li.innerHTML = `
                <div class="flex items-center cursor-pointer folder-toggle p-1 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-5 text-slate-500 dark:text-slate-400 mr-2 flex-shrink-0">
                        <path d="M3.5 2A1.5 1.5 0 0 0 2 3.5v9A1.5 1.5 0 0 0 3.5 14h9a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 12.5 4H9.379a1.5 1.5 0 0 1-1.06-.44L7.257 2.5A1.5 1.5 0 0 0 6.197 2H3.5Z" />
                    </svg>
                    <span class="font-medium text-slate-800 dark:text-slate-200">${key}</span>
                </div>
            `;
            const subContainer = document.createElement('div');
            subContainer.className = 'ml-4 pl-2 border-l border-slate-200 dark:border-slate-700 hidden';
            li.appendChild(subContainer);
            li.querySelector('.folder-toggle').addEventListener('click', (e) => {
                e.stopPropagation();
                const isHidden = subContainer.classList.toggle('hidden');
                if (!isHidden && subContainer.innerHTML === '') {
                    renderAvailableVideos(node[key], subContainer, fullPath);
                }
            });
        } else {
            const fileData = node[key];
            li.innerHTML = `
                <div class="flex items-center cursor-pointer file-item p-1 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700" data-path="${fullPath}">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-5 text-slate-500 dark:text-slate-400 mr-2 flex-shrink-0">
                        <path fill-rule="evenodd" d="M1 3.5A1.5 1.5 0 0 1 2.5 2h11A1.5 1.5 0 0 1 15 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 12.5v-9Zm1.5.25a.25.25 0 0 1 .25-.25h1.5a.25.25 0 0 1 .25.25v1a.25.25 0 0 1-.25.25h-1.5a.25.25 0 0 1-.25-.25v-1Zm3.75-.25a.25.25 0 0 0-.25.25v3.5c0 .138.112.25.25.25h3.5a.25.25 0 0 0 .25-.25v-3.5a.25.25 0 0 0-.25-.25h-3.5ZM6 8.75a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.5a.25.25 0 0 1-.25.25h-3.5a.25.25 0 0 1-.25-.25v-3.5Zm5.75-5.25a.25.25 0 0 0-.25.25v1c0 .138.112.25.25.25h1.5a.25.25 0 0 0 .25-.25v-1a.25.25 0 0 0-.25-.25h-1.5ZM2.5 11.25a.25.25 0 0 1 .25-.25h1.5a.25.25 0 0 1 .25.25v1a.25.25 0 0 1-.25.25h-1.5a.25.25 0 0 1-.25-.25v-1Zm9.25-.25a.25.25 0 0 0-.25.25v1c0 .138.112.25.25.25h1.5a.25.25 0 0 0 .25-.25v-1a.25.25 0 0 0-.25-.25h-1.5ZM2.5 8.75a.25.25 0 0 1 .25-.25h1.5a.25.25 0 0 1 .25.25v1a.25.25 0 0 1-.25.25h-1.5a.25.25 0 0 1-.25-.25v-1Zm9.25-.25a.25.25 0 0 0-.25.25v1c0 .138.112.25.25.25h1.5a.25.25 0 0 0 .25-.25v-1a.25.25 0 0 0-.25-.25h-1.5ZM2.5 6.25A.25.25 0 0 1 2.75 6h1.5a.25.25 0 0 1 .25.25v1a.25.25 0 0 1-.25.25h-1.5a.25.25 0 0 1-.25-.25v-1ZM11.75 6a.25.25 0 0 0-.25.25v1c0 .138.112.25.25.25h1.5a.25.25 0 0 0 .25-.25v-1a.25.25 0 0 0-.25-.25h-1.5Z" clip-rule="evenodd" />
                    </svg>
                    <span class="truncate flex-grow text-sm text-slate-700 dark:text-slate-300">${key}</span>
                    <span class="text-xs text-slate-500 dark:text-slate-400 flex-shrink-0 ml-2">${filesize(fileData.size)}</span>
                </div>
            `;
            li.querySelector('.file-item').addEventListener('click', (e) => {
                e.stopPropagation();
                const target = e.currentTarget;
                const isSelected = target.classList.contains('font-bold');

                if (isSelected) {
                    // Deselect
                    const indexToDeselect = selectedFiles.findIndex(f => f.name === fullPath);
                    if (indexToDeselect > -1) {
                        deleteFile(indexToDeselect);
                    }
                } else {
                    // Select
                    const file = { name: fullPath, size: fileData.size };
                    handleFiles([file]);
                    target.classList.add('font-bold');
                }
            });
        }
        ul.appendChild(li);
    }
    container.appendChild(ul);
}
