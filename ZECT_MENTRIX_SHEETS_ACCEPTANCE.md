# Mentrix Sheets acceptance

Sheets is a Zinnia-owned workbook tool (UX reference only — no third-party branding).

## Operator flow

- Sidebar Mentrix → **Sheets** (`/sheets`)
- Chat prompt → Generate returns workbook JSON `{ sheets: [{ name, cells: { A1: { v, f? } } }] }`
- HTML grid (no AG Grid / Excel COM)
- Import/export XLSX via `openpyxl`
- Formulas stored as text (`f`), never executed in Python
- Optional ContextPack when an active project is set
- Paths must stay under allowed roots `.zect/workbooks/`

## Tests

- `backend/tests/fixes_and_phases/test_mentrix_sheets.py` — mocked 2×3 generate, XLSX round-trip, `..` path escape
- `frontend/src/pages/MentrixSheets.test.tsx` — generate fills A1..C2
