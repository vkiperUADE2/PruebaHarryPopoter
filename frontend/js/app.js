const API = "";
let sessionToken = localStorage.getItem("hp_token") || null;
let currentUser  = JSON.parse(localStorage.getItem("hp_user") || "null");

// ── utils ────────────────────────────────────────────────────────────────────

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (sessionToken) headers["X-Session-Token"] = sessionToken;
  const res = await fetch(API + path, { ...opts, headers });
  if (res.status === 401 && sessionToken) {
    clearLocalSession();
    const method = (opts.method || "GET").toUpperCase();
    const publicGet = method === "GET" &&
      (path.startsWith("/universo/") || path.startsWith("/rankings/global"));
    if (publicGet) return api(path, opts);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function toast(msg, duration = 2800) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), duration);
}

function spin(id) {
  document.getElementById(id).innerHTML = '<p class="spinner">Cargando…</p>';
}

// ── auth ─────────────────────────────────────────────────────────────────────

function clearLocalSession() {
  sessionToken = null;
  currentUser = null;
  localStorage.removeItem("hp_token");
  localStorage.removeItem("hp_user");
  if (document.readyState !== "loading") updateNavAuth();
}

function updateNavAuth() {
  const btn   = document.getElementById("btn-login-nav");
  const ubar  = document.getElementById("user-bar");
  const uname = document.getElementById("user-name");
  if (currentUser) {
    btn.textContent = "Cerrar sesión";
    ubar.style.display  = "flex";
    uname.textContent   = currentUser.nombre;
    document.getElementById("btn-admin-section").style.display = Number(currentUser.rol_id) === 2 ? "block" : "none";
  } else {
    btn.textContent = "Iniciar sesión";
    ubar.style.display  = "none";
    document.getElementById("btn-admin-section").style.display = "none";
  }
}

