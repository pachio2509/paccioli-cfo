// Paccioli CFO · tablero en vivo. Pregunta al servidor local cada 2 s si hubo cambios.
"use strict";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const peso = (v) => (v < 0 ? "−$" : "$") + Math.abs(Math.round(v)).toLocaleString("es-MX");
const pct = (v) => (v == null ? "—" : (v * 100).toFixed(1) + "%");
const NS = "http://www.w3.org/2000/svg";

let E = null, version = null, mesSel = null, buscar = "";

// ---------------------------------------------------------------- datos
async function cargar() {
  try {
    const r = await fetch("/api/estado", { cache: "no-store" });
    E = await r.json();
    version = E.version;
    if (!mesSel || !E.por_mes || !E.por_mes[mesSel]) mesSel = E.mes_actual;
    render();
    vivo(true);
  } catch (e) { vivo(false); }
}
async function vigilar() {
  try {
    const r = await fetch("/api/version", { cache: "no-store" });
    const v = (await r.json()).version;
    vivo(true);
    if (v !== version) await cargar();
  } catch (e) { vivo(false); }
  setTimeout(vigilar, 2000);
}
function vivo(ok) {
  const l = $("#live");
  l.classList.toggle("off", !ok);
  l.lastChild.textContent = ok ? (E && E.actualizado ? "En vivo · " + E.actualizado.slice(11, 19) : "En vivo") : "Sin conexión con el servidor";
}
async function post(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json();
  if (!j.ok) throw new Error(j.error || "Algo salió mal");
  return j;
}
function toast(t, ms = 2600) {
  const el = $("#toast"); el.textContent = t; el.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (el.hidden = true), ms);
}

// ---------------------------------------------------------------- subir archivos
async function subir(files) {
  for (const f of files) {
    toast("Leyendo " + f.name + "…", 6000);
    try {
      const r = await fetch("/api/subir?nombre=" + encodeURIComponent(f.name), { method: "POST", body: f });
      const j = await r.json();
      if (!j.ok) throw new Error(j.error);
    } catch (e) { toast("No pude subir " + f.name + ": " + e.message, 5000); return; }
  }
  await cargar();
  toast("Listo. Ya leí tu estado de cuenta.");
}
$("#archivo").addEventListener("change", (e) => { subir([...e.target.files]); e.target.value = ""; });
let arrastre = 0;
window.addEventListener("dragenter", (e) => { e.preventDefault(); arrastre++; $("#overlay").hidden = false; });
window.addEventListener("dragleave", () => { if (--arrastre <= 0) { arrastre = 0; $("#overlay").hidden = true; } });
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => { e.preventDefault(); arrastre = 0; $("#overlay").hidden = true; subir([...e.dataTransfer.files]); });
$("#imprimir").addEventListener("click", () => window.print());
$("#buscar").addEventListener("input", (e) => { buscar = e.target.value.toLowerCase(); renderMovs(); });

// ---------------------------------------------------------------- render
function render() {
  if (E.error) { $("#vacio").hidden = false; $("#contenido").hidden = true; $(".empty-card h1").textContent = "Algo falló al leer tus archivos"; $(".empty-card .sub").textContent = E.error; return; }
  $("#ver").textContent = "v" + (E.app || "");
  $("#carpeta").textContent = E.carpeta || "mis-estados-de-cuenta";
  const hay = E.meses && E.meses.length;
  $("#vacio").hidden = !!hay; $("#contenido").hidden = !hay;
  if (!hay) { if (E.errores && E.errores.length) toast(E.errores[0].error, 7000); return; }
  const d = E.por_mes[mesSel];
  const nombreMes = E.meses.find((m) => m.mes === mesSel).nombre;
  $("#periodo").textContent = "Cierre de " + nombreMes + (d.parcial ? ` · mes incompleto (${d.dias} días)` : "");
  $("#titulo").textContent = "¿Cómo le fue a " + E.negocio + "?";
  $("#subtitulo").textContent = `Leí ${E.movimientos.length} movimientos de ${E.archivos.length} archivo${E.archivos.length > 1 ? "s" : ""}. Ingresos y gastos sin IVA; lo que sale del banco, con IVA.`;
  $("#meses").innerHTML = E.meses.map((m) => `<button class="month" role="tab" aria-selected="${m.mes === mesSel}" data-m="${m.mes}">${esc(m.nombre)}${E.por_mes[m.mes].parcial ? "<small>parcial</small>" : ""}</button>`).join("");
  document.querySelectorAll(".month").forEach((b) => b.addEventListener("click", () => { mesSel = b.dataset.m; render(); }));
  renderVeredicto(d); renderKpis(d); renderAlertas(); renderPreguntas();
  renderCascada(d); renderTendencia(); renderBarras("#clientes", d.clientes.slice(0, 10), "var(--s1)");
  renderBarras("#gastos", d.gastos_categoria.slice(0, 12), "var(--s2)"); renderER(d); renderMovs(); renderArchivos();
}

