(function () {
  "use strict";

  const $ = (s) => document.querySelector(s);
  const estado = { datos: null, tab: null, rodado: "todos", marca: "", medida: "", auto: "", q: "", solo: null };
  const RODADOS = [
    { id: "todos", txt: "Todos" },
    { id: "13", txt: "R13" },
    { id: "14", txt: "R14" },
    { id: "15", txt: "R15" },
    { id: "16", txt: "R16" },
    { id: "17+", txt: "R17+" },
  ];
  const ICONO_WA = '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path fill="currentColor" d="M12 2.2A9.8 9.8 0 0 0 3.6 17l-1.4 4.8 4.9-1.3A9.8 9.8 0 1 0 12 2.2Zm0 1.8a8 8 0 1 1-4.1 14.9l-.3-.2-2.9.8.8-2.8-.2-.3A8 8 0 0 1 12 4Zm-3.3 4c-.2 0-.5 0-.7.3-.3.3-1 1-1 2.4s1 2.8 1.2 3c.1.2 2 3.2 5 4.4 2.5 1 3 .8 3.5.7.6 0 1.8-.7 2-1.4.3-.7.3-1.3.2-1.4l-.5-.3-1.8-.9c-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.6.1a6.6 6.6 0 0 1-3.3-2.9c-.2-.4.2-.4.7-1.3.1-.2 0-.3 0-.5l-.8-2c-.2-.5-.4-.4-.6-.4h-.5Z"/></svg>';
  const ICONO_COMPARTIR = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M12 3v12M7 8l5-5 5 5M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const RUEDA = '<svg viewBox="0 0 64 64" width="72" height="72" aria-hidden="true"><circle cx="32" cy="32" r="28" fill="none" stroke="currentColor" stroke-width="7"/><circle cx="32" cy="32" r="12" fill="none" stroke="currentColor" stroke-width="4"/><circle cx="32" cy="32" r="3" fill="currentColor"/></svg>';

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pesos = (n) => "$" + Math.round(n).toLocaleString("es-AR");
  const wa = (texto) => `https://wa.me/${estado.datos.sitio.whatsapp}?text=${encodeURIComponent(texto)}`;

  // "205/55 R16" -> {nums: ["205","55","16"]}; "gol 4x100" -> {nums: ["4","100"], palabras: ["gol"]}
  function analizar(q) {
    const t = q.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    const nums = t.match(/\d+/g) || [];
    const palabras = t.replace(/\d+/g, " ").split(/[^a-zñ]+/).filter((w) => w.length > 1);
    return { nums, palabras };
  }
  // cada número buscado tiene que estar en el producto: "195" trae todas las 195, "15" todas las R15,
  // "195 15" las 195 rodado 15. Un número largo pegado ("1956515") se compara con la medida completa.
  function coincideNum(p, n) {
    const sueltos = p.nums || [];
    if (sueltos.includes(n)) return true;
    if (n.length >= 3 && sueltos.some((k) => k.startsWith(n))) return true;
    return n.length >= 4 && p.claves.some((k) => k.startsWith(n) || k.includes(n));
  }
  function coincide(p, q) {
    if (!q.nums.length && !q.palabras.length) return true;
    if (!q.nums.every((n) => coincideNum(p, n))) return false;
    const texto = p.texto.normalize("NFD").replace(/[̀-ͯ]/g, "");
    return q.palabras.every((w) => texto.includes(w));
  }
  function pasaRodado(p) {
    if (estado.rodado === "todos") return true;
    if (estado.rodado === "17+") return Number(p.rodado) >= 17;
    return String(p.rodado) === estado.rodado;
  }

  function pasaMarca(p) {
    if (!estado.marca) return true;
    const [tipo, m] = [estado.marca.slice(0, 1), estado.marca.slice(2)];
    return (tipo === "l" ? p.marcas_llanta : p.marcas_cubierta).includes(m);
  }
  function pasaMedida(p) {
    return !estado.medida || p.medida_cubierta === estado.medida;
  }
  const pasaAuto = (p) => !estado.auto || p.auto === estado.auto;
  const pasaFiltros = (p) => pasaRodado(p) && pasaMarca(p) && pasaMedida(p) && pasaAuto(p);
  const unicos = (arr) => [...new Set(arr)].sort((a, b) => a.localeCompare(b, "es", { numeric: true }));

  function renderFiltros(base, cat) {
    const ml = unicos(base.flatMap((p) => p.marcas_llanta));
    const mc = cat && cat.id === "llanta" ? [] : unicos(base.flatMap((p) => p.marcas_cubierta));  // en Llantas solo marca de llanta
    const opt = (v, t) => `<option value="${esc(v)}"${v === estado.marca ? " selected" : ""}>${esc(t)}</option>`;
    $("#f-marca").innerHTML = opt("", "Todas") +
      (ml.length ? `<optgroup label="Marca de llanta">${ml.map((m) => opt("l:" + m, m)).join("")}</optgroup>` : "") +
      (mc.length ? `<optgroup label="Marca de cubierta">${mc.map((m) => opt("c:" + m, m)).join("")}</optgroup>` : "");
    const medidas = unicos(base.map((p) => p.medida_cubierta).filter(Boolean));
    $("#f-medida").innerHTML = [`<option value="">Todas</option>`]
      .concat(medidas.map((m) => `<option value="${esc(m)}"${m === estado.medida ? " selected" : ""}>${esc(m)}</option>`)).join("");
    const conMedida = !!(cat && cat.filtro_medida && medidas.length);
    $("#filtro-medida").style.display = conMedida ? "" : "none";
    // pestaña "En autos": filtro por auto (marca + modelo del auto donde están puestas las ruedas)
    const autos = unicos(base.map((p) => p.auto).filter(Boolean));
    const conAuto = !!(cat && cat.filtro_auto && autos.length);
    $("#filtro-auto").style.display = conAuto ? "" : "none";
    $("#f-auto").innerHTML = [`<option value="">Todos</option>`]
      .concat(autos.map((a) => `<option value="${esc(a)}"${a === estado.auto ? " selected" : ""}>${esc(a)}</option>`)).join("");
    $("#f-auto").classList.toggle("activo", !!estado.auto);
    $("#filtros").classList.toggle("uno", !conMedida && !conAuto);
    $("#filtros").classList.toggle("con-auto", conAuto);
    $("#filtros").style.display = ml.length || mc.length || conMedida || conAuto ? "" : "none";
    $("#f-marca").classList.toggle("activo", !!estado.marca);
    $("#f-medida").classList.toggle("activo", !!estado.medida);
  }

  // la pestaña Llantas también muestra las ruedas completas (config "incluye")
  function enPestana(p, tab) {
    if (p.tipo === tab) return true;
    const cat = estado.datos.categorias.find((c) => c.id === tab);
    return !!(cat && cat.incluye && cat.incluye.includes(p.tipo));
  }
  function visibles(tab) {
    const q = analizar(estado.q);
    return estado.datos.productos.filter((p) => enPestana(p, tab) && coincide(p, q));
  }

  // ---------- render ----------
  function renderTabs() {
    // una pestaña sin nada cargado (ej. "En autos" al principio) no se muestra
    const cats = estado.datos.categorias.filter((c) => c.id === estado.tab || estado.datos.productos.some((p) => p.tipo === c.id));
    $("#tabs").innerHTML = cats.map((c) => `
      <button class="tab" role="tab" data-tab="${c.id}" aria-selected="${c.id === estado.tab}">
        ${esc(c.nombre)} <span class="n">(${visibles(c.id).length})</span>
      </button>`).join("");
    const cat = cats.find((c) => c.id === estado.tab);
    const base = visibles(estado.tab);
    renderFiltros(base, cat);
    $("#chips").style.display = cat && cat.filtro_rodado ? "" : "none";
    $("#chips").innerHTML = RODADOS.map((r) => {
      const hay = r.id === "todos" || base.some((p) => (r.id === "17+" ? Number(p.rodado) >= 17 : String(p.rodado) === r.id));
      return `<button class="chip" data-rodado="${r.id}" aria-pressed="${r.id === estado.rodado}" ${hay || r.id === estado.rodado ? "" : "disabled"}>${r.txt}</button>`;
    }).join("");
  }

  function tarjeta(p) {
    const comoLlanta = estado.tab === "llanta" && (p.tipo === "rueda" || p.tipo === "auto") && p.titulo_llanta;  // rueda completa vista en Llantas
    const fotos = p.fotos.length
      ? `<div class="fotos">${p.fotos.map((f, i) => {
          const mini = (p.miniaturas && p.miniaturas[i]) || f;
          return `<img ${i ? "data-src" : "src"}="${esc(mini)}" data-full="${esc(f)}" alt="${esc(p.titulo + " " + p.subtitulo)} — foto ${i + 1}" loading="lazy" decoding="async" onload="this.classList.add('cargada')">`;
        }).join("")}</div>
         ${p.fotos.length > 1 ? `<span class="contador">1/${p.fotos.length}</span>
         <button class="flecha izq" aria-label="Foto anterior"><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></button><button class="flecha der" aria-label="Foto siguiente"><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></button>` : ""}`
      : `<div class="sin-foto">${RUEDA}<span>Foto a confirmar</span></div>`;

    const clase = (p.estado || "").toLowerCase().replace(/\s+/g, "-");
    const estadoHtml = p.estado ? `
      <div class="estado">
        <div class="estado-txt"><strong>Estado: ${esc(p.estado)}</strong>${p.vida != null ? `<span>${p.vida}% de vida</span>` : ""}</div>
        ${p.segmentos != null ? `<div class="segs ${clase}" role="img" aria-label="${p.segmentos} de 5">${[1, 2, 3, 4, 5].map((i) => `<i class="${i <= p.segmentos ? "on" : ""}"></i>`).join("")}</div>` : ""}
      </div>` : "";

    const precio = p.precio_unidad
      ? `<div class="precio-linea"><span class="monto">${pesos(p.precio_unidad)}</span><span class="por">por unidad</span></div>
         ${p.precios_extra.map((x) => `<p class="juego">Precio por ${esc(x.txt)}: <b>${pesos(x.monto)}</b></p>`).join("")}`
      : `<div class="precio-linea"><span class="consultar-precio">Consultar precio</span></div>`;

    return `
    <article class="card${estado.solo === p.id ? " destacada" : ""}" id="${esc(p.id)}">
      <div class="media">
        ${fotos}
        <span class="badge">${esc(p.cantidad_txt)}</span>
      </div>
      <div class="cuerpo">
        <h2>${esc(comoLlanta ? p.titulo_llanta : p.titulo)}</h2>
        <p class="medida">${esc(comoLlanta ? p.subtitulo_llanta : p.subtitulo)}</p>
        ${estadoHtml}
        ${p.etiquetas.length ? `<ul class="tags">${p.etiquetas.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` : ""}
        ${p.sirve ? `<p class="sirve"><b>Sirve para:</b> ${esc(p.sirve)}</p>` : ""}
        ${p.tipo === "llanta" || p.tipo === "rueda" ? `<p class="detalle">¿No sabés si le va a tu auto? Consultanos con el modelo y el año.</p>` : ""}
        ${p.detalle ? `<p class="detalle">${esc(p.detalle)}</p>` : ""}
        <div class="precio">${precio}</div>
        <a class="btn btn-wa" href="${wa(p.wa)}" target="_blank" rel="noopener">${ICONO_WA}Consultar por WhatsApp</a>
        <button class="btn btn-compartir" data-compartir="${esc(p.id)}">${ICONO_COMPARTIR}Compartir</button>
      </div>
    </article>`;
  }

  function vacio() {
    const cat = estado.datos.categorias.find((c) => c.id === estado.tab);
    const q = estado.q.trim();
    const texto = q ? `Hola, estoy buscando ${cat.plural} ${q}. ¿Tienen o les puede entrar?` : `Hola, estoy buscando ${cat.plural}. ¿Qué tienen disponible?`;
    return `<div class="vacio">
      <h2>${q ? `No tenemos ${esc(q)} ahora` : `Sin ${esc(cat.plural)} por ahora`}</h2>
      <p>Escribinos y te avisamos apenas entre${q ? " esa medida" : ""}.</p>
      <a class="btn btn-wa" href="${wa(texto)}" target="_blank" rel="noopener">${ICONO_WA}Consultar por WhatsApp</a>
    </div>`;
  }

  function render() {
    renderTabs();
    let lista;
    if (estado.solo) {
      const p = estado.datos.productos.find((x) => x.id === estado.solo);
      $("#aviso").innerHTML = `<div class="aviso"><p>${p ? "Te compartieron este producto" : "Ese producto ya se vendió 🙌 Mirá el resto del stock."}</p><button class="link-btn" data-ver-todo>Ver todo el stock</button></div>`;
      lista = p ? [p] : [];
      if (!p) { estado.solo = null; return render(); }
    } else {
      $("#aviso").innerHTML = "";
      lista = visibles(estado.tab).filter(pasaFiltros);
    }
    estado.lista = lista;
    estado.mostrados = Math.min(POR_TANDA, lista.length);
    $("#lista").innerHTML = lista.length ? lista.slice(0, estado.mostrados).map(tarjeta).join("") + botonMas() : vacio();
    observarMas();
  }

  // ---------- de a tandas: en el celular 300+ tarjetas juntas colgaban la página ----------
  const POR_TANDA = 24;
  function botonMas() {
    const faltan = estado.lista.length - estado.mostrados;
    return faltan > 0 ? `<div class="mas"><button class="btn btn-mas" data-ver-mas>Ver más (${faltan})</button></div>` : "";
  }
  function verMas() {
    const viejo = $("#lista .mas");
    if (!viejo) return;
    const desde = estado.mostrados;
    estado.mostrados = Math.min(desde + POR_TANDA, estado.lista.length);
    viejo.insertAdjacentHTML("beforebegin", estado.lista.slice(desde, estado.mostrados).map(tarjeta).join(""));
    viejo.outerHTML = botonMas();
    observarMas();
  }
  let obsMas = null;
  function observarMas() {
    if (!("IntersectionObserver" in window)) return;  // sin soporte: queda el botón "Ver más"
    if (obsMas) obsMas.disconnect();
    const b = $("#lista .mas");
    if (!b) return;
    obsMas = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) verMas(); }, { rootMargin: "600px 0px" });
    obsMas.observe(b);
  }
  // fotos 2, 3... de una tarjeta: se descargan recién cuando el cliente desliza o toca la flecha
  function cargarResto(f) {
    f.querySelectorAll("img[data-src]").forEach((im) => { im.src = im.dataset.src; im.removeAttribute("data-src"); });
  }

  // ---------- eventos ----------
  function avisar(txt) {
    const t = document.createElement("div");
    t.className = "toast"; t.textContent = txt;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2200);
  }

  document.addEventListener("click", async (e) => {
    const tab = e.target.closest("[data-tab]");
    if (tab) { estado.tab = tab.dataset.tab; estado.rodado = "todos"; estado.marca = ""; estado.medida = ""; estado.auto = ""; estado.solo = null; return render(); }
    const chip = e.target.closest("[data-rodado]");
    if (chip) { estado.rodado = chip.dataset.rodado; return render(); }
    if (e.target.closest("[data-ver-todo]")) {
      estado.solo = null; history.replaceState(null, "", location.pathname); return render();
    }
    const foto = e.target.closest(".fotos img");
    if (foto) { abrirVisor(foto); return; }
    if (e.target.closest("[data-ver-mas]")) return verMas();
    const flecha = e.target.closest(".flecha");
    if (flecha) {
      const f = flecha.parentElement.querySelector(".fotos");
      cargarResto(f);
      f.scrollBy({ left: (flecha.classList.contains("der") ? 1 : -1) * f.clientWidth, behavior: "smooth" });
      return;
    }
    const comp = e.target.closest("[data-compartir]");
    if (comp) {
      const p = estado.datos.productos.find((x) => x.id === comp.dataset.compartir);
      const titulo = `${p.titulo} ${p.subtitulo}`;
      if (navigator.share) {
        try { await navigator.share({ title: titulo, text: titulo, url: p.url }); } catch (_) {}
      } else {
        try { await navigator.clipboard.writeText(p.url); avisar("Link copiado"); }
        catch (_) { window.open(`https://wa.me/?text=${encodeURIComponent(titulo + " " + p.url)}`, "_blank"); }
      }
    }
  });

  // contador de fotos al deslizar
  document.addEventListener("scroll", (e) => {
    const f = e.target;
    if (!(f instanceof Element) || !f.classList.contains("fotos")) return;
    cargarResto(f);
    const c = f.parentElement.querySelector(".contador");
    if (c) c.textContent = `${Math.round(f.scrollLeft / f.clientWidth) + 1}/${f.children.length}`;
  }, true);

  // ---------- visor de fotos en grande (foto completa, sin recortar) ----------
  const visor = document.createElement("div");
  visor.className = "visor";
  visor.hidden = true;
  visor.setAttribute("role", "dialog");
  visor.setAttribute("aria-modal", "true");
  visor.setAttribute("aria-label", "Foto en grande");
  visor.innerHTML = `
    <div class="visor-fotos"></div>
    <button class="visor-cerrar" aria-label="Cerrar"><svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg></button>
    <button class="visor-flecha izq" aria-label="Foto anterior"><svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
    <button class="visor-flecha der" aria-label="Foto siguiente"><svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true"><path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
    <span class="visor-contador"></span>`;
  document.body.appendChild(visor);
  const vFotos = visor.querySelector(".visor-fotos");
  const vCont = visor.querySelector(".visor-contador");
  let vOrigen = null;

  function vIndice() { return Math.round(vFotos.scrollLeft / (vFotos.clientWidth || 1)); }
  function vActualizar() {
    const n = vFotos.children.length, i = vIndice();
    vCont.textContent = n > 1 ? `${i + 1}/${n}` : "";
    visor.querySelector(".izq").hidden = n < 2 || i === 0;
    visor.querySelector(".der").hidden = n < 2 || i === n - 1;
  }
  function vIr(paso) {
    vFotos.scrollBy({ left: paso * vFotos.clientWidth, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }
  function abrirVisor(img) {
    const imgs = [...img.closest(".fotos").querySelectorAll("img")];
    vOrigen = img;
    vFotos.innerHTML = imgs.map((x) => `<div class="visor-item"><img src="${esc(x.dataset.full || x.getAttribute("src") || x.dataset.src)}" alt="${esc(x.alt)}" decoding="async"></div>`).join("");
    visor.hidden = false;
    document.documentElement.classList.add("visor-abierto");
    vFotos.scrollLeft = imgs.indexOf(img) * vFotos.clientWidth;
    vActualizar();
    history.pushState({ visor: true }, "");
    visor.querySelector(".visor-cerrar").focus({ preventScroll: true });
  }
  function cerrarVisor(desdeHistorial) {
    if (visor.hidden) return;
    visor.hidden = true;
    document.documentElement.classList.remove("visor-abierto");
    vFotos.innerHTML = "";
    if (!desdeHistorial && history.state && history.state.visor) history.back();
    if (vOrigen) vOrigen.closest(".media").querySelector(".flecha, .fotos")?.focus?.({ preventScroll: true });
  }
  vFotos.addEventListener("scroll", vActualizar, { passive: true });
  visor.addEventListener("click", (e) => {
    if (e.target.closest(".visor-flecha")) return vIr(e.target.closest(".der") ? 1 : -1);
    if (e.target.closest(".visor-cerrar") || !e.target.closest("img")) cerrarVisor(false);  // tocar afuera de la foto cierra
  });
  document.addEventListener("keydown", (e) => {
    if (visor.hidden) return;
    if (e.key === "Escape") cerrarVisor(false);
    else if (e.key === "ArrowRight") vIr(1);
    else if (e.key === "ArrowLeft") vIr(-1);
  });
  window.addEventListener("popstate", () => cerrarVisor(true));  // botón "atrás" del celular cierra el visor
  window.addEventListener("resize", () => { if (!visor.hidden) vFotos.scrollLeft = vIndice() * vFotos.clientWidth; });

  $("#f-marca").addEventListener("change", (e) => { estado.marca = e.target.value; estado.solo = null; render(); });
  $("#f-medida").addEventListener("change", (e) => { estado.medida = e.target.value; estado.solo = null; render(); });
  $("#f-auto").addEventListener("change", (e) => { estado.auto = e.target.value; estado.solo = null; render(); });

  let espera;
  $("#q").addEventListener("input", (e) => {
    clearTimeout(espera);
    espera = setTimeout(() => { estado.q = e.target.value; estado.solo = null; autoTab(); render(); }, 150);
  });
  $("#buscador").addEventListener("submit", (e) => {
    e.preventDefault();
    estado.q = $("#q").value; estado.solo = null; autoTab(); render();
    $("#q").blur();
    $("#barra").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  });

  // si la búsqueda no da nada en la pestaña actual pero sí en otra, cambia de pestaña
  function autoTab() {
    if (visibles(estado.tab).length) return;
    const otra = estado.datos.categorias.find((c) => visibles(c.id).length);
    if (otra) { estado.tab = otra.id; estado.rodado = "todos"; estado.marca = ""; estado.medida = ""; estado.auto = ""; }
  }

  // ---------- inicio ----------
  fetch("data/productos.json?t=" + Date.now(), { cache: "no-store" })
    .then((r) => r.json())
    .then((d) => {
      estado.datos = d;
      const params = new URLSearchParams(location.search);
      estado.solo = params.get("p");
      const p = d.productos.find((x) => x.id === estado.solo);
      // abre en la pestaña con más productos
      const cuantos = (c) => d.productos.filter((x) => x.tipo === c.id).length;  // sin contar las ruedas que también salen en Llantas
      estado.tab = p ? p.tipo : d.categorias.reduce((a, c) => (cuantos(c) > cuantos(a) ? c : a)).id;
      $("#wa-pie").href = wa("Hola, estoy buscando una medida que no vi en el catálogo: ");
      render();
      if (p) setTimeout(() => $("#barra").scrollIntoView(), 50);
    })
    .catch(() => {
      $("#lista").innerHTML = '<p class="cargando">No se pudo cargar el stock. Probá recargar la página.</p>';
    });
})();
