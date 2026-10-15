(function () {
  "use strict";

  const $ = (s) => document.querySelector(s);
  const estado = { datos: null, tab: null, rodado: "todos", marca: "", medida: "", q: "", solo: null };
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

  // "205/55 R16" -> "2055516"; "gol 4x100" -> {num: "4100", palabras: ["gol"]}
  function analizar(q) {
    const t = q.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    const num = t.replace(/\D/g, "");
    const palabras = t.replace(/\d+/g, " ").split(/[^a-zñ]+/).filter((w) => w.length > 1);
    return { num, palabras };
  }
  function coincide(p, q) {
    if (!q.num && !q.palabras.length) return true;
    if (q.num && !p.claves.some((k) => k.startsWith(q.num) || (q.num.length >= 4 && k.includes(q.num)))) return false;
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
  const pasaFiltros = (p) => pasaRodado(p) && pasaMarca(p) && pasaMedida(p);
  const unicos = (arr) => [...new Set(arr)].sort((a, b) => a.localeCompare(b, "es", { numeric: true }));

  function renderFiltros(base, cat) {
    const ml = unicos(base.flatMap((p) => p.marcas_llanta));
    const mc = unicos(base.flatMap((p) => p.marcas_cubierta));
    const opt = (v, t) => `<option value="${esc(v)}"${v === estado.marca ? " selected" : ""}>${esc(t)}</option>`;
    $("#f-marca").innerHTML = opt("", "Todas") +
      (ml.length ? `<optgroup label="Marca de llanta">${ml.map((m) => opt("l:" + m, m)).join("")}</optgroup>` : "") +
      (mc.length ? `<optgroup label="Marca de cubierta">${mc.map((m) => opt("c:" + m, m)).join("")}</optgroup>` : "");
    const medidas = unicos(base.map((p) => p.medida_cubierta).filter(Boolean));
    $("#f-medida").innerHTML = [`<option value="">Todas</option>`]
      .concat(medidas.map((m) => `<option value="${esc(m)}"${m === estado.medida ? " selected" : ""}>${esc(m)}</option>`)).join("");
    const conMedida = !!(cat && cat.filtro_medida && medidas.length);
    $("#filtro-medida").style.display = conMedida ? "" : "none";
    $("#filtros").classList.toggle("uno", !conMedida);
    $("#filtros").style.display = ml.length || mc.length || conMedida ? "" : "none";
    $("#f-marca").classList.toggle("activo", !!estado.marca);
    $("#f-medida").classList.toggle("activo", !!estado.medida);
  }

  function visibles(tab) {
    const q = analizar(estado.q);
    return estado.datos.productos.filter((p) => p.tipo === tab && coincide(p, q));
  }

  // ---------- render ----------
  function renderTabs() {
    const cats = estado.datos.categorias;
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
    const fotos = p.fotos.length
      ? `<div class="fotos">${p.fotos.map((f, i) => `<img src="${esc(f)}" alt="${esc(p.titulo + " " + p.subtitulo)} — foto ${i + 1}" loading="${i === 0 ? "lazy" : "lazy"}" decoding="async">`).join("")}</div>
         ${p.fotos.length > 1 ? `<span class="contador">1/${p.fotos.length}</span>
         <button class="flecha izq" aria-label="Foto anterior">‹</button><button class="flecha der" aria-label="Foto siguiente">›</button>` : ""}`
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
        <h2>${esc(p.titulo)}</h2>
        <p class="medida">${esc(p.subtitulo)}</p>
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
    $("#lista").innerHTML = lista.length ? lista.map(tarjeta).join("") : vacio();
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
    if (tab) { estado.tab = tab.dataset.tab; estado.rodado = "todos"; estado.marca = ""; estado.medida = ""; estado.solo = null; return render(); }
    const chip = e.target.closest("[data-rodado]");
    if (chip) { estado.rodado = chip.dataset.rodado; return render(); }
    if (e.target.closest("[data-ver-todo]")) {
      estado.solo = null; history.replaceState(null, "", location.pathname); return render();
    }
    const flecha = e.target.closest(".flecha");
    if (flecha) {
      const f = flecha.parentElement.querySelector(".fotos");
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
    const c = f.parentElement.querySelector(".contador");
    if (c) c.textContent = `${Math.round(f.scrollLeft / f.clientWidth) + 1}/${f.children.length}`;
  }, true);

  $("#f-marca").addEventListener("change", (e) => { estado.marca = e.target.value; estado.solo = null; render(); });
  $("#f-medida").addEventListener("change", (e) => { estado.medida = e.target.value; estado.solo = null; render(); });

  let espera;
  $("#q").addEventListener("input", (e) => {
    clearTimeout(espera);
    espera = setTimeout(() => { estado.q = e.target.value; estado.solo = null; autoTab(); render(); }, 150);
  });
  $("#buscador").addEventListener("submit", (e) => {
    e.preventDefault();
    estado.q = $("#q").value; estado.solo = null; autoTab(); render();
    $("#q").blur();
    $("#barra").scrollIntoView({ behavior: "smooth" });
  });

  // si la búsqueda no da nada en la pestaña actual pero sí en otra, cambia de pestaña
  function autoTab() {
    if (visibles(estado.tab).length) return;
    const otra = estado.datos.categorias.find((c) => visibles(c.id).length);
    if (otra) { estado.tab = otra.id; estado.rodado = "todos"; estado.marca = ""; estado.medida = ""; }
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
      const cuantos = (c) => d.productos.filter((x) => x.tipo === c.id).length;
      estado.tab = p ? p.tipo : d.categorias.reduce((a, c) => (cuantos(c) > cuantos(a) ? c : a)).id;
      $("#wa-pie").href = wa("Hola, estoy buscando una medida que no vi en el catálogo: ");
      render();
      if (p) setTimeout(() => $("#barra").scrollIntoView(), 50);
    })
    .catch(() => {
      $("#lista").innerHTML = '<p class="cargando">No se pudo cargar el stock. Probá recargar la página.</p>';
    });
})();
