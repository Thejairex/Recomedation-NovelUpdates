# AGENTS.md — NovelUpdates Recommender

## Descripción del proyecto

Sistema de recomendación de novelas web personalizado que scrapea NovelUpdates, analiza las novelas seguidas por el usuario y genera recomendaciones usando similitud coseno sobre vectores de tags y géneros.

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| API | FastAPI |
| ORM | SQLAlchemy (async) |
| Base de datos | SQLite3 (Desarrollo), PostgreSQL (Produccion) |
| Scraping | requests + BeautifulSoup4 |
| Recomendación | pandas + scikit-learn |
| Contenedores | Docker + docker-compose |
| Migraciones | Alembic |

## Estructura del proyecto

```
novelupdates-recommender/
├── main.py                  # FastAPI app y endpoints
├── config.py                # Settings via pydantic-settings (.env)
├── database.py              # SQLAlchemy engine, sesión async
├── models.py                # Modelos ORM: Novel, Tag, Candidate, Recommendation
├── schemas.py               # Pydantic schemas request/response
├── scraper.py               # Lógica de scraping (reading list, series, finder)
├── recommender.py           # Vectorización TF-IDF + similitud coseno
├── alembic/                 # Migraciones de base de datos
│   └── versions/
├── docker-compose.yml       # Servicios: api + postgres
├── Dockerfile
├── requirements.txt
├── .env                     # Variables de entorno (NO commitear)
├── .env.example             # Plantilla de variables de entorno
└── .gitignore
```

## Archivos existentes y su responsabilidad

### `config.py`
- Usa `pydantic-settings` para leer variables del `.env`
- Expone: `DATABASE_URL`, `NU_SESSION_COOKIE`, `TOP_N_RECOMMENDATIONS`, `CANDIDATE_PAGES`, `CACHE_TTL_HOURS`
- La cookie de sesión de NovelUpdates va aquí — nunca hardcodear

### `database.py`
- Configura `AsyncEngine` y `AsyncSession` de SQLAlchemy
- Provee `get_db()` como dependency de FastAPI
- Función `create_tables()` para desarrollo (en producción usar Alembic)

### `models.py`
Tablas principales:

| Tabla | Descripción |
|---|---|
| `novels` | Novelas del usuario (título, slug, lista de origen, peso) |
| `tags` | Catálogo único de tags y géneros |
| `novel_tags` | Relación M2M entre `novels` y `tags` |
| `candidates` | Novelas candidatas del Series Finder |
| `candidate_tags` | Relación M2M entre `candidates` y `tags` |
| `recommendations` | Últimas recomendaciones generadas con score y timestamp |

### `scraper.py`
Tres responsabilidades:

1. **`fetch_reading_list()`** — Descarga y parsea el XML de export de NovelUpdates (`/export-reading-list/`) usando la cookie de sesión. Retorna lista de `{title, list_name}`.

2. **`fetch_novel_metadata(slug)`** — Dado el slug de una novela, scrapea su página (`/series/<slug>/`) y extrae géneros y tags.

3. **`fetch_candidates(pages)`** — Scrapea el Series Finder (`/series-finder/`) paginado. Extrae título, slug, géneros y tags de cada novela candidata.

**Reglas de scraping:**
- Usar `requests.Session` con la cookie `NU_SESSION_COOKIE` en cada request
- Rate limiting: `time.sleep(1)` entre requests para no sobrecargar el servidor
- Reintentos: máximo 3 intentos con backoff exponencial ante errores 429 o 5xx
- User-Agent: usar un User-Agent real de navegador

### `recommender.py`
Pipeline de recomendación:

1. **Construir perfil del usuario**: frecuencia de tags ponderada por lista
   - `Best the Best` → peso **3**
   - `Reading`, `Completed`, `On Hold` → peso **1**
   - `Plan to Read`, `Dropped` → **ignorar**

