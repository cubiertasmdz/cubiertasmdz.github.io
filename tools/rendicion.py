"""Excel de rendición de cuentas: todo lo hecho desde el inicio (stock, ingresos, ventas, comisiones, bajas).
Uso: .venv/bin/python tools/rendicion.py  →  exportes/RENDICION DE CUENTAS <fecha>.xlsx
No incluye notas privadas."""
import datetime as dt
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from catalogo import ROOT, CONFIG, cargar, historial, categoria, medida, nombre_planilla, pesos, hoy  # noqa: E402

from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side  # noqa: E402

COM = CONFIG.get("comision", 0.10)
NEGRO = PatternFill("solid", fgColor="1F2937")
GRIS = PatternFill("solid", fgColor="F3F4F6")
AMARILLO = PatternFill("solid", fgColor="FEF3C7")
PESOS = '"$"#,##0'
LINEA = Border(bottom=Side(style="thin", color="D1D5DB"))


def fecha_venta(m):
    return (m.get("fecha_venta") or m["fecha"])[:10]


def ddmm(iso):
    return dt.date.fromisoformat(iso[:10]).strftime("%d/%m/%Y") if iso else ""


def tabla(ws, encabezado, filas, anchos, dinero=(), total=None):
    ws.append(encabezado)
    for c in ws[ws.max_row]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = NEGRO
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[ws.max_row].height = 30
    inicio = ws.max_row
    for f in filas:
        ws.append(f)
    if total:
        ws.append([])
        ws.append(total)
        for c in ws[ws.max_row]:
            c.font = Font(bold=True)
            c.fill = AMARILLO
    for col in dinero:
        for c in ws[col][inicio:]:
            c.number_format = PESOS
    for i, a in enumerate(anchos):
        ws.column_dimensions[chr(65 + i)].width = a
    ws.freeze_panes = ws.cell(inicio + 1, 1)
    ws.auto_filter.ref = f"A{inicio}:{chr(64 + len(encabezado))}{inicio + len(filas)}"


