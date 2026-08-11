let input;
let label;
let lastSent;
let timer;
let configured = false;

function sendValue() {
  const value = input.value;
  if (value !== lastSent) {
    lastSent = value;
    Streamlit.setComponentValue(value);
  }
}

function scheduleValue() {
  window.clearTimeout(timer);
  timer = window.setTimeout(sendValue, window.debounceMs || 400);
}

function onRender(event) {
  const args = event.detail.args;
  document.documentElement.style.setProperty("--primary", event.detail.theme.primaryColor);
  document.documentElement.style.setProperty("--text", event.detail.theme.textColor);
  document.documentElement.style.setProperty("--background", event.detail.theme.secondaryBackgroundColor);
  document.documentElement.style.setProperty("--font", event.detail.theme.font);

  input = document.getElementById("input_box");
  label = document.getElementById("label");
  label.textContent = args.label || "";
  input.placeholder = args.placeholder || "";
  window.debounceMs = Number(args.debounce_ms) || 400;

  // A selected suggestion comes back from Python as a canonical value. Do
  // not replace what someone is actively typing, but do reflect selections.
  if (document.activeElement !== input && args.value !== undefined && input.value !== args.value) {
    input.value = args.value || "";
    lastSent = input.value;
  }

  if (!configured) {
    input.addEventListener("input", scheduleValue);
    input.addEventListener("keyup", scheduleValue);
    Streamlit.setFrameHeight(74);
    configured = true;
  }
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
Streamlit.setComponentReady();
