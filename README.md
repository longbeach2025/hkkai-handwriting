# hkkai-handwriting

Generate A4 PDF practice sheets for Hong Kong Traditional Chinese ( **Satisfaction v1.0.4** ).
CSV-driven (`part,char,jyut,examples`) → title/footer, Cangjie5 first+last keys, Jyutping,
Cantonese examples, 10×15 mm Mi-grids (×10), subtle watermark.

## Quick Start
1) `pip install -r requirements.txt`
2) Put required assets into `assets/`:
   - `Iansui-Regular.ttf` (body/title font)
   - `SourceHanSerifSC-VF.ttf` (watermark SC font)
   - `cangjie5_hk.txt` (Cangjie5 mapping)
   - `parts.csv` (data, UTF-8 BOM; header: `part,char,jyut,examples`)
3) (Optional) Clean CSV: `python scripts/clean_parts_csv.py`
4) Generate PDFs: `python scripts/gen_hkkai_pdf_v1_0_4.py` → output in `dist/`

## CSV Rules
- Header: `part,char,jyut,examples`
- Each **Part** must have **exactly 15** rows; `char` is a single Han character.
- `jyut` all **lowercase** (`si1`, `jan1`); import to Excel as **Text** to avoid date auto-format.
- Use **Chinese list comma** `、` in `examples`, or wrap with quotes if using English commas.

## Versioning
- Layout parameters are **frozen** in `v1.0.4`. Any visual changes go into a new script
  (e.g. `gen_hkkai_pdf_v1_0_5.py`) so old versions remain reproducible.

## Licenses
- This repository’s **code** is under the license in `/LICENSE`.
- Third-party assets (fonts / mappings) keep **their own licenses**. If unsure, do **not**
  commit binaries—place files locally in `assets/` and document sources here.
