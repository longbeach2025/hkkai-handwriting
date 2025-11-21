# -*- coding: utf-8 -*-
# 批量生成「繁體手寫百日計劃」PDF —— 满意版 1.0.4
# 数据来源：assets/parts.csv（列：part,char,jyut,examples）
# 版式：A4 竖版；每 part 2 页（Page1=7 条有标题，Page2=8 条无标题）
# 要点：15 mm 米字格（10 个）、简体斜 30°水印、页脚「繁體手寫百日計劃 Part X - Page Y」、
#       Cangjie5_HK 首尾码显示为「形旁 (键) + 形旁 (键)」

import os, io, csv, re
from pathlib import Path
from collections import defaultdict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

# ========= 1) 路径（请改成你的实际路径） =========
BASE        = Path(r"C:\HKKaiPlan")
ASSETS      = BASE / "assets"
OUTDIR      = BASE / "out"            # 输出目录
CSV_PATH    = ASSETS / "parts.csv"    # 主 CSV：part,char,jyut,examples
CJ5_PATH    = ASSETS / "cangjie5_hk.txt"
FONT_IANSUI = ASSETS / "Iansui-Regular.ttf"              # 正文/标题
FONT_SC     = ASSETS / "SourceHanSerifSC-VF.ttf"         # 水印简体

OUT_NAME_PATTERN = "百日計劃_Part{part}_v1.0.4_fixedCJ5_簡體水印版.pdf"  # 输出文件命名模板

# ========= 2) 路径校验 =========
OUTDIR.mkdir(parents=True, exist_ok=True)
for p, label in [(CSV_PATH, "主 CSV parts.csv"),
                 (CJ5_PATH, "Cangjie5 碼表"),
                 (FONT_IANSUI, "Iansui-Regular.ttf"),
                 (FONT_SC, "SourceHanSerifSC-VF.ttf")]:
    if not p.is_file():
        raise SystemExit(f"[ERR] 找不到 {label}：{p}")

# ========= 3) 字体注册 =========
pdfmetrics.registerFont(TTFont("Iansui", str(FONT_IANSUI)))
pdfmetrics.registerFont(TTFont("SHSerifSC", str(FONT_SC)))

# ========= 4) 版式常量（锁定 1.0.4） =========
PAGE_W, PAGE_H = A4
MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 18*mm, 12*mm, 16*mm, 16*mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

col_char     = 24*mm
col_jyut     = 24*mm
col_decomp   = 60*mm
col_examples = CONTENT_W - (col_char + col_jyut + col_decomp)

content_row_h   = 11*mm
practice_row_h  = 17*mm
between_entries = 1*mm

BOX_SIZE_MM = 15   # 米字格大小（mm）
BOX_GAP_MM  = 2    # 格间隙（mm）
BOX_SIZE    = BOX_SIZE_MM * mm
BOX_GAP     = BOX_GAP_MM  * mm

# ========= 5) Cangjie5 首尾码 =========
CJ5_NAME = {"A":"日","B":"月","C":"金","D":"木","E":"水","F":"火","G":"土","H":"竹","I":"戈","J":"十",
            "K":"大","L":"中","M":"一","N":"弓","O":"人","P":"心","Q":"手","R":"口","S":"尸","T":"廿",
            "U":"山","V":"女","W":"田","X":"難","Y":"卜","Z":"重"}

def show_fl(code: str) -> str:
    letters = re.findall(r'[A-Za-z]', code or "")
    if not letters: return "—"
    a, b = letters[0].upper(), letters[-1].upper()
    return f"{CJ5_NAME.get(a, a)} ({a}) + {CJ5_NAME.get(b, b)} ({b})"

def load_cj5_robust(path):
    d = {}
    with io.open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split("\t")
            # 1) char \t code
            if len(parts) == 2 and len(parts[0]) == 1 and re.fullmatch(r"[A-Za-z]+", parts[1]):
                ch, code = parts[0], parts[1].upper()
                d[ch] = code
                continue
            # 2) code \t chars
            if len(parts) == 2 and re.fullmatch(r"[A-Za-z]+", parts[0]):
                code = parts[0].upper()
                for ch in parts[1]:
                    if ch.strip():
                        d.setdefault(ch, code)
                continue
            # fallback
            segs = s.split()
            if len(segs) >= 2:
                if len(segs[0]) == 1 and re.fullmatch(r"[A-Za-z]+", segs[1]):
                    d[segs[0]] = segs[1].upper()
                elif re.fullmatch(r"[A-Za-z]+", segs[0]):
                    code = segs[0].upper()
                    for ch in "".join(segs[1:]):
                        if ch.strip():
                            d.setdefault(ch, code)
    return d

CJ = load_cj5_robust(str(CJ5_PATH))

