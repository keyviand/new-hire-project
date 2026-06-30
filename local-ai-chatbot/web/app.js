const conversation = document.querySelector("#conversation");
const welcome = document.querySelector("#welcome");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const clearButton = document.querySelector("#clear-button");
const statusLine = document.querySelector("#status");
const messages = [];
let busy = false;

function scrollToBottom() {
  conversation.scrollTop = conversation.scrollHeight;
}

function addMessage(role, content, extraClass = "") {
  welcome?.remove();
  const element = document.createElement("div");
  element.className = `message ${role} ${extraClass}`.trim();
  element.textContent = content;
  conversation.appendChild(element);
  scrollToBottom();
  return element;
}

function resizeInput() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 150)}px`;
}

async function loadStatus() {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error("offline");
    const status = await response.json();
    const device = status.gpu || status.device.toUpperCase();
    statusLine.innerHTML =
      `<span class="status-dot online"></span> Local · ${device} · step ${status.trainingStep}`;
  } catch {
    statusLine.innerHTML = `<span class="status-dot"></span> Nova is offline`;
  }
}

async function sendMessage(text) {
  if (busy || !text.trim()) return;
  busy = true;
  sendButton.disabled = true;
  input.disabled = true;

  const userMessage = { role: "user", content: text.trim() };
  messages.push(userMessage);
  addMessage("user", userMessage.content);
  input.value = "";
  resizeInput();

  const thinking = addMessage("assistant", "Nova is thinking…", "thinking");
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages, temperature: 0.7 })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Nova could not answer.");
    thinking.remove();
    messages.push({ role: "assistant", content: result.reply });
    addMessage("assistant", result.reply);
  } catch (error) {
    thinking.textContent = `Error: ${error.message}`;
    thinking.classList.remove("thinking");
  } finally {
    busy = false;
    sendButton.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(input.value);
});

input.addEventListener("input", resizeInput);
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

clearButton.addEventListener("click", () => {
  messages.length = 0;
  conversation.replaceChildren();
  const fresh = document.createElement("div");
  fresh.className = "welcome";
  fresh.innerHTML = `
    <div class="welcome-orb" aria-hidden="true">N</div>
    <h2>New conversation</h2>
    <p>Nova's short-term chat memory has been cleared.</p>`;
  conversation.appendChild(fresh);
  input.focus();
});

document.querySelectorAll(".suggestions button").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.textContent));
});

loadStatus();
input.focus();

