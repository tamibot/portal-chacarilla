# Cómo actualizar el benchmark cada mes

El portal es un **benchmark vivo**: cada mes se hace un "corte" que fotografía la
zona y deja ver la evolución. Este es el proceso, de principio a fin. Idealmente
toma 1–2 horas una vez al mes.

Toda la data vive en `data/portal-data.json` (y su espejo `data/portal-data.js`).
**Nunca edites el `.js` a mano** — los scripts lo regeneran desde el `.json`.

---

## Paso 1 · Levantar novedades (campo)

Abrí el portal → pestaña **Time lapse**. Arriba dice cuántos proyectos están
**"por reconfirmar"** (🔴 +35 días sin tocar). Esos son la lista de trabajo.

Contactá por WhatsApp a cada asesor (los números están en **Análisis →
Directorio del cuadrante**) y preguntá: precio vigente, stock disponible, fecha
de entrega, si la cochera va incluida. Anotá lo que te digan.

## Paso 2 · Editar los proyectos que cambiaron

En `portal-data.json`, para cada proyecto con novedad, actualizá lo que
corresponda:

- `precio_desde_usd`, `precio_hasta_usd` — precio de lista (unidad sola).
- `stock` → `{ "n": <nº o null>, "label": "texto corto" }`.
- `estado_raw`, `estado_grupo`, `entrega`.
- `cochera_status`: `"si"` (incluida), `"no"` (aparte), `"nd"` (sin dato).
- Si conseguiste lista por unidad, actualizá `flats_summary` y `typologies`.

**Regla de cochera (clave para comparar bien):** el `$/m²` del portal es
**unidad sola, sin cochera**. Si el precio de lista incluye cochera, restá su
valor antes de calcular `precio_m2` (guardá `precio_lista_usd` +
`ajuste_cochera_usd` + `precio_usd` neto). Un flat solo entra al comparativo si
tiene `comparable_confirmado: true`.

## Paso 3 · Registrar cada interacción en la bitácora

En `meta.bitacora`, agregá **arriba** un objeto por cada conversación:

```json
{ "fecha": "2026-09-15", "proyecto": "Monte Mayor 183", "dev": "Azzurra",
  "tipo": "mensaje", "canal": "WhatsApp", "autor": "Jenniffer",
  "texto": "Qué dijeron, en una o dos líneas." }
```

`tipo`: `mensaje` · `llamada` · `visita` · `web` · `cambio`. Esto alimenta el
Time lapse **y** la frescura (el proyecto vuelve a verde con la fecha nueva).

## Paso 4 · Cerrar el corte (script)

Corré **siempre en seco primero** y leé el reporte de qué se movió:

```bash
python3 scripts/nuevo_corte.py --fecha 2026-09-19 \
  --titulo "Corte 3 · Septiembre" \
  --resumen "Una línea con lo más importante del mes." --dry
```

Si el reporte se ve bien, corré igual **sin `--dry`** para aplicar. El script
fotografía los precios en `precio_hist` (así aparecen las flechas ▲▼), registra
el corte en `meta.cortes` y actualiza fechas y contadores.

## Paso 5 · Validar

```bash
python3 scripts/validar.py
```

Tiene que decir **✅ Integridad OK** con **0 errores**. Si hay errores, corregí
y volvé a correr. No publiques con errores.

## Paso 6 · Refrescar caché

En `index.html`, subí el número de versión (fuerza a los navegadores a bajar la
data nueva):

```
<script src="data/portal-data.js?v=20260919a"></script>
```

## Paso 7 · Publicar

El portal en vivo es el repo **`tamibot/portal-chacarilla`** (GitHub Pages).
Copiá los 3 archivos y publicá:

```bash
# desde una copia del repo live (git clone tamibot/portal-chacarilla)
cp <este-repo>/index.html            .
cp <este-repo>/data/portal-data.js   data/
cp <este-repo>/data/portal-data.json data/
git add -A && git commit -m "Corte N · septiembre" && git push origin main
```

Confirmá que `git rev-parse HEAD` == `git rev-parse origin/main`. GitHub Pages
tarda ~1 minuto en refrescar: <https://tamibot.github.io/portal-chacarilla/>

---

## Recetas rápidas

**Agregar un proyecto nuevo:** copiá el bloque de un proyecto parecido en
`projects`, cambiá `id` (kebab-case único), `name`, `dev`, `addr`, `lat`,
`lng`, `estado_grupo`, precios. Poné `mostrar: true`, `en_cuadrante: true`.
Registralo en la bitácora. Corré validar.py.

**Retirar un proyecto (se agotó):** poné `mostrar: false` — desaparece del portal
pero queda el histórico. No lo borres.

**Marcar un flat como comparable:** en su `flats_summary`, poné
`comparable_confirmado: true` (con `m2`, `precio_usd`, `precio_m2` netos de
cochera). Sale automáticamente en todos los rankings.
