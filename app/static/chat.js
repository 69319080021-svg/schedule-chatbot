const form = document.getElementById("chat-form");
const input = document.getElementById("question-input");
const chatWindow = document.getElementById("chat-window");
const suggestions = document.getElementById("suggestions");
const conversationHistory = [];

function addMessage(text, cssClass) {
  const div = document.createElement("div");
  div.className = `message ${cssClass}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatInline(str) {
  return str
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

// แปลง Markdown พื้นฐานที่ Gemini มักตอบกลับมา (ตัวหนา, list ซ้อนกันได้) ให้เป็น HTML
// โดยไม่พึ่ง library ภายนอก — escape ก่อนเสมอเพื่อกันการฉีด HTML
// สร้างเป็นโครงสร้าง block ก่อน แล้วค่อย serialize เพื่อให้ list ที่มีรายการย่อยคั่นกลาง
// ยังนับเลขต่อเนื่องถูกต้อง (ไม่ตัดเป็นคนละ <ol> จนเลขรีเซ็ต)
function formatMarkdown(raw) {
  const blocks = [];
  // stack ของ list ที่กำลังเปิดอยู่ พร้อม indent เพื่อรู้ระดับการซ้อน
  const stack = []; // { indent, type, items: [] }
  let paragraph = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: "p", content: paragraph.join("<br>") });
      paragraph = [];
    }
  };
  const closeListsDeeperThan = (indent) => {
    while (stack.length && stack[stack.length - 1].indent > indent) {
      stack.pop();
    }
  };
  const closeAllLists = () => {
    stack.length = 0;
  };
  const currentContainer = () => {
    if (!stack.length) return blocks;
    const top = stack[stack.length - 1];
    const lastItem = top.items[top.items.length - 1];
    return lastItem.children;
  };

  const lines = escapeHtml(raw).split(/\r?\n/);
  const isListLine = (line) => /^[*-]\s+/.test(line.trim()) || /^\d+\.\s+/.test(line.trim());

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const indent = rawLine.length - rawLine.trimStart().length;
    const trimmed = rawLine.trim();
    const bullet = trimmed.match(/^[*-]\s+(.*)/);
    const numbered = trimmed.match(/^\d+\.\s+(.*)/);
    const type = bullet ? "ul" : numbered ? "ol" : null;

    if (type) {
      flushParagraph();
      closeListsDeeperThan(indent);
      const top = stack[stack.length - 1];

      if (top && top.indent === indent && top.type === type) {
        // ต่อรายการในลิสต์เดิมระดับเดียวกัน (ไม่ต้องเปิดลิสต์ใหม่)
      } else {
        if (top && top.indent === indent) stack.pop(); // ระดับเดียวกันแต่เปลี่ยนชนิด -> แทนที่
        const list = { indent, type, items: [] };
        currentContainer().push(list);
        stack.push(list);
      }

      const content = formatInline(bullet ? bullet[1] : numbered[1]);
      stack[stack.length - 1].items.push({ content, children: [] });
    } else if (trimmed === "") {
      // บรรทัดว่างระหว่าง list item (loose list) ไม่ควรตัด list ทิ้ง
      // มิเช่นนั้นเลขลำดับจะรีเซ็ตกลายเป็นคนละ <ol>
      let next = i + 1;
      while (next < lines.length && lines[next].trim() === "") next++;
      const nextIsList = next < lines.length && isListLine(lines[next]);
      flushParagraph();
      if (!nextIsList) closeAllLists();
    } else {
      closeAllLists();
      paragraph.push(formatInline(trimmed));
    }
  }
  flushParagraph();

  const renderBlocks = (list) =>
    list
      .map((block) => {
        if (block.type === "p") return `<p>${block.content}</p>`;
        const inner = block.items
          .map((item) => `<li>${item.content}${renderBlocks(item.children)}</li>`)
          .join("");
        return `<${block.type}>${inner}</${block.type}>`;
      })
      .join("");

  return renderBlocks(blocks);
}

function addBotMessage(text) {
  const div = document.createElement("div");
  div.className = "message bot";
  div.innerHTML = formatMarkdown(text);
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
      body: JSON.stringify({ question, history: conversationHistory }),
    });
    const data = await res.json();
    loadingMsg.remove();
    if (data.error) {
      addMessage(data.error, "bot error");
    } else {
      addBotMessage(data.answer);
      conversationHistory.push({ role: "user", text: question });
      conversationHistory.push({ role: "bot", text: data.answer });
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