async function doLogin(email, password) {
  const data = await api("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  sessionToken = data.token;
  currentUser  = { user_id: data.user_id, nombre: data.nombre, email: data.email, rol_id: Number(data.rol_id) };
  localStorage.setItem("hp_token", sessionToken);
  localStorage.setItem("hp_user",  JSON.stringify(currentUser));
  closeModal();
  updateNavAuth();
  toast(`Bienvenido, ${data.nombre}`);
}

async function doRegister(nombre, email, password) {
  await api("/auth/register", {
    method: "POST",
    body: JSON.stringify({ nombre, email, password }),
  });
  await doLogin(email, password);
}

async function doLogout() {
  if (sessionToken) await api("/auth/logout", { method: "POST" }).catch(() => {});
  clearLocalSession();
  toast("Sesión cerrada");
}

// ── modal ─────────────────────────────────────────────────────────────────────

function openModal()  { document.getElementById("auth-modal").classList.add("open"); }
function closeModal() { document.getElementById("auth-modal").classList.remove("open"); }

function switchTab(tab) {
  document.querySelectorAll(".modal-tab").forEach(t => t.classList.remove("active"));
  document.querySelector(`[data-tab="${tab}"]`).classList.add("active");
  document.getElementById("tab-login").style.display    = tab === "login"    ? "block" : "none";
  document.getElementById("tab-register").style.display = tab === "register" ? "block" : "none";
  document.getElementById("modal-error").textContent    = "";
}

// ── navigation ────────────────────────────────────────────────────────────────

function showSection(id) {
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
  document.querySelectorAll("nav button[data-section]").forEach(b =>
    b.classList.toggle("active", b.dataset.section === id)
  );
  const loaders = {
    "sec-personajes": loadPersonajes,
    "sec-casas":      loadCasas,
    "sec-hechizos":   loadHechizos,
    "sec-eventos":    loadEventos,
    "sec-peliculas":  loadPeliculas,
    "sec-objetos":    loadObjetos,
    "sec-rankings":   loadRankings,
    "sec-actividad":  loadActividad,
    "sec-admin":      loadAdminPanel,
  };
  if (loaders[id]) loaders[id]();
}

// ── personajes ────────────────────────────────────────────────────────────────

async function loadPersonajes(q = "") {
  spin("personajes-grid");
  try {
    const path = q ? `/universo/personajes/buscar?q=${encodeURIComponent(q)}` : "/universo/personajes";
    const data  = await api(path);
    const grid  = document.getElementById("personajes-grid");
    if (!data.length) { grid.innerHTML = '<p class="spinner">Sin resultados</p>'; return; }
    grid.innerHTML = data.map(p => `
      <div class="card" onclick="showPersonaje('${p._id}')">
        <h3>${p.nombre}</h3>
        <p>${p.rol || ""} · ${p.alineacion || ""}</p>
        <span class="tag">${p.casa?.nombre || "Sin casa"}</span>
      </div>`).join("");
  } catch (e) { document.getElementById("personajes-grid").innerHTML = `<p class="spinner">Error: ${e.message}</p>`; }
}

async function showPersonaje(id) {
  const p = await api(`/universo/personajes/${id}`).catch(e => { toast(e.message); return null; });
  if (!p) return;
  const panel = document.getElementById("personaje-detail");
  panel.style.display = "block";
  panel.innerHTML = `
    <div class="detail-panel">
      <h3>${p.nombre}</h3>
      <div class="detail-grid">
        <div><label>Rol</label><br><span>${p.rol || "-"}</span></div>
        <div><label>Alineación</label><br><span>${p.alineacion || "-"}</span></div>
        <div><label>Casa</label><br><span>${p.casa?.nombre || "-"}</span></div>
        <div><label>Nacimiento</label><br><span>${p.fecha_nacimiento ? p.fecha_nacimiento.split("T")[0] : "-"}</span></div>
      </div>
      ${p.hechizos?.length ? `<p style="margin-top:1rem;font-size:.82rem;color:var(--muted)">Hechizos: ${p.hechizos.map(h=>h.nombre).join(", ")}</p>` : ""}
    </div>`;
}

// ── casas ─────────────────────────────────────────────────────────────────────

async function loadCasas() {
  spin("casas-grid");
  try {
    const data = await api("/universo/casas");
    document.getElementById("casas-grid").innerHTML = data.map(c => `
      <div class="card">
        <h3>${c.nombre}</h3>
        <p>Fundador: ${c.fundador}</p>
        <p>Mascota: ${c.mascota}</p>
        <span class="tag">${c.valores?.join(" · ") || ""}</span>
      </div>`).join("");
  } catch (e) { document.getElementById("casas-grid").innerHTML = `<p class="spinner">Error: ${e.message}</p>`; }
}

// ── hechizos ──────────────────────────────────────────────────────────────────

async function loadHechizos(q = "") {
  spin("hechizos-grid");
  try {
    const path = q ? `/universo/hechizos/buscar?q=${encodeURIComponent(q)}` : "/universo/hechizos";
    const data  = await api(path);
    document.getElementById("hechizos-grid").innerHTML = data.map(h => `
      <div class="card">
        <h3>${h.nombre}</h3>
        <p>${h.descripcion}</p>
        <span class="tag">${h.efecto}</span>
      </div>`).join("");
  } catch (e) { document.getElementById("hechizos-grid").innerHTML = `<p class="spinner">Error: ${e.message}</p>`; }
}

// ── eventos ───────────────────────────────────────────────────────────────────

async function loadEventos() {
  spin("eventos-table");
  try {
    const data = await api("/universo/eventos");
    document.getElementById("eventos-table").innerHTML = `
      <table>
        <thead><tr><th>Nombre</th><th>Fecha</th><th>Descripción</th></tr></thead>
        <tbody>${data.map(e => `
          <tr>
            <td>${e.nombre}</td>
            <td>${e.fecha ? e.fecha.split("T")[0] : "-"}</td>
            <td>${e.descripcion}</td>
          </tr>`).join("")}
        </tbody>
      </table>`;
  } catch (err) { document.getElementById("eventos-table").innerHTML = `<p class="spinner">Error: ${err.message}</p>`; }
}

// ── peliculas ─────────────────────────────────────────────────────────────────

async function loadPeliculas() {
  spin("peliculas-grid");
  try {
    const data = await api("/universo/peliculas");
    document.getElementById("peliculas-grid").innerHTML = data.map(p => `
      <div class="card">
        <h3>${p.titulo}</h3>
        <p>${p.descripcion}</p>
        <span class="tag">${p.tipo} · ${p.anio_lanzamiento}</span>
      </div>`).join("");
  } catch (e) { document.getElementById("peliculas-grid").innerHTML = `<p class="spinner">Error: ${e.message}</p>`; }
}

// ── objetos ───────────────────────────────────────────────────────────────────

async function loadObjetos() {
  spin("objetos-grid");
  try {
    const data = await api("/universo/objetos");
    document.getElementById("objetos-grid").innerHTML = data.map(o => `
      <div class="card">
        <h3>${o.nombre}</h3>
        <p>${o.descripcion}</p>
        <span class="tag">${o.tipo}</span>
      </div>`).join("");
  } catch (e) { document.getElementById("objetos-grid").innerHTML = `<p class="spinner">Error: ${e.message}</p>`; }
}

// ── rankings ──────────────────────────────────────────────────────────────────

async function loadRankings() {
  spin("rankings-global");
  const today = new Date().toISOString().split("T")[0];
  try {
    const data = await api(`/rankings/global?fecha=${today}&top=10`);
    const el   = document.getElementById("rankings-global");
    if (!data.length) { el.innerHTML = '<p class="spinner">Sin datos hoy aún. Explorá el contenido primero.</p>'; return; }
    el.innerHTML = data.map((r, i) => `
      <div class="rank-item">
        <span class="rank-num">#${i+1}</span>
        <span>${r.contenido_id}</span>
        <span class="rank-score">${r.visitas} visita${r.visitas !== 1 ? "s" : ""}</span>
      </div>`).join("");
  } catch (e) { document.getElementById("rankings-global").innerHTML = `<p class="spinner">Error: ${e.message}</p>`; }

  if (currentUser) {
    const uid = currentUser.user_id;
    if (uid) {
      const data2 = await api(`/rankings/usuario/${uid}`).catch(() => []);
      document.getElementById("rankings-usuario").innerHTML = data2.map((r, i) => `
        <div class="rank-item">
          <span class="rank-num">#${i+1}</span>
          <span>${r.contenido_id}</span>
          <span class="rank-score">${r.visitas} visita${r.visitas !== 1 ? "s" : ""}</span>
        </div>`).join("") || '<p class="spinner">Sin actividad personal</p>';
    }
  }
}

// ── actividad ─────────────────────────────────────────────────────────────────

async function loadActividad() {
  if (!currentUser) {
    document.getElementById("actividad-content").innerHTML = '<p class="spinner">Iniciá sesión para ver tu actividad.</p>';
    return;
  }
  const me = await api("/auth/me").catch(() => null);
  if (!me) return;
  const uid = me.user_id;

  spin("actividad-content");
  try {
    const rows = await api(`/actividad/usuario/${uid}`);
    document.getElementById("actividad-content").innerHTML = rows.length ? `
      <table>
        <thead><tr><th>Tipo</th><th>Contenido</th><th>Categoría</th><th>Fecha</th></tr></thead>
        <tbody>${rows.slice(0, 50).map(r => `
          <tr>
            <td>${r.tipo_actividad}</td>
            <td>${r.contenido_nombre}</td>
            <td>${r.contenido_tipo}</td>
            <td>${r.created_at ? new Date(r.created_at).toLocaleString() : "-"}</td>
          </tr>`).join("")}
        </tbody>
      </table>` : '<p class="spinner">Sin actividad registrada.</p>';
    const searches = await api(`/actividad/busquedas/${uid}`).catch(() => []);
    document.getElementById("busquedas-content").innerHTML = searches.length
      ? `<table><thead><tr><th>Texto</th><th>Resultados</th><th>Fecha</th></tr></thead><tbody>${searches.map(s =>
          `<tr><td>${s.texto_busqueda}</td><td>${s.cantidad_resultados}</td><td>${new Date(s.created_at).toLocaleString()}</td></tr>`
        ).join("")}</tbody></table>`
      : '<p class="spinner">Sin búsquedas registradas.</p>';
  } catch (e) {
    document.getElementById("actividad-content").innerHTML = `<p class="spinner">Error: ${e.message}</p>`;
  }
}

async function globalSearch() {
  const q = document.getElementById("search-global").value.trim();
  if (!q) return;
  spin("global-results");
  try {
    const rows = await api(`/universo/buscar?q=${encodeURIComponent(q)}`);
    document.getElementById("global-results").innerHTML = rows.length ? rows.map(r => {
      const c = r.contenido;
      return `<div class="card"><h3>${c.nombre || c.titulo}</h3><p>${c.descripcion || c.rol || ""}</p><span class="tag">${r.tipo}</span></div>`;
    }).join("") : '<p class="spinner">Sin resultados</p>';
  } catch (e) { document.getElementById("global-results").innerHTML = `<p class="spinner">Error: ${e.message}</p>`; }
}

const adminLabels = {
  personajes: "personaje", casas: "casa", hechizos: "hechizo",
  eventos: "evento", peliculas: "película o libro", objetos: "objeto mágico",
};
let adminStore = {};
let adminRoles = [];
let adminUsers = [];
let adminEditing = null;

const field = (id, label, type = "text", placeholder = "") =>
  `<label for="${id}">${label}</label><input id="${id}" type="${type}" placeholder="${placeholder}" required/>`;
const selectField = (id, label, options) =>
  `<label for="${id}">${label}</label><select id="${id}" required>${options}</select>`;
const optionsFor = (rows, label) => rows.map(r => `<option value="${r._id}">${r[label]}</option>`).join("");

function renderAdminForm(item = null) {
  adminEditing = item;
  const type = document.getElementById("admin-category").value;
  document.getElementById("admin-form-title").textContent =
    `${item ? "Editar" : "Agregar"} ${adminLabels[type]}`;
  let html = "";
  if (type === "personajes") {
    html = field("af-name", "Nombre completo") +
      field("af-birth", "Fecha de nacimiento", "date") +
      selectField("af-house", "Casa", optionsFor(adminStore.casas || [], "nombre")) +
      field("af-role", "Rol en la historia", "text", "Ejemplo: profesor") +
      field("af-alignment", "Alineación", "text", "Ejemplo: bien, mal o neutral");
  } else if (type === "casas") {
    html = field("af-name", "Nombre de la casa") + field("af-founder", "Fundador") +
      field("af-mascot", "Mascota") + field("af-values", "Valores", "text", "Separados por comas");
  } else if (type === "hechizos") {
    html = field("af-name", "Nombre del hechizo") + field("af-description", "Descripción") +
      field("af-effect", "Efecto que produce");
  } else if (type === "eventos") {
    html = field("af-name", "Nombre del evento") + field("af-date", "Fecha", "date") +
      field("af-description", "Descripción");
  } else if (type === "peliculas") {
    html = field("af-title", "Título") +
      selectField("af-type", "Tipo", '<option value="pelicula">Película</option><option value="libro">Libro</option>') +
      field("af-year", "Año de lanzamiento", "number") + field("af-description", "Descripción");
  } else {
    html = field("af-name", "Nombre del objeto") + field("af-description", "Descripción") +
      field("af-type", "Tipo de objeto", "text", "Ejemplo: reliquia, varita o artefacto");
  }
  document.getElementById("admin-friendly-form").innerHTML = html;
  if (item) fillAdminForm(type, item);
}

function fillAdminForm(type, item) {
  const set = (id, value) => { const el = document.getElementById(id); if (el) el.value = value ?? ""; };
  set("af-name", item.nombre); set("af-description", item.descripcion); set("af-type", item.tipo);
  if (type === "personajes") {
    set("af-birth", item.fecha_nacimiento?.split("T")[0]); set("af-house", item.casa?.id);
    set("af-role", item.rol); set("af-alignment", item.alineacion);
  } else if (type === "casas") {
    set("af-founder", item.fundador); set("af-mascot", item.mascota); set("af-values", item.valores?.join(", "));
  } else if (type === "hechizos") set("af-effect", item.efecto);
  else if (type === "eventos") set("af-date", item.fecha?.split("T")[0]);
  else if (type === "peliculas") {
    set("af-title", item.titulo); set("af-year", item.anio_lanzamiento);
  }
}

function adminFormBody(type) {
  const value = id => document.getElementById(id)?.value.trim();
  if (type === "personajes") {
    const house = (adminStore.casas || []).find(c => c._id === value("af-house"));
    return {
      nombre: value("af-name"), fecha_nacimiento: `${value("af-birth")}T00:00:00`,
      casa: { id: house._id, nombre: house.nombre }, rol: value("af-role"), alineacion: value("af-alignment"),
      peliculas_libros: adminEditing?.peliculas_libros || [], hechizos: adminEditing?.hechizos || [],
      eventos: adminEditing?.eventos || [],
    };
  }
  if (type === "casas") return { nombre: value("af-name"), fundador: value("af-founder"), mascota: value("af-mascot"), valores: value("af-values").split(",").map(v => v.trim()).filter(Boolean) };
  if (type === "hechizos") return { nombre: value("af-name"), descripcion: value("af-description"), efecto: value("af-effect") };
  if (type === "eventos") return { nombre: value("af-name"), fecha: `${value("af-date")}T00:00:00`, descripcion: value("af-description"), participantes: adminEditing?.participantes || [] };
  if (type === "peliculas") return { titulo: value("af-title"), tipo: value("af-type"), anio_lanzamiento: Number(value("af-year")), descripcion: value("af-description"), personajes: adminEditing?.personajes || [], eventos: adminEditing?.eventos || [] };
  return { nombre: value("af-name"), descripcion: value("af-description"), tipo: value("af-type") };
}

function renderAdminItems() {
  const type = document.getElementById("admin-category").value;
  const rows = adminStore[type] || [];
  const name = row => row.nombre || row.titulo;
  document.getElementById("admin-items-list").innerHTML = rows.length ? rows.map((row, i) => `
    <div class="admin-list-row"><div><strong>${name(row)}</strong><small>${row.descripcion || row.rol || row.fundador || ""}</small></div>
    <div class="row-actions"><button class="btn btn-outline" onclick="editAdminItem(${i})">Editar</button>
    <button class="btn btn-danger" onclick="deleteAdminItem(${i})">Eliminar</button></div></div>`).join("") :
    '<p class="helper">Todavía no hay contenido cargado.</p>';
}

async function loadAdminPanel() {
  if (!currentUser || Number(currentUser.rol_id) !== 2) return;
  const types = Object.keys(adminLabels);
  const data = await Promise.all(types.map(type => api(`/universo/${type}?limit=100`)));
  types.forEach((type, i) => adminStore[type] = data[i]);
  [adminRoles, adminUsers] = await Promise.all([api("/auth/roles"), api("/auth/usuarios")]);
  renderAdminForm(); renderAdminItems(); renderRelationOptions(); renderUsersAndRoles();
}

function editAdminItem(index) {
  const type = document.getElementById("admin-category").value;
  renderAdminForm(adminStore[type][index]);
  document.getElementById("admin-friendly-form").scrollIntoView({ behavior: "smooth" });
}

async function deleteAdminItem(index) {
  const type = document.getElementById("admin-category").value;
  const item = adminStore[type][index];
  if (!confirm(`¿Seguro que querés eliminar "${item.nombre || item.titulo}"?`)) return;
  await api(`/universo/${type}/${item._id}`, { method: "DELETE" });
  toast("Contenido eliminado"); await loadAdminPanel();
}

async function saveAdminItem() {
  const form = document.getElementById("admin-friendly-form");
  if (!form.reportValidity()) return;
  const type = document.getElementById("admin-category").value;
  const method = adminEditing ? "PUT" : "POST";
  const path = `/universo/${type}${adminEditing ? `/${adminEditing._id}` : ""}`;
  await api(path, { method, body: JSON.stringify(adminFormBody(type)) });
  toast(adminEditing ? "Cambios guardados" : "Contenido agregado");
  await loadAdminPanel();
}

function renderRelationOptions() {
  const chars = optionsFor(adminStore.personajes || [], "nombre");
  document.getElementById("relation-event-character").innerHTML = chars;
  document.getElementById("relation-movie-character").innerHTML = chars;
  document.getElementById("relation-event-target").innerHTML = optionsFor(adminStore.eventos || [], "nombre");
  document.getElementById("relation-movie-target").innerHTML = optionsFor(adminStore.peliculas || [], "titulo");
}

async function changeRelation(kind, remove = false) {
  const char = document.getElementById(`relation-${kind === "eventos" ? "event" : "movie"}-character`).value;
  const target = document.getElementById(`relation-${kind === "eventos" ? "event" : "movie"}-target`).value;
  if (remove) {
    const key = kind === "eventos" ? "evento_id" : "pelicula_id";
    await api(`/universo/asociaciones/${kind}?personaje_id=${char}&${key}=${target}`, { method: "DELETE" });
  } else {
    const body = kind === "eventos"
      ? { personaje_id: char, evento_id: target, rol_en_evento: document.getElementById("relation-event-role").value.trim() }
      : { personaje_id: char, pelicula_id: target };
    await api(`/universo/asociaciones/${kind}`, { method: "POST", body: JSON.stringify(body) });
  }
  toast(remove ? "Relación eliminada" : "Relación agregada"); await loadAdminPanel();
}

function renderUsersAndRoles() {
  const roleOptions = selected => adminRoles.map(r => `<option value="${r.id}" ${r.id === selected ? "selected" : ""}>${r.nombre}</option>`).join("");
  document.getElementById("admin-users-list").innerHTML = adminUsers.map(u => `
    <div class="admin-user-card"><strong>${u.nombre}</strong><small>${u.email}</small>
    <label>Tipo de usuario</label><select id="user-role-${u.id}">${roleOptions(u.rol_id)}</select>
    <label>Estado</label><select id="user-active-${u.id}"><option value="true" ${u.activo ? "selected" : ""}>Activo</option><option value="false" ${!u.activo ? "selected" : ""}>Inactivo</option></select>
    <button class="btn" onclick="saveFriendlyUser(${u.id})">Guardar cambios</button></div>`).join("");
  document.getElementById("admin-roles-list").innerHTML = adminRoles.map((r, i) => `
    <div class="admin-list-row"><div><strong>${r.nombre}</strong><small>${r.descripcion || ""}</small></div>
    <div class="row-actions"><button class="btn btn-outline" onclick="editFriendlyRole(${i})">Editar</button>
    ${r.id > 2 ? `<button class="btn btn-danger" onclick="deleteFriendlyRole(${r.id}, '${r.nombre}')">Eliminar</button>` : ""}</div></div>`).join("");
}

async function saveFriendlyUser(id) {
  await api(`/auth/usuarios/${id}`, { method: "PUT", body: JSON.stringify({
    rol_id: Number(document.getElementById(`user-role-${id}`).value),
    activo: document.getElementById(`user-active-${id}`).value === "true",
  }) });
  toast("Usuario actualizado"); await loadAdminPanel();
}

function editFriendlyRole(index) {
  const role = adminRoles[index];
  document.getElementById("role-edit-id").value = role.id;
  document.getElementById("role-name").value = role.nombre;
  document.getElementById("role-description").value = role.descripcion || "";
}

async function saveFriendlyRole() {
  if (!document.getElementById("role-friendly-form").reportValidity()) return;
  const id = document.getElementById("role-edit-id").value;
  await api(`/auth/roles${id ? `/${id}` : ""}`, { method: id ? "PUT" : "POST", body: JSON.stringify({
    nombre: document.getElementById("role-name").value, descripcion: document.getElementById("role-description").value,
  }) });
  clearFriendlyRole(); toast("Tipo de usuario guardado"); await loadAdminPanel();
}

function clearFriendlyRole() {
  document.getElementById("role-edit-id").value = "";
  document.getElementById("role-friendly-form").reset();
}

async function deleteFriendlyRole(id, name) {
  if (!confirm(`¿Eliminar el tipo de usuario "${name}"?`)) return;
  await api(`/auth/roles/${id}`, { method: "DELETE" });
  toast("Tipo de usuario eliminado"); await loadAdminPanel();
}

// ── init ──────────────────────────────────────────────────────────────────────

async function syncSession() {
  if (!sessionToken) return;
  const me = await api("/auth/me").catch(() => null);
  if (!me) return;
  currentUser = {
    user_id: Number(me.user_id),
    nombre: me.nombre,
    email: me.email,
    rol_id: Number(me.rol),
  };
  localStorage.setItem("hp_user", JSON.stringify(currentUser));
  updateNavAuth();
}

document.addEventListener("DOMContentLoaded", async () => {
  updateNavAuth();
  await syncSession();
  showSection("sec-personajes");

  // nav buttons
  document.querySelectorAll("nav button[data-section]").forEach(btn => {
    btn.addEventListener("click", () => showSection(btn.dataset.section));
  });

  // login/logout nav button
  document.getElementById("btn-login-nav").addEventListener("click", () => {
    if (currentUser) doLogout();
    else openModal();
  });

  // modal tabs
  document.querySelectorAll(".modal-tab").forEach(t =>
    t.addEventListener("click", () => switchTab(t.dataset.tab))
  );
  document.getElementById("close-modal").addEventListener("click", closeModal);

  // login form
  document.getElementById("form-login").addEventListener("submit", async e => {
    e.preventDefault();
    const email    = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    document.getElementById("modal-error").textContent = "";
    try { await doLogin(email, password); }
    catch (err) { document.getElementById("modal-error").textContent = err.message; }
  });

  // register form
  document.getElementById("form-register").addEventListener("submit", async e => {
    e.preventDefault();
    const nombre   = document.getElementById("reg-nombre").value;
    const email    = document.getElementById("reg-email").value;
    const password = document.getElementById("reg-password").value;
    document.getElementById("modal-error").textContent = "";
    try { await doRegister(nombre, email, password); }
    catch (err) { document.getElementById("modal-error").textContent = err.message; }
  });

  // search personajes
  document.getElementById("search-personajes").addEventListener("input", e => {
    clearTimeout(window._st);
    window._st = setTimeout(() => loadPersonajes(e.target.value), 350);
  });

  // search hechizos
  document.getElementById("search-hechizos").addEventListener("input", e => {
    clearTimeout(window._sh);
    window._sh = setTimeout(() => loadHechizos(e.target.value), 350);
  });

  // filter actividad por fecha
  document.getElementById("btn-filter-fecha").addEventListener("click", async () => {
    const fecha = document.getElementById("input-fecha").value;
    if (!fecha) return;
    const me = await api("/auth/me").catch(() => null);
    if (!me) { toast("Iniciá sesión primero"); return; }
    spin("actividad-content");
    try {
      const rows = await api(`/actividad/usuario/${me.user_id}/fecha/${fecha}`);
      document.getElementById("actividad-content").innerHTML = rows.length
        ? `<table>
            <thead><tr><th>Tipo</th><th>Contenido</th><th>Categoría</th></tr></thead>
            <tbody>${rows.map(r => `<tr><td>${r.tipo_actividad}</td><td>${r.contenido_nombre}</td><td>${r.contenido_tipo}</td></tr>`).join("")}</tbody>
           </table>`
        : '<p class="spinner">Sin actividad en esa fecha</p>';
    } catch (e) {
      document.getElementById("actividad-content").innerHTML = `<p class="spinner">Error: ${e.message}</p>`;
    }
  });

  document.getElementById("btn-search-global").addEventListener("click", globalSearch);
  document.getElementById("search-global").addEventListener("keydown", e => { if (e.key === "Enter") globalSearch(); });
  document.querySelectorAll(".admin-tab").forEach(tab => tab.addEventListener("click", () => {
    document.querySelectorAll(".admin-tab").forEach(t => t.classList.toggle("active", t === tab));
    document.querySelectorAll(".admin-view").forEach(v => v.classList.toggle("active", v.id === tab.dataset.adminView));
  }));
  document.getElementById("admin-category").addEventListener("change", () => { renderAdminForm(); renderAdminItems(); });
  document.getElementById("admin-new-item").addEventListener("click", () => renderAdminForm());
  document.getElementById("admin-cancel-edit").addEventListener("click", () => renderAdminForm());
  document.getElementById("admin-save-item").addEventListener("click", () => saveAdminItem().catch(e => toast(e.message)));
  document.getElementById("relation-event-add").addEventListener("click", () => changeRelation("eventos").catch(e => toast(e.message)));
  document.getElementById("relation-event-remove").addEventListener("click", () => changeRelation("eventos", true).catch(e => toast(e.message)));
  document.getElementById("relation-movie-add").addEventListener("click", () => changeRelation("peliculas").catch(e => toast(e.message)));
  document.getElementById("relation-movie-remove").addEventListener("click", () => changeRelation("peliculas", true).catch(e => toast(e.message)));
  document.getElementById("role-save").addEventListener("click", () => saveFriendlyRole().catch(e => toast(e.message)));
  document.getElementById("role-clear").addEventListener("click", clearFriendlyRole);
});
