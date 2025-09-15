const FORMAT_TZ = "Asia/Kolkata";

function fmtDateTime(ts) {
  return new Date(ts).toLocaleString("en-IN", {
    timeZone: FORMAT_TZ,
    year: "numeric", month: "numeric", day: "numeric",
    hour: "2-digit", minute: "2-digit"
  });
}

function fmtTime(ts) {
  return new Date(ts).toLocaleTimeString("en-IN", {
    timeZone: FORMAT_TZ,
    hour: "2-digit", minute: "2-digit"
  });
}

// ====== CONFIG ======
const TEACHER_ID = Number.isInteger(window.TEACHER_ID) ? window.TEACHER_ID : null;
const CSRF = window.CSRF_TOKEN || null;

const API = {
  list:   "/api/sessions",
  create: "/api/sessions",
  update: (id) => `/api/sessions/${id}`,
  del:    (id) => `/api/sessions/${id}`,
  count:  (id) => `/api/sessions/${id}/attendance_count`
};

// ===== Elements =====
const sessionList = document.getElementById("sessionList");
const pastList    = document.getElementById("pastList");
const btnNew      = document.getElementById("btnNewSession");
const modal       = document.getElementById("sessionModal");
const form        = document.getElementById("sessionForm");
const titleEl     = document.getElementById("modalTitle");
const btnUseLoc   = document.getElementById("btnUseMyLocation");
const btnCancel   = document.getElementById("btnCancel");

let editing = null;

// ===== Helpers =====
const hdrs = () => {
  const h = { "Content-Type": "application/json" };
  if (CSRF) h["X-CSRFToken"] = CSRF;
  return h;
};
const toIso     = (ms) => new Date(ms).toISOString();
const parseISOms= (s) => new Date(s).getTime();

async function failIfNotOk(res, msg) {
  if (res.ok) return;
  let detail = "";
  try { detail = await res.text(); } catch {}
  throw new Error(`${msg} (${res.status})${detail ? ": " + detail : ""}`);
}

// ===== API calls =====
async function apiListSessions() {
  const r = await fetch(API.list, { credentials:"same-origin" });
  await failIfNotOk(r, "Failed to fetch sessions");
  return r.json();
}
async function apiCreateSession(payload) {
  const r = await fetch(API.create, {
    method:"POST", headers:hdrs(), credentials:"same-origin",
    body: JSON.stringify(payload)
  });
  await failIfNotOk(r, "Failed to create session");
  return r.json();
}
async function apiUpdateSession(id, payload) {
  const r = await fetch(API.update(id), {
    method:"PUT", headers:hdrs(), credentials:"same-origin",
    body: JSON.stringify(payload)
  });
  await failIfNotOk(r, "Failed to update session");
  return r.json();
}
async function apiDeleteSession(id) {
  const r = await fetch(API.del(id), { method:"DELETE", headers:hdrs(), credentials:"same-origin" });
  await failIfNotOk(r, "Failed to delete session");
}
async function apiAttendanceCount(id) {
  const r = await fetch(API.count(id), { credentials:"same-origin" });
  await failIfNotOk(r, "Failed to fetch count");
  return r.json();
}

// ===== UI render =====
async function render() {
  const now = Date.now();
  const rows = await apiListSessions();
  const sessions = rows.map(s => ({
    id: s.id,
    className: s.class_name,
    startTs: parseISOms(s.start_ts),
    endTs:   parseISOms(s.end_ts),
    lat: s.lat, lng: s.lng, radius: s.radius_m
  }));

  const upAct = sessions.filter(s => (now >= s.startTs && now <= s.endTs) || s.startTs > now);
  const past  = sessions.filter(s => s.endTs < now);

  async function cardHTML(s) {
    const active = now >= s.startTs && now <= s.endTs;
    const status = active ? "🟢 Active" : (s.startTs > now ? "🕒 Upcoming" : "⏹ Ended");
    const startStr = fmtDateTime(s.startTs);
    const endStr   = fmtTime(s.endTs);
    const { count } = await apiAttendanceCount(s.id);
    return `
      <div class="session">
        <h3>${s.className}</h3>
        <div class="badge">${status}</div>
        <div class="badge">${startStr} → ${endStr}</div>
        <div class="badge">👥 ${count} marked</div>
        ${Number.isFinite(s.radius) ? `<div class="badge">📍 ${s.radius}m radius</div>` : ""}
        <div style="margin-top:10px">
          <button class="btn" data-edit="${s.id}">Edit</button>
          <button class="btn" data-del="${s.id}">Delete</button>
        </div>
      </div>
    `;
  }

  sessionList.innerHTML = upAct.length
    ? (await Promise.all(upAct.map(cardHTML))).join("")
    : `<p class="badge">No sessions yet.</p>`;

  pastList.innerHTML = past.length
    ? (await Promise.all(past.map(cardHTML))).join("")
    : `<p class="badge">No past sessions.</p>`;
}

