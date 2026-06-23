const DEFAULT_SERVER_URL = "http://127.0.0.1:8765";

function getStorage(keys) {
  return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
}

function setStorage(values) {
  return new Promise((resolve) => chrome.storage.local.set(values, resolve));
}

function status(text) {
  document.getElementById("status").textContent = text;
}

async function loadOptions() {
  const data = await getStorage({
    serverUrl: DEFAULT_SERVER_URL,
    token: ""
  });
  document.getElementById("serverUrl").value = data.serverUrl || DEFAULT_SERVER_URL;
  document.getElementById("token").value = data.token || "";
}

async function saveOptions() {
  const serverUrl = document.getElementById("serverUrl").value.trim() || DEFAULT_SERVER_URL;
  const token = document.getElementById("token").value.trim();
  await setStorage({ serverUrl, token });
  status("Saved.");
}

async function testServer() {
  await saveOptions();
  const serverUrl = document.getElementById("serverUrl").value.trim() || DEFAULT_SERVER_URL;
  try {
    const response = await fetch(`${serverUrl.replace(/\/$/, "")}/health`);
    const data = await response.json();
    status(JSON.stringify(data, null, 2));
  } catch (error) {
    status(`Server test failed: ${error.message}`);
  }
}

document.getElementById("save").addEventListener("click", saveOptions);
document.getElementById("test").addEventListener("click", testServer);
loadOptions();
