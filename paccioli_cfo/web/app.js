// Paccioli CFO · tablero en vivo. Pregunta al servidor local cada 2 s si hubo cambios.
"use strict";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
// dinero en la moneda de tu pais (MXN, COP, PEN, EUR...) con el formato de tu pais
let FMT = null;
const peso = (v) => {
  if (!FMT) {
    const c = (E && E.contexto) || {};
    try { FMT = new Intl.NumberFormat(c.locale || "es-MX", { style: "currency", currency: c.moneda || "MXN", maximumFractionDigits: 0, minimumFractionDigits: 0 }); }
    catch (e) { FMT = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 }); }
  }
  return (v < 0 ? "−" : "") + FMT.format(Math.abs(Math.round(v)));
};
const simb = () => (E && E.contexto && E.contexto.simbolo) || "$";
// textos segun quien lo usa: negocio, independiente o finanzas personales
function T() {
  const c = (E && E.contexto) || {}, u = c.uso || "negocio", per = u === "personal", ind = u === "independiente";
  const imp = c.impuesto || "IVA", aut = c.autoridad || "el SAT";
  return {
    per, ind, imp, aut,
    titulo: per ? (E.negocio && E.negocio !== "Tus Finanzas" ? "¿Cómo van las finanzas de " + E.negocio + "?" : "¿Cómo van tus finanzas?") : "¿Cómo le fue a " + E.negocio + "?",
    big: per ? "Lo que te sobró" : "Lo que te quedó",
    vendes: per ? "te entran" : ind ? "cobras" : "vendes",
    k1: per ? "Te entró" : ind ? "Cobraste" : "Vendiste",
    k1s: per || !c.tasa ? "En el periodo" : "Sin " + imp,
    deLo: per ? " de lo que te entró" : ind ? " de lo que cobraste" : " de lo que vendiste",
    rent: per ? "Ahorro" : "Rentabilidad", meta: per ? 0.2 : 0.15,
    tend: per ? "Tendencia de ingresos" : "Tendencia de ventas",
    sano: per ? "Tus finanzas están sanas. Cuida que sigan así." : "Tu negocio está sano. Cuida que siga así.",
  };
}
const pct = (v) => (v == null ? "—" : (v * 100).toFixed(1) + "%");
const NS = "http://www.w3.org/2000/svg";

let E = null, version = null, mesSel = null, buscar = "";
// archivo exportado (python -m paccioli_cfo exportar): los datos vienen dentro, sin servidor
const ESTATICO = !!window.__ESTADO__;
const lucca = (pose) => (window.__LUCCA__ && window.__LUCCA__[pose]) || "/lucca/lucca-" + pose + ".png";

