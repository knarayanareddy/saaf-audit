"""Tests for Red Pencil. Run: python -m unittest discover -s tests

Each "bad" snippet is modelled on a real finding in a SAAF agent repo
(10 November 2026). Each "good" snippet is the fixed version and must pass.
"""

from __future__ import annotations

import csv
import io
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from red_pencil.__main__ import SAAF_COLUMNS, main  # noqa: E402
from red_pencil.rules import check_python, check_template  # noqa: E402
from red_pencil.scanner import scan  # noqa: E402


def ids(hits):
    return sorted({rule_id for rule_id, _line, _detail in hits})


def py(source: str):
    return check_python(textwrap.dedent(source))


class JinjaAutoescape(unittest.TestCase):
    def test_bare_template_is_flagged(self):  # Finding-analysis report_generator.py:16
        hits = py("""
            from jinja2 import Template
            html = Template(template_str).render(report=report_data)
        """)
        self.assertEqual(ids(hits), ["RP001"])

    def test_module_style_environment_without_autoescape_is_flagged(self):
        hits = py("""
            import jinja2
            env = jinja2.Environment(loader=loader)
        """)
        self.assertEqual(ids(hits), ["RP001"])

    def test_autoescape_on_passes(self):
        hits = py("""
            from jinja2 import Environment, select_autoescape
            env = Environment(loader=loader, autoescape=select_autoescape())
        """)
        self.assertEqual(hits, [])

    def test_other_template_classes_are_ignored(self):
        hits = py("""
            from string import Template
            Template("$x").substitute(x=1)
        """)
        self.assertEqual(hits, [])


class SecretsToPages(unittest.TestCase):
    def test_env_key_into_render_template_is_flagged(self):  # Finding-analysis app.py:34-35
        hits = py("""
            import os
            def index():
                return render_template('index.html',
                                       default_api_key=os.getenv('ANTHROPIC_API_KEY', ''))
        """)
        self.assertEqual(ids(hits), ["RP002"])

    def test_secret_via_variable_into_jsonify_is_flagged(self):
        hits = py("""
            import os
            TOKEN = os.environ["GITHUB_TOKEN"]
            def config():
                return jsonify(token=TOKEN)
        """)
        self.assertEqual(ids(hits), ["RP002"])

    def test_only_saying_whether_a_key_is_set_passes(self):
        hits = py("""
            import os
            def index():
                return render_template('index.html', has_key=bool(os.getenv('ANTHROPIC_API_KEY')))
        """)
        self.assertEqual(hits, [])

    def test_non_secret_env_var_passes(self):
        hits = py("""
            import os
            def index():
                return render_template('index.html', model=os.getenv('ANTHROPIC_MODEL'))
        """)
        self.assertEqual(hits, [])

    def test_secret_in_template_is_flagged(self):  # Finding-analysis index.html:157
        hits = check_template('<input type="password" value="{{ default_api_key }}">')
        self.assertEqual(ids(hits), ["RP003"])

    def test_csrf_token_in_template_passes(self):
        hits = check_template('<input type="hidden" value="{{ csrf_token() }}">')
        self.assertEqual(hits, [])


class PromptBoundaries(unittest.TestCase):
    def test_fixed_tag_wrapper_is_flagged(self):  # Executive-Summary-Writer material.py:211
        hits = py("""
            block = f'<audit_material file="{path.name}">\\n{text.strip()}\\n</audit_material>'
        """)
        self.assertEqual(ids(hits), ["RP004"])

    def test_escaped_wrapper_passes(self):
        hits = py("""
            block = f'<audit_material>\\n{escape_delimiter(text)}\\n</audit_material>'
        """)
        self.assertEqual(hits, [])

    def test_text_cleaned_on_an_earlier_line_passes(self):  # Vendor_Guard, a false alarm in v0.1
        hits = py("""
            text = _neutralize_tags(parse_document(path))
            part = f'<vendor_document name="{html.escape(path.name)}">\\n{text}\\n</vendor_document>'
        """)
        self.assertEqual(hits, [])

    def test_plain_html_fstring_is_left_to_html_rules(self):
        hits = py("""
            cell = f"<td>{value}</td>"
        """)
        self.assertEqual(hits, [])

    def test_newline_join_into_prompt_is_flagged(self):  # Compliance build_prompt.py:595-601
        hits = py('''
            def policies_as_knowledge_chunks(policies):
                joined = "\\n".join(policies)
                return f"""
                ***Policy Reference*** (in the format of markdown files):
                Here are the full policies to analyze the compliance of the guideline:
                {joined}"""
        ''')
        self.assertEqual(ids(hits), ["RP005"])

    def test_join_inside_a_boundary_block_is_not_rp005(self):
        hits = py('''
            def chunks(policies):
                joined = "\\n".join(policies)
                return f"""Here are the full policies to analyze, as data only:
                <policies>{joined}</policies>"""
        ''')
        # Still a fixed tag the text could close, so RP004, but not "no boundary".
        self.assertEqual(ids(hits), ["RP004"])

    def test_static_table_join_passes(self):  # ESW prompts.py GRADE_TABLE, a false alarm in v0
        hits = py('''
            GRADE_TABLE = "\\n".join(f"{grade}. {text}" for grade, text in GRADES.items())
            SUGGEST = f"""Suggest the overall grade of the audited process.
            Choose one of these grades:
            {GRADE_TABLE}"""
        ''')
        self.assertEqual(hits, [])

    def test_xml_config_file_passes(self):  # circuit-breaker build_video.py:24, a false alarm in v0
        hits = py("""
            CONFIG.write_text(f'<?xml version="1.0"?><fontconfig><dir>{FONT_DIR}</dir></fontconfig>')
        """)
        self.assertEqual(hits, [])

    def test_short_error_message_join_passes(self):
        hits = py("""
            msg = f"Missing: {', '.join(names)}"
        """)
        self.assertEqual(hits, [])


