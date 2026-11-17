#!/usr/bin/env python3
"""Excel único con TODAS las ventas: página de cubiertas/llantas (CUBIERTASMDZ) + página de autopartes (AUTOPARTESMDZ).

Uso:  .venv/bin/python tools/ventas_unificadas.py [AAAA-MM | todo]     (por defecto: todo)
Sale en exportes/VENTAS UNIFICADAS <fecha>.xlsx. Las páginas siguen separadas; esto solo junta las ventas.
"""
import datetime as dt
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

CUB = Path(__file__).resolve().parent.parent
AUTO = Path.home() / "Desktop" / "GENERAL" / "AUTOPARTESMDZ"


def leer(proy, pagina, campo_id):
    hist = json.loads((proy / "privado" / "historial.json").read_text())
    conf = json.loads((proy / "tools" / "config.json").read_text())
    com_base = conf.get("comision")  # None = todavía no definida
    filas = []
    for m in hist:
        if m.get("tipo") != "venta" or m.get("prueba"):
            continue
        com = m.get("comision", com_base)
        monto = m.get("monto") or 0
        filas.append({
            "fecha": (m.get("fecha_venta") or m["fecha"])[:10], "pagina": pagina, "codigo": m.get(campo_id),
            "que": m.get("detalle_venta") or m.get("producto"), "cantidad": m.get("cantidad"), "monto": monto,
            "cliente": m.get("cliente"), "vendedor": m.get("vendedor") or "", "comision_pct": com,
            "ganancia": round(monto * com) if com is not None else None,
            "a_pagar": round(monto * (1 - com)) if com is not None else None, "nota": m.get("detalle"),
        })
    return filas


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] not in ("todo", "todas") else ""
    ventas = leer(CUB, "Cubiertas y llantas", "id") + leer(AUTO, "Autopartes", "codigo")
    ventas = sorted((v for v in ventas if v["fecha"].startswith(filtro)), key=lambda v: (v["fecha"], v["pagina"]))
    wb = Workbook()

    def hoja(ws, cols, filas, dinero=()):
        ws.append(cols)
        for f in filas:
            ws.append(f)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="111111")
            c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.row_dimensions[1].height = 30
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for i, col in enumerate(ws.columns, 1):
            ws.column_dimensions[get_column_letter(i)].width = min(48, max(10, max(len(str(c.value or "")) for c in col) + 2))
            if cols[i - 1] in dinero:
                for c in col[1:]:
                    c.number_format = '"$"#,##0'

    # --- Resumen ---
    def tot(vs):
        g = [v["ganancia"] for v in vs if v["ganancia"] is not None]
        return [len(vs), sum(v["cantidad"] or 0 for v in vs), sum(v["monto"] for v in vs), sum(g) if g else None,
                sum(v["a_pagar"] for v in vs if v["a_pagar"] is not None) or None]
    filas = [["TOTAL", *tot(ventas)]]
    for pag in ("Cubiertas y llantas", "Autopartes"):
        filas.append([pag, *tot([v for v in ventas if v["pagina"] == pag])])
    filas.append([])
    for mes in sorted({v["fecha"][:7] for v in ventas}):
        filas.append([f"Mes {mes}", *tot([v for v in ventas if v["fecha"].startswith(mes)])])
    filas.append([])
    for vend in sorted({v["vendedor"] or "(nosotros)" for v in ventas}):
        filas.append([f"Vendedor: {vend}", *tot([v for v in ventas if (v["vendedor"] or "(nosotros)") == vend])])
    r = wb.active
    r.title = "Resumen"
    hoja(r, ["Dato", "Ventas", "Unidades", "Cobrado", "Ganancia (comisión)", "A pagar a dueños"], filas,
         dinero={"Cobrado", "Ganancia (comisión)", "A pagar a dueños"})
    r.append([])
    r.append([f"Generado {dt.datetime.now():%d/%m/%Y %H:%M}. Autopartes: comisión según su config (vacía = todavía sin definir)."])

    hoja(wb.create_sheet("Ventas"),
         ["Fecha", "Página", "Código", "Qué se vendió", "Cantidad", "Monto", "Cliente", "Vendedor", "Comisión %",
          "Ganancia", "A pagar a dueños", "Nota"],
         [[v["fecha"], v["pagina"], v["codigo"], v["que"], v["cantidad"], v["monto"], v["cliente"], v["vendedor"],
           f'{round(v["comision_pct"] * 100)}%' if v["comision_pct"] is not None else "a definir",
           v["ganancia"], v["a_pagar"], v["nota"]] for v in ventas],
         dinero={"Monto", "Ganancia", "A pagar a dueños"})
    (CUB / "exportes").mkdir(exist_ok=True)
    destino = CUB / "exportes" / f"VENTAS UNIFICADAS {filtro or 'todo'} {dt.date.today():%Y-%m-%d}.xlsx"
    wb.save(destino)
    print(destino, f"({len(ventas)} ventas)")


if __name__ == "__main__":
    main()
