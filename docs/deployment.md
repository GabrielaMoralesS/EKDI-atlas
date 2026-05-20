# Deployment

## Option A: Deploy From `/app`

Use the `app/` folder as the web root.

Expected entry point:

```text
app/index.html
```

Local test:

```bash
cd app
python -m http.server 8000
```

Open:

```text
http://localhost:8000/
```

## Option B: Copy App Contents To `/docs`

For GitHub Pages projects that deploy from `/docs`, copy the contents of `app/` into a repository-level `docs/` publishing folder.

The published structure should contain:

```text
docs/index.html
docs/data/
```

## GitHub Pages Checklist

- [ ] `app/index.html` opens locally.
- [ ] Data loads from relative `./data/...` paths.
- [ ] Critical Gaps are visible.
- [ ] Selected-cell panel works.
- [ ] Expedition CSV export works.
- [ ] Evidence JSON export works.
- [ ] Data Integrity opens.
- [ ] Generate EKDI Atlas opens.
- [ ] About EKDI opens.
- [ ] No EKDI-owned console 404 errors.
- [ ] Large files are documented.

## Large File Note

`data/geo/priority_cells.geojson` is large for public static hosting. For a final public deployment, consider vector tiles, PMTiles or another optimized delivery format.