// ---------------------------------------------------------------- datos
async function cargar() {
  if (ESTATICO) { E = window.__ESTADO__; FMT = null; mesSel = mesSel || E.mes_actual; render(); vivo(true); return; }
  try {
    const r = await fetch("/api/estado", { cache: "no-store" });
    E = await r.json();
    FMT = null;
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
  l.lastChild.textContent = ESTATICO ? "Tablero del " + (E && E.actualizado ? E.actualizado.slice(0, 10) : "") : ok ? (E && E.actualizado ? "En vivo · " + E.actualizado.slice(11, 19) : "En vivo") : "Sin conexión con el servidor";
}
async function post(url, body) {
  if (ESTATICO) throw new Error("Este tablero es un archivo: para contestar, ábrelo en Paccioli CFO o díselo a Claude.");
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
const espera = (ms) => new Promise((r) => setTimeout(r, ms));
// pantalla de carga con Lucca: avanza los pasos mientras el servidor lee los archivos
async function pasosCarga(trabajo) {
  const lis = [...document.querySelectorAll("#pasos li")];
  lis.forEach((l) => (l.className = ""));
  $("#cargando").hidden = false;
  let listo = false, error = null;
  trabajo.then(() => (listo = true), (e) => { error = e; listo = true; });
  for (let i = 0; i < lis.length; i++) {
    lis[i].className = "activo";
    await espera(850);
    while (i === lis.length - 1 && !listo) await espera(150);
    if (error) break;
    lis[i].className = "hecho";
  }
  await espera(error ? 0 : 450);
  $("#cargando").hidden = true;
  if (error) throw error;
}
async function subir(files) {
  if (!files.length) return;
  const trabajo = (async () => {
    for (const f of files) {
      const r = await fetch("/api/subir?nombre=" + encodeURIComponent(f.name), { method: "POST", body: f });
      const j = await r.json();
      if (!j.ok) throw new Error(f.name + ": " + j.error);
    }
    await cargar();
  })();
  try { await pasosCarga(trabajo); } catch (e) { toast("No pude leer " + e.message, 6000); return; }
  vista = "resumen"; mostrarVista(); window.scrollTo({ top: 0, behavior: "smooth" });
  toast("Listo. Ya leí tu estado de cuenta.");
}
let vista = "resumen";
function mostrarVista() {
  document.querySelectorAll(".vista").forEach((b) => b.setAttribute("aria-selected", b.dataset.v === vista));
  $("#v-resumen").hidden = vista !== "resumen"; $("#v-detalle").hidden = vista !== "detalle";
}
document.querySelectorAll(".vista").forEach((b) => b.addEventListener("click", () => { vista = b.dataset.v; mostrarVista(); }));
$("#archivo").addEventListener("change", (e) => { subir([...e.target.files]); e.target.value = ""; });
let arrastre = 0;
window.addEventListener("dragenter", (e) => { e.preventDefault(); if (ESTATICO) return; arrastre++; $("#overlay").hidden = false; });
window.addEventListener("dragleave", () => { if (--arrastre <= 0) { arrastre = 0; $("#overlay").hidden = true; } });
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => { e.preventDefault(); if (ESTATICO) return; arrastre = 0; $("#overlay").hidden = true; subir([...e.dataTransfer.files]); });
$("#imprimir").addEventListener("click", () => window.print());
$("#buscar").addEventListener("input", (e) => { buscar = e.target.value.toLowerCase(); renderMovs(); });

// ---------------------------------------------------------------- render
function render() {
  if (E.error) { $("#vacio").hidden = false; $("#contenido").hidden = true; $(".empty-card h1").textContent = "Algo falló al leer tus archivos"; $(".empty-card .sub").textContent = E.error; return; }
  $("#ver").textContent = "v" + (E.app || "");
  $("#carpeta").textContent = E.carpeta ? "…/" + E.carpeta.split(/[\\/]/).filter(Boolean).slice(-2).join("/") : "mis-estados-de-cuenta";
  $("#carpeta").title = E.carpeta || "";
  const hay = E.meses && E.meses.length;
  $("#vacio").hidden = !!hay; $("#contenido").hidden = !hay;
  if (!hay) { if (E.errores && E.errores.length) toast(E.errores[0].error, 7000); return; }
  const d = E.por_mes[mesSel];
  const nombreMes = E.meses.find((m) => m.mes === mesSel).nombre;
  $("#periodo").textContent = d.es_periodo ? `Periodo de tu estado de cuenta · ${nombreMes} (${d.dias} días)` : "Cierre de " + nombreMes + (d.parcial ? ` · mes incompleto (${d.dias} días)` : "");
  $("#titulo").textContent = T().titulo;
  aplicarMarca(); textosUso();
  $("#meses").innerHTML = E.meses.map((m) => `<button class="month" role="tab" aria-selected="${m.mes === mesSel}" data-m="${m.mes}">${esc(m.nombre)}${E.por_mes[m.mes].parcial ? "<small>parcial</small>" : m.periodo ? "<small>periodo</small>" : ""}</button>`).join("");
  document.querySelectorAll(".month").forEach((b) => b.addEventListener("click", () => { mesSel = b.dataset.m; render(); }));
  const prev = mesAnterior();
  renderVeredicto(d, prev); renderSalud(d, prev); renderKpis(d, prev); renderAlertas(); renderPreguntas(); renderSim(d);
  renderCascada(d); renderTendencia(); renderBarras("#clientes", d.clientes.slice(0, 10), "var(--s1)");
  renderBarras("#gastos", d.gastos_categoria.slice(0, 12), "var(--s2)"); renderKaptal(d); renderER(d); renderMovs(); renderArchivos();
}

const ORDEN = ["rojo", "ambar", "verde", "info"];
const porNivel = (xs) => [...xs].sort((x, y) => ORDEN.indexOf(x.nivel) - ORDEN.indexOf(y.nivel));
const enMes = (m) => {
  const d = E.por_mes[mesSel];
  return d && d.es_periodo ? m.fecha >= d.desde && m.fecha <= d.hasta : m.mes === mesSel;
};
function mesAnterior() {
  if (E.por_mes[mesSel] && E.por_mes[mesSel].es_periodo) return null;
  const i = E.meses.findIndex((m) => m.mes === mesSel);
  return i > 0 ? E.por_mes[E.meses[i - 1].mes] : null;
}
// cambio contra el mes anterior; "bueno" dice si subir es buena noticia
function delta(actual, antes, bueno = true) {
  if (antes == null || actual == null || !antes) return "";
  const c = (actual - antes) / Math.abs(antes);
  if (Math.abs(c) < 0.005) return `<span class="delta flat">= vs mes ant.</span>`;
  const sube = c > 0, cls = sube === bueno ? "up" : "down";
  return `<span class="delta ${cls}" title="Contra el mes anterior">${sube ? "▲" : "▼"} ${Math.abs(c * 100).toFixed(Math.abs(c) < 0.1 ? 1 : 0)}%</span>`;
}

function renderVeredicto(d, prev) {
  const a = porNivel(E.alertas)[0];
  const nivel = a ? a.nivel : "info";
  const txt = { rojo: "Semáforo rojo", ambar: "Semáforo ámbar", verde: "Semáforo verde", info: "Tu resumen" }[nivel];
  const ut = d.utilidad;
  $("#big").textContent = peso(ut);
  $(".big-l").textContent = T().big + (d.es_periodo ? " en el periodo" : " este mes");
  $("#big").classList.toggle("neg", ut < 0);
  const c100 = d.ingresos ? (ut / d.ingresos) * 100 : null;
  $("#big-s").innerHTML = `${c100 != null ? `De cada <b>${simb()}100</b> que ${T().vendes} ${c100 >= 0 ? `te quedan <b>${simb()}${c100.toFixed(2)}</b>` : `<b>pierdes ${simb()}${(-c100).toFixed(2)}</b>`}` : ""} ${delta(ut, prev && prev.utilidad)}`;
  $("#veredicto").className = "bubble " + nivel;
  $("#veredicto").innerHTML = `<span class="tag">${txt}</span>
    ${a ? `<p><b>${esc(a.titulo)}.</b> ${esc(a.accion || a.detalle)}</p>` : `<p>${ut >= 0 ? "Te quedaron" : "Te faltaron"} <b>${peso(Math.abs(ut))}</b> de ${peso(d.ingresos)}.</p>`}`;
  $("#lucca-hero").src = lucca(nivel === "verde" || nivel === "info" ? "pulgar" : nivel === "rojo" ? "libreta" : "cafe");
}

// ---------------------------------------------------------------- salud financiera (0-100)
function salud(d, prev) {
  const lim = (x) => Math.max(0, Math.min(100, x));
  const dias = E.saldo != null && E.gasto_diario ? E.saldo / E.gasto_diario : null;
  const sinId = d.lineas.filter((l) => l.seccion === "sin_identificar").reduce((s, l) => s + l.monto, 0);
  const f = [
    [T().rent, d.utilidad <= 0 ? 0 : lim(((d.margen || 0) / T().meta) * 100), d.margen != null ? pct(d.margen) + (T().per ? " ahorrado" : " de margen") : "—"],
    dias != null ? ["Colchón de caja", lim((dias / 30) * 100), Math.max(0, Math.round(dias)) + (Math.round(dias) === 1 ? " día" : " días")] : null,
    ["Claridad de tus números", d.gastos ? lim((1 - sinId / d.gastos / 0.5) * 100) : 100, d.gastos ? pct(sinId / d.gastos) + " sin identificar" : "—"],
    prev && prev.ingresos ? [T().tend, lim((((d.ingresos - prev.ingresos) / prev.ingresos + 0.3) / 0.35) * 100), pct((d.ingresos - prev.ingresos) / prev.ingresos) + " vs mes ant."] : null,
  ].filter(Boolean);
  const score = Math.round(f.reduce((s, x) => s + x[1], 0) / f.length);
  const g = score >= 75 ? ["Sólido", T().sano, "#4fd39b"] : score >= 55 ? ["Estable", "Funciona, pero hay dinero que se te está yendo.", "#03cdd0"]
    : score >= 35 ? ["En riesgo", "Hay focos rojos que conviene atender este mes.", "#ffb648"] : ["Crítico", "Atiende tu plan de acción hoy.", "#ff6b7a"];
  return { score, factores: f, grado: g };
}
function renderSalud(d, prev) {
  const { score, factores, grado } = salud(d, prev);
  const r = 46, cir = 2 * Math.PI * r;
  $("#salud").innerHTML = `<div class="salud-top">
      <div class="ring"><svg viewBox="0 0 112 112" aria-hidden="true"><circle cx="56" cy="56" r="${r}" fill="none" stroke="rgba(255,255,255,.1)" stroke-width="10"/>
        <circle cx="56" cy="56" r="${r}" fill="none" stroke="${grado[2]}" stroke-width="10" stroke-linecap="round" stroke-dasharray="${(cir * score) / 100} ${cir}"/></svg>
        <div class="n"><div><b>${score}</b><span>de 100</span></div></div></div>
      <div><h3>Salud financiera</h3><div class="grado" style="color:${grado[2]}">${grado[0]}</div><div class="gs">${grado[1]}</div></div>
    </div>
    <div class="factores">${factores.map(([n, v, t]) => `<div class="factor ${v < 35 ? "bajo" : v < 65 ? "medio" : ""}"><span>${n}</span><b>${esc(t)}</b><div class="bar"><i style="width:${Math.max(3, v)}%"></i></div></div>`).join("")}</div>`;
}

function spark(serie, color) {
  if (serie.length < 2) return "";
  const W = 84, H = 26, lo = Math.min(...serie), hi = Math.max(...serie), sp = hi - lo || 1;
  const pts = serie.map((v, i) => [(i / (serie.length - 1)) * (W - 4) + 2, H - 3 - ((v - lo) / sp) * (H - 6)]);
  const [lx, ly] = pts[pts.length - 1];
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" aria-hidden="true"><polyline points="${pts.map((p) => p.join(",")).join(" ")}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${lx}" cy="${ly}" r="2.8" fill="${color}"/></svg>`;
}
function renderKpis(d, prev) {
  const imp = d.impuestos;
  const dias = E.saldo != null && E.gasto_diario ? E.saldo / E.gasto_diario : null;
  const hasta = E.tendencia.slice(0, E.tendencia.findIndex((t) => t.mes === mesSel) + 1);
  const serie = (k) => hasta.map((t) => t[k]);
  const k = [
    [T().k1, peso(d.ingresos), T().k1s, "marca", delta(d.ingresos, prev && prev.ingresos), spark(serie("ingresos"), "var(--s1)")],
    ["Gastaste", peso(d.gastos), d.ingresos ? pct(d.gastos / d.ingresos) + T().deLo : "", "", delta(d.gastos, prev && prev.gastos, false), spark(serie("gastos"), "var(--s2)")],
    ["Tienes en el banco", E.saldo != null ? peso(E.saldo) : "—", dias != null ? `Cubre ${Math.max(0, Math.round(dias))} día${Math.round(dias) === 1 ? "" : "s"} de pagos` : "Sube un PDF para ver tu saldo", dias != null && dias < 15 ? "crit" : dias != null && dias < 30 ? "warn" : "good", "", ""],
    T().per
      ? ["Ahorraste", peso(d.utilidad), d.margen != null ? pct(d.margen) + " de lo que te entró" : "", d.utilidad < 0 ? "crit" : d.margen < 0.1 ? "warn" : "good", delta(d.utilidad, prev && prev.utilidad), spark(serie("utilidad"), "var(--ink)")]
      : ["Aparta para " + T().aut, imp.definido ? peso(imp.total) : "—",
         imp.definido ? (imp.solo_consumo ? `${T().imp} por pagar` : `ISR ${peso(imp.isr)} + ${T().imp} ${peso(imp.iva)}`) : (imp.netas ? "Falta tu estado de comisiones" : E.contexto.es_mx ? "Contesta tu régimen fiscal" : "Confírmalo con tu contador"),
         imp.definido ? "warn" : "", "", ""],
  ];
  $("#kpis").innerHTML = k.map(([l, v, s, c, dl, sp]) => `<div class="kpi ${c}"><span class="l">${l}</span><span class="v">${v}</span><span class="s">${esc(s)}</span>${dl || sp ? `<div class="row">${dl || "<span></span>"}${sp}</div>` : ""}</div>`).join("");
}

let todasAlertas = false;
function renderAlertas() {
  const xs = porNivel(E.alertas), ver = todasAlertas ? xs : xs.slice(0, 3);
  $("#alertas").innerHTML = xs.length ? ver.map((a, i) => `<div class="alert ${a.nivel}"><span class="ic">${a.nivel === "verde" ? "✓" : i + 1}</span><div>
    <b>${esc(a.titulo)}</b><div class="d">${esc(a.detalle)}</div>${a.accion ? `<div class="a">→ ${esc(a.accion)}</div>` : ""}</div></div>`).join("")
    + (xs.length > 3 ? `<button class="mas" id="mas-alertas" type="button">${todasAlertas ? "Ver solo las 3 importantes" : `Ver las ${xs.length} cosas que noté`}</button>` : "")
    : `<div class="done">✓ Nada urgente este mes. Sigue así.</div>`;
  const m = $("#mas-alertas"); if (m) m.addEventListener("click", () => { todasAlertas = !todasAlertas; renderAlertas(); });
}

// ---------------------------------------------------------------- simulador "¿y si...?"
const SIM0 = { p: 0, v: 0, g: 0 };
let sim = { ...SIM0 };
const PALANCAS = [
  ["p", "Sube tus precios", "Mismos clientes, mismo volumen, precio más alto.", 0, 30, "%"],
  ["v", "Vende más (o menos)", "Más clientes o más pedidos. Tu costo directo crece igual.", -30, 50, "%"],
  ["g", "Recorta gastos fijos", "Renta, nómina, servicios, suscripciones.", 0, 40, "%"],
];
function simular(d, s) {
  const I = d.ingresos, C = d.costo || 0, F = Math.max(0, d.gastos - C);
  const I2 = I * (1 + s.p / 100) * (1 + s.v / 100), C2 = C * (1 + s.v / 100), F2 = F * (1 - s.g / 100), U2 = I2 - C2 - F2;
  const mc = I2 ? 1 - C2 / I2 : 0;
  return { I: I2, U: U2, m: I2 ? U2 / I2 : null, pe: mc > 0 ? F2 / mc : null, base: { I, C, F } };
}
function renderSim(d) {
  if (!$("#sliders").children.length) {
    $("#sliders").innerHTML = PALANCAS.map(([k, n, h, lo, hi]) => `<div class="sl"><label for="sl-${k}">${n}<output id="o-${k}"></output></label><small>${h}</small>
      <input type="range" id="sl-${k}" min="${lo}" max="${hi}" step="1" value="0"></div>`).join("");
    PALANCAS.forEach(([k]) => $("#sl-" + k).addEventListener("input", (e) => { sim[k] = +e.target.value; pintarSim(); }));
    $("#sim-reset").addEventListener("click", () => { sim = { ...SIM0 }; pintarSim(); });
  }
  pintarSim();
}
function pintarSim() {
  const d = E.por_mes[mesSel];
  PALANCAS.forEach(([k, , , lo, hi, u]) => {
    const r = $("#sl-" + k); r.value = sim[k];
    r.style.setProperty("--p", ((sim[k] - lo) / (hi - lo)) * 100 + "%");
    $("#o-" + k).textContent = (sim[k] > 0 && k === "v" ? "+" : k === "g" && sim[k] ? "−" : k === "p" && sim[k] ? "+" : "") + sim[k] + u;
  });
  const r = simular(d, sim), dif = r.U - d.utilidad;
  const { I, C, F } = r.base;
  const pNec = I ? (C + F) / (0.85 * I) - 1 : null, gNec = F ? 1 - (0.85 * I - C) / F : null;
  const meta = d.margen != null && d.margen >= 0.15 ? `Ya estás arriba de 15% de margen, el nivel de un negocio sano.`
    : `Para llegar a <b>15% de margen</b> necesitas subir precios <b>${pNec != null ? Math.ceil(pNec * 100) + "%" : "—"}</b> o recortar gastos fijos <b>${gNec != null && gNec < 1 ? Math.ceil(gNec * 100) + "%" : "—"}</b> (o una mezcla).`;
  $("#sim-out").innerHTML = `<div><div class="l">Tu utilidad al mes sería</div><div class="nv ${r.U < 0 ? "neg" : ""}">${peso(r.U)}</div></div>
    <div class="dif">${Math.abs(dif) < 1 ? "Mueve las palancas para ver el efecto." : `${dif > 0 ? "<b>+" : "<b>−"}${peso(Math.abs(dif)).replace("−", "")}</b> al mes · <b>${dif > 0 ? "+" : "−"}${peso(Math.abs(dif * 12)).replace("−", "")}</b> al año`}</div>
    <div class="mini"><div><b>${r.m != null ? pct(r.m) : "—"}</b><span>Margen</span></div><div><b>${peso(r.I)}</b><span>Ingresos</span></div><div><b>${r.pe ? peso(r.pe) : "—"}</b><span>Punto de equilibrio</span></div></div>
    <div class="meta">${meta}</div>`;
}

// ---------------------------------------------------------------- marca y asesor (configurables en marca.json)
function aplicarMarca() {
  const m = E.marca || {};
  document.title = m.producto || "Paccioli CFO";
  if (m.logo_url) { $(".logo-img").src = m.logo_url; $(".brand-tag").hidden = true; }
  const c = m.colores || {}, raiz = document.documentElement.style;
  if (c.principal) { raiz.setProperty("--navy", c.principal); raiz.setProperty("--navy-deep", c.principal); }
  if (c.acento) { raiz.setProperty("--cyan", c.acento); raiz.setProperty("--accent", c.acento); raiz.setProperty("--s1", c.acento); }
  if (m.mascota === false) document.querySelectorAll(".mascota").forEach((x) => (x.hidden = true));
  const a = m.asesor || {}, emp = a.empresa || a.nombre;
  $("#pie-marca").innerHTML = emp ? `Hecho${a.hecho_en ? " en " + esc(a.hecho_en) : ""} por ${a.web ? `<a href="${esc(a.web)}" target="_blank" rel="noopener">${esc(emp)}</a>` : esc(emp)} · <strong>${esc(m.producto || "")}</strong>` : `<strong>${esc(m.producto || "")}</strong>`;
  const hay = m.mostrar_asesor !== false && a.nombre && (a.whatsapp || a.correo || a.web);
  $("#asesor").hidden = !hay;
  $("#pie-contacto").innerHTML = !hay ? "" : `¿Dudas o algo más especializado? ${esc(a.nombre)}${a.empresa ? ", " + esc(a.empresa) : ""}: ` +
    [a.whatsapp && `<a href="https://wa.me/${esc(a.whatsapp)}" target="_blank" rel="noopener">WhatsApp ${esc(a.whatsapp_visible || a.whatsapp)}</a>`,
     a.correo && `<a href="mailto:${esc(a.correo)}">${esc(a.correo)}</a>`, !a.whatsapp && !a.correo && a.web && `<a href="${esc(a.web)}" target="_blank" rel="noopener">${esc(a.web)}</a>`].filter(Boolean).join(" · ");
}
function textosUso() {
  const t = T();
  $("#t-pregunta").textContent = t.per ? "Ayúdame a entender tus gastos" : t.ind ? "Ayúdame a entender tu trabajo" : "Ayúdame a entender tu negocio";
  $("#h-clientes").textContent = t.per ? "¿De dónde te entra dinero?" : "¿Quién te paga?";
  $("#t-clientes").textContent = t.per ? "Lo que te entró este mes, por origen." : "Tus clientes y fuentes de ingreso del mes.";
  $(".sim").hidden = t.per;  // las palancas de precio y volumen son de negocio
}
function renderKaptal(d) {
  const m = E.marca || {}, a = m.asesor || {}, t = T();
  if (m.mostrar_asesor === false || !a.nombre) return;
  const nivel = (porNivel(E.alertas)[0] || {}).nivel;
  const quien = [a.nombre, [a.puesto, a.empresa].filter(Boolean).join(" de ")].filter(Boolean).join(", ") + (a.puesto || a.empresa ? "," : "");
  $("#asesor-lema").textContent = `${m.producto || "Paccioli CFO"} te dice qué pasa · ${a.empresa || a.nombre} te ayuda a arreglarlo`;
  const lista = t.per
    ? ["Un plan para salir de deudas y tarjetas.", "Tu presupuesto y tu meta de ahorro, en números reales.", `Tus impuestos en orden con ${t.aut} si tienes ingresos extra.`]
    : ["Revisamos tus números contigo y armamos el plan para subir tu margen.", `Planeación fiscal: pagas lo justo a ${t.aut}, a tiempo y sin sorpresas.`, "Tu contabilidad y declaraciones al día, con contadores de verdad."];
  $("#asesor-lista").innerHTML = lista.map((x) => `<li>${esc(x)}</li>`).join("");
  if (t.per) {
    $("#t-kaptal").textContent = d.utilidad < 0 ? "Este mes gastaste más de lo que te entró. Tiene arreglo." : "¿Quieres que tu dinero rinda más?";
    $("#kaptal-txt").textContent = `${quien} revisa tus números contigo y te arma un plan sencillo.`;
  } else {
    const falta = d.ingresos ? 0.15 * d.ingresos - d.utilidad : 0;
    $("#t-kaptal").textContent = d.utilidad < 0 ? "Estás perdiendo dinero. No lo resuelvas solo."
      : nivel === "rojo" || nivel === "ambar" ? "Funciona, pero te deja poco. Eso se arregla." : "Vas bien. Ahora toca crecer sin pagar de más.";
    $("#kaptal-txt").innerHTML = falta > 0
      ? `Este mes te quedaron ${peso(d.utilidad)} de ${peso(d.ingresos)}. Con un margen sano de 15% serían <b>${peso(falta)} más al mes</b>. ${esc(quien)} revisa estos números contigo y te dice exactamente qué mover.`
      : `Tu margen ya está sano. ${esc(quien)} te ayuda a planear tus impuestos, proyectar tu crecimiento y decidir dónde invertir.`;
  }
  const nombre1 = (a.nombre || "").split(" ")[0];
  const msj = encodeURIComponent(`Hola ${nombre1}, usé ${m.producto || "Paccioli CFO"} y quiero más información.`);
  $("#contacto").innerHTML = `<div class="quien"><b>${esc(a.nombre)}</b><span>${esc([a.puesto, a.empresa].filter(Boolean).join(" · "))}</span></div>
    <p>¿Quieres más información o algo más especializado? Escríbeme directo.</p>
    ${a.whatsapp ? `<a class="btn cta" href="https://wa.me/${esc(a.whatsapp)}?text=${msj}" target="_blank" rel="noopener">WhatsApp · ${esc(a.whatsapp_visible || a.whatsapp)}</a>` : ""}
    ${a.correo ? `<a class="btn ${a.whatsapp ? "cta2" : "cta"}" href="mailto:${esc(a.correo)}?subject=${encodeURIComponent((m.producto || "Paccioli CFO") + ": quiero más información")}">${esc(a.correo)}</a>` : ""}
    ${!a.whatsapp && !a.correo && a.web ? `<a class="btn cta" href="${esc(a.web)}" target="_blank" rel="noopener">Conócenos →</a>` : ""}`;
}

// una pregunta a la vez para no abrumar; "despues" la manda al final de la fila
let saltadas = [], contestadas = 0;
function renderPreguntas() {
  const todas = E.preguntas.filter((q) => q.tipo !== "info");
  const qs = [...todas.filter((q) => !saltadas.includes(q.id)), ...todas.filter((q) => saltadas.includes(q.id))];
  const total = qs.length + contestadas;
  $("#q-prog").innerHTML = qs.length ? `Pregunta ${contestadas + 1} de ${total} · tu respuesta se aplica sola a los movimientos parecidos<div class="prog"><i style="width:${(contestadas / total) * 100}%"></i></div>` : "";
  if (!qs.length) { $("#preguntas").innerHTML = `<div class="done">✓ Ya entendí todo tu mes. Si algo cambia, te aviso.</div>`; return; }
  const q = qs[0];
  let cuerpo = "";
  if (q.entrada) cuerpo = `<form class="entrada" data-id="${esc(q.id)}"><input name="v" type="${q.entrada === "numero" ? "number" : "text"}" ${q.entrada === "numero" ? 'min="0" step="100"' : ""} required aria-label="${esc(q.titulo)}"><button class="btn primary">Guardar</button></form>`;
  else if (q.opciones.length) cuerpo = `<div class="opts">${q.opciones.map((o) => `<button class="opt" data-id="${esc(q.id)}" data-v="${esc(o.valor)}">${esc(o.label)}</button>`).join("")}</div>`;
  $("#preguntas").innerHTML = `<div class="q1"><b>${esc(q.titulo)}</b>${q.detalle ? `<div class="d">${esc(q.detalle)}</div>` : ""}${cuerpo}
    ${qs.length > 1 ? `<button class="mas saltar" type="button">Después te contesto →</button>` : ""}</div>`;
  document.querySelectorAll(".q1 .opt").forEach((b) => b.addEventListener("click", () => responder(b.dataset.id, b.dataset.v, b)));
  document.querySelectorAll(".q1 form.entrada").forEach((f) => f.addEventListener("submit", (e) => { e.preventDefault(); responder(f.dataset.id, f.v.value, f); }));
  const s = $(".q1 .saltar"); if (s) s.addEventListener("click", () => { saltadas = [...saltadas.filter((x) => x !== q.id), q.id]; renderPreguntas(); });
}
async function responder(id, valor, el) {
  const caja = el.closest(".q1"); caja.style.opacity = .45;
  try { await post("/api/responder", { id, valor }); contestadas++; saltadas = saltadas.filter((x) => x !== id); toast("Anotado. Recalculando tu tablero…"); await cargar(); }
  catch (e) { caja.style.opacity = 1; toast(e.message, 5000); }
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
  $("#t-cascada").innerHTML = !d.ingresos ? "" : c100 >= 0 ? `De cada <b>${simb()}100</b> que entran te quedan <b>${simb()}${c100.toFixed(2)}</b>.` : `De cada <b>${simb()}100</b> que entran <b>pierdes ${simb()}${(-c100).toFixed(2)}</b>.`;
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
  const t = T();
  $("#t-er").textContent = t.per ? "Tus ingresos y gastos del mes. Pagos de tarjetas, créditos y traspasos entre tus cuentas van aparte."
    : `Ingresos y gastos${E.contexto && E.contexto.tasa && E.perfil.precios_iva !== "no_cobro" ? " sin " + t.imp : ""}. Tarjetas, créditos, impuestos, préstamos y gastos personales van aparte: no son gasto de la operación.`;
}

function renderMovs() {
  if (!E || !E.movimientos) return;
  let ms = E.movimientos.filter(enMes);
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

if (ESTATICO) {
  document.querySelectorAll('label[for="archivo"], #archivo').forEach((x) => (x.hidden = true));
  cargar();
} else cargar().then(vigilar);