# ========= 6) 读 CSV（更耐脏版本） =========
import io, csv, re

def normalize_jyut(s: str) -> str:
    """把被 Excel 误识别为日期的粤拼修回，并统一小写：Jan-01 -> jan1；si1/ze6 不受影响"""
    t = (s or "").strip()
    t = t.replace("-", "").replace("/", "").replace(" ", "")
    t = t.lower()
    t = re.sub(r'([a-z]+)0([1-6])$', r'\1\2', t)
    return t

def _read_text_flex(path: Path) -> str:
    """容错读取文本：优先 utf-8-sig，再 utf-8，最后本地 mbcs(ANSI/GBK)"""
    tried = []
    for enc in ("utf-8-sig", "utf-8", "mbcs"):
        try:
            with io.open(path, "r", encoding=enc) as f:
                return f.read()
        except Exception as e:
            tried.append(f"{enc}:{e.__class__.__name__}")
    raise SystemExit(f"[ERR] 打不开 CSV：{path}\n尝试编码失败：{' ; '.join(tried)}")

def read_parts(csv_path: Path):
    raw = _read_text_flex(csv_path)
    # 统一换行
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")

    # 自动嗅探分隔符（逗号/分号/制表符）
    first_line = raw.split("\n", 1)[0]
    try:
        dialect = csv.Sniffer().sniff(first_line, delimiters=",;\t")
        delim = dialect.delimiter
    except Exception:
        delim = ","  # 兜底用逗号

    # 先用 csv.reader 拿“原始行”，以便处理 examples 中未加引号的英文逗号
    reader = csv.reader(io.StringIO(raw), delimiter=delim)
    rows = list(reader)
    if not rows:
        raise SystemExit("[ERR] CSV 为空。")

    header = [h.strip().lower() for h in rows[0]]
    need = ["part", "char", "jyut", "examples"]
    if not set(need).issubset(set(header)):
        raise SystemExit(f"[ERR] 表头不完整：{rows[0]}（需包含 {need}）")

    # 建立列索引
    idx = {name: header.index(name) for name in need}

    by_part = defaultdict(list)
    for lineno, r in enumerate(rows[1:], start=2):
        # 去掉行尾空列（有些编辑器会加多余分隔符）
        while r and r[-1] == "":
            r.pop()

        if len(r) < 3:
            raise SystemExit(f"[ERR] 第{lineno}行列数过少：{r}")

        # 安全取前三列；examples 可能被切成多列，则合并回去
        try:
            part_str = r[idx["part"]].strip() if idx["part"] < len(r) else ""
            char     = r[idx["char"]].strip() if idx["char"] < len(r) else ""
            jyut     = r[idx["jyut"]].strip() if idx["jyut"] < len(r) else ""
            # examples：把从 examples 索引开始的所有剩余列重新拼成一个字段
            if idx["examples"] < len(r):
                tail = r[idx["examples"]:]
                examples = delim.join(t.strip() for t in tail if t is not None)
            else:
                examples = ""
        except Exception:
            raise SystemExit(f"[ERR] 第{lineno}行解析失败：{r}")

        if not (part_str and char and jyut and examples):
            raise SystemExit(f"[ERR] CSV 有缺失（第{lineno}行）：{r}（需含 part,char,jyut,examples）")

        # part 转 int
        try:
            p = int(part_str)
        except:
            raise SystemExit(f"[ERR] 第{lineno}行 part 非整数：{part_str}")

        # char 必须是单字
        if len(char) != 1:
            raise SystemExit(f"[ERR] 第{lineno}行 char 不是单个字：{char}")

        # 粤拼自愈（修 Excel 日期、小写化）
        jyut = normalize_jyut(jyut)

        # 去掉 examples 外层成对引号（如果有）
        if (examples.startswith('"') and examples.endswith('"')) or (examples.startswith("'") and examples.endswith("'")):
            examples = examples[1:-1]

        by_part[p].append((char, jyut, examples))

    # 校验每个 part 恰好 15 条
    bad = [p for p, items in by_part.items() if len(items) != 15]
    if bad:
        det = ", ".join([f"Part {p}={len(by_part[p])}" for p in sorted(bad)])
        raise SystemExit(f"[ERR] 每个 Part 必须 15 行：{det}")

    return by_part

# ========= 7) 绘制工具 =========
def draw_title(c, part_no):
    c.setFont("Iansui", 20)
    title = f"繁體手寫百日計劃 Part {part_no}"
    c.drawString(MARGIN_L, PAGE_H - MARGIN_T - 6*mm, title)
    c.setStrokeColor(colors.black); c.setLineWidth(0.5)
    c.line(MARGIN_L, PAGE_H - MARGIN_T - 10*mm, PAGE_W - MARGIN_R, PAGE_H - MARGIN_T - 10*mm)

