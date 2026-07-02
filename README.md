# Portal Competitivo · Chacarilla del Estanque

Mapa interactivo + análisis de competencia para **Ave. del Sur 220** (Grupo Espacio Urbano).

Sitio 100% estático (HTML + Leaflet, sin build). Funciona en GitHub Pages o en cualquier
host estático; incluye además un micro-servidor Node opcional para correrlo local.

## Qué incluye

- **🗺 Mapa competitivo** — mapa real con calles, el cuadrante de Chacarilla pintado,
  un marcador por proyecto sobre su calle real, tarjeta al pasar el mouse y panel de
  detalle con tipologías y precio por m². Vista lista alternativa con filtros arriba.
- **📊 Estadísticas** — nuestro proyecto primero, resumen del cuadrante y comparativo
  solo con proyectos del cuadrante.
- **💰 Precio por m²** — tabla de flats típicos (pisos intermedios) por nº de dormitorios.
- **📈 Análisis del cuadrante** — precio por m² por tipología, comparativo por proyecto,
  ajuste por cochera y estado de la oferta.
- Ficha individual por proyecto (`proyecto.html?id=...`) con planos, brochure y fuentes.

## Estructura

```
portal-web/
├── index.html            # la app (Leaflet + lógica)
├── proyecto.html         # ficha individual de cada proyecto
├── data/
│   ├── portal-data.json  # datos (fuente única)
│   └── portal-data.js    # mismo dato como window.PORTAL_DATA (lo carga el HTML)
├── assets/               # imágenes, planos y brochures por proyecto
└── server.js             # micro-servidor estático opcional (npm start)
```

## Ver en local

```bash
npm start   # sirve la carpeta en local
# o sin Node:
python3 -m http.server 8080
```

## Datos

- Dirección de cada proyecto verificada una a una dentro del cuadrante.
- Precios y disponibilidad confirmados con los asesores comerciales (jun–jul 2026).
- Tipo de cambio: S/ 3.40 por US$.
- Al actualizar `data/portal-data.*`, subir la versión del query param
  `portal-data.js?v=...` en `index.html` y `proyecto.html` para invalidar la caché.
