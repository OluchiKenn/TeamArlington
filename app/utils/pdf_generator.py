# app/utils/pdf_generator.py
import json
import os
import subprocess
from datetime import datetime
from typing import List, Dict, Any

from app.models import Request  # type: ignore


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _latex_escape(s: str) -> str:
    # Minimal LaTeX escaping
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = []
    for ch in s:
        out.append(replacements.get(ch, ch))
    return "".join(out)


def _render_form_fields(fields: Dict[str, Any]) -> str:
    lines = ["\\begin{itemize}"]
    for k, v in fields.items():
        key = _latex_escape(str(k))
        val = _latex_escape(json.dumps(v) if isinstance(v, (dict, list)) else str(v))
        lines.append(f"  \\item \\textbf{{{key}}}: {val}")
    lines.append("\\end{itemize}")
    return "\n".join(lines)


def generate_request_pdf(request: Request, signature_paths: List[str]) -> str:
    """
    Generate a PDF for a Request using LaTeX and Makefile integration.

    Returns absolute path to the generated PDF.
    Raises RuntimeError if LaTeX compilation fails.
    """
    # Determine repo root and latex dir
    utils_dir = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(utils_dir, os.pardir, os.pardir))
    latex_dir = os.path.join(repo_root, "latex_templates")
    _ensure_dir(latex_dir)

    # Build names
    form_type = (getattr(getattr(request, "form_template", None), "form_code", None) or
                 getattr(getattr(request, "form_template", None), "name", None) or
                 "form").upper().replace(" ", "_")
    req_id = getattr(request, "id", "unknown")
    base_name = f"{form_type}_{req_id}"
    tex_path = os.path.join(latex_dir, f"{base_name}.tex")
    pdf_path = os.path.join(latex_dir, f"{base_name}.pdf")

    # Resolve form data from our model (supports .form_data_json or .form_data)
    form_data_raw = None
    if hasattr(request, "form_data_json"):
        form_data_raw = getattr(request, "form_data_json")
    elif hasattr(request, "form_data"):
        form_data_raw = getattr(request, "form_data")

    if isinstance(form_data_raw, str):
        form_data = json.loads(form_data_raw or "{}")
    elif isinstance(form_data_raw, dict):
        form_data = form_data_raw
    else:
        form_data = {}

    # Submitter and date
    submitter_name = _latex_escape(getattr(getattr(request, "requester", None), "name", "Unknown"))
    submitted_at = getattr(request, "submitted_at", None)
    submitted_date = submitted_at.strftime("%Y-%m-%d %H:%M UTC") if isinstance(submitted_at, datetime) and submitted_at else datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Prepare relative signature paths from latex_dir
    rel_sigs: List[str] = []
    for p in signature_paths or []:
        if not p:
            continue
        abs_p = p
        if not os.path.isabs(abs_p):
            abs_p = os.path.join(repo_root, p)
        if os.path.exists(abs_p):
            rel = os.path.relpath(abs_p, latex_dir)
            rel_sigs.append(rel)

    # Write Makefile if missing
    makefile_path = os.path.join(latex_dir, "Makefile")
    if not os.path.exists(makefile_path):
        makefile_contents = (
            "PDFLATEX=pdflatex\n"
            ".SUFFIXES: .tex .pdf\n"
            "%.pdf: %.tex\n\t$(PDFLATEX) -interaction=nonstopmode -halt-on-error $< > build.log 2>&1\n"
            "\nclean:\n\trm -f *.aux *.log *.out *.toc build.log\n"
        )
        with open(makefile_path, "w", encoding="utf-8") as mf:
            mf.write(makefile_contents)

    # Compose LaTeX document
    fields_block = _render_form_fields(form_data)
    signatures_block = "\n".join(
        [f"\\includegraphics[width=0.35\\textwidth]{{{_latex_escape(sig)}}}" for sig in rel_sigs]
    ) if rel_sigs else "\\emph{No signatures provided}"

    latex = f"""\\documentclass[11pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}
\\usepackage[T1]{{fontenc}}
\\usepackage[utf8]{{inputenc}}
\\title{{{_latex_escape(form_type.replace('_', ' '))} Request}}
\\date{{{_latex_escape(submitted_date)}}}
\\begin{{document}}
\\maketitle
\\section*{{Submitter}}
\\textbf{{Name}}: {submitter_name} \\\\
\\section*{{Form Data}}
{fields_block}
\\section*{{Signatures}}
{signatures_block}
\\end{{document}}
"""

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex)

    # Run make to build PDF
    result = subprocess.run([
        "make", "-C", latex_dir, f"{base_name}.pdf"
    ], capture_output=True, text=True)

    if result.returncode != 0 or not os.path.exists(pdf_path):
        stderr = result.stderr or ""
        stdout = result.stdout or ""
        # Try to read build.log if present for better error output
        build_log = os.path.join(latex_dir, "build.log")
        log_content = ""
        if os.path.exists(build_log):
            try:
                with open(build_log, "r", encoding="utf-8", errors="ignore") as lf:
                    log_content = lf.read()
            except Exception:
                pass
        raise RuntimeError(
            "LaTeX compilation failed.\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}\n"
            f"build.log:\n{log_content}\n"
        )

    # Return project-root-relative path as specified
    return os.path.relpath(pdf_path, repo_root)
