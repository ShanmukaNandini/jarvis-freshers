"""Pure-Python PDF renderer for the tailored resume - the SAME template as the
.tex output (centered small-caps name, pipe contact row, ruled small-caps
section headings, bold entry headings with right-aligned dates, compact
bullets, 1.9cm margins, one page), produced with fpdf2 and the OFL-licensed
Latin Modern Roman fonts bundled under assets/fonts/, so the PDF genuinely
looks like the LaTeX original.

Streamlit Cloud has no LaTeX toolchain; this module needs none. The .tex
download stays available alongside the PDF.

Content model is identical to latex_resume.generate_tex: facts keep their own
text verbatim; entries render whole; font size follows the same one-page rule.
"""
from pathlib import Path

from fpdf import FPDF

from jarvis.core import _ordered_facts, choose_font_size, loose_section_facts

_FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
_MARGIN = 19  # mm, 1.9cm like the .tex template
_PAGE_W = 210


def _register_fonts(pdf):
    """Register Latin Modern Roman (regular/bold/italic/caps). Returns False
    (caller falls back to a core serif) if the bundled fonts are missing."""
    files = {"LM": "lmroman12-regular.ttf", "LM-B": "lmroman12-bold.ttf",
             "LM-I": "lmroman12-italic.ttf", "LMC": "lmromancaps10-regular.ttf"}
    if not all((_FONT_DIR / f).exists() for f in files.values()):
        return False
    pdf.add_font("LM", "", str(_FONT_DIR / files["LM"]))
    pdf.add_font("LM", "B", str(_FONT_DIR / files["LM-B"]))
    pdf.add_font("LM", "I", str(_FONT_DIR / files["LM-I"]))
    pdf.add_font("LMC", "", str(_FONT_DIR / files["LMC"]))
    return True


def _fonts(pdf, have_lm):
    """Map logical styles onto registered families (or the Times fallback)."""
    if have_lm:
        return {"reg": ("LM", ""), "bold": ("LM", "B"),
                "italic": ("LM", "I"), "caps": ("LMC", "")}
    return {"reg": ("times", ""), "bold": ("times", "B"),
            "italic": ("times", "I"), "caps": ("times", "B")}


def _use(pdf, fonts, key, size):
    family, style = fonts[key]
    pdf.set_font(family, style, size)


def _section(pdf, fonts, size, text):
    pdf.ln(1.2)
    _use(pdf, fonts, "caps", size + 3)
    pdf.cell(0, 5.4, text, new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 0.4
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.3)
    pdf.line(_MARGIN, y, _PAGE_W - _MARGIN, y)
    pdf.set_y(y + 1.2)


def _skill_line(pdf, fonts, size, line_h, text):
    text = text.strip()
    if ": " in text and len(text.split(": ", 1)[0]) <= 40:
        label, rest = text.split(": ", 1)
        _use(pdf, fonts, "bold", size)
        label_txt = label + ": "
        pdf.cell(pdf.get_string_width(label_txt), line_h, label_txt)
        _use(pdf, fonts, "reg", size)
        pdf.multi_cell(0, line_h, rest, new_x="LMARGIN", new_y="NEXT")
    else:
        _use(pdf, fonts, "reg", size)
        pdf.multi_cell(0, line_h, text, new_x="LMARGIN", new_y="NEXT")


def _bullets(pdf, fonts, size, line_h, bullets):
    width = _PAGE_W - 2 * _MARGIN
    for b in bullets:
        pdf.set_x(_MARGIN + 2)
        _use(pdf, fonts, "reg", size)
        pdf.cell(4, line_h, "\u2022")
        saved = pdf.l_margin
        pdf.l_margin = _MARGIN + 6
        pdf.set_x(_MARGIN + 6)
        pdf.multi_cell(width - 6, line_h, b, new_x="LMARGIN", new_y="NEXT")
        pdf.l_margin = saved
    pdf.ln(0.8)