2. **Vectorizar con TF-IDF**: usar `TfidfVectorizer` de scikit-learn sobre el corpus de tags

3. **Calcular similitud coseno**: entre el vector del usuario y cada candidata

4. **Filtrar**: excluir novelas que ya están en las listas del usuario

5. **Retornar top N** ordenadas por score descendente

### `main.py`
Endpoints REST:

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/scrape/my-novels` | Dispara scraping de la reading list (BackgroundTask) |
| `POST` | `/scrape/candidates` | Dispara scraping del Series Finder (BackgroundTask) |
| `POST` | `/recommend` | Genera y persiste recomendaciones |
| `GET` | `/recommend` | Devuelve las últimas recomendaciones guardadas |
| `GET` | `/status` | Estado actual del scraping en progreso |
| `GET` | `/health` | Health check del servicio |

## Variables de entorno (`.env.example`)

```env
# Base de datos
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/novelupdates_recommender

# NovelUpdates — cookie de sesión del navegador
# Cómo obtenerla: DevTools → Application → Cookies → novelupdates.com
# Buscar la cookie que empieza con "wordpress_logged_in_"
NU_SESSION_COOKIE=wordpress_logged_in_xxxx=valor_de_la_cookie

# Configuración del recomendador
TOP_N_RECOMMENDATIONS=20
CANDIDATE_PAGES=10

# TTL del caché en horas (0 = sin caché)
CACHE_TTL_HOURS=24
```

## Docker

### `docker-compose.yml`
Dos servicios:
- **`db`**: PostgreSQL 15, datos persistidos en volumen `postgres_data`
- **`api`**: FastAPI con hot-reload en desarrollo, depende de `db`

### Comandos útiles

```bash
# Levantar el stack completo
docker-compose up --build

# Correr migraciones
docker-compose exec api alembic upgrade head

# Ver logs de la API
docker-compose logs -f api

# Acceder a la DB
docker-compose exec db psql -U user -d novelupdates_recommender
```

## Flujo de uso completo

```
1. Copiar .env.example → .env y completar NU_SESSION_COOKIE
2. docker-compose up --build
3. POST /scrape/my-novels   → scrapea tu reading list y persiste en DB
4. POST /scrape/candidates  → scrapea Series Finder y persiste candidatas
5. POST /recommend          → genera recomendaciones y las guarda
6. GET  /recommend          → obtiene las top 20 recomendaciones
```

## Cómo obtener la cookie de sesión

1. Ir a [novelupdates.com](https://www.novelupdates.com) e iniciar sesión
2. Abrir DevTools (`F12`) → pestaña **Application** (Chrome) o **Storage** (Firefox)
3. Ir a **Cookies** → `https://www.novelupdates.com`
4. Copiar el **valor** de la cookie `wordpress_logged_in_...`
5. Pegarlo en `NU_SESSION_COOKIE` del `.env`

> ⚠️ La cookie expira si cerrás sesión. Si el scraper falla con 401/403, renovarla.

## Convenciones de código

- **Python 3.11+**
- Type hints en todas las funciones
- Async/await para operaciones de DB y HTTP donde sea posible
- Logging con el módulo estándar `logging`, nivel configurable por env var
- No usar `print()` — usar `logger.info()` / `logger.error()`
- Errores de scraping: loguear y continuar (no detener todo el proceso por una novela)

## Notas importantes para el agente

- **No commitear `.env`** — está en `.gitignore`
- El XML de export de NovelUpdates trae: título, lista de origen, capítulos. **No trae slug ni tags** — hay que buscar el slug via search (`/?s=titulo&post_type=seriesplan`) y luego scrapear la página de la novela
- El Series Finder puede ser lento — paginar de a 1 con delay de 1s entre requests
- `Best the Best` es una lista personalizada del usuario, no una lista estándar de NovelUpdates
- Las listas a ignorar en el perfil son: `Plan to Read` y `Dropped`
- En producción usar Alembic para migraciones, no `create_tables()` directo