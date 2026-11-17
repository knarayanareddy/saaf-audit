// HighTable – options page logic

const backendUrlInput = document.getElementById('backendUrl');
const backendApiKeyInput = document.getElementById('backendApiKey');
const saveBtn = document.getElementById('save-btn');
const statusEl = document.getElementById('status');

let statusTimer = null;

function showStatus(message, isError = false) {
  clearTimeout(statusTimer);
  statusEl.textContent = message;
  statusEl.classList.toggle('error', isError);
  statusEl.classList.add('visible');
  statusTimer = setTimeout(() => {
    statusEl.classList.remove('visible');
  }, 2500);
}

// Load saved settings when the page opens
chrome.storage.sync.get(['backendUrl', 'backendApiKey'], (items) => {
  if (items.backendUrl) backendUrlInput.value = items.backendUrl;
  if (items.backendApiKey) backendApiKeyInput.value = items.backendApiKey;
});

// Save settings on button click
saveBtn.addEventListener('click', () => {
  const backendUrl = backendUrlInput.value.trim();
  const backendApiKey = backendApiKeyInput.value.trim();

  if (!backendUrl) {
    showStatus('Backend URL cannot be empty.', true);
    backendUrlInput.focus();
    return;
  }

  chrome.storage.sync.set({ backendUrl, backendApiKey }, () => {
    if (chrome.runtime.lastError) {
      showStatus('Error saving settings.', true);
    } else {
      showStatus('Saved!');
    }
  });
});

// Allow saving with Enter key
[backendUrlInput, backendApiKeyInput].forEach((input) => {
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') saveBtn.click();
  });
});
