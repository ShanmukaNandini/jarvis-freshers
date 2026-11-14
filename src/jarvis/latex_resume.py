"""Generate clean, compilable LaTeX SOURCE for a tailored resume.

The template reproduces the user's own resume format: Computer Modern,
centered small-caps name block, single-line contact row with pipe separators,
small-caps section headings with a full-width rule underneath, compact
itemize bullets, ~1.9cm margins, no page number - a one-page feel.

Streamlit Cloud has no LaTeX toolchain, so this module only produces .tex
source. The user compiles it themselves, e.g. by pasting it into Overleaf
(https://www.overleaf.com -> New Project -> Blank Project).

Every piece of dynamic content goes through escape_latex. The template uses
only core LaTeX plus geometry and fontenc - no third-party style packages -
so it compiles on any TeX installation, including a minimal one and Overleaf.

Content model: profile facts keep their own text, verbatim - the template
never rewrites a claim, it only places facts into her section layout. Job
-matched facts are listed first within each section (reordering only).
"""

_LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(text):
    """Escape LaTeX special characters in arbitrary (possibly user-supplied) text."""
    return "".join(_LATEX_SPECIALS.get(ch, ch) for ch in str(text))


_HEADER_TMPL = r"""\documentclass[%(size)spt,a4paper]{article}
\usepackage[a4paper,margin=1.9cm]{geometry}
\usepackage[T1]{fontenc}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.5pt}
%% Compact bullet list using only core LaTeX (no enumitem dependency):
\newenvironment{resbullets}{\begin{list}{$\bullet$}{%%
  \setlength{\leftmargin}{1.3em}\setlength{\itemsep}{0pt}%%
  \setlength{\topsep}{1pt}\setlength{\parsep}{0pt}\setlength{\parskip}{0pt}}}
  {\end{list}}
%% Section heading: small caps + full-width rule underneath (her format)
\newcommand{\ressection}[1]{\par\vspace{3pt}{\large\bfseries\scshape #1}\par\vspace{1pt}\hrule\vspace{2pt}}
%% Entry heading: bold title left, location/dates right on the same line
\newcommand{\resentry}[2]{{\bfseries #1}\hfill #2\par\vspace{1pt}}
\begin{document}
"""

_FOOTER = "\\end{document}\n"

# Profile fact sections -> her resume's section headings, in her order.
_SECTION_FLOW = [
    ("Technical Skills", {"skill"}),
    ("Experience", {"experience"}),
    ("Projects", {"project"}),
    ("Education", {"education"}),
    ("Achievements & Additional", {"other"}),
]


def _name_block(profile):
    name = escape_latex(profile.get("name", "Candidate"))
    lines = ["\\begin{center}",
             "{\\huge\\bfseries\\scshape " + name + "}\\\\[2pt]"]
    contact = [escape_latex(x) for x in
               (profile.get("location"), profile.get("phone"), profile.get("email"))
               if x]
    for link in profile.get("links", []) or []:
        contact.append(escape_latex(link))
    if contact:
        lines.append(" $|$ ".join(contact))
    lines.append("\\end{center}")
    return lines


def _skill_line(fact_text):
    """Render one skill fact in her style: a bold 'Label:' prefix when the
    fact has one (e.g. 'Programming: Python, C, SQL'), else a plain line."""
    text = fact_text.strip()
    if ": " in text and len(text.split(": ", 1)[0]) <= 40:
        label, rest = text.split(": ", 1)
        return "\\textbf{" + escape_latex(label) + ":} " + escape_latex(rest) + "\\par"
    return escape_latex(text) + "\\par"


def _entry_tex(entry):
    lines = ["\\resentry{%s}{%s}" % (escape_latex(entry["title"]),
                                      escape_latex(entry.get("right", "")))]
    if entry.get("subtitle"):
        lines.append("{\\itshape " + escape_latex(entry["subtitle"]) + "}\\par")
    if entry["bullets"]:
        lines.append("\\begin{resbullets}")
        for b in entry["bullets"]:
            lines.append(f"  \\item {escape_latex(b)}")
        lines.append("\\end{resbullets}")
    lines.append("\\vspace{1pt}")
    return lines


def generate_tex(profile, tailored):
    """Build a complete, standalone .tex document for the tailored resume.

    profile: BASE_RESUME-shaped dict (contact fields + facts, optional entries)
    tailored: output of core.tailor_resume_for_job(profile, job)
    Returns the full LaTeX source as a string. When the profile has entries
    (uploaded resumes), the document structure is preserved: every project
    renders whole, with its own description bullets, entries ordered by match.
    Font size is chosen so the result fits one page (11pt, 10pt if needed).
    """
    from jarvis.core import _ordered_facts, choose_font_size, loose_section_facts

    body = [_HEADER_TMPL % {"size": choose_font_size(profile, tailored)}]
    body += _name_block(profile)

    # Professional Summary
    body.append("\\ressection{Professional Summary}")
    body.append(escape_latex(tailored["summary"]))

    skill_facts = _ordered_facts(profile, tailored, {"skill"})
    skill_lines = tailored.get("skill_lines", {})
    if skill_facts:
        body.append("\\ressection{Technical Skills}")
        body += [_skill_line(skill_lines.get(f["id"], f["text"])) for f in skill_facts]

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
            body.append(f"\\ressection{{{escape_latex(heading)}}}")
            for entry in group:
                body += _entry_tex(entry)
            if loose:
                body.append("\\begin{resbullets}")
                for f in loose:
                    body.append(f"  \\item {escape_latex(f['text'])}")
                body.append("\\end{resbullets}")
        other = [f for f in profile["facts"] if f.get("section") == "other"
                 and f.get("role") in ("bullet", "line")]
        if other:
            body.append("\\ressection{Achievements \\& Leadership}")
            body.append("\\begin{resbullets}")
            for f in other:
                body.append(f"  \\item {escape_latex(f['text'])}")
            body.append("\\end{resbullets}")
        body.append(_FOOTER)
        return "\n".join(body)

    for heading, sections in _SECTION_FLOW:
        if sections == {"skill"}:
            continue  # already rendered above
        facts = _ordered_facts(profile, tailored, sections)
        if not facts:
            continue
        body.append(f"\\ressection{{{escape_latex(heading)}}}")
        body.append("\\begin{resbullets}")
        for fact in facts:
            body.append(f"  \\item {escape_latex(fact['text'])}")
        body.append("\\end{resbullets}")

    body.append(_FOOTER)
    return "\n".join(body)
