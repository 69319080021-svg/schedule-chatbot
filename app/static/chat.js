const form = document.getElementById("chat-form");
const input = document.getElementById("question-input");
const chatWindow = document.getElementById("chat-window");

function addMessage(text, cssClass) {
  const div = document.createElement("div");
  div.className = `message ${cssClass}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = input.value.trim();
  if (!question) return;

  addMessage(question, "user");
  input.value = "";

  const loadingMsg = addMessage("กำลังค้นหา...", "bot loading");

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
});
