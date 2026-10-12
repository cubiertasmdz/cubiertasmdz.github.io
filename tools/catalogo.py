#!/usr/bin/env python3
"""Herramienta del catálogo de autopartes usadas.

Uso:  .venv/bin/python tools/catalogo.py <comando> [opciones]

Comandos:
  ver [texto] [--todos]            Lista productos (con datos internos). --todos incluye ocultos.
  nuevo <archivo.json>             Carga un producto nuevo (ingreso). Imprime el código asignado.
  sumar <id> <n>                   Suma unidades a un lote existente (ingreso).
  fotos <id> <img...> [--reemplazar]  Comprime y agrega fotos al producto.
  venta <id> <n> [--monto X] [--nota "..."]
  precio <id> [--unidad X] [--juego X] [--juego-de N]
  baja <id> [--nota "..."]         Oculta el producto del catálogo.
  alta <id>                        Vuelve a mostrar un producto oculto.
  editar <id> campo=valor ...      Corrige datos (valor en JSON o texto).
  build                            Genera los archivos públicos (data/, p/).
  resumen [--mes AAAA-MM]
  excel                            Exporta stock e historial a exportes/.
  publicar "mensaje"               build + commit + push.
  limpiar-pruebas                  Borra los productos marcados como prueba.
"""
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIV = ROOT / "privado"
STOCK = PRIV / "stock.json"
HIST = PRIV / "historial.json"
CONFIG = json.loads((ROOT / "tools" / "config.json").read_text())
FOTOS = ROOT / "fotos"
FONTS = ROOT / "tools" / "fonts"

# Campos que NUNCA salen al sitio público.
PRIVADOS = {"costo", "notas_privadas", "proveedor", "prueba"}


# ---------- datos ----------

def hoy():
    return dt.date.today()


def ahora():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def cargar():
    if not STOCK.exists():
        return {"siguiente": {}, "productos": []}
    return json.loads(STOCK.read_text())


def guardar(stock):
    PRIV.mkdir(exist_ok=True)
    STOCK.write_text(json.dumps(stock, ensure_ascii=False, indent=2) + "\n")


def historial():
    return json.loads(HIST.read_text()) if HIST.exists() else []


def registrar(tipo, prod, cantidad=None, monto=None, detalle=""):
    h = historial()
    h.append({
        "fecha": ahora(), "tipo": tipo, "id": prod["id"], "producto": nombre_interno(prod),
        "cantidad": cantidad, "monto": monto, "detalle": detalle,
        **({"prueba": True} if prod.get("prueba") else {}),
    })
    HIST.write_text(json.dumps(h, ensure_ascii=False, indent=2) + "\n")


def categoria(cat_id):
    for c in CONFIG["categorias"]:
        if c["id"] == cat_id:
            return c
    sys.exit(f"Categoría desconocida: {cat_id}")


def buscar(stock, pid):
    for p in stock["productos"]:
        if p["id"].upper() == pid.upper():
            return p
    sys.exit(f"No existe el producto {pid}")


def pesos(n):
    return "$" + f"{int(round(n)):,}".replace(",", ".") if n is not None else "—"


# ---------- cálculos ----------

def dot_fecha(dot):
    """'2322' -> (semana 23, año 2022)."""
    if not dot:
        return None
    m = re.fullmatch(r"\s*(\d{2})(\d{2})\s*", str(dot))
    if not m:
        return None
    semana, anio = int(m.group(1)), 2000 + int(m.group(2))
    if not 1 <= semana <= 53:
        return None
    return semana, anio


def antiguedad(dot):
    f = dot_fecha(dot)
    if not f:
        return None
    fabricada = dt.date.fromisocalendar(f[1], min(f[0], 52), 1)
    return round((hoy() - fabricada).days / 365.25, 1)


def vida_de(p):
    if p.get("vida") is not None:
        return int(p["vida"])
    if p.get("mm") is not None:  # 8 mm nueva, 1.6 mm límite legal
        return max(0, min(100, round((float(p["mm"]) - 1.6) / (8 - 1.6) * 100)))
    return None


