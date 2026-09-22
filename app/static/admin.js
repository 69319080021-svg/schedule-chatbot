const textarea = document.getElementById("data-json");
const preview = document.getElementById("preview-table");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function renderPreview() {
  let data;
  try {
    data = JSON.parse(textarea.value);
  } catch (e) {
    preview.innerHTML = `<p class="error">JSON ไม่ถูกต้อง: ${escapeHtml(e.message)}</p>`;
    return;
  }

  let html = `<p><strong>${escapeHtml(data.name || "-")}</strong> (${escapeHtml(data.qualification || "-")})<br>`;
  html += `${escapeHtml(data.department || "-")} · ${escapeHtml(data.school || "-")} · ภาคเรียน ${escapeHtml(data.semester || "-")}</p>`;

  if (Array.isArray(data.schedule) && data.schedule.length) {
    html += "<table><thead><tr><th>วัน</th><th>เวลา</th><th>คาบ</th><th>ประเภท</th><th>วิชา</th><th>สถานที่</th><th>กลุ่ม</th></tr></thead><tbody>";
    for (const row of data.schedule) {
      html += `<tr><td>${escapeHtml(row.day)}</td><td>${escapeHtml(row.start_time)}-${escapeHtml(row.end_time)}</td><td>${escapeHtml(row.periods)}</td><td>${escapeHtml(row.type)}</td><td>${escapeHtml(row.course_code)} ${escapeHtml(row.course_name)}</td><td>${escapeHtml(row.location)}</td><td>${escapeHtml(row.group)}</td></tr>`;
    }
    html += "</tbody></table>";
  } else {
    html += "<p>ไม่มีข้อมูลตารางสอน</p>";
  }

  preview.innerHTML = html;
}

let debounceTimer;
textarea.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(renderPreview, 300);
});

renderPreview();
