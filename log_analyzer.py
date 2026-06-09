"""
Local log analysis for FDMEE / Data Management / ODI / Process Details logs.

The point of doing this locally (no LLM) is twofold:
  1. The Groq free tier caps tokens/minute, so we never want to paste a 50k-line
     log into the prompt. We extract the signal here and send a compact summary.
  2. Regex pattern detection for *known* EPM failure signatures is faster and more
     reliable than asking an LLM to scan raw text.

The output of analyze_log() is a human-readable summary string that gets handed to
the LLM (with LOG_ANALYSIS prompt) for root-cause + prioritized fixes.
"""

import re
from collections import Counter, OrderedDict

# Severity tokens as they appear in EPM/ODI logs, roughly highest -> lowest.
SEVERITY_ORDER = ["FATAL", "ERROR", "SEVERE", "WARNING", "WARN"]
SEVERITY_RE = re.compile(r"\b(FATAL|ERROR|SEVERE|WARNING|WARN)\b")

# Known EPM/FDMEE/ODI failure signatures. Each entry:
#   key -> (compiled regex, short human label, suggested-area hint)
# Keep these conservative and well-known so we don't mislead.
KNOWN_PATTERNS = OrderedDict({
    "no_period_mapping": (
        re.compile(r"no\s+periods?\s+(were\s+)?(identified|mapped)|period.*null|invalid\s+period",
                   re.I),
        "Period mapping gap (no/ invalid period mapping for the load)",
        "Data Management > Period Mapping (Application + Global), and the POV period.",
    ),
    "no_mapping_found": (
        re.compile(r"no\s+mapping|unmapped|member.*not\s+mapped|mapping.*not\s+found", re.I),
        "Dimension member mapping missing",
        "Data Load Mapping for the affected dimension; add an explicit or wildcard rule.",
    ),
    "member_not_found": (
        re.compile(r"member\s+['\"]?[\w\-#\. ]+['\"]?\s+(does\s+not\s+exist|not\s+found|is\s+invalid)|unknown\s+member",
                   re.I),
        "Target member does not exist / invalid intersection",
        "Verify the mapped target member exists in the dimension and is a valid level-0/intersection.",
    ),
    "data_not_loaded": (
        re.compile(r"no\s+data\s+(was\s+)?loaded|0\s+rows?\s+loaded|rejected\s+\d+", re.I),
        "Rows rejected / no data loaded",
        "Check import format, decimal/thousand separators, sign handling, and rejected-row log.",
    ),
    "import_format": (
        re.compile(r"import\s+format|delimiter|number\s+format|unable\s+to\s+parse|invalid\s+(amount|number)",
                   re.I),
        "Import format / parsing issue",
        "Import Format: delimiter, header rows, amount column, and number format.",
    ),
    "odi_session_fail": (
        re.compile(r"odi.*(error|failed)|session\s+\d+.*(error|failed)|knowledge\s+module", re.I),
        "ODI session failure (underlying integration step failed)",
        "Open the ODI Operator / session log for the failing step to see the real SQL/error.",
    ),
    "sql_error": (
        re.compile(r"ORA-\d{4,5}|SQL\s+Exception|JDBC|deadlock|unique\s+constraint", re.I),
        "Database / SQL error",
        "Inspect the ORA- code; often a constraint, datatype, or staging-table issue.",
    ),
    "auth": (
        re.compile(r"AUTH-\d+|authentication\s+failed|invalid\s+credentials|token.*(expired|invalid)|kerberos|OAuth",
                   re.I),
        "Authentication / token failure",
        "Re-check service credentials, OAuth2/IDCS app config, and token expiry.",
    ),
    "essbase": (
        re.compile(r"essbase\s+error|cannot\s+(calculate|load)|calc.*error|aggregation\s+failed", re.I),
        "Essbase calc / load error",
        "Check the calc/business rule, dense-sparse config, and outline validity.",
    ),
    "timeout": (
        re.compile(r"timed?\s*out|timeout|connection\s+reset|read\s+timed", re.I),
        "Timeout / connectivity",
        "Long-running step or network/agent issue; check the ODI agent and run time.",
    ),
    "permission": (
        re.compile(r"insufficient\s+(privileges|permission)|access\s+denied|not\s+authorized", re.I),
        "Insufficient permissions",
        "Verify the run-as user's provisioning and application/dimension access.",
    ),
})