def main():
    productos = [p for p in cargar()["productos"] if not p.get("prueba")]
    por_id = {p["id"]: p for p in productos}
    hist = [m for m in historial() if not m.get("prueba")]
    ventas = sorted([m for m in hist if m["tipo"] == "venta"], key=fecha_venta)
    bajas = [m for m in hist if m["tipo"] == "baja"]

    vendidas = defaultdict(int)
    for m in ventas:
        vendidas[m["id"]] += m.get("cantidad") or 0
    dadas_de_baja = defaultdict(int)
    for m in bajas:  # las bajas viejas no guardaban la cantidad: se toma la que tenía el producto
        if not m.get("cantidad") and m["id"] in por_id:
            m["cantidad"] = int(por_id[m["id"]].get("cantidad", 0))
        dadas_de_baja[m["id"]] += m.get("cantidad") or 0

    inicio = min(p["fecha_ingreso"] for p in productos)
    wb = Workbook()

    # ---------- Ventas ----------
    ws = wb.active
    ws.title = "Ventas"
    filas, tot = [], [0, 0, 0, 0]
    for m in ventas:
        p = por_id.get(m["id"], {})
        com = m.get("comision", COM)
        monto = m.get("monto") or 0
        cant = m.get("cantidad") or 0
        quien = f'{m["vendedor"]} (desarmadero)' if m.get("vendedor") else "Nosotros"
        filas.append([ddmm(fecha_venta(m)), m["id"], m.get("detalle_venta") or m.get("producto"),
                      categoria(p["tipo"])["singular"].capitalize() if p else "", cant, monto,
                      f"{round(com * 100)}%", round(monto * com), monto - round(monto * com), quien,
                      m.get("cliente") or ""])
        tot[0] += cant; tot[1] += monto; tot[2] += round(monto * com); tot[3] += monto - round(monto * com)
    tabla(ws, ["Fecha", "Código", "Qué se vendió", "Tipo", "Unidades", "Total cobrado", "Comisión", "Ganancia (comisión)",
               "Para el dueño", "Vendió", "Cliente"], filas, (12, 9, 48, 16, 10, 15, 10, 16, 15, 20, 24),
          dinero="FHI", total=["TOTAL", "", f"{len(ventas)} ventas", "", tot[0], tot[1], "", tot[2], tot[3]])

    # ---------- Stock actual ----------
    ws = wb.create_sheet("Stock actual")
    filas = []
    stock_cat = defaultdict(lambda: [0, 0])
    for p in sorted(productos, key=lambda x: x["id"]):
        n = int(p.get("cantidad", 0))
        if not (p.get("activo", True) and n > 0):
            continue
        cat = categoria(p["tipo"])["nombre"]
        stock_cat[cat][0] += 1
        stock_cat[cat][1] += n
        filas.append([p["id"], cat, nombre_planilla(p, n), medida(p), p.get("llanta_marca") or
                      (p.get("marca") if p["tipo"] == "llanta" else ""),
                      p.get("marca") if p["tipo"] != "llanta" else "", n, ddmm(p.get("fecha_ingreso")),
                      f'{CONFIG["sitio_url"]}p/{p["id"]}/'])
    tabla(ws, ["Código", "Categoría", "Descripción", "Medida / rodado", "Marca llanta", "Marca cubierta", "Unidades",
               "Fecha de ingreso", "Link"], filas, (9, 20, 56, 15, 16, 22, 10, 14, 40),
          total=["TOTAL", "", f"{len(filas)} publicaciones", "", "", "", sum(f[6] for f in filas)])

    # ---------- Ingresos ----------
    ws = wb.create_sheet("Ingresos")
    filas = []
    ingreso_mes = defaultdict(lambda: [0, 0])
    for p in sorted(productos, key=lambda x: (x.get("fecha_ingreso", ""), x["id"])):
        queda = int(p.get("cantidad", 0)) if p.get("activo", True) else 0
        entro = queda + vendidas[p["id"]] + dadas_de_baja[p["id"]]
        ingreso_mes[p["fecha_ingreso"][:7]][0] += 1
        ingreso_mes[p["fecha_ingreso"][:7]][1] += entro
        filas.append([ddmm(p.get("fecha_ingreso")), p["id"], categoria(p["tipo"])["nombre"],
                      nombre_planilla(p, entro), entro, vendidas[p["id"]], dadas_de_baja[p["id"]], queda])
    tabla(ws, ["Fecha de ingreso", "Código", "Categoría", "Descripción", "Unidades ingresadas", "Vendidas",
               "Dadas de baja", "Quedan"], filas, (14, 9, 20, 56, 12, 10, 10, 10),
          total=["TOTAL", "", f"{len(filas)} publicaciones", "", sum(f[4] for f in filas),
                 sum(f[5] for f in filas), sum(f[6] for f in filas), sum(f[7] for f in filas)])

    # ---------- Bajas ----------
    ws = wb.create_sheet("Bajas")
    filas = [[ddmm(m["fecha"]), m["id"], m.get("producto"), m.get("cantidad") or "",
              m.get("detalle") or "Sacado de la venta"] for m in bajas]
    tabla(ws, ["Fecha", "Código", "Producto", "Unidades", "Motivo"], filas, (12, 9, 50, 10, 60))

    # ---------- Resumen ----------
    r = wb.create_sheet("Resumen", 0)
    r.column_dimensions["A"].width = 44
    for col in "BCDE":
        r.column_dimensions[col].width = 18

    def titulo(t):
        r.append([])
        r.append([t])
        r[r.max_row][0].font = Font(bold=True, size=12)

    def fila(etiqueta, *valores, dinero=False, fuerte=False):
        r.append([etiqueta, *valores])
        for c in r[r.max_row][1:]:
            if dinero and isinstance(c.value, (int, float)):
                c.number_format = PESOS
        if fuerte:
            for c in r[r.max_row]:
                c.font = Font(bold=True)
                c.fill = AMARILLO

    r.append(["RENDICIÓN DE CUENTAS — CATÁLOGO DE LLANTAS Y CUBIERTAS"])
    r["A1"].font = Font(bold=True, size=14)
    r.append([f"Período: del {ddmm(inicio)} al {hoy().strftime('%d/%m/%Y')}"])
    r.append([f"Generado el {dt.datetime.now().strftime('%d/%m/%Y %H:%M')}. Mercadería en consignación: "
              f"la comisión es el {round(COM * 100)}% de cada venta (5% en las ventas hechas en el desarmadero)."])
    r["A3"].font = Font(italic=True, color="6B7280")

    titulo("Ventas")
    fila("Operaciones de venta", len(ventas))
    fila("Unidades vendidas", tot[0])
    fila("Total cobrado", tot[1], dinero=True)
    fila("Comisión (ganancia nuestra)", tot[2], dinero=True, fuerte=True)
    fila("A pagar a los dueños de la mercadería", tot[3], dinero=True, fuerte=True)

    titulo("Ventas por mes")
    r.append(["Mes", "Ventas", "Unidades", "Cobrado", "Comisión"])
    for c in r[r.max_row]:
        c.font = Font(bold=True); c.fill = GRIS
    meses = defaultdict(lambda: [0, 0, 0, 0])
    for m in ventas:
        x = meses[fecha_venta(m)[:7]]
        monto = m.get("monto") or 0
        x[0] += 1; x[1] += m.get("cantidad") or 0; x[2] += monto; x[3] += round(monto * m.get("comision", COM))
    nombres = {"10": "Octubre", "11": "Noviembre", "12": "Diciembre", "01": "Enero"}
    for k in sorted(meses):
        fila(f'{nombres.get(k[5:], k[5:])} {k[:4]}', *meses[k], dinero=True)

    titulo("Ventas por quién vendió")
    r.append(["Vendió", "Ventas", "Unidades", "Cobrado", "Comisión"])
    for c in r[r.max_row]:
        c.font = Font(bold=True); c.fill = GRIS
    quien = defaultdict(lambda: [0, 0, 0, 0])
    for m in ventas:
        x = quien[f'{m["vendedor"]} (desarmadero, 5%)' if m.get("vendedor") else f"Nosotros ({round(COM * 100)}%)"]
        monto = m.get("monto") or 0
        x[0] += 1; x[1] += m.get("cantidad") or 0; x[2] += monto; x[3] += round(monto * m.get("comision", COM))
    for k, v in sorted(quien.items(), key=lambda kv: -kv[1][2]):
        fila(k, *v, dinero=True)

    titulo("Ventas por tipo de producto")
    r.append(["Tipo", "Ventas", "Unidades", "Cobrado"])
    for c in r[r.max_row]:
        c.font = Font(bold=True); c.fill = GRIS
    tipos = defaultdict(lambda: [0, 0, 0])
    for m in ventas:
        p = por_id.get(m["id"])
        x = tipos[categoria(p["tipo"])["nombre"] if p else "Otro"]
        x[0] += 1; x[1] += m.get("cantidad") or 0; x[2] += m.get("monto") or 0
    for k, v in sorted(tipos.items(), key=lambda kv: -kv[1][2]):
        fila(k, *v, dinero=True)

    titulo("Mercadería ingresada")
    tot_ing = sum(v[1] for v in ingreso_mes.values())
    fila("Publicaciones cargadas", len(productos))
    fila("Unidades ingresadas", tot_ing)
    for k in sorted(ingreso_mes):
        fila(f'   {nombres.get(k[5:], k[5:])} {k[:4]}', f"{ingreso_mes[k][0]} publicaciones", f"{ingreso_mes[k][1]} u.")
    fila("Unidades dadas de baja (no vendidas)", sum(dadas_de_baja.values()))

    titulo("Stock actual a la venta")
    r.append(["Categoría", "Publicaciones", "Unidades"])
    for c in r[r.max_row]:
        c.font = Font(bold=True); c.fill = GRIS
    for k, v in sorted(stock_cat.items(), key=lambda kv: -kv[1][1]):
        fila(k, *v)
    fila("TOTAL", sum(v[0] for v in stock_cat.values()), sum(v[1] for v in stock_cat.values()), fuerte=True)
    r.append([])
    r.append(["El detalle de cada venta, del stock, de los ingresos y de las bajas está en las otras hojas."])
    r[r.max_row][0].font = Font(italic=True, color="6B7280")

    (ROOT / "exportes").mkdir(exist_ok=True)
    ruta = ROOT / "exportes" / f"RENDICION DE CUENTAS {hoy().strftime('%Y-%m-%d')}.xlsx"
    if "--solo-ventas" in sys.argv:  # solo la pestaña Ventas
        for nombre in wb.sheetnames:
            if nombre != "Ventas":
                del wb[nombre]
        ruta = ROOT / "exportes" / f"VENTAS RENDICION {hoy().strftime('%Y-%m-%d')}.xlsx"
    wb.save(ruta)
    print(ruta)
    print(f"{len(ventas)} ventas, {tot[0]} u., cobrado {pesos(tot[1])}, comisión {pesos(tot[2])}, "
          f"dueños {pesos(tot[3])}; ingresadas {tot_ing} u.; stock {sum(v[1] for v in stock_cat.values())} u.")


if __name__ == "__main__":
    main()