def _entry(pdf, fonts, size, line_h, entry):
    width = _PAGE_W - 2 * _MARGIN
    _use(pdf, fonts, "bold", size)
    title = entry["title"]
    right = entry.get("right", "")
    if right:
        _use(pdf, fonts, "reg", size)
        right_w = pdf.get_string_width(right)
        _use(pdf, fonts, "bold", size)
        pdf.cell(width - right_w - 2, line_h, title)
        _use(pdf, fonts, "reg", size)
        pdf.cell(right_w + 2, line_h, right, align="R",
                 new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(width, line_h, title, new_x="LMARGIN", new_y="NEXT")
    if entry.get("subtitle"):
        _use(pdf, fonts, "italic", size)
        pdf.multi_cell(width, line_h, entry["subtitle"],
                       new_x="LMARGIN", new_y="NEXT")
    _bullets(pdf, fonts, size, line_h, entry["bullets"])


def generate_pdf(profile, tailored):
    """Render the tailored resume to a one-page PDF. Returns bytes."""
    size = choose_font_size(profile, tailored)
    line_h = 4.4 if size == 11 else 4.0

    pdf = FPDF(unit="mm", format="A4")
    pdf.set_margins(_MARGIN, _MARGIN, _MARGIN)
    pdf.set_auto_page_break(False)
    pdf.add_page()
    have_lm = _register_fonts(pdf)
    fonts = _fonts(pdf, have_lm)
    width = _PAGE_W - 2 * _MARGIN

    # Name block (small caps) + single-line pipe-separated contact row
    _use(pdf, fonts, "caps", 21 if size == 11 else 19)
    pdf.cell(0, 8, profile.get("name", "Candidate"),
             align="C", new_x="LMARGIN", new_y="NEXT")
    contact = [x for x in (profile.get("location"), profile.get("phone"),
                           profile.get("email")) if x]
    contact += list(profile.get("links") or [])
    if contact:
        _use(pdf, fonts, "reg", size - 0.5)
        pdf.multi_cell(0, line_h, " | ".join(contact), align="C",
                       new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.2)

    _section(pdf, fonts, size, "Professional Summary")
    _use(pdf, fonts, "reg", size)
    pdf.multi_cell(width, line_h, tailored["summary"],
                   new_x="LMARGIN", new_y="NEXT")

    skill_facts = _ordered_facts(profile, tailored, {"skill"})
    skill_lines = tailored.get("skill_lines", {})
    if skill_facts:
        _section(pdf, fonts, size, "Technical Skills")
        for f in skill_facts:
            _skill_line(pdf, fonts, size, line_h, skill_lines.get(f["id"], f["text"]))

    if profile.get("entries"):
        by_id = {e["id"]: e for e in profile["entries"]}
        view = tailored.get("entry_view") or \
            [by_id[eid] for eid in tailored.get("entry_order", []) if eid in by_id]
        for heading, sec_key in (("Experience", "experience"),
                                 ("Projects", "project"),
                                 ("Education", "education")):
            group = [e for e in view if e["section"] == sec_key]
            loose = loose_section_facts(profile, sec_key)
            if not group and not loose:
                continue
            _section(pdf, fonts, size, heading)
            for entry in group:
                _entry(pdf, fonts, size, line_h, entry)
            if loose:
                _bullets(pdf, fonts, size, line_h, [f["text"] for f in loose])
        other = [f for f in profile["facts"] if f.get("section") == "other"
                 and f.get("role") in ("bullet", "line")]
        if other:
            _section(pdf, fonts, size, "Achievements & Leadership")
            _bullets(pdf, fonts, size, line_h, [f["text"] for f in other])
    else:
        for heading, sections in (("Experience & Projects", {"experience", "project"}),
                                  ("Education", {"education"}),
                                  ("Achievements & Additional", {"other"})):
            facts = _ordered_facts(profile, tailored, sections)
            if not facts:
                continue
            _section(pdf, fonts, size, heading)
            _bullets(pdf, fonts, size, line_h, [f["text"] for f in facts])

    return bytes(pdf.output())