# Capture lines that contain an ORA code or an XXX-#### style EPM code, for surfacing.
CODE_RE = re.compile(r"\b(ORA-\d{4,5}|[A-Z]{2,5}-\d{2,5})\b")


def _line_severity(line: str):
    m = SEVERITY_RE.search(line)
    return m.group(1).upper() if m else None


def analyze_log(text: str, max_sample_lines: int = 12):
    """Parse a raw log string into a compact summary dict + summary text."""
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    total = len(lines)

    severity_counts = Counter()
    flagged = []          # (severity_rank, severity, line)
    for ln in lines:
        sev = _line_severity(ln)
        if sev:
            severity_counts[sev] += 1
            rank = SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else 99
            flagged.append((rank, sev, ln))

    # Detected known patterns (dedup by key) with a sample line each.
    detected = OrderedDict()
    for key, (rx, label, hint) in KNOWN_PATTERNS.items():
        for ln in lines:
            if rx.search(ln):
                detected[key] = {"label": label, "hint": hint, "sample": ln.strip()[:300]}
                break

    # Distinct error codes seen.
    codes = Counter()
    for ln in lines:
        for c in CODE_RE.findall(ln):
            codes[c] += 1

    # Deduplicate flagged lines (collapse near-identical messages) and keep top by severity.
    seen_norm = set()
    unique_flagged = []
    for rank, sev, ln in sorted(flagged, key=lambda t: t[0]):
        norm = re.sub(r"\d+", "#", ln)[:160]   # strip varying numbers/timestamps
        if norm in seen_norm:
            continue
        seen_norm.add(norm)
        unique_flagged.append((sev, ln.strip()[:300]))
        if len(unique_flagged) >= max_sample_lines:
            break

    summary = {
        "total_lines": total,
        "severity_counts": dict(severity_counts),
        "detected_patterns": detected,
        "error_codes": dict(codes.most_common(10)),
        "sample_errors": unique_flagged,
    }
    return summary, _format_summary(summary)


def _format_summary(s: dict) -> str:
    """Render the parsed summary as compact text to feed the LLM."""
    out = [f"LOG SUMMARY ({s['total_lines']} non-empty lines)"]

    if s["severity_counts"]:
        sev = ", ".join(f"{k}={v}" for k, v in sorted(
            s["severity_counts"].items(),
            key=lambda kv: SEVERITY_ORDER.index(kv[0]) if kv[0] in SEVERITY_ORDER else 99))
        out.append(f"Severity tally: {sev}")
    else:
        out.append("Severity tally: no FATAL/ERROR/WARNING tokens found "
                   "(log may be info-level or a non-standard format).")

    if s["error_codes"]:
        out.append("Error codes: " + ", ".join(f"{c}(x{n})" for c, n in s["error_codes"].items()))

    if s["detected_patterns"]:
        out.append("\nDetected known patterns:")
        for i, (key, d) in enumerate(s["detected_patterns"].items(), 1):
            out.append(f"  {i}. {d['label']}")
            out.append(f"     check: {d['hint']}")
            out.append(f"     e.g.: {d['sample']}")
    else:
        out.append("\nNo known FDMEE/ODI signatures matched by the local parser.")

    if s["sample_errors"]:
        out.append("\nTop distinct error/warning lines (deduplicated):")
        for sev, ln in s["sample_errors"]:
            out.append(f"  [{sev}] {ln}")

    return "\n".join(out)