// ===== Modal open/fill =====
function openModal(session=null) {
  editing = session;
  titleEl.textContent = editing ? "Edit Session" : "Create Session";
  form.reset();
  if (session) {
    const start = new Date(session.startTs);
    const end   = new Date(session.endTs);
    form.elements.className.value = session.className;
    form.elements.date.value      = start.toISOString().slice(0,10);
    form.elements.start.value     = start.toTimeString().slice(0,5);
    form.elements.end.value       = end.toTimeString().slice(0,5);
    form.elements.duration.value  = "";
    form.elements.lat.value       = session.lat ?? "";
    form.elements.lng.value       = session.lng ?? "";
    form.elements.radius.value    = session.radius ?? "";
  }
  modal.showModal();
}

// ===== Save / Delete =====
async function onSave(e) {
  e.preventDefault();

  if (!Number.isInteger(TEACHER_ID)) {
    alert("Please sign in as a teacher first.");
    return;
  }

  const f = new FormData(form);
  const className = (f.get("className") || "").trim();
  const date      = f.get("date");
  const start     = f.get("start");
  const end       = f.get("end");
  const duration  = parseInt(f.get("duration") || "0", 10);

  if (!className || !date || !start) { alert("Fill Class, Date, Start."); return; }
  if (!end && !duration)             { alert("Provide End time or Duration."); return; }

  // helper: convert teacher's local IST time → UTC ISO
  function toUTC(dateStr, timeStr) {
    return new Date(`${dateStr}T${timeStr}:00+05:30`).toISOString();
  }

  const startIso = toUTC(date, start);
  const endIso   = end
    ? toUTC(date, end)
    : new Date(new Date(`${date}T${start}:00+05:30`).getTime() + duration * 60000).toISOString();

  const lat    = parseFloat(f.get("lat"));
  const lng    = parseFloat(f.get("lng"));
  const radius = parseFloat(f.get("radius"));

  const payload = {
    teacher_id: TEACHER_ID,
    class_name: className,
    start_ts: startIso,
    end_ts:   endIso,
    lat: Number.isFinite(lat) ? lat : null,
    lng: Number.isFinite(lng) ? lng : null,
    radius_m: Number.isFinite(radius) ? radius : null
  };

  try {
    if (editing) await apiUpdateSession(editing.id, payload);
    else         await apiCreateSession(payload);
    modal.close();
    await render();
  } catch (err) {
    console.error("Save error:", err);
    alert(err.message || "Save failed");
  }
}

async function onDelete(id) {
  if (!confirm("Delete this session?")) return;
  try {
    await apiDeleteSession(id);
    await render();
  } catch (err) {
    alert(err.message || "Delete failed");
  }
}

// ===== Location =====
async function useMyLocation() {
  try {
    const pos = await new Promise((res, rej) =>
      navigator.geolocation.getCurrentPosition(res, rej, { enableHighAccuracy:true, timeout:8000 })
    );
    form.elements.lat.value = pos.coords.latitude.toFixed(6);
    form.elements.lng.value = pos.coords.longitude.toFixed(6);
    if (!form.elements.radius.value) form.elements.radius.value = 150;
  } catch (e) {
    alert("Could not get location: " + e.message);
  }
}

// ===== Init =====
document.addEventListener("DOMContentLoaded", () => {
  render().catch(err => {
    console.error(err);
    sessionList.innerHTML = `<p class="badge">Failed to load sessions.</p>`;
  });

  btnNew.onclick    = () => openModal(null);
  form.onsubmit     = onSave;
  btnUseLoc.onclick = useMyLocation;
  btnCancel.onclick = () => modal.close();

  document.addEventListener("click", async (e) => {
    const editId = e.target?.dataset?.edit;
    const delId  = e.target?.dataset?.del;
    if (editId) {
      const rows = await apiListSessions();
      const list = rows.map(s => ({
        id: s.id,
        className: s.class_name,
        startTs: parseISOms(s.start_ts),
        endTs:   parseISOms(s.end_ts),
        lat: s.lat, lng: s.lng, radius: s.radius_m
      }));
      const s = list.find(x => String(x.id) === String(editId));
      if (s) openModal(s);
    }
    if (delId) onDelete(delId);
  });

  setInterval(() => render().catch(console.error), 15000);
});
