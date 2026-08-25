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

# 2b) coherencia geométrica del cuadrante
poly=d.get('quadrant') or []
def _dentro(lat,lon,poly):
    n=len(poly);ins=False;j=n-1
    for i in range(n):
        yi,xi=poly[i][0],poly[i][1];yj,xj=poly[j][0],poly[j][1]
        if ((yi>lat)!=(yj>lat)) and (lon<(xj-xi)*(lat-yi)/((yj-yi) or 1e-12)+xi): ins=not ins
        j=i
    return ins
if poly:
    for p in projects:
        if p.get("mostrar") is False or p.get("lat") is None: continue
        real=_dentro(p["lat"],p["lng"],poly)
        if p.get("borde_avenida"):
            # excepcion declarada: da sobre una avenida-limite, se registra "en el borde"
            if p.get("en_cuadrante"):
                err(f'{p["id"]}: marcado borde_avenida pero sigue como en_cuadrante=True')
            continue
        if bool(p.get("en_cuadrante")) != real:
            err(f'{p["id"]}: en_cuadrante={p.get("en_cuadrante")} pero geométricamente está {"DENTRO" if real else "FUERA"} del cuadrante')

# 2c) COHERENCIA DEL RELATO: que el estado, la entrega, el stock y la obra cuenten lo mismo
MES={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,
 'setiembre':9,'octubre':10,'noviembre':11,'diciembre':12,'ene':1,'feb':2,'mar':3,'abr':4,'may':5,
 'jun':6,'jul':7,'ago':8,'sep':9,'oct':10,'nov':11,'dic':12}
def entrega_ym(txt):
    """(año, mes) de un texto de entrega libre. None si no hay año o si el texto
    no compromete una fecha (rangos de licencia, 'por confirmar', 'aprox')."""
    t=(txt or '').lower()
    if re.search(r'por confirmar|sin confirmar|por definir|aprox|licencia|vencida', t): return None
    años=re.findall(r'(20\d\d)',t)
    if not años: return None
    if len(años)>1: return None           # rango: no compromete una fecha
    mo=None
    for k,v in MES.items():
        if re.search(r'\b'+k,t): mo=v; break
    return (int(años[0]), mo or 12)

HOY=datetime.date.today()
HOY_YM=(HOY.year,HOY.month)
for p in projects:
    if p.get("mostrar") is False or p.get("isGEU"): continue
    pid=p.get("id","?"); eg=p.get("estado_grupo") or ""
    ent=entrega_ym(p.get("entrega"))
    obra=(p.get("estado_obra") or "").lower()
    stock=((p.get("stock") or {}).get("label") or "").lower()
    excusa=p.get("coherencia_alerta")   # incoherencia ya detectada y declarada: no vuelve a gritar

    # entrega futura no puede convivir con "entrega inmediata"
    if eg=="Entrega inmediata" and ent and ent>HOY_YM and not excusa:
        err(f'{pid}: dice "Entrega inmediata" pero su entrega ({p.get("entrega")}) todavia no llega')
    # un proyecto en planos no remata stock ni tiene obra terminada
    if eg=="En planos":
        if re.search(r'ltim|agotad|vendid', stock) and not excusa:
            err(f'{pid}: esta "En planos" pero su stock dice "{stock}"')
        if re.search(r'terminad|entregad|acabado', obra) and not excusa:
            err(f'{pid}: esta "En planos" pero su estado de obra dice "{obra[:60]}"')
    # entrega vencida sin haber pasado a entregado
    if ent and ent<HOY_YM and eg in ("En construccion","En construcción","En planos") and not excusa:
        err(f'{pid}: su entrega ({p.get("entrega")}) ya vencio y sigue como "{eg}"')
    # obra en ejecucion no es entrega inmediata
    if eg=="Entrega inmediata" and re.search(r'obra en ejecuci|en obra|sin obra|grua|grúa', obra) and not excusa:
        err(f'{pid}: dice "Entrega inmediata" pero su estado de obra dice "{obra[:60]}"')
    # todo proyecto visible declara de donde sale su estado
    evd=p.get("estado_evidencia") or {}
    if not evd.get("tipo"):
        warn(f'{pid}: sin estado_evidencia (no se sabe de que fuente sale su estado)')
    elif not iso_ok(evd.get("fecha","")):
        err(f'{pid}: estado_evidencia con fecha invalida {evd.get("fecha")}')

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
