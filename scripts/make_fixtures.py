"""
Generate synthetic fixture PDFs for Pulp benchmarking and snapshot testing.

Covers the document types called out in the PRD (§11.1):
  - resume (text-layer)
  - technical report with tables
  - multi-page report with headers/footers/page numbers
  - footnote-heavy document
  - hyphenated text document
  - multi-page academic-style document
  - short memo / single-page
  - numbered list / enumeration document

Run with:
  uv run python scripts/make_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "pdfs"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
H1 = styles["Heading1"]
H2 = styles["Heading2"]
BODY = styles["BodyText"]
BODY.leading = 14


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc(name: str, pagesize=letter) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(FIXTURES_DIR / name),
        pagesize=pagesize,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )


def _p(text: str, style=None) -> Paragraph:
    return Paragraph(text, style or BODY)


def _sp(h: float = 0.3) -> Spacer:
    return Spacer(1, h * inch)


# ---------------------------------------------------------------------------
# 1. Resume (text-layer, single page)
# ---------------------------------------------------------------------------


def make_resume() -> None:
    doc = _doc("resume.pdf")
    story = [
        _p("Jane Doe", H1),
        _p("jane.doe@email.com  |  (555) 012-3456  |  linkedin.com/in/janedoe"),
        _sp(0.2),
        _p("Summary", H2),
        _p(
            "Software engineer with 5 years of experience building scalable backend systems "
            "in Python and Go. Strong background in distributed systems, API design, and "
            "developer tooling. Passionate about clean code and measurable impact."
        ),
        _sp(0.2),
        _p("Experience", H2),
        _p("<b>Senior Software Engineer — Acme Corp</b> (2021–present)"),
        _p("• Led migration of monolithic API to microservices, reducing p99 latency by 40%."),
        _p("• Built internal PDF processing pipeline handling 50k documents per day."),
        _p("• Mentored 3 junior engineers; introduced weekly code review rituals."),
        _sp(0.15),
        _p("<b>Software Engineer — Beta Labs</b> (2019–2021)"),
        _p("• Designed and shipped a real-time notification system (WebSocket + Redis)."),
        _p("• Reduced CI build time by 60% via parallelisation and caching."),
        _sp(0.2),
        _p("Education", H2),
        _p("<b>B.S. Computer Science</b> — State University, 2019"),
        _sp(0.2),
        _p("Skills", H2),
        _p("Python, Go, PostgreSQL, Redis, Docker, Kubernetes, GitHub Actions, ruff, pytest"),
    ]
    doc.build(story)
    print(f"  wrote {FIXTURES_DIR / 'resume.pdf'}")


# ---------------------------------------------------------------------------
# 2. Technical report with tables
# ---------------------------------------------------------------------------


def make_technical_report() -> None:
    doc = _doc("technical_report.pdf")

    table_data = [
        ["Metric", "Baseline", "Optimised", "Delta"],
        ["Throughput (req/s)", "1,200", "3,450", "+187%"],
        ["p50 latency (ms)", "42", "18", "-57%"],
        ["p99 latency (ms)", "310", "95", "-69%"],
        ["Error rate (%)", "0.8", "0.1", "-87%"],
        ["CPU usage (%)", "78", "45", "-42%"],
        ["Memory (MB RSS)", "640", "390", "-39%"],
    ]
    table = Table(table_data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story = [
        _p("Performance Optimisation Report", H1),
        _p("System: Order Processing Service  |  Date: March 2026  |  Author: Engineering Team"),
        _sp(0.2),
        _p("1. Executive Summary", H2),
        _p(
            "This report documents the results of a three-week performance optimisation effort "
            "on the Order Processing Service. The primary bottleneck was identified as "
            "synchronous database calls within the request path. By introducing connection "
            "pooling, query batching, and an in-process LRU cache for read-heavy endpoints, "
            "throughput increased by 187% while p99 latency dropped from 310ms to 95ms."
        ),
        _sp(0.2),
        _p("2. Results Summary", H2),
        _sp(0.1),
        table,
        _sp(0.2),
        _p("3. Methodology", H2),
        _p(
            "All measurements were taken on production hardware during a low-traffic window "
            "(02:00–04:00 UTC). Load was generated using k6 with a constant arrival rate of "
            "2,000 virtual users. Results were averaged over three 10-minute runs per "
            "configuration. The baseline configuration was the unmodified release tagged v2.3.1."
        ),
        _sp(0.2),
        _p("4. Conclusions", H2),
        _p(
            "The optimised build is ready for gradual rollout. A feature flag controls the "
            "new connection pool size. Recommend 10% canary for 48 hours before full rollout. "
            "Monitoring dashboards have been updated to track the new latency SLOs."
        ),
    ]
    doc.build(story)
    print(f"  wrote {FIXTURES_DIR / 'technical_report.pdf'}")


# ---------------------------------------------------------------------------
# 3. Multi-page report with running headers/footers and page numbers
# ---------------------------------------------------------------------------


def _header_footer_canvas(canvas, doc) -> None:  # type: ignore[type-arg]
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(2 * cm, A4[1] - 1.5 * cm, "Quarterly Business Review — Q1 2026")
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.5 * cm, "CONFIDENTIAL")
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def make_multipage_report() -> None:
    doc = SimpleDocTemplate(
        str(FIXTURES_DIR / "multipage_report.pdf"),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=3 * cm,
        bottomMargin=3 * cm,
    )

    lorem = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor "
        "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
        "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute "
        "irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
        "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia "
        "deserunt mollit anim id est laborum."
    )

    story = []
    for section in range(1, 6):
        story.append(_p(f"Section {section}: Key Findings", H1))
        for sub in range(1, 4):
            story.append(_p(f"{section}.{sub} Sub-topic {sub}", H2))
            story.append(_p(lorem))
            story.append(_p(lorem))
            story.append(_sp(0.15))
        story.append(_sp(0.3))

    doc.build(story, onFirstPage=_header_footer_canvas, onLaterPages=_header_footer_canvas)
    print(f"  wrote {FIXTURES_DIR / 'multipage_report.pdf'}")


# ---------------------------------------------------------------------------
# 4. Footnote-heavy document
# ---------------------------------------------------------------------------


def make_footnote_doc() -> None:
    doc = _doc("footnote_doc.pdf")
    story = [
        _p("Understanding Neural Scaling Laws", H1),
        _p("Abstract", H2),
        _p(
            "Neural scaling laws describe how model performance improves predictably as a "
            "function of compute, data, and parameter count.¹ These power-law relationships "
            "have been empirically validated across a wide range of architectures and tasks.² "
            "This paper reviews the key findings and their practical implications for "
            "resource allocation in large-scale training runs.³"
        ),
        _sp(0.2),
        _p("1. Introduction", H2),
        _p(
            "The observation that loss decreases as a smooth power law of scale was first "
            "systematically documented in Kaplan et al. (2020).⁴ Subsequent work confirmed "
            "that the optimal compute allocation shifts toward larger models and less data as "
            "total compute increases.⁵ This result, known as the Chinchilla scaling law,⁶ "
            "overturned conventional wisdom that had favoured large models trained on "
            "relatively small datasets."
        ),
        _sp(0.2),
        _p("2. Methodology", H2),
        _p(
            "We replicate the core scaling experiments using a decoder-only transformer "
            "architecture.⁷ Models range from 1M to 1B parameters. Training data is drawn "
            "from a deduplicated web corpus filtered with a quality classifier.⁸ All runs "
            "use the same tokenizer with a vocabulary of 32,768 tokens.⁹"
        ),
        _sp(0.4),
        _p("Footnotes", H2),
        _p("¹ Hestness et al., 2017. Deep Learning Scaling is Predictable, Empirically."),
        _p("² Zoph et al., 2022. ST-MoE: Designing Stable and Transferable Sparse Expert Models."),
        _p("³ Hoffmann et al., 2022. Training Compute-Optimal Large Language Models."),
        _p("⁴ Kaplan et al., 2020. Scaling Laws for Neural Language Models."),
        _p("⁵ Compute-optimal training: fewer tokens per parameter than previously assumed."),
        _p("⁶ Named after Chinchilla model; 4× more tokens than GPT-3 at equal compute."),
        _p("⁷ Vaswani et al., 2017. Attention Is All You Need."),
        _p("⁸ Quality filtering reduces noise and improves downstream task performance."),
        _p("⁹ Byte-pair encoding with a coverage-optimised merge schedule."),
    ]
    doc.build(story)
    print(f"  wrote {FIXTURES_DIR / 'footnote_doc.pdf'}")


# ---------------------------------------------------------------------------
# 5. Hyphenation-heavy document (tests hyphen rejoining in clean.py)
# ---------------------------------------------------------------------------


def make_hyphenated_doc() -> None:
    # Use narrow columns to force mid-word line breaks in the PDF.
    narrow_doc = SimpleDocTemplate(
        str(FIXTURES_DIR / "hyphenated_doc.pdf"),
        pagesize=letter,
        leftMargin=5 * cm,
        rightMargin=5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )
    story = [
        _p("Hyphenation Test Document", H1),
        _p("1. Background", H2),
        _p(
            "The internationalisation of software systems requires careful attention to "
            "localisation, character encoding, and bidirectional text rendering. "
            "Implementations that ignore these requirements will encounter incompatibilities "
            "when deployed in multilingual environments."
        ),
        _sp(0.2),
        _p("2. Implementation Notes", H2),
        _p(
            "The reconfiguration of the infrastructure was straightforward despite the "
            "interdependencies between the authentication, authorisation, and "
            "microservice-orchestration layers. The containerisation strategy reduced "
            "environment-specific configuration drift significantly."
        ),
        _sp(0.2),
        _p("3. Recommendations", H2),
        _p(
            "We recommend a phased decommissioning of the legacy monorepo, beginning with "
            "the decomposition of the user-management and notification subsystems. "
            "Parameterisation of environment variables via the configuration-management "
            "layer will simplify cross-environment deployments."
        ),
    ]
    narrow_doc.build(story)
    print(f"  wrote {FIXTURES_DIR / 'hyphenated_doc.pdf'}")


# ---------------------------------------------------------------------------
# 6. Short memo (single page, minimal content)
# ---------------------------------------------------------------------------


def make_memo() -> None:
    doc = _doc("memo.pdf")
    story = [
        _p("MEMORANDUM", H1),
        _sp(0.1),
        _p("<b>TO:</b> Engineering Leadership"),
        _p("<b>FROM:</b> Platform Team"),
        _p("<b>DATE:</b> March 31, 2026"),
        _p("<b>RE:</b> Deprecation of Legacy Auth Service"),
        _sp(0.2),
        _p(
            "Effective April 30, 2026, the legacy OAuth 1.0 authentication service will be "
            "decommissioned. All consuming services must migrate to the OAuth 2.0 endpoint "
            "before this date. Documentation is available on the internal wiki."
        ),
        _sp(0.2),
        _p(
            "Please confirm migration status with your team lead by April 15. Services still "
            "using the legacy endpoint after April 30 will receive 401 errors."
        ),
        _sp(0.2),
        _p("Action required: Acknowledge receipt and confirm migration timeline."),
    ]
    doc.build(story)
    print(f"  wrote {FIXTURES_DIR / 'memo.pdf'}")


# ---------------------------------------------------------------------------
# 7. Numbered list / enumeration document
# ---------------------------------------------------------------------------


def make_numbered_list_doc() -> None:
    doc = _doc("numbered_list.pdf")
    story = [
        _p("API Design Checklist", H1),
        _p("Use this checklist when reviewing new API endpoints before shipping to production."),
        _sp(0.2),
        _p("Authentication & Authorisation", H2),
        _p("1. All endpoints require authentication unless explicitly documented as public."),
        _p("2. Authorisation checks are enforced at the service layer, not just the gateway."),
        _p("3. OAuth 2.0 scopes are defined and documented for each endpoint."),
        _p("4. Token expiry and refresh flows are tested end-to-end."),
        _sp(0.2),
        _p("Input Validation", H2),
        _p("5. All request parameters are validated against a schema before processing."),
        _p("6. String inputs are length-bounded to prevent abuse."),
        _p("7. Numeric inputs have explicit min/max constraints."),
        _p("8. File uploads are type-checked and size-limited."),
        _sp(0.2),
        _p("Error Handling", H2),
        _p("9. Errors return RFC 7807 Problem Details responses."),
        _p("10. Validation errors enumerate all failing fields, not just the first."),
        _p("11. Internal errors never leak stack traces to API consumers."),
        _p("12. Rate limiting returns 429 with Retry-After header."),
        _sp(0.2),
        _p("Documentation", H2),
        _p("13. OpenAPI spec is generated from code annotations, not written by hand."),
        _p("14. Each endpoint has at least one example request and response."),
        _p("15. Breaking changes are noted with a deprecation timeline."),
    ]
    doc.build(story)
    print(f"  wrote {FIXTURES_DIR / 'numbered_list.pdf'}")


# ---------------------------------------------------------------------------
# 8. Multi-page document with boilerplate watermark-like lines
# ---------------------------------------------------------------------------


def _watermark_canvas(canvas, doc) -> None:  # type: ignore[type-arg]
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.lightgrey)
    canvas.drawCentredString(A4[0] / 2, A4[1] - 1 * cm, "DRAFT — NOT FOR DISTRIBUTION — DRAFT")
    canvas.drawCentredString(A4[0] / 2, 0.7 * cm, f"Internal Use Only  |  Page {doc.page} of 3")
    canvas.restoreState()


def make_boilerplate_doc() -> None:
    doc = SimpleDocTemplate(
        str(FIXTURES_DIR / "boilerplate_doc.pdf"),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=3 * cm,
        bottomMargin=3 * cm,
    )

    body = (
        "Machine learning models are increasingly deployed in production environments where "
        "reliability and latency are critical. Ensuring that models behave predictably under "
        "distribution shift requires comprehensive monitoring and evaluation infrastructure. "
        "This document outlines the requirements for a production ML observability platform."
    )

    story = []
    for section in range(1, 4):
        story.append(_p(f"Chapter {section}", H1))
        story.append(_p(f"{section}.1 Overview", H2))
        story.append(_p(body))
        story.append(_p(body))
        story.append(_p(f"{section}.2 Details", H2))
        story.append(_p(body))
        story.append(_p(body))
        story.append(_sp(0.3))

    doc.build(story, onFirstPage=_watermark_canvas, onLaterPages=_watermark_canvas)
    print(f"  wrote {FIXTURES_DIR / 'boilerplate_doc.pdf'}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Writing fixtures to {FIXTURES_DIR}")
    make_resume()
    make_technical_report()
    make_multipage_report()
    make_footnote_doc()
    make_hyphenated_doc()
    make_memo()
    make_numbered_list_doc()
    make_boilerplate_doc()
    print("Done.")
