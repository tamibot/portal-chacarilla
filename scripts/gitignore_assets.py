# -*- coding: utf-8 -*-
"""Regenera el .gitignore del repo publicado.

El repo live ignora los assets que el portal no referencia, para no publicar peso
muerto. Pero esa lista envejece: en agosto-2026 había 155 imágenes en disco que ya
estaban enlazadas en la ficha y el .gitignore las seguía bloqueando — se veían en
local y salían 404 en producción.

Correrlo desde el clone del repo publicado, ANTES de hacer commit:
    python3 scripts/gitignore_assets.py
"""
import json, os, sys
from pathlib import Path

BASE = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
d = json.load(open(BASE / "data/portal-data.json"))

usadas = set()
def add(v):
    if isinstance(v, str) and v.startswith("assets/"):
        usadas.add(v)

for p in d["projects"]:
    for x in (p.get("planos") or []):
        add(x)
    add(p.get("img")); add(p.get("tarifario")); add(p.get("brochure"))
    for x in (p.get("documentos") or []):
        add(x.get("archivo"))
    for x in ((p.get("anuncios") or {}).get("imgs") or []):
        add(x)
for a in (d["meta"].get("archivo_zona") or []):
    for x in (a.get("planos") or []):
        add(x)
    add(a.get("brochure"))
for e in (d["meta"].get("bitacora") or []):
    for x in (e.get("imgs") or []):
        add(x)

disco = {os.path.join(r, f) for r, _, fs in os.walk(BASE / "assets") for f in fs
         if not f.startswith(".")}
disco = {os.path.relpath(x, BASE) for x in disco}
huerfanos = sorted(disco - usadas)
faltan = sorted(x for x in usadas if not (BASE / x).exists())

BASESET = ["node_modules/", ".DS_Store", "*.log", ".env", "*.bak*", "*.orig"]
(BASE / ".gitignore").write_text("\n".join(
    BASESET + ["", "# Assets que hoy no referencia el portal. Lista regenerada por",
               "# scripts/gitignore_assets.py — no editar a mano.", ""] + huerfanos) + "\n")

print(f"referenciados: {len(usadas)} · en disco: {len(disco)} · ignorados por huérfanos: {len(huerfanos)}")
if faltan:
    print(f"\n⚠ {len(faltan)} referencias del portal sin archivo en este clone:")
    for x in faltan[:15]:
        print("   ", x)
    sys.exit(1)
