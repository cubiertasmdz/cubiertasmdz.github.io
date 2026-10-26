#!/usr/bin/env python3
"""Agrupa un export de WhatsApp (_chat.txt) en publicaciones: texto + fotos del mismo remitente.

Uso: .venv/bin/python tools/leer_chat.py <_chat.txt> <DD-MM-AA> [<DD-MM-AA> ...] [--json salida.json]
Una publicación = mensajes seguidos del mismo remitente con menos de 20 s entre sí; un texto nuevo corta la anterior.
"""
import json
import re
import sys


def agrupar(ruta, dias):
    txt = open(ruta, encoding="utf-8").read().replace("\u200e", "")
    pat = re.compile(r"^\[(\d\d-\d\d-\d\d), (\d\d:\d\d:\d\d)\] ([^:]+):\s?(.*)$")
    msgs, cur = [], None
    for l in txt.split("\n"):
        m = pat.match(l)
        if m:
            cur = {"d": m[1], "t": m[2], "s": m[3].strip(), "x": m[4]}
            msgs.append(cur)
        elif cur:
            cur["x"] += "\n" + l
    msgs = [m for m in msgs if m["d"] in dias]
    seg = lambda t: sum(int(a) * b for a, b in zip(t.split(":"), (3600, 60, 1)))
    grupos = []
    for m in msgs:
        fotos = re.findall(r"<adjunto: ([^>]+\.(?:jpg|jpeg|png|webp))>", m["x"])
        omit = m["x"].count("imagen omitida")
        texto = re.sub(r"<adjunto: [^>]+>|imagen omitida", "", m["x"]).strip()
        if texto.startswith(("Eliminaste este mensaje", "Se eliminó este mensaje")):
            continue
        if not fotos and not texto and not omit:
            continue
        g = grupos[-1] if grupos else None
        if not (g and g["s"] == m["s"] and g["d"] == m["d"] and seg(m["t"]) - seg(g["ult"]) <= 20 and not (texto and g["texto"])):
            g = {"d": m["d"], "s": m["s"], "t": m["t"], "texto": "", "fotos": [], "omitidas": 0}
            grupos.append(g)
        g["ult"] = m["t"]
        g["fotos"] += fotos
        g["omitidas"] += omit
        if texto:
            g["texto"] = texto
    for i, g in enumerate(grupos, 1):
        g["n"] = i
    return grupos


if __name__ == "__main__":
    args = sys.argv[1:]
    salida = None
    if "--json" in args:
        i = args.index("--json"); salida = args[i + 1]; del args[i:i + 2]
    gs = agrupar(args[0], set(args[1:]))
    if salida:
        json.dump(gs, open(salida, "w"), ensure_ascii=False, indent=1)
    for g in gs:
        print(g["n"], g["d"], g["t"], g["s"], "|", g["texto"].replace("\n", " / ")[:90], "| fotos", len(g["fotos"]),
              f"| OMITIDAS {g['omitidas']}" if g["omitidas"] else "")
