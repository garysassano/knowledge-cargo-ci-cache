"""Failure-oriented checks for the repository's documentation validator."""

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from check_docs import jsonl_errors, markdown_errors


class DocumentationChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def records(self):
        identity = {
            "schema_version": "cargo-ci-cache/v1",
            "run_id": "trial-a",
            "strategy": "no-cache",
            "scenario_id": "case-a",
            "privacy": "sanitized",
        }
        return [
            dict(identity, record_type="run", job_total_ms=100),
            dict(
                identity,
                record_type="phase",
                phase_id="total",
                phase="job_total",
                accounting="inclusive",
                duration_ms=100,
            ),
            dict(
                identity,
                record_type="phase",
                phase_id="work",
                phase="workload_total",
                parent_phase_id="total",
                accounting="exclusive",
                start_offset_ms=10,
                end_offset_ms=90,
                duration_ms=80,
            ),
            dict(
                identity,
                record_type="metric",
                name="bytes",
                value=42,
                unit="bytes",
                **{"future:field": "ignored"},
            ),
        ]

    def data_errors(self, records):
        path = self.write(
            "measurements.jsonl", "\n".join(json.dumps(row) for row in records) + "\n"
        )
        return jsonl_errors(self.root, [path])[0]

    def test_markdown_destinations_and_fenced_examples(self):
        target = self.write(
            "My Report.md",
            '# Setup `sccache`\n\n# Repeat\n# Repeat\n# Repeat-1\n<a id="custom"></a>\n',
        )
        self.write("diagram(a).svg", "<svg/>")
        page = self.write(
            "README.md",
            """# Index
[one](<My Report.md#setup-sccache>)
[two](My%20Report.md#repeat-1-1)
[named][report]
[report]: <My Report.md#custom>
![image](diagram(a).svg)
[external](https://example.invalid/missing)
`[literal](missing.md)`
````markdown
```
[example](missing.md)
````
~~~markdown
[example](also-missing.md)
~~~
""",
        )
        errors, count = markdown_errors(self.root, [page, target])
        self.assertEqual([], errors)
        self.assertEqual(4, count)

    def test_broken_paths_anchors_references_and_escape(self):
        page = self.write(
            "README.md",
            "# Index\n[a](missing.md)\n[b](#missing)\n[c][undefined]\n[d](../outside.md)\n",
        )
        errors, _ = markdown_errors(self.root, [page])
        for fragment in (
            "missing destination",
            "missing heading anchor",
            "undefined reference",
            "leaves the repository",
        ):
            self.assertTrue(any(fragment in error for error in errors), errors)

    def test_valid_records_allow_unknown_extensions(self):
        self.assertEqual([], self.data_errors(self.records()))

    def test_invalid_identity_cardinality_and_phase_graph(self):
        cases = []
        rows = self.records()
        rows.append(deepcopy(rows[0]))
        cases.append((rows, "exactly one run"))
        rows = self.records()
        rows[2]["scenario_id"] = "other"
        cases.append((rows, "inconsistent scenario_id"))
        rows = self.records()
        rows.append(deepcopy(rows[2]))
        cases.append((rows, "duplicate phase_id"))
        rows = self.records()
        rows[2]["parent_phase_id"] = "unknown"
        cases.append((rows, "missing parent phase"))
        rows = self.records()
        rows[1]["parent_phase_id"] = "work"
        cases.append((rows, "cycle in parent phases"))
        for rows, message in cases:
            with self.subTest(message=message):
                self.assertTrue(
                    any(message in error for error in self.data_errors(rows))
                )

    def test_bad_measurements_fail_without_crashing(self):
        for field, value, message in [
            ("duration_ms", True, "invalid duration_ms"),
            ("duration_ms", -1, "invalid duration_ms"),
            ("end_offset_ms", 91, "interval does not match"),
            ("accounting", [], "invalid phase accounting"),
            ("run_id", [], "common fields"),
        ]:
            with self.subTest(field=field, value=value):
                rows = self.records()
                rows[2][field] = value
                self.assertTrue(
                    any(message in error for error in self.data_errors(rows))
                )
        rows = self.records()
        rows[1]["duration_ms"] = 101
        self.assertTrue(
            any("authoritative wall time" in error for error in self.data_errors(rows))
        )
        rows = self.records()
        rows[3]["value"] = float("nan")
        self.assertTrue(
            any("invalid JSON" in error for error in self.data_errors(rows))
        )

    def test_malformed_json_and_repeated_run_across_files(self):
        malformed = self.write("broken.jsonl", "{\n[]\n")
        errors, _ = jsonl_errors(self.root, [malformed])
        self.assertEqual(2, len(errors))
        rows = self.records()
        body = "\n".join(json.dumps(row) for row in rows) + "\n"
        first, second = self.write("one.jsonl", body), self.write("two.jsonl", body)
        errors, _ = jsonl_errors(self.root, [first, second])
        self.assertTrue(any("is also in" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
