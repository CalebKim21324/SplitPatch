"""Inline runs/workflow_data.json into app/workflow.html -> <out> (default runs/workflow_page.html).

Usage: python eval/build_page.py [out_path]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "runs" / "workflow_page.html"
data = (ROOT / "runs" / "workflow_data.json").read_text(encoding="utf-8").replace("</", "<\/")
html = (ROOT / "app" / "workflow.html").read_text(encoding="utf-8").replace("/*DATA*/null", data)
out.write_text(html, encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
