// HighTable – background service worker
// Sets default storage values when the extension is first installed.

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({
    backendUrl: 'http://localhost:8000',
    backendApiKey: ''
  });
});