function renderVeredicto(d) {
  const orden = ["rojo", "ambar", "verde", "info"];
  const a = [...E.alertas].sort((x, y) => orden.indexOf(x.nivel) - orden.indexOf(y.nivel))[0];
  const nivel = a ? a.nivel : "info";
  const txt = { rojo: "Semáforo rojo", ambar: "Semáforo ámbar", verde: "Semáforo verde", info: "Tu resumen" }[nivel];
  const ut = d.utilidad;
  $("#veredicto").className = "verdict " + nivel;
  $("#veredicto").innerHTML = `<div class="dot"></div><div>
    <p><b>${txt}.</b> ${ut >= 0 ? "Tu operación dejó" : "Tu operación perdió"} <b>${peso(Math.abs(ut))}</b> sobre ingresos de ${peso(d.ingresos)}${d.margen != null ? ` (${pct(d.margen)} de margen)` : ""}.</p>
    ${a ? `<p><b>Lo más importante:</b> ${esc(a.titulo)}. ${esc(a.accion || a.detalle)}</p>` : ""}</div>`;
}

function renderKpis(d) {
  const imp = d.impuestos;
  const dias = E.saldo != null && E.gasto_diario ? E.saldo / E.gasto_diario : null;
  const k = [
    ["Ingresos", peso(d.ingresos), "Lo que vendiste, sin IVA", ""],
    ["Gastos de operación", peso(d.gastos), d.ingresos ? pct(d.gastos / d.ingresos) + " de tus ingresos" : "", ""],
    ["Utilidad", peso(d.utilidad), d.margen != null ? pct(d.margen) + " de margen" : "", d.utilidad < 0 ? "crit" : d.margen < 0.1 ? "warn" : "good"],
    ["Punto de equilibrio", d.equilibrio ? peso(d.equilibrio) : "—", "Lo mínimo que debes vender al mes", d.equilibrio && d.ingresos < d.equilibrio ? "crit" : ""],
    ["Dinero en el banco", E.saldo != null ? peso(E.saldo) : "—", dias != null ? `Cubre ${Math.max(0, Math.round(dias))} día${Math.round(dias) === 1 ? "" : "s"} de pagos` : "Sube un PDF para ver tu saldo", dias != null && dias < 15 ? "crit" : dias != null && dias < 30 ? "warn" : ""],
    ["Aparta para el SAT", imp.definido ? peso(imp.total) : "—", imp.definido ? `ISR ${peso(imp.isr)} + IVA ${peso(imp.iva)}` : "Contesta tu régimen fiscal", ""],
  ];
  $("#kpis").innerHTML = k.map(([l, v, s, c]) => `<div class="kpi ${c}"><span class="l">${l}</span><span class="v">${v}</span><span class="s">${esc(s)}</span></div>`).join("");
}