def estado_de(p):
    if p.get("estado"):
        return p["estado"]
    v = vida_de(p)
    if v is None:
        return None
    return "Muy buena" if v >= 70 else "Buena" if v >= 45 else "Regular"


SEGMENTOS_ESTADO = {"muy buena": 5, "buena": 4, "regular": 2}


def segmentos(p):
    v = vida_de(p)
    if v is not None:
        return max(1, min(5, round(v / 20))) if v > 0 else 0
    e = (estado_de(p) or "").lower()
    return SEGMENTOS_ESTADO.get(e)


def medida(p):
    if p["tipo"] == "cubierta":
        return f'{p["ancho"]}/{p["perfil"]} R{p["rodado"]}'
    if p["tipo"] == "llanta":
        return f'R{p["rodado"]}'
    return p.get("medida", "")


def nombre_interno(p):
    if p["tipo"] == "cubierta":
        return f'{p.get("marca", "")} {p.get("modelo", "")} {medida(p)}'.replace("  ", " ").strip()
    if p["tipo"] == "llanta":
        return f'Llanta {p.get("material", "")} {medida(p)} {p.get("agujeros", "")}x{p.get("distancia", "")}'.strip()
    return p.get("titulo", p["id"])


def visible(p):
    return p.get("activo", True) and int(p.get("cantidad", 0)) > 0


def etiqueta_cantidad(n, juego_de):
    if n == 1:
        return "1 unidad"
    if juego_de and n == juego_de == 2:
        return "Par"
    if n == 4:
        return "Juego de 4"
    return f"{n} unidades"


def texto_juego(n):
    return "el par" if n == 2 else f"el juego de {n}" if n == 4 else f"los {n}"


# ---------- versión pública de cada producto ----------

def publico(p):
    cat = categoria(p["tipo"])
    n = int(p["cantidad"])
    juego_de = p.get("juego_de") if p.get("precio_juego") else None
    etiquetas, claves = [], []
    detalle = p.get("observaciones") or ""
    sirve = ""

    if p["tipo"] == "cubierta":
        titulo = f'{p.get("marca", "")} {p.get("modelo", "")}'.strip() or "Cubierta"
        sub = medida(p)
        ic = f'{p.get("indice_carga") or ""}{p.get("indice_velocidad") or ""}'
        if ic:
            sub += f" · {ic}"
        f = dot_fecha(p.get("dot"))
        if f:
            etiquetas.append(f"Fabricada en {f[1]}")
        if p.get("mm") is not None:
            etiquetas.append(f'{str(p["mm"]).replace(".", ",")} mm de dibujo')
        if p.get("parches") == 0:
            etiquetas.append("Sin parches")
        elif p.get("parches"):
            etiquetas.append(f'{p["parches"]} parche{"s" if p["parches"] > 1 else ""}')
        claves = [f'{p["ancho"]}{p["perfil"]}{p["rodado"]}']
        mensaje_prod = f'{p.get("marca", "")} {medida(p)}'.replace("  ", " ").strip()
    elif p["tipo"] == "llanta":
        mat = (p.get("material") or "").lower()
        titulo = f"Llanta de {mat} R{p['rodado']}" if mat else f"Llanta R{p['rodado']}"
        if p.get("marca_modelo"):
            titulo = p["marca_modelo"]
        partes = []
        if p.get("agujeros") and p.get("distancia"):
            partes.append(f'{p["agujeros"]}x{p["distancia"]}')
        partes.append(f'R{p["rodado"]}')
        if p.get("ancho"):
            partes.append(f'{str(p["ancho"]).replace(".", ",")}" de ancho')
        if p.get("offset") not in (None, ""):
            partes.append(f'ET{p["offset"]}')
        sub = " · ".join(partes)
        if p.get("original") is True:
            etiquetas.append("Original")
        elif p.get("original") is False:
            etiquetas.append("Alternativa")
        for e in p.get("detalles_estado", []):
            etiquetas.append(e)
        if p.get("vehiculos"):
            sirve = ", ".join(p["vehiculos"])
        claves = [str(p["rodado"])]
        if p.get("agujeros") and p.get("distancia"):
            claves += [f'{p["agujeros"]}{p["distancia"]}', f'{p["rodado"]}{p["agujeros"]}{p["distancia"]}']
        mensaje_prod = (f"de {mat} " if mat else "") + f'R{p["rodado"]}'
        if p.get("agujeros") and p.get("distancia"):
            mensaje_prod += f' {p["agujeros"]}x{p["distancia"]}'
    else:  # categorías futuras: campos genéricos
        titulo = p.get("titulo", cat["singular"].capitalize())
        sub = p.get("subtitulo", "")
        sirve = ", ".join(p.get("vehiculos", []))
        claves = p.get("claves", [])
        mensaje_prod = titulo

    etiquetas += p.get("etiquetas", [])
    palabra = cat["singular"] if n == 1 else cat["plural"]
    cuantas = f"la {palabra}" if n == 1 else f"las {n} {palabra}"
    url = CONFIG["sitio_url"] + f'p/{p["id"]}/'
    wa = f"Hola, quería consultar por {cuantas} {mensaje_prod} que vi en el catálogo (cód. {p['id']}).\n{url}"

    v = vida_de(p)
    return {
        "id": p["id"],
        "tipo": p["tipo"],
        "titulo": titulo,
        "subtitulo": sub,
        "rodado": p.get("rodado"),
        "cantidad": n,
        "cantidad_txt": etiqueta_cantidad(n, juego_de),
        "estado": estado_de(p),
        "vida": v,
        "segmentos": segmentos(p),
        "etiquetas": etiquetas,
        "sirve": sirve,
        "detalle": detalle,
        "precio_unidad": p.get("precio_unidad"),
        "precio_juego": p.get("precio_juego") if juego_de and n >= juego_de else None,
        "juego_txt": texto_juego(juego_de) if juego_de else None,
        "fotos": p.get("fotos", []),
        "claves": claves,
        "texto": " ".join([titulo, sub, sirve, " ".join(etiquetas)]).lower(),
        "wa": wa,
        "url": url,
        "alta": p.get("fecha_ingreso"),
    }


