const form = document.getElementById("chat-form");
const input = document.getElementById("question-input");
const chatWindow = document.getElementById("chat-window");
const suggestions = document.getElementById("suggestions");

function addMessage(text, cssClass) {
  const div = document.createElement("div");
  div.className = `message ${cssClass}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function addLoadingMessage() {
  const div = document.createElement("div");
  div.className = "message bot loading";
  div.innerHTML = 'กำลังค้นหา <span class="dot-pulse"><span></span><span></span><span></span></span>';
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

async function sendQuestion(question) {
  if (!question) return;

  if (suggestions) suggestions.remove();

  addMessage(question, "user");
  input.value = "";

  const loadingMsg = addLoadingMessage();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    loadingMsg.remove();
    if (data.error) {
      addMessage(data.error, "bot error");
    } else {
      addMessage(data.answer, "bot");
    }
  } catch (err) {
    loadingMsg.remove();
    addMessage("เกิดข้อผิดพลาดในการเชื่อมต่อ กรุณาลองใหม่อีกครั้ง", "bot error");
  }
}

if (suggestions) {
  suggestions.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    sendQuestion(chip.textContent.trim());
  });
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  sendQuestion(input.value.trim());
});