function renderAlertas() {
  const ic = { rojo: "!", ambar: "!", verde: "✓", info: "i" };
  $("#alertas").innerHTML = E.alertas.map((a) => `<div class="alert ${a.nivel}"><span class="ic">${ic[a.nivel]}</span><div>
    <b>${esc(a.titulo)}</b><div class="d">${esc(a.detalle)}</div>${a.accion ? `<div class="a">→ ${esc(a.accion)}</div>` : ""}</div></div>`).join("");
}

function renderPreguntas() {
  const qs = E.preguntas;
  const n = qs.filter((q) => q.tipo !== "info").length;
  $("#nq").textContent = n || "";
  if (!qs.length) { $("#preguntas").innerHTML = `<div class="done">✓ Ya entendí todo tu mes. Si algo cambia, te aviso.</div>`; return; }
  $("#preguntas").innerHTML = qs.map((q) => {
    let cuerpo = "";
    if (q.entrada) cuerpo = `<form class="entrada" data-id="${esc(q.id)}"><input name="v" type="${q.entrada === "numero" ? "number" : "text"}" ${q.entrada === "numero" ? 'min="0" step="100"' : ""} required aria-label="${esc(q.titulo)}"><button class="btn primary">Guardar</button></form>`;
    else if (q.opciones.length) cuerpo = `<div class="opts">${q.opciones.map((o) => `<button class="opt" data-id="${esc(q.id)}" data-v="${esc(o.valor)}">${esc(o.label)}</button>`).join("")}</div>`;
    return `<div class="q ${q.tipo === "info" ? "info" : ""}"><b>${esc(q.titulo)}</b><div class="d">${esc(q.detalle || "")}</div>${cuerpo}</div>`;
  }).join("");
  document.querySelectorAll(".opt").forEach((b) => b.addEventListener("click", () => responder(b.dataset.id, b.dataset.v, b)));
  document.querySelectorAll("form.entrada").forEach((f) => f.addEventListener("submit", (e) => { e.preventDefault(); responder(f.dataset.id, f.v.value, f); }));
}
async function responder(id, valor, el) {
  el.closest(".q").style.opacity = .45;
  try { await post("/api/responder", { id, valor }); toast("Anotado. Recalculando tu tablero…"); await cargar(); }
  catch (e) { el.closest(".q").style.opacity = 1; toast(e.message, 5000); }
}

