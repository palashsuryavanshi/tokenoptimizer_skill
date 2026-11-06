#!/usr/bin/env python3
"""
Token Optimizer CI Gate — Scans for verbose patterns that waste tokens.

Exit codes:
  0 = clean
  1 = violations found
  2 = error
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple


class Violation(NamedTuple):
    file: str
    line: int
    pattern: str
    message: str
    context: str


# Patterns that indicate verbose/wasteful output
PATTERNS: List[Dict] = [
    {
        "name": "excessive_explanation",
        "regex": r"(?i)(here is|here are|below is|below are|the following|as follows).{0,50}(code|implementation|solution|example)",
        "message": "Excessive explanatory preamble before code",
        "severity": "warning",
    },
    {
        "name": "verbose_list_intro",
        "regex": r"(?i)^\s*(here are|the following are|list of|several|multiple|various)\s+\w+",
        "message": "Verbose list introduction",
        "severity": "warning",
    },
    {
        "name": "apologetic_language",
        "regex": r"(?i)\b(sorry|apologize|unfortunately|regrettably)\b",
        "message": "Apologetic language wastes tokens",
        "severity": "warning",
    },
    {
        "name": "hedging_language",
        "regex": r"(?i)\b(i think|i believe|probably|maybe|perhaps|might be|could be|seems like)\b",
        "message": "Hedging language reduces clarity",
        "severity": "info",
    },
    {
        "name": "redundant_confirmation",
        "regex": r"(?i)(as requested|as you asked|per your request|following your instruction)",
        "message": "Redundant confirmation of request",
        "severity": "warning",
    },
    {
        "name": "excessive_formatting",
        "regex": r"(```\w*\n.{0,10}\n```)|(^#{1,6}\s+.+$\n^#{1,6}\s+.+$)",
        "message": "Excessive markdown formatting for minimal content",
        "severity": "info",
    },
    {
        "name": "todo_comments_in_output",
        "regex": r"(?i)(TODO|FIXME|XXX|HACK):",
        "message": "TODO/FIXME comments in output",
        "severity": "info",
    },
    {
        "name": "repeated_phrases",
        "regex": r"(.{20,}?)\1{2,}",
        "message": "Repeated phrases detected",
        "severity": "warning",
    },
]

# File extensions to scan
SCAN_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".txt", ".yaml", ".yml", ".json", ".sh", ".fish"}

# Files/directories to skip
SKIP_PATTERNS = [
    r"\.git",
    r"__pycache__",
    r"\.pytest_cache",
    r"node_modules",
    r"\.venv",
    r"venv",
    r"dist",
    r"build",
    r"\.egg-info",
    r"test_shim\.bats",  # Test fixtures
]


def should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    path_str = str(path)
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, path_str):
            return True
    return False


def scan_file(file_path: Path) -> List[Violation]:
    """Scan a single file for verbose patterns."""
    violations = []
    
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return violations
    
    lines = content.split("\n")
    
    for pattern_def in PATTERNS:
        regex = re.compile(pattern_def["regex"], re.MULTILINE)
        for match in regex.finditer(content):
            # Find line number
            line_num = content[:match.start()].count("\n") + 1
            
            # Get context (surrounding lines)
            start_ctx = max(0, line_num - 3)
            end_ctx = min(len(lines), line_num + 2)
            context = "\n".join(f"{i+1:4}: {lines[i]}" for i in range(start_ctx, end_ctx))
            
            violations.append(Violation(
                file=str(file_path),
                line=line_num,
                pattern=pattern_def["name"],
                message=pattern_def["message"],
                context=context,
            ))
    
    return violations


def scan_directory(root: Path, extensions: set = None) -> List[Violation]:
    """Recursively scan directory for violations."""
    if extensions is None:
        extensions = SCAN_EXTENSIONS
    
    all_violations = []
    
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if should_skip(file_path):
            continue
        if extensions and file_path.suffix not in extensions:
            continue
        
        violations = scan_file(file_path)
        all_violations.extend(violations)
    
    return all_violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Token Optimizer CI Gate - Scan for verbose patterns")
    parser.add_argument("paths", nargs="*", default=["."], help="Paths to scan (default: current directory)")
    parser.add_argument("--extensions", help="Comma-separated file extensions to scan")
    parser.add_argument("--severity", choices=["error", "warning", "info"], default="warning",
                        help="Minimum severity to fail on (default: warning)")
    parser.add_argument("--output", choices=["text", "json", "github"], default="text",
                        help="Output format (default: text)")
    parser.add_argument("--max-violations", type=int, default=50,
                        help="Maximum violations to report (default: 50)")
    
    args = parser.parse_args()
    
    # Parse extensions
    extensions = None
    if args.extensions:
        extensions = set(f".{ext.lstrip('.')}" for ext in args.extensions.split(","))
    
    # Collect all violations
    all_violations = []
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file():
            if not should_skip(path) and (extensions is None or path.suffix in extensions):
                all_violations.extend(scan_file(path))
        elif path.is_dir():
            all_violations.extend(scan_directory(path, extensions))
    
    # Filter by severity
    severity_order = {"error": 0, "warning": 1, "info": 2}
    min_severity = severity_order[args.severity]
    filtered = [v for v in all_violations if severity_order.get(
        next((p["severity"] for p in PATTERNS if p["name"] == v.pattern), "warning"), 1) <= min_severity]
    
    # Sort by file, line
    filtered.sort(key=lambda v: (v.file, v.line))
    
    # Limit output
    display_violations = filtered[:args.max_violations]
    truncated = len(filtered) > args.max_violations
    
    # Output
    if args.output == "json":
        import json
        print(json.dumps([
            {"file": v.file, "line": v.line, "pattern": v.pattern, "message": v.message, "context": v.context}
            for v in display_violations
        ], indent=2))
    elif args.output == "github":
        # GitHub Actions annotation format
        for v in display_violations:
            print(f"::{v.pattern} file={v.file},line={v.line}::{v.message}")
    else:
        # Text format
        if not display_violations:
            print("OK: No verbose patterns detected")
            return 0
        
        print(f"Found {len(filtered)} violation(s)" + (" (truncated)" if truncated else ""))
        print()
        
        current_file = None
        for v in display_violations:
            if v.file != current_file:
                current_file = v.file
                print(f"\nFILE: {v.file}")
            
            severity_icon = {"error": "[ERROR]", "warning": "[WARN]", "info": "[INFO]"}.get(
                next((p["severity"] for p in PATTERNS if p["name"] == v.pattern), "warning"), "[WARN]"
            )
            
            print(f"  {severity_icon} Line {v.line}: [{v.pattern}] {v.message}")
            for ctx_line in v.context.split("\n"):
                print(f"      {ctx_line}")
    
    # Return error code if violations found at or above threshold
    if filtered:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())