def draw_table_header(c, top_offset_mm, with_title=False, part_no=None):
    if with_title and part_no is not None:
        draw_title(c, part_no)
    y = PAGE_H - MARGIN_T - top_offset_mm*mm
    c.setFont("Iansui", 11)
    x = MARGIN_L
    c.drawString(x + 2*mm, y, "字"); x += col_char
    c.drawString(x + 2*mm, y, "粵拼"); x += col_jyut
    c.drawString(x + 2*mm, y, "拆解（首尾碼）"); x += col_decomp
    c.drawString(x + 2*mm, y, "常用例詞")
    c.line(MARGIN_L, y-2*mm, PAGE_W - MARGIN_R, y-2*mm)
    return y - 4*mm

def draw_mizige(c, x, y_top, size):
    c.rect(x, y_top - size, size, size, stroke=1, fill=0)
    c.setStrokeColorRGB(0.75,0.75,0.75); c.setLineWidth(0.3)
    c.line(x + size/2, y_top, x + size/2, y_top - size)
    c.line(x, y_top - size/2, x + size, y_top - size/2)
    c.line(x, y_top, x + size, y_top - size)
    c.line(x + size, y_top, x, y_top - size)
    c.setStrokeColor(colors.black); c.setLineWidth(0.5)

def draw_practice_line_centered(c, y_base):
    total_w = 10*BOX_SIZE + 9*BOX_GAP
    start_x = MARGIN_L + (CONTENT_W - total_w)/2
    for i in range(10):
        x = start_x + i*(BOX_SIZE + BOX_GAP)
        draw_mizige(c, x, y_base, BOX_SIZE)

def draw_entry(c, y_top, ch, jyut, examples, cjmap):
    x = MARGIN_L
    c.setFont("Iansui", 17)
    c.drawCentredString(x + col_char/2, y_top, ch); x += col_char

    c.setFont("Iansui", 11)
    c.drawString(x + 2*mm, y_top, jyut); x += col_jyut

    c.drawString(x + 2*mm, y_top, show_fl(cjmap.get(ch, ""))); x += col_decomp

    # 例詞截断防溢出
    max_w = col_examples - 2*mm
    t = examples
    while c.stringWidth(t, "Iansui", 11) > max_w and len(t) > 3:
        t = t[:-2] + "…"
    c.drawString(x + 2*mm, y_top, t)

    draw_practice_line_centered(c, y_top - 3*mm)

def draw_footer(c, part_no, page_no):
    c.setFont("Iansui", 10)
    c.drawCentredString(PAGE_W/2, MARGIN_B/2, f"繁體手寫百日計劃 Part {part_no} - Page {page_no}")

def draw_watermark_sc(c):
    c.saveState()
    c.setFont("SHSerifSC", 44)
    c.setFillColorRGB(0.86, 0.86, 0.86)    # 浅灰
    c.translate(PAGE_W/2, PAGE_H/2)
    c.rotate(30)
    c.drawCentredString(0, 0, "更多内容搜公号港学圈")
    c.restoreState()

# ========= 8) 生成单个 Part =========
def render_part(part_no: int, items, cjmap):
    out_pdf = OUTDIR / OUT_NAME_PATTERN.format(part=part_no)
    c = canvas.Canvas(str(out_pdf), pagesize=A4)
    c.setAuthor("Iansui practice pack")
    c.setTitle(f"繁體手寫百日計劃 Part {part_no}（簡體水印）")

    # Page 1（7条，带标题）
    draw_watermark_sc(c)
    y = draw_table_header(c, top_offset_mm=16, with_title=True, part_no=part_no)
    yc = y
    for ch,jy,ex in items[:7]:
        yc -= content_row_h
        draw_entry(c, yc, ch, jy, ex, cjmap)
        yc -= (practice_row_h + between_entries)
    draw_footer(c, part_no, 1)
    c.showPage()

    # Page 2（8条，无标题）
    draw_watermark_sc(c)
    y = draw_table_header(c, top_offset_mm=8, with_title=False)
    yc = y
    for ch,jy,ex in items[7:]:
        yc -= content_row_h
        draw_entry(c, yc, ch, jy, ex, cjmap)
        yc -= (practice_row_h + between_entries)
    draw_footer(c, part_no, 2)
    c.save()
    print(f"[OK] 生成：{out_pdf}")

# ========= 9) 主流程 =========
def main():
    by_part = read_parts(CSV_PATH)
    for part_no in sorted(by_part.keys()):
        render_part(part_no, by_part[part_no], CJ)

if __name__ == "__main__":
    main()
    print("[DONE] 全部生成完成。")

