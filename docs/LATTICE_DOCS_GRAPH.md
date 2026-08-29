# Lattice Documentation Graph

ZECT **Lattice** graphifies code repos (symbols, imports, calls, routes) and, when enabled, **markdown documentation** as a wikilink graph inspired by [brain-map](https://github.com/zubair-trabzada/brain-map) patterns — **reference only**, not a runtime dependency.

## Two layers

| Layer | Source | Node kinds | Edge kinds |
|-------|--------|------------|------------|
| **Code** | `.py`, `.ts`, `.js`, … | file, class, function, endpoint | imports, calls, contains |
| **Docs** | `.md`, `.mdx` | doc, folder, vault | wikilink, md_link, in_folder, references |

Brain-map is **not** used to replace code graphify. It informs the docs ingest algorithm (wikilink regex, stem map, folder tree).

## Ingest

```http
POST /api/lattice/ingest
{ "path": "C:\\repos\\my-service", "index_docs": true }
```

Set `LATTICE_INDEX_DOCS=0` in `backend/.env` to skip docs layer.

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/lattice/graph?layer=combined\|code\|docs` | Filtered graph |
| `GET /api/lattice/graph/backlinks?doc=path/to.md` | Inbound wikilinks |
| `POST /api/lattice/query` | Search with optional `kinds[]`, `include_backlinks` |

## UI

`/lattice` — layer toggle (Code | Docs | Combined) and interactive force-directed graph. Click a node to highlight neighbors; search to fly-to.

## Mentrix voice

- "Open Lattice docs" → `/lattice?layer=docs`
- "Lattice query wiki Delivery" → `lattice_query` with doc kinds + backlink artifact
- Code symbol search unchanged on code layer

## Stats

Blueprint and graph JSON include `doc_files_indexed`, `wikilinks_resolved`, `wikilinks_unresolved`.