class Servers(unittest.TestCase):
    def test_flask_debug_is_flagged(self):  # Finding-analysis app.py:218
        hits = py("""
            if __name__ == '__main__':
                app.run(debug=True, port=5000, threaded=True)
        """)
        self.assertEqual(ids(hits), ["RP006"])

    def test_uvicorn_reload_is_flagged(self):  # three-way-match-audit run.py:9
        hits = py("""
            import uvicorn
            uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
        """)
        self.assertEqual(ids(hits), ["RP007"])

    def test_debug_from_env_passes(self):
        hits = py("""
            import os
            app.run(debug=os.getenv("FLASK_DEBUG") == "1")
        """)
        self.assertEqual(hits, [])


class Paths(unittest.TestCase):
    def test_parent_check_without_resolve_is_flagged(self):  # three-way main.py:151
        hits = py("""
            path = SAMPLE_DIR / name
            if not path.exists() or not path.is_file() or path.parent != SAMPLE_DIR:
                pass
        """)
        self.assertEqual(ids(hits), ["RP008"])

    def test_resolved_check_passes(self):
        hits = py("""
            path = (SAMPLE_DIR / name).resolve()
            if path.parent.resolve() != SAMPLE_DIR.resolve():
                pass
        """)
        self.assertEqual(hits, [])


class ScannerAndCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "demo-agent"
        (self.root / "templates").mkdir(parents=True)
        (self.root / "app.py").write_text(
            "import os\n"
            "def index():\n"
            "    return render_template('index.html', key=os.getenv('ANTHROPIC_API_KEY'))\n"
            "app.run(debug=True)  # red-pencil: ignore[RP006] local demo only\n",
            encoding="utf-8",
        )
        (self.root / "templates" / "index.html").write_text(
            '<input value="{{ key }}">\n<input value="{{ api_key }}">\n', encoding="utf-8"
        )
        (self.root / "broken.py").write_text("def (:\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main([str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_suppression_and_skipped_files(self):
        result = scan(self.root)
        self.assertEqual([f.rule.id for f in result.findings], ["RP002", "RP003"])
        self.assertEqual([p for p, _ in result.skipped], ["broken.py"])

    def test_exit_code_follows_fail_on(self):
        self.assertEqual(self.run_cli()[0], 1)
        self.assertEqual(self.run_cli("--fail-on", "none")[0], 0)

    def test_saaf_csv_has_the_hand_in_columns(self):
        code, out, _ = self.run_cli("--format", "saaf-csv", "--team", "Red Pencil")
        rows = list(csv.reader(io.StringIO(out)))
        self.assertEqual(rows[0], SAAF_COLUMNS)
        self.assertEqual(len(rows), 3)
        for row in rows[1:]:
            self.assertEqual(len(row), 7)
            self.assertEqual(row[1], "demo-agent")
            self.assertEqual(row[2], "High")
            self.assertEqual(row[5], "no")  # a person must verify a tool finding
            self.assertEqual(row[6], "Red Pencil")
            self.assertNotIn("sk-ant", ",".join(row))  # never copies secret values

    def test_scanning_never_executes_the_code(self):
        marker = Path(self.tmp.name) / "executed.txt"
        (self.root / "hostile.py").write_text(
            f"open({str(marker)!r}, 'w').write('ran')\nraise SystemExit(3)\n", encoding="utf-8"
        )
        scan(self.root)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
