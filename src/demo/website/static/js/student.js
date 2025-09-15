// ===== time formatting =====
const FORMAT_TZ = "Asia/Kolkata";
function fmtDateTime(ts) {
  return new Date(ts).toLocaleString("en-IN", {
    timeZone: FORMAT_TZ, year:"numeric", month:"numeric", day:"numeric",
    hour:"2-digit", minute:"2-digit"
  });
}
function fmtTime(ts) {
  return new Date(ts).toLocaleTimeString("en-IN", {
    timeZone: FORMAT_TZ, hour:"2-digit", minute:"2-digit"
  });
}

// ===== config & API =====
const STUDENT_ID = window.STUDENT_ID || null;
const API = {
  listSessions: "/api/sessions",
  myAttendance: (sid) => `/api/attendance?student_id=${sid}`,
  mark: "/api/attendance",
  faceVerify: "/face_verif",
  speechPhrase: "/speech_verif_phrase",
  speechVerify: "/speech_verif",
};

// ===== elements =====
const activeList    = document.getElementById("activeList");
const upcomingList  = document.getElementById("upcomingList");
const myAttendance  = document.getElementById("myAttendance");
const studentNameEl = document.getElementById("studentName");
const btnFace       = document.getElementById("btnFace");
const btnSpeech     = document.getElementById("btnSpeech");
const btnLocation   = document.getElementById("btnLocation");
const verifyBadge   = document.getElementById("verifyBadge");
const locBadge      = document.getElementById("locBadge");   // ✅ MUST exist in HTML
const speechPhraseEl= document.getElementById("speechPhrase");

// ===== verification state =====
let faceVerified = false;
let speechVerified = false;

// ===== geolocation state =====
let haveLocation = false;
let myLat = null, myLng = null;

// ===== helpers =====
const parseISOms = (s) => Date.parse(s);
function distanceM(lat1, lon1, lat2, lon2) {
  const R=6371000, toRad=d=>d*Math.PI/180;
  const dLat=toRad(lat2-lat1), dLon=toRad(lon2-lon1);
  const a=Math.sin(dLat/2)**2 + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLon/2)**2;
  return 2*R*Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}
const hasFence = (s) =>
  Number.isFinite(s.lat) && Number.isFinite(s.lng) && Number.isFinite(s.radius);

// ===== location =====
async function getLocationOnce() {
  if (!navigator.geolocation) {
    alert("Geolocation not supported");
    return;
  }

  locBadge.textContent = "📍 fetching...";
  locBadge.classList.remove("primary");

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      myLat = pos.coords.latitude;
      myLng = pos.coords.longitude;
      haveLocation = true;
      updateLocUI();
    },
    (err) => {
      haveLocation = false;
      locBadge.textContent = "📍 location off";
      locBadge.classList.remove("primary");
      alert("❌ Location error: " + err.message);
      updateVerifyUI();
    },
    { enableHighAccuracy: false, timeout: 5000, maximumAge: 15000 }
  );
}

function updateLocUI() {
  if (haveLocation) {
    locBadge.textContent = `📍 ${myLat.toFixed(5)}, ${myLng.toFixed(5)}`;
    locBadge.classList.add("primary");
  } else {
    locBadge.textContent = "📍 location off";
    locBadge.classList.remove("primary");
  }
  updateVerifyUI();
}

// ===== UI updates =====
function updateVerifyUI() {
  const count = (faceVerified?1:0) + (speechVerified?1:0) + (haveLocation?1:0);
  verifyBadge.textContent = `${count}/3 verified`;

  btnFace.classList.toggle("primary", faceVerified);
  btnSpeech.classList.toggle("primary", speechVerified);
  btnLocation.classList.toggle("primary", haveLocation);

  btnFace.textContent   = faceVerified   ? "Facial ✓" : "Facial verification";
  btnSpeech.textContent = speechVerified ? "Speech ✓" : "Speech verification";
  btnLocation.textContent = haveLocation ? "Location ✓" : "Use my location";

  render().catch(console.error);
}

// ===== API calls =====
async function apiListSessions(){
  const r = await fetch(API.listSessions, { credentials:"same-origin" });
  if(!r.ok) throw new Error("Failed to load sessions");
  return r.json();
}
async function apiMyAttendance(studentId){
  const r = await fetch(API.myAttendance(studentId), { credentials:"same-origin" });
  if(!r.ok) throw new Error("Failed to load attendance");
  return r.json();
}
async function apiMarkAttendance(payload){
  const r = await fetch(API.mark, {
    method:"POST",
    headers: { "Content-Type":"application/json" },
    credentials:"same-origin",
    body: JSON.stringify(payload)
  });
  const json = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(json.error || "Mark failed");
  return json;
}

// ===== sessions cache =====
let SESSION_CACHE = [];