// ---------------------------------------------------------------- graficas (SVG sin librerias)
function el(t, a, p) { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; }
function txt(p, x, y, s, a = {}) { const t = el("text", Object.assign({ x, y }, a), p); t.textContent = s; return t; }
const tip = $("#tip");
function hover(g, h) {
  g.addEventListener("mousemove", (ev) => { tip.innerHTML = h; tip.hidden = false; tip.style.left = Math.min(ev.clientX + 14, innerWidth - tip.offsetWidth - 8) + "px"; tip.style.top = ev.clientY + 14 + "px"; });
  g.addEventListener("mouseleave", () => (tip.hidden = true));
}
function vbar(x, y, w, h, r = 4) { r = Math.min(r, h / 2, w / 2); return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`; }
function hbar(x, y, w, h, r = 4) { r = Math.min(r, h / 2, w / 2); return `M${x},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h - r}Q${x + w},${y + h} ${x + w - r},${y + h}H${x}Z`; }
function escala(lo, hi) { const span = hi - lo || 1; const mag = Math.pow(10, Math.floor(Math.log10(span))); const step = span / mag > 5 ? mag : span / mag > 2 ? mag / 2 : mag / 5; return step; }
const corto = (v) => (Math.abs(v) >= 1e6 ? (v / 1e6).toFixed(1) + "M" : Math.abs(v) >= 1000 ? Math.round(v / 1000) + "k" : Math.round(v));

function renderCascada(d) {
  const gastos = d.lineas.filter((l) => !["ventas", "otros_ingresos"].includes(l.seccion) && l.monto > 0).sort((a, b) => b.monto - a.monto);
  const top = gastos.slice(0, 4), resto = gastos.slice(4).reduce((s, l) => s + l.monto, 0);
  const S = [["Ingresos", d.ingresos, "t"], ...top.map((l) => [l.label, l.monto, "d"])];
  if (resto > 0.5) S.push(["Otros gastos", resto, "d"]);
  S.push(["Utilidad", d.utilidad, "t"]);
  const c100 = d.ingresos ? d.utilidad / d.ingresos * 100 : 0;
  $("#t-cascada").innerHTML = !d.ingresos ? "" : c100 >= 0 ? `De cada <b>$100</b> que entran te quedan <b>$${c100.toFixed(2)}</b>.` : `De cada <b>$100</b> que entran <b>pierdes $${(-c100).toFixed(2)}</b>.`;
  const box = $("#cascada"); box.innerHTML = "";
  const W = 1100, H = 320, L = 62, R = 10, T = 26, B = 50, pw = W - L - R, ph = H - T - B;
  let rr = 0; const runs = S.map(([, v, k]) => (rr = k === "t" ? v : rr - v));
  const hi = Math.max(...S.map((s) => Math.abs(s[1])), 1) * 1.1, lo = Math.min(0, ...runs) * 1.15;
  const y = (v) => T + ph - ((v - lo) / (hi - lo)) * ph;
  const s = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Cascada de ingresos a utilidad" }, box);
  const st = escala(lo, hi);
  for (let g = Math.ceil(lo / st) * st; g <= hi; g += st) { el("line", { x1: L, x2: W - R, y1: y(g), y2: y(g), class: "gl" }, s); txt(s, L - 8, y(g) + 4, corto(g), { "text-anchor": "end" }); }
  const bw = pw / S.length; let run = 0;
  S.forEach(([n, v, k], i) => {
    let top, bot; if (k === "t") { top = Math.max(v, 0); bot = Math.min(v, 0); run = v; } else { top = run; bot = run - v; run = bot; }
    const x = L + i * bw + bw * 0.18, w = bw * 0.64, g = el("g", {}, s);
    el("path", { d: vbar(x, y(top), w, Math.max(1, y(bot) - y(top))), fill: k === "t" ? (v < 0 ? "var(--crit)" : "var(--s1)") : "var(--s2)" }, g);
    el("rect", { x: L + i * bw, y: T, width: bw, height: ph, fill: "transparent" }, g);
    txt(g, x + w / 2, y(top) - 8, (k === "t" ? "" : "−") + peso(Math.abs(v)).replace("−", ""), { "text-anchor": "middle", class: "val" });
    txt(g, x + w / 2, H - B + 18, n.length > 20 ? n.slice(0, 19) + "…" : n, { "text-anchor": "middle" });
    if (d.ingresos) txt(g, x + w / 2, H - B + 34, pct((k === "t" ? v : Math.abs(v)) / d.ingresos), { "text-anchor": "middle" });
    hover(g, `<b>${esc(n)}</b><br>${peso(v)}${d.ingresos ? " · " + pct(Math.abs(v) / d.ingresos) + " de tus ingresos" : ""}`);
  });
  el("line", { x1: L, x2: W - R, y1: y(0), y2: y(0), class: "axis" }, s);
}

function renderTendencia() {
  const T0 = E.tendencia; $("#card-tendencia").hidden = T0.length < 2; if (T0.length < 2) return;
  const box = $("#tendencia"); box.innerHTML = "";
  const W = 1100, H = 300, L = 62, R = 10, T = 20, B = 40, pw = W - L - R, ph = H - T - B;
  const hi = Math.max(...T0.map((t) => Math.max(t.ingresos, t.gastos)), 1) * 1.1, lo = Math.min(0, ...T0.map((t) => t.utilidad)) * 1.15;
  const y = (v) => T + ph - ((v - lo) / (hi - lo)) * ph;
  const s = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Ingresos, gastos y utilidad por mes" }, box);
  const st = escala(lo, hi);
  for (let g = Math.ceil(lo / st) * st; g <= hi; g += st) { el("line", { x1: L, x2: W - R, y1: y(g), y2: y(g), class: "gl" }, s); txt(s, L - 8, y(g) + 4, corto(g), { "text-anchor": "end" }); }
  const gw = pw / T0.length, bw = Math.min(46, gw * 0.3);
  const pts = [];
  T0.forEach((t, i) => {
    const cx = L + gw * i + gw / 2, g = el("g", {}, s);
    el("path", { d: vbar(cx - bw - 1, y(t.ingresos), bw, y(0) - y(t.ingresos)), fill: "var(--s1)" }, g);
    el("path", { d: vbar(cx + 1, y(t.gastos), bw, y(0) - y(t.gastos)), fill: "var(--s2)" }, g);
    el("rect", { x: L + gw * i, y: T, width: gw, height: ph, fill: "transparent" }, g);
    txt(g, cx, H - B + 20, t.nombre, { "text-anchor": "middle" });
    hover(g, `<b>${esc(t.nombre)}</b><br>Ingresos ${peso(t.ingresos)}<br>Gastos ${peso(t.gastos)}<br>Utilidad ${peso(t.utilidad)}`);
    pts.push([cx, y(t.utilidad)]);
  });
  el("polyline", { points: pts.map((p) => p.join(",")).join(" "), fill: "none", stroke: "var(--ink)", "stroke-width": 2 }, s);
  pts.forEach(([x, yy], i) => { el("circle", { cx: x, cy: yy, r: 5, fill: "var(--ink)", stroke: "var(--panel)", "stroke-width": 2 }, s); if (i === pts.length - 1) txt(s, x + 8, yy - 8, peso(T0[i].utilidad), { class: "val" }); });
  el("line", { x1: L, x2: W - R, y1: y(0), y2: y(0), class: "axis" }, s);
}

function renderBarras(sel, data, color) {
  const box = $(sel); box.innerHTML = "";
  if (!data.length) { box.innerHTML = '<p class="note">Sin datos este mes.</p>'; return; }
  const W = 560, rowH = 30, L = 200, R = 92, T = 4, H = T + data.length * rowH + 4, max = Math.max(...data.map((d) => d.monto)) * 1.04, pw = W - L - R;
  const s = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img" }, box);
  data.forEach((d, i) => {
    const g = el("g", {}, s), yy = T + i * rowH, bh = rowH * 0.56, w = Math.max(2, (d.monto / max) * pw);
    el("rect", { x: 0, y: yy, width: W, height: rowH, fill: "transparent" }, g);
    txt(g, L - 10, yy + rowH / 2 + 4, d.nombre.length > 28 ? d.nombre.slice(0, 27) + "…" : d.nombre, { "text-anchor": "end" });
    el("path", { d: hbar(L, yy + (rowH - bh) / 2, w, bh), fill: d.nombre.startsWith("Sin identificar") ? "var(--crit)" : color }, g);
    txt(g, L + w + 8, yy + rowH / 2 + 4, peso(d.monto), { class: "val" });
    hover(g, `<b>${esc(d.nombre)}</b><br>${peso(d.monto)}`);
  });
  el("line", { x1: L, x2: L, y1: T, y2: H - 4, class: "axis" }, s);
}

// ---------------------------------------------------------------- tablas
function renderER(d) {
  const secs = [["Ingresos", ["ventas", "otros_ingresos"], 1], ["Costo directo", ["costo"], -1], ["Gastos de venta", ["gasto_venta"], -1], ["Gastos de administración", ["gasto_admin"], -1], ["Por identificar (los cuento como gasto)", ["sin_identificar"], -1]];
  const row = (n, v, cls = "ind") => `<tr class="${cls}"><td>${esc(n)}</td><td class="n ${v < 0 && cls === "tot" ? "neg" : ""}">${peso(v)}</td><td class="n">${d.ingresos ? pct(Math.abs(v) / d.ingresos) : ""}</td></tr>`;
  let h = '<table><tr><th>Concepto</th><th class="n">Monto</th><th class="n">% ingresos</th></tr>';
  for (const [t, ss, sg] of secs) {
    const ls = d.lineas.filter((l) => ss.includes(l.seccion));
    if (!ls.length) continue;
    h += `<tr class="sec"><td colspan="3">${t}</td></tr>` + ls.map((l) => row(l.label, sg * l.monto)).join("");
    if (t === "Ingresos") h += row("Total ingresos", d.ingresos, "tot");
  }
  h += row("Gastos de operación", -d.gastos, "tot") + row("UTILIDAD DE OPERACIÓN", d.utilidad, "tot");
  if (d.debajo.length) h += `<tr class="sec"><td colspan="3">Debajo de la línea (no cambian tu utilidad)</td></tr>` + d.debajo.map((l) => row(l.label, l.monto)).join("");
  $("#er").innerHTML = h + "</table>";
  $("#t-er").textContent = "Ingresos y gastos sin IVA. Tarjetas, créditos, impuestos, préstamos y gastos personales van aparte: no son gasto de la operación.";
}

function renderMovs() {
  if (!E || !E.movimientos) return;
  let ms = E.movimientos.filter((m) => m.mes === mesSel);
  if (buscar) ms = ms.filter((m) => (m.descripcion + " " + m.contraparte + " " + m.etiqueta).toLowerCase().includes(buscar));
  const ops = Object.entries(E.categorias).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("");
  const chip = (r) => r === "tuya" || r.startsWith("tu respuesta") ? '<span class="chip tuya">tú</span>' : r === "sin regla" || r === "supuesto" ? `<span class="chip sin">${r === "supuesto" ? "supuesto" : "sin identificar"}</span>` : '<span class="chip">auto</span>';
  $("#movs").innerHTML = `<table><tr><th>Fecha</th><th>Contraparte</th><th class="n">Entra</th><th class="n">Sale</th><th>Categoría</th></tr>` +
    ms.slice(0, 300).map((m) => `<tr><td>${esc(m.fecha)}</td><td>${esc(m.contraparte)}<div class="note" style="margin:0">${esc(m.descripcion.slice(0, 70))}</div></td>
      <td class="n pos">${m.abono ? peso(m.abono) : ""}</td><td class="n">${m.cargo ? peso(m.cargo) : ""}</td>
      <td><select data-id="${m.id}" aria-label="Categoría">${ops.replace(`value="${m.categoria}"`, `value="${m.categoria}" selected`)}</select> ${chip(m.regla)}</td></tr>`).join("") +
    (ms.length > 300 ? `<tr><td colspan="5" class="note">Mostrando 300 de ${ms.length}. Usa el buscador.</td></tr>` : "") + "</table>";
  document.querySelectorAll("#movs select").forEach((s) => s.addEventListener("change", async () => {
    try { await post("/api/reclasificar", { id: s.dataset.id, categoria: s.value }); toast("Cambiado. Recalculando…"); await cargar(); } catch (e) { toast(e.message); }
  }));
}

function renderArchivos() {
  $("#archivos").innerHTML = E.archivos.map((f) => {
    const v = f.validacion;
    return `<div class="file"><div><b>${esc(f.nombre)}</b><div class="note" style="margin:0">${esc(f.banco)} · ${esc(f.periodo)} · ${f.movimientos} movimientos${f.saldo_final != null ? " · saldo " + peso(f.saldo_final) : ""}</div></div>
      <div><span class="${v.ok ? "ok" : v.ok === false ? "bad" : ""}">${v.ok ? "✓" : v.ok === false ? "✗" : "·"} ${esc(v.texto)}</span> <button class="link" data-n="${esc(f.nombre)}">Quitar</button></div></div>`;
  }).join("") + (E.errores || []).map((x) => `<div class="file"><b>${esc(x.archivo)}</b><span class="bad">✗ ${esc(x.error)}</span></div>`).join("");
  document.querySelectorAll("#archivos .link").forEach((b) => b.addEventListener("click", async () => { await post("/api/quitar_archivo", { nombre: b.dataset.n }); toast("Archivo quitado."); await cargar(); }));
  $("#supuestos").textContent = (E.supuestos || []).join(" ");
}

cargar().then(vigilar);
