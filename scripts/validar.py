#!/usr/bin/env python3
"""Validador de integridad del benchmark. Correr ANTES de publicar.

    python3 scripts/validar.py

Sale con código 0 si todo OK, 1 si hay ERRORES (no publicar). Los WARN no bloquean
pero conviene revisarlos. No modifica nada.
"""
import json, sys, os, datetime, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON = os.path.join(ROOT, "data", "portal-data.json")
JS   = os.path.join(ROOT, "data", "portal-data.js")

errores, warns = [], []
def err(m): errores.append(m)
def warn(m): warns.append(m)

# 1) JSON válido y .js == .json
try:
    d = json.load(open(JSON))
except Exception as e:
    print(f"ERROR FATAL: portal-data.json no parsea: {e}"); sys.exit(1)
try:
    js = open(JS).read()
    body = js[js.index("{"):].rstrip().rstrip(";")
    if json.loads(body) != d:
        err(".js y .json están DESINCRONIZADOS (contenido distinto).")
except Exception as e:
    err(f".js no parsea o no coincide: {e}")

projects = d.get("projects", [])
meta = d.get("meta", {})
vis = [p for p in projects if p.get("mostrar") is not False]

def iso_ok(s):
    try: datetime.date.fromisoformat(s); return True
    except Exception: return False

# 2) por proyecto
ids = set()
for p in projects:
    pid = p.get("id", "?")
    if pid in ids: err(f"id duplicado: {pid}")
    ids.add(pid)
    if not p.get("name"): err(f"{pid}: sin name")
    if p.get("mostrar") is False:  # ocultos no se validan a fondo
        continue
    if not p.get("isGEU"):
        if p.get("lat") is None or p.get("lng") is None:
            err(f"{pid}: sin coordenadas (no aparece en el mapa)")
        if not p.get("estado_grupo"):
            warn(f"{pid}: sin estado_grupo")
    for f in (p.get("flats_summary") or []):
        if f.get("comparable_confirmado"):
            if not (f.get("m2") and f.get("precio_usd") and f.get("precio_m2")):
                err(f"{pid}: flat comparable sin m2/precio_usd/precio_m2")
            elif abs(round(f["precio_usd"]/f["m2"]) - f["precio_m2"]) > 2:
                warn(f"{pid}: precio_m2 no cuadra ({f['precio_usd']}/{f['m2']}≈{round(f['precio_usd']/f['m2'])} vs {f['precio_m2']})")
    ha, hd = p.get("precio_hasta_usd"), p.get("precio_desde_usd")
    if ha and hd and ha < hd:
        err(f"{pid}: precio_hasta ({ha}) < precio_desde ({hd})")
    for h in (p.get("precio_hist") or []):
        if not iso_ok(h.get("corte", "")):
            err(f"{pid}: precio_hist con fecha inválida {h.get('corte')}")

# 3) meta: cortes, bitácora, fechas, contadores
for c in meta.get("cortes", []):
    if not iso_ok(c.get("fecha", "")): err(f"corte con fecha inválida: {c.get('fecha')}")
act = [c for c in meta.get("cortes", []) if c.get("estado") == "actual"]
if len(act) != 1: warn(f"meta.cortes tiene {len(act)} cortes 'actual' (debería ser 1)")
for b in meta.get("bitacora", []):
    if not iso_ok(b.get("fecha", "")): err(f"bitácora con fecha inválida: {b.get('fecha')}")
for f in ("fecha", "proximo_corte", "verif_web_fecha"):
    if meta.get(f) and not iso_ok(meta[f]): err(f"meta.{f} fecha inválida: {meta[f]}")

# contadores vs recalculo
def hascomp(p): return any(f.get("comparable_confirmado") for f in (p.get("flats_summary") or []))
real_comp = sum(1 for p in projects if hascomp(p))
if meta.get("comparables_confirmados") != real_comp:
    warn(f"meta.comparables_confirmados={meta.get('comparables_confirmados')} pero el real es {real_comp} (corré nuevo_corte.py o ajustá)")

# 4) salida
print(f"Proyectos: {len(projects)} ({len(vis)} visibles) · {len(errores)} errores · {len(warns)} warnings")
for m in warns:  print("  WARN:", m)
for m in errores: print("  ERROR:", m)
if errores:
    print("\n❌ NO PUBLICAR hasta corregir los errores."); sys.exit(1)
print("\n✅ Integridad OK." + (" Revisá los warnings." if warns else ""))