// ===== render =====
async function render(){
  const t = Date.now();
  const rows = await apiListSessions();
  SESSION_CACHE = rows.map(s => ({
    id: s.id,
    className: s.class_name,
    startTs: parseISOms(s.start_ts),
    endTs:   parseISOms(s.end_ts),
    lat: s.lat, lng: s.lng, radius: s.radius_m
  }));

  const actives   = SESSION_CACHE.filter(s => t >= s.startTs && t <= s.endTs);
  const upcomings = SESSION_CACHE.filter(s => s.startTs > t);

  const card = (s, isActive) => {
    const startStr = fmtDateTime(s.startTs);
    const endStr   = fmtTime(s.endTs);

    let geoOK = haveLocation;
    let geoInfo = haveLocation ? "" : `<div class="badge">📍 enable location</div>`;

    const fenced = hasFence(s);
    if (fenced && haveLocation) {
      const d = distanceM(myLat, myLng, s.lat, s.lng);
      geoOK = geoOK && (d <= s.radius);
      const dm = Math.max(1, Math.round(d));
      geoInfo = (d <= s.radius)
        ? `<div class="badge">📍 within ~${dm}m</div>`
        : `<div class="badge" style="background:#ffe6e6;color:#a33;">📍 too far (~${dm}m, limit ${s.radius}m)</div>`;
    }

    const canMark = isActive && faceVerified && speechVerified && geoOK;

    return `
      <div class="session">
        <h3>${s.className}</h3>
        <div class="badge">${startStr} → ${endStr}</div>
        ${fenced ? `<div class="badge">📌 ${s.radius}m radius</div>` : ""}
        ${geoInfo}
        ${isActive ? `
          <div style="margin-top:10px">
            <button class="btn ${canMark ? 'primary' : ''}"
                    data-mark="${s.id}"
                    ${canMark ? '' : 'disabled title="Complete facial, speech & location (and be inside geofence if set)"'}>
              Mark Attendance
            </button>
          </div>` : ``}
      </div>
    `;
  };

  activeList.innerHTML   = actives.length   ? actives.map(s => card(s,true)).join("")  : `<p class="badge">No active sessions.</p>`;
  upcomingList.innerHTML = upcomings.length ? upcomings.map(s => card(s,false)).join(""): `<p class="badge">No upcoming sessions.</p>`;

  await renderMyAttendance();
}

async function renderMyAttendance(){
  if (!STUDENT_ID) {
    myAttendance.innerHTML = `<p class="badge">Log in to see your attendance.</p>`;
    return;
  }
  const recs = await apiMyAttendance(STUDENT_ID);
  if (!recs.length) {
    myAttendance.innerHTML = `<p class="badge">No records yet.</p>`;
    return;
  }
  const items = recs.map(r => {
    const s = SESSION_CACHE.find(x => x.id === r.session_id);
    const title = s ? s.className : `Session #${r.session_id}`;
    const when  = fmtDateTime(r.marked_at || Date.now());
    return `
      <div class="session">
        <h3>${title}</h3>
        <div class="badge">✅ Marked</div>
        <div class="badge">${when}</div>
      </div>
    `;
  });
  myAttendance.innerHTML = items.join("");
}

// ===== mark flow =====
async function handleMark(sessionId){
  if (!STUDENT_ID) { alert("Please log in first."); return; }
  if (!faceVerified || !speechVerified) {
    alert("Please complete facial & speech verification before marking.");
    return;
  }
  if (!haveLocation) {
    alert("Please click 'Use my location' first.");
    return;
  }

  const s = SESSION_CACHE.find(x => String(x.id) === String(sessionId));
  if (!s) { alert("Session not found."); return; }

  const payload = {
    session_id: s.id,
    student_id: STUDENT_ID,
    speech_ok: speechVerified,
    face_ok:   faceVerified,
    geo_ok:    true,
    lat: myLat,
    lng: myLng
  };

  try {
    await apiMarkAttendance(payload);
    await render();
  } catch (err) {
    const msg = String(err.message || "");
    if (msg === "proxy_detected") {
      alert("Proxy/VPN detected. Disable it to mark attendance.");
    } else if (msg.startsWith("outside_radius:")) {
      const n = msg.split(":")[1] || "";
      alert(`You're too far: ~${n}m (limit may apply).`);
    } else if (msg === "geolocation required for this session") {
      alert("Location is required for this session. Click 'Use my location'.");
    } else {
      alert(msg || "Already marked or invalid.");
    }
  }
}

// ===== init =====
document.addEventListener("DOMContentLoaded", () => {
  studentNameEl.value = localStorage.getItem("att_student_name") || "";
  studentNameEl.addEventListener("input", () =>
    localStorage.setItem("att_student_name", studentNameEl.value)
  );

  btnFace.addEventListener("click", async () => {
    const res = await fetch(API.faceVerify);
    const data = await res.json();
    if (data.ok) {
      alert("✅ Face verified successfully");
      faceVerified = true;
    } else {
      alert("❌ " + (data.message || "Face verification failed"));
      faceVerified = false;
    }
    updateVerifyUI();
  });

  btnSpeech.addEventListener("click", async () => {
    const phraseRes = await fetch(API.speechPhrase);
    const phraseData = await phraseRes.json();
    const phrase = phraseData.phrase;
    speechPhraseEl.textContent = `📢 Please read aloud: "${phrase}"`;

    const res = await fetch(`${API.speechVerify}?id=${STUDENT_ID}&phrase=${encodeURIComponent(phrase)}`, {
      method: "POST"
    });
    const data = await res.json();
    if (data.ok) {
      alert("✅ Speech verified successfully");
      speechVerified = true;
    } else {
      alert("❌ " + (data.message || "Speech verification failed"));
      speechVerified = false;
    }
    updateVerifyUI();
  });

  btnLocation.addEventListener("click", getLocationOnce);

  updateVerifyUI();
  updateLocUI();

  document.addEventListener("click", (e) => {
    const id = e.target?.dataset?.mark;
    if (id) handleMark(id);
  });

  setInterval(() => render().catch(console.error), 15000);
});
