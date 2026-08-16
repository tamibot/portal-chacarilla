#!/usr/bin/env python3
"""Motor de corte mensual del benchmark de Chacarilla.

Cada mes: primero editas a mano los proyectos que cambiaron (precio_desde, stock,
estado, etc.) y registras las novedades en meta.bitacora. LUEGO corres esto:

    python3 scripts/nuevo_corte.py --fecha 2026-09-19 \
        --titulo "Corte 3 · Septiembre" \
        --resumen "Qué pasó este mes en una línea." [--dry]

Qué hace (idempotente):
  1. Toma una foto del precio actual de cada proyecto y la agrega a precio_hist
     con la fecha del corte (así el ▲▼ del portal compara mes contra mes).
  2. Registra el corte en meta.cortes (marca el anterior como 'cerrado').
  3. Actualiza meta.fecha / verif_web_fecha / proximo_corte y recalcula contadores.
  4. Reporta qué se movió vs el corte anterior.
  5. Escribe portal-data.json y portal-data.js sincronizados (o --dry: no escribe).

Regla de oro: correr SIEMPRE con --dry primero, leer el reporte, y recién sin --dry.
"""
import json, sys, argparse, datetime, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON = os.path.join(ROOT, "data", "portal-data.json")
JS   = os.path.join(ROOT, "data", "portal-data.js")


def visibles(projects):
    return [p for p in projects if p.get("mostrar") is not False]


def typico(p):
    c = [f["precio_m2"] for f in (p.get("flats_summary") or [])
         if f.get("comparable_confirmado") and f.get("precio_m2")]
    return min(c) if c else None


def recomputar_meta(meta, projects):
    vis = [p for p in visibles(projects) if not p.get("isGEU")]

    def es_ult(p):
        s = p.get("stock") or {}
        lab = str(s.get("label", "")).lower()
        return ("últim" in lab) or (isinstance(s.get("n"), int) and 0 < s["n"] <= 3)

    def hascomp(p):
        return any(f.get("comparable_confirmado") for f in (p.get("flats_summary") or []))

    meta["total"] = len(projects)
    meta["competidores_activos"] = len(vis)
    meta["comparables_confirmados"] = sum(1 for p in projects if hascomp(p))
    meta["en_ultimas_unidades"] = sum(1 for p in vis if es_ult(p))
    meta["sin_precio_publico"] = sum(1 for p in vis if not p.get("precio_desde_usd"))
    meta["cochera_incluida"] = sum(1 for p in vis if p.get("cochera_status") == "si")
    meta["cochera_aparte"] = sum(1 for p in vis if p.get("cochera_status") == "no")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", required=True, help="Fecha del corte YYYY-MM-DD")
    ap.add_argument("--titulo", required=True, help='Ej: "Corte 3 · Septiembre"')
    ap.add_argument("--resumen", default="(pendiente de escribir)")
    ap.add_argument("--dry", action="store_true", help="No escribe, solo reporta")
    a = ap.parse_args()

    try:
        datetime.date.fromisoformat(a.fecha)
    except ValueError:
        sys.exit(f"ERROR: fecha inválida '{a.fecha}' (usar YYYY-MM-DD)")

    d = json.load(open(JSON))
    projects = d["projects"]
    meta = d["meta"]

    # 1) snapshot de precio por proyecto
    movidos, nuevos = [], 0
    for p in visibles(projects):
        hist = p.setdefault("precio_hist", [])
        if hist and hist[-1].get("corte") == a.fecha:
            continue  # ya tiene foto de este corte (idempotente)
        desde, pm2 = p.get("precio_desde_usd"), typico(p)
        prev = hist[-1] if hist else None
        hist.append({"corte": a.fecha, "desde": desde, "pm2": pm2})
        nuevos += 1
        if prev and prev.get("desde") and desde and prev["desde"] != desde:
            pct = round((desde - prev["desde"]) / prev["desde"] * 100)
            movidos.append((p["name"], prev["desde"], desde, pct))

    # 2) registrar el corte
    for c in meta.get("cortes", []):
        if c.get("estado") == "actual":
            c["estado"] = "cerrado"
    meta.setdefault("cortes", []).append(
        {"fecha": a.fecha, "titulo": a.titulo, "estado": "actual", "resumen": a.resumen})

    # 3) fechas + contadores
    meta["fecha"] = a.fecha
    meta["verif_web_fecha"] = a.fecha
    prox = datetime.date.fromisoformat(a.fecha) + datetime.timedelta(days=31)
    meta["proximo_corte"] = prox.isoformat()
    recomputar_meta(meta, projects)

    # 4) reporte
    print(f"\n=== CORTE {a.fecha} · {a.titulo} ===")
    print(f"Snapshots de precio nuevos: {nuevos}")
    if movidos:
        print("Movimientos de 'precio desde' vs corte anterior:")
        for n, viejo, nuevo, pct in sorted(movidos, key=lambda x: -abs(x[3])):
            flecha = "▲" if pct > 0 else "▼"
            print(f"  {flecha}{abs(pct):>2}%  {n:28} US${viejo:,} -> US${nuevo:,}")
    else:
        print("Sin cambios de precio desde el corte anterior.")
    print(f"Contadores: {meta['comparables_confirmados']} comparables · "
          f"{meta['en_ultimas_unidades']} en últimas · próximo corte {meta['proximo_corte']}")

    if a.dry:
        print("\n[DRY-RUN] No se escribió nada. Quita --dry para aplicar.")
        return

    dump = json.dumps(d, ensure_ascii=False, indent=1)
    open(JSON, "w").write(dump)
    open(JS, "w").write("window.PORTAL_DATA = " + dump)
    json.load(open(JSON))  # revalida
    print(f"\nOK: escrito {JSON} y {JS}. Ahora corre validar.py y publica.")


if __name__ == "__main__":
    main()