# ---------- build ----------

def esc(s):
    return html.escape(str(s), quote=True)


def pagina_compartir(p, pub):
    """Página chica por producto: da la vista previa en WhatsApp y redirige al catálogo."""
    base = CONFIG["sitio_url"]
    destino = f"../../?p={p['id']}"
    if pub:
        titulo = f'{pub["titulo"]} {pub["subtitulo"]}'.strip()
        desc = " · ".join(x for x in [
            pub["cantidad_txt"],
            f'{pub["estado"]}' + (f' ({pub["vida"]}% de vida)' if pub["vida"] is not None else "") if pub["estado"] else "",
            f'{pesos(pub["precio_unidad"])} c/u' if pub["precio_unidad"] else "",
        ] if x)
        img = base + pub["fotos"][0] if pub["fotos"] else base + "assets/og.jpg"
    else:
        titulo, desc, img = CONFIG["titulo"], "Este producto ya no está disponible. Mirá el resto del stock.", base + "assets/og.jpg"
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>{esc(titulo)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta property="og:type" content="product">
<meta property="og:title" content="{esc(titulo)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{esc(img)}">
<meta property="og:url" content="{esc(base + 'p/' + p['id'] + '/')}">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={destino}">
<script>location.replace("{destino}")</script>
</head><body><a href="{destino}">Ver producto</a></body></html>
"""


def og_imagen():
    from PIL import Image, ImageDraw, ImageFont
    destino = ROOT / "assets" / "og.jpg"
    im = Image.new("RGB", (1200, 630), "#111111")
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype(str(FONTS / "BarlowCondensed-Bold.ttf"), 118)
    mid = ImageFont.truetype(str(FONTS / "BarlowCondensed-Bold.ttf"), 64)
    small = ImageFont.truetype(str(FONTS / "Barlow-Medium.ttf"), 38)
    d.rectangle([0, 0, 1200, 18], fill="#FFC400")
    d.text((80, 120), CONFIG["titulo"].upper().replace(" Y ", "\nY ", 1), font=big, fill="white", spacing=4)
    d.text((80, 400), CONFIG["bajada"].upper(), font=mid, fill="#FFC400")
    linea = CONFIG["ubicacion"] + (" · Hacemos envíos" if CONFIG.get("envios") else "")
    d.text((80, 500), linea, font=small, fill="#BDBDBD")
    im.save(destino, quality=82, optimize=True, progressive=True)


def build(silencioso=False):
    stock = cargar()
    productos = [publico(p) for p in stock["productos"] if visible(p)]
    productos.sort(key=lambda x: (x["alta"] or ""), reverse=True)
    for x in productos:
        x.pop("alta")
    salida = {
        "actualizado": ahora(),
        "sitio": {k: CONFIG[k] for k in ["titulo", "bajada", "whatsapp", "whatsapp_visible", "ubicacion", "envios", "sitio_url"]},
        "categorias": [{k: c[k] for k in ["id", "nombre", "singular", "plural", "filtro_rodado"]} for c in CONFIG["categorias"]],
        "productos": productos,
    }
    texto = json.dumps(salida, ensure_ascii=False, indent=1)
    for campo in PRIVADOS:  # control de seguridad
        if f'"{campo}"' in texto:
            sys.exit(f"ERROR: el campo privado '{campo}' iba a publicarse. Cancelado.")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "productos.json").write_text(texto + "\n")

    carpeta = ROOT / "p"
    shutil.rmtree(carpeta, ignore_errors=True)
    pubs = {x["id"]: x for x in productos}
    for p in stock["productos"]:
        if p.get("prueba") and not visible(p):
            continue
        d = carpeta / p["id"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(pagina_compartir(p, pubs.get(p["id"])))
    if not (ROOT / "assets" / "og.jpg").exists():
        og_imagen()
    if not silencioso:
        print(f"Build OK: {len(productos)} productos visibles.")


# ---------- fotos ----------

def procesar_fotos(pid, rutas, reemplazar=False):
    from PIL import Image, ImageOps
    stock = cargar()
    p = buscar(stock, pid)
    FOTOS.mkdir(exist_ok=True)
    if reemplazar:
        for f in p.get("fotos", []):
            (ROOT / f).unlink(missing_ok=True)
        p["fotos"] = []
    p.setdefault("fotos", [])
    usados = {int(m.group(1)) for f in p["fotos"] if (m := re.search(r"-(\d+)\.jpg$", f))}
    n = max(usados, default=0)
    for ruta in rutas:
        n += 1
        im = Image.open(ruta)
        im = ImageOps.exif_transpose(im).convert("RGB")  # endereza y descarta EXIF (GPS, etc.)
        im.thumbnail((1280, 1280), Image.LANCZOS)
        nombre = f"fotos/{p['id'].lower()}-{n}.jpg"
        im.save(ROOT / nombre, "JPEG", quality=72, optimize=True, progressive=True)
        p["fotos"].append(nombre)
        print(f"{nombre}  {(ROOT / nombre).stat().st_size // 1024} KB")
    guardar(stock)


# ---------- movimientos ----------

def opciones(args):
    pos, op = [], {}
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            clave = a[2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                op[clave] = args[i + 1]
                i += 2
            else:
                op[clave] = True
                i += 1
        else:
            pos.append(a)
            i += 1
    return pos, op


def num(s):
    return float(str(s).replace("$", "").replace(".", "").replace(",", "."))


def cmd_nuevo(ruta):
    datos = json.loads(Path(ruta).read_text())
    stock = cargar()
    cat = categoria(datos["tipo"])
    sig = stock.setdefault("siguiente", {})
    n = sig.get(cat["prefijo"], 1)
    sig[cat["prefijo"]] = n + 1
    datos["id"] = f'{cat["prefijo"]}{n:03d}'
    datos.setdefault("activo", True)
    datos.setdefault("fecha_ingreso", hoy().isoformat())
    datos.setdefault("fotos", [])
    if datos.get("precio_juego") and not datos.get("juego_de"):
        datos["juego_de"] = 2 if int(datos["cantidad"]) == 2 else 4
    stock["productos"].append(datos)
    guardar(stock)
    registrar("ingreso", datos, int(datos["cantidad"]), None,
              f'Alta. {pesos(datos.get("precio_unidad"))} c/u' + (f', juego {pesos(datos["precio_juego"])}' if datos.get("precio_juego") else ""))
    print(datos["id"])


def cmd_sumar(pid, n):
    stock = cargar()
    p = buscar(stock, pid)
    p["cantidad"] = int(p["cantidad"]) + int(n)
    p["activo"] = True
    guardar(stock)
    registrar("ingreso", p, int(n), None, f'Se suman al lote. Ahora hay {p["cantidad"]}')
    print(f'{p["id"]}: ahora {p["cantidad"]}')


def cmd_venta(pid, n, op):
    stock = cargar()
    p = buscar(stock, pid)
    n = int(n)
    if n > int(p["cantidad"]):
        sys.exit(f'Solo hay {p["cantidad"]} de {p["id"]}')
    if "monto" in op:
        monto = num(op["monto"])
    elif p.get("precio_juego") and n == (p.get("juego_de") or 4):
        monto = p["precio_juego"]
    else:
        monto = n * (p.get("precio_unidad") or 0)
    p["cantidad"] = int(p["cantidad"]) - n
    guardar(stock)
    registrar("venta", p, n, monto, op.get("nota", "") + (" — queda en 0, se oculta" if p["cantidad"] == 0 else ""))
    print(f'{p["id"]}: vendidas {n} por {pesos(monto)}. Quedan {p["cantidad"]}.')


def cmd_precio(pid, op):
    stock = cargar()
    p = buscar(stock, pid)
    cambios = []
    if "unidad" in op:
        cambios.append(f'unidad {pesos(p.get("precio_unidad"))} → {pesos(num(op["unidad"]))}')
        p["precio_unidad"] = num(op["unidad"])
    if "juego" in op:
        if op["juego"] in ("no", "0", "ninguno"):
            cambios.append("se quita precio por juego")
            p.pop("precio_juego", None)
        else:
            cambios.append(f'juego {pesos(p.get("precio_juego"))} → {pesos(num(op["juego"]))}')
            p["precio_juego"] = num(op["juego"])
            p.setdefault("juego_de", 2 if int(p["cantidad"]) == 2 else 4)
    if "juego-de" in op:
        p["juego_de"] = int(op["juego-de"])
        cambios.append(f'juego de {p["juego_de"]}')
    guardar(stock)
    registrar("precio", p, None, None, "; ".join(cambios))
    print(f'{p["id"]}: ' + "; ".join(cambios))


def cmd_activo(pid, activo, op):
    stock = cargar()
    p = buscar(stock, pid)
    p["activo"] = activo
    guardar(stock)
    registrar("baja" if not activo else "alta", p, None, None, op.get("nota", ""))
    print(f'{p["id"]}: {"oculto" if not activo else "visible de nuevo"}')


def cmd_editar(pid, pares):
    stock = cargar()
    p = buscar(stock, pid)
    cambios = []
    for par in pares:
        k, v = par.split("=", 1)
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            pass
        if v is None:
            p.pop(k, None)
        else:
            p[k] = v
        cambios.append(f"{k}={v}")
    guardar(stock)
    registrar("edicion", p, None, None, "; ".join(cambios))
    print(f'{p["id"]}: ' + "; ".join(cambios))


def cmd_ver(texto, todos):
    stock = cargar()
    for p in stock["productos"]:
        if not todos and not visible(p):
            continue
        if texto and texto.lower() not in json.dumps(p, ensure_ascii=False).lower():
            continue
        a = antiguedad(p.get("dot"))
        alerta = f"  ⚠ {a} años" if a and a > CONFIG["anios_alerta"] else ""
        estado = "" if visible(p) else "  [OCULTO]"
        print(f'{p["id"]}  {nombre_interno(p):40s} cant {p["cantidad"]}  {pesos(p.get("precio_unidad"))} c/u'
              f'{"  juego " + pesos(p["precio_juego"]) if p.get("precio_juego") else ""}'
              f'  vida {vida_de(p) if vida_de(p) is not None else "-"}%  DOT {p.get("dot", "-")}{alerta}{estado}'
              f'  fotos {len(p.get("fotos", []))}{"  PRUEBA" if p.get("prueba") else ""}')


def cmd_resumen(mes):
    stock = cargar()
    vis = [p for p in stock["productos"] if visible(p)]
    print(f"RESUMEN — {hoy().strftime('%d/%m/%Y')}\n")
    for cat in CONFIG["categorias"]:
        ps = [p for p in vis if p["tipo"] == cat["id"]]
        if not ps:
            continue
        unidades = sum(int(p["cantidad"]) for p in ps)
        valor = sum(int(p["cantidad"]) * (p.get("precio_unidad") or 0) for p in ps)
        print(f'{cat["nombre"].upper()}: {len(ps)} productos, {unidades} unidades, valor {pesos(valor)}')
        for p in ps:
            print(f'   {p["id"]}  {nombre_interno(p)} — {p["cantidad"]} u. x {pesos(p.get("precio_unidad"))}')
    total = sum(int(p["cantidad"]) * (p.get("precio_unidad") or 0) for p in vis)
    costo = sum(int(p["cantidad"]) * (p.get("costo") or 0) for p in vis)
    print(f"\nVALOR TOTAL DEL STOCK (a precio de venta por unidad): {pesos(total)}")
    if costo:
        print(f"Costo cargado del stock: {pesos(costo)}")
    mes = mes or hoy().strftime("%Y-%m")
    ventas = [h for h in historial() if h["tipo"] == "venta" and h["fecha"].startswith(mes)]
    print(f"\nVENTAS DE {mes}: {len(ventas)} operaciones, {sum(h['cantidad'] or 0 for h in ventas)} unidades, "
          f"{pesos(sum(h['monto'] or 0 for h in ventas))}")
    for h in ventas:
        print(f'   {h["fecha"][:10]}  {h["id"]} {h["producto"]} — {h["cantidad"]} u. {pesos(h["monto"])}')
    viejas = [(p, antiguedad(p.get("dot"))) for p in vis if p["tipo"] == "cubierta"]
    viejas = [(p, a) for p, a in viejas if a and a > CONFIG["anios_alerta"]]
    print(f'\nCUBIERTAS CON MÁS DE {CONFIG["anios_alerta"]} AÑOS: {len(viejas)}')
    for p, a in viejas:
        print(f'   {p["id"]}  {nombre_interno(p)} — DOT {p["dot"]} ({a} años), {p["cantidad"]} u.')


def cmd_excel():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    stock = cargar()
    wb = Workbook()
    ws = wb.active
    ws.title = "Stock"
    cols = ["Código", "Tipo", "Producto", "Marca", "Modelo", "Medida", "Índice", "DOT", "Antigüedad (años)",
            "+5 años", "Vida %", "mm", "Estado", "Material", "Agujeros", "Offset", "Vehículos", "Original",
            "Cantidad", "Precio unidad", "Precio juego", "Juego de", "Valor stock", "Costo", "Visible",
            "Fecha ingreso", "Observaciones", "Notas privadas", "Fotos"]
    ws.append(cols)
    for p in stock["productos"]:
        a = antiguedad(p.get("dot"))
        ws.append([
            p["id"], p["tipo"], nombre_interno(p), p.get("marca"), p.get("modelo"), medida(p),
            f'{p.get("indice_carga") or ""}{p.get("indice_velocidad") or ""}' or None, p.get("dot"), a,
            "SÍ" if a and a > CONFIG["anios_alerta"] else "", vida_de(p), p.get("mm"), estado_de(p),
            p.get("material"), f'{p["agujeros"]}x{p["distancia"]}' if p.get("agujeros") else None, p.get("offset"),
            ", ".join(p.get("vehiculos", [])) or None,
            {True: "Original", False: "Alternativa"}.get(p.get("original")),
            int(p["cantidad"]), p.get("precio_unidad"), p.get("precio_juego"), p.get("juego_de"),
            int(p["cantidad"]) * (p.get("precio_unidad") or 0), p.get("costo"),
            "Sí" if visible(p) else "No", p.get("fecha_ingreso"), p.get("observaciones"),
            p.get("notas_privadas"), len(p.get("fotos", [])),
        ])
    h = wb.create_sheet("Historial")
    h.append(["Fecha", "Movimiento", "Código", "Producto", "Cantidad", "Monto", "Detalle"])
    for m in historial():
        h.append([m["fecha"], m["tipo"], m["id"], m["producto"], m["cantidad"], m["monto"], m["detalle"]])
    for hoja in (ws, h):
        for c in hoja[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="111111")
        hoja.freeze_panes = "A2"
        for col in hoja.columns:
            ancho = max(len(str(c.value or "")) for c in col)
            hoja.column_dimensions[col[0].column_letter].width = min(45, max(9, ancho + 2))
        for fila in hoja.iter_rows(min_row=2):
            for c in fila:
                if hoja[1][c.column - 1].value in ("Precio unidad", "Precio juego", "Valor stock", "Costo", "Monto"):
                    c.number_format = '"$"#,##0'
    (ROOT / "exportes").mkdir(exist_ok=True)
    ruta = ROOT / "exportes" / f"stock-{dt.datetime.now().strftime('%Y-%m-%d_%H%M')}.xlsx"
    wb.save(ruta)
    print(ruta)


def cmd_publicar(mensaje):
    build()
    def git(*a, check=True):
        return subprocess.run(["git", *a], cwd=ROOT, check=check, capture_output=True, text=True)
    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        print("Sin cambios para publicar.")
        return
    git("commit", "-m", mensaje)
    r = git("push", check=False)
    if r.returncode:
        sys.exit("ERROR al publicar:\n" + r.stderr)
    print("Publicado:", mensaje)


def cmd_limpiar_pruebas():
    stock = cargar()
    quedan = []
    for p in stock["productos"]:
        if p.get("prueba"):
            for f in p.get("fotos", []):
                (ROOT / f).unlink(missing_ok=True)
            print("Borrado", p["id"], nombre_interno(p))
        else:
            quedan.append(p)
    stock["productos"] = quedan
    if not quedan:
        stock["siguiente"] = {}
    guardar(stock)
    HIST.write_text(json.dumps([h for h in historial() if not h.get("prueba")], ensure_ascii=False, indent=2) + "\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, (pos, op) = sys.argv[1], opciones(sys.argv[2:])
    if cmd == "ver":
        cmd_ver(pos[0] if pos else "", op.get("todos"))
    elif cmd == "nuevo":
        cmd_nuevo(pos[0])
    elif cmd == "sumar":
        cmd_sumar(pos[0], pos[1])
    elif cmd == "fotos":
        procesar_fotos(pos[0], pos[1:], op.get("reemplazar"))
    elif cmd == "venta":
        cmd_venta(pos[0], pos[1], op)
    elif cmd == "precio":
        cmd_precio(pos[0], op)
    elif cmd == "baja":
        cmd_activo(pos[0], False, op)
    elif cmd == "alta":
        cmd_activo(pos[0], True, op)
    elif cmd == "editar":
        cmd_editar(pos[0], pos[1:])
    elif cmd == "build":
        build()
    elif cmd == "resumen":
        cmd_resumen(op.get("mes"))
    elif cmd == "excel":
        cmd_excel()
    elif cmd == "publicar":
        cmd_publicar(pos[0] if pos else "Actualización del catálogo")
    elif cmd == "limpiar-pruebas":
        cmd_limpiar_pruebas()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
