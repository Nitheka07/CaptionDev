const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('video-upload');
const uploadSection = document.getElementById('upload-section');
const progressSection = document.getElementById('progress-section');
const editorSection = document.getElementById('editor-section');
const resultSection = document.getElementById('result-section');
const progressBar = document.getElementById('progress-bar');
const statusText = document.getElementById('status-text');
const progressMessage = document.getElementById('progress-message');
const downloadBtn = document.getElementById('download-btn');
const transcriptGrid = document.getElementById('transcript-grid');

let currentTaskId = null;
let currentWords = [];
let activePollInterval = null;
let isSubmittingBurn = false;

function safeJson(response) {
    return response.json().catch(() => ({}));
}

function clearActivePoll() {
    if (activePollInterval) {
        clearInterval(activePollInterval);
        activePollInterval = null;
    }
}

// Drag & Drop Handlers
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.add('drag-over'), false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove('drag-over'), false);
});

dropZone.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    let dt = e.dataTransfer;
    let files = dt.files;
    handleFiles(files);
}

fileInput.addEventListener('change', function() {
    handleFiles(this.files);
});

function handleFiles(files) {
    if (files.length > 0) {
        uploadFile(files[0]);
    }
}

function uploadFile(file) {
    clearActivePoll();
    isSubmittingBurn = false;

    const fileName = file.name.toLowerCase();
    if (!fileName.endsWith('.mp4') && !fileName.endsWith('.mov')) {
        alert('Please upload an MP4 or MOV file.');
        return;
    }
    
    if (file.size > 130 * 1024 * 1024) {
        alert('File is too large. Max size is 130MB.');
        return;
    }

    const formData = new FormData();
    formData.append('video', file);

    uploadSection.classList.add('hidden');
    progressSection.classList.remove('hidden');

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(async response => {
        const data = await safeJson(response);
        if (!response.ok) {
            throw new Error(data.error || 'Upload failed.');
        }
        return data;
    })
    .then(data => {
        if (data.task_id) {
            currentTaskId = data.task_id;
            pollStatus(currentTaskId);
        } else {
            handleError("Server did not return a task ID.");
        }
    })
    .catch(error => {
        handleError(error.message || "Upload failed. Please try again.");
    });
}

function pollStatus(taskId) {
    clearActivePoll();
    activePollInterval = setInterval(() => {
        fetch(`/status/${taskId}`)
            .then(async response => {
                const data = await safeJson(response);
                if (!response.ok) {
                    throw new Error(data.error || 'Status check failed.');
                }
                return data;
            })
            .then(data => {
                if (data.status === 'error') {
                    clearActivePoll();
                    handleError(data.message);
                } else if (data.status === 'transcription_ready') {
                    clearActivePoll();
                    showEditor(data.words);
                } else if (data.status === 'completed') {
                    clearActivePoll();
                    showResult(data.download_url);
                } else {
                    updateProgress(data);
                }
            })
            .catch(error => {
                clearActivePoll();
                handleError(error.message || "Polling failed. Please try again.");
            });
    }, 2000);
}

function updateProgress(data) {
    progressBar.style.width = `${data.progress}%`;
    statusText.innerText = data.progress < 100 ? "Processing..." : "Finishing Up...";
    progressMessage.innerText = data.message;
}

function showEditor(words) {
    progressSection.classList.add('hidden');
    editorSection.classList.remove('hidden');
    currentWords = words;
    
    transcriptGrid.innerHTML = '';
    words.forEach((w, index) => {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'word-input';
        input.value = w.word.trim();
        input.dataset.index = index;
        
        // Auto-sizing based on logic
        input.style.width = (input.value.length + 1) + 'ch';
        input.addEventListener('input', function() {
            this.style.width = (this.value.length + 1) + 'ch';
            currentWords[this.dataset.index].word = this.value;
        });
        
        transcriptGrid.appendChild(input);
    });
    
    // Initialize the preview
    updatePreview();
}

function submitBurn() {
    if (isSubmittingBurn) {
        return;
    }
    if (!currentTaskId) {
        handleError("No active task. Please upload a video again.");
        return;
    }

    const styleSelect = document.getElementById('style-select').value;
    const posSelect = document.getElementById('pos-select').value;
    const fontSelect = document.getElementById('font-select').value;
    const colorPicker = document.getElementById('color-picker').value;
    const hlEnable = document.getElementById('hl-enable').checked;
    const bgEnable = document.getElementById('bg-enable').checked;
    const bgColor = document.getElementById('bg-color-picker').value;
    const bgOpacity = parseInt(document.getElementById('bg-opacity').value);
    
    isSubmittingBurn = true;
    editorSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    
    // Reset progress UI
    updateProgress({progress: 60, message: "Generating subtitles..."});
    
    fetch('/burn', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            task_id: currentTaskId,
            words: currentWords,
            style: styleSelect,
            position: posSelect,
            font: fontSelect,
            color: colorPicker,
            hl_enable: hlEnable,
            bg_enable: bgEnable,
            bg_color: bgColor,
            bg_opacity: bgOpacity
        })
    })
    .then(async response => {
        const data = await safeJson(response);
        if (!response.ok) {
            throw new Error(data.error || 'Burn request failed.');
        }
        return data;
    })
    .then(data => {
        pollStatus(currentTaskId); // Resume polling
    })
    .catch(error => {
        handleError(error.message || "Burning failed. Please try again.");
    });
}

function showResult(downloadUrl) {
    progressSection.classList.add('hidden');
    resultSection.classList.remove('hidden');
    downloadBtn.href = downloadUrl;
}

function handleError(errorMessage) {
    isSubmittingBurn = false;
    clearActivePoll();
    uploadSection.classList.remove('hidden');
    progressSection.classList.add('hidden');
    editorSection.classList.add('hidden');
    alert(`Error: ${errorMessage}`);
}

function resetApp() {
    clearActivePoll();
    isSubmittingBurn = false;
    resultSection.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    fileInput.value = '';
    progressBar.style.width = '0%';
    statusText.innerText = 'Uploading...';
    progressMessage.innerText = 'Please wait while we process your video.';
    currentTaskId = null;
    currentWords = [];
}

// --- Live Preview CSS Logic ---
function updatePreview() {
    const style = document.getElementById('style-select').value;
    const font = document.getElementById('font-select').value;
    const color = document.getElementById('color-picker').value;
    const hlEnable = document.getElementById('hl-enable').checked;
    const bgEnable = document.getElementById('bg-enable').checked;
    const bgColor = document.getElementById('bg-color-picker').value;
    const bgOpacity = parseInt(document.getElementById('bg-opacity').value) / 100.0;
    
    const previewBlock = document.getElementById('preview-text-block');
    const previewActive = document.getElementById('preview-highlight');
    const frame = document.getElementById('preview-frame');
    const pos = document.getElementById('pos-select').value;
    
    // Position handling
    frame.style.alignItems = pos === 'top' ? 'flex-start' : (pos === 'bottom' ? 'flex-end' : 'center');
    
    // Set font
    previewBlock.style.fontFamily = `"${font}", sans-serif`;
    
    // Reset defaults
    previewBlock.style.background = 'transparent';
    previewBlock.style.padding = '20px';
    previewBlock.style.textShadow = 'none';
    
    // Background toggling logic
    if (bgEnable) {
        let r = parseInt(bgColor.slice(1, 3), 16),
            g = parseInt(bgColor.slice(3, 5), 16),
            b = parseInt(bgColor.slice(5, 7), 16);
        previewBlock.style.background = `rgba(${r}, ${g}, ${b}, ${bgOpacity})`;
        previewBlock.style.display = 'inline-block';
        previewBlock.style.borderRadius = '5px';
    }

    const bases = document.querySelectorAll('.preview-base');
    
    if (style === 'typewriter') {
        bases[0].style.color = 'white'; // Past words visible
        bases[1].style.color = 'transparent'; // Future words hidden
        previewActive.style.color = hlEnable ? color : 'white';
        previewActive.style.textShadow = 'none';
        previewActive.style.background = 'transparent';
    } 
    else if (style === 'normal') {
        // Normal means the whole text just shows statically
        let baseTextCol = hlEnable ? color : 'white';
        bases.forEach(b => b.style.color = baseTextCol);
        previewActive.style.color = baseTextCol;
        previewActive.style.textShadow = 'none';
        previewActive.style.background = 'transparent';
    }
}

// Bind listeners
document.getElementById('style-select').addEventListener('change', updatePreview);
document.getElementById('font-select').addEventListener('change', updatePreview);
document.getElementById('pos-select').addEventListener('change', updatePreview);
document.getElementById('color-picker').addEventListener('input', updatePreview);
document.getElementById('hl-enable').addEventListener('change', updatePreview);
document.getElementById('bg-color-picker').addEventListener('input', updatePreview);
document.getElementById('bg-enable').addEventListener('change', updatePreview);
document.getElementById('bg-opacity').addEventListener('input', updatePreview);
