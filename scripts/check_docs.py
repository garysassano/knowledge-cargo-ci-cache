#!/usr/bin/env python3
"""Check repository Markdown destinations and the documented JSONL contract.

Uses the standard library and Git's file inventory. External URLs, source truth,
privacy, and Markdown rendering are review concerns, not validated by this tool.
"""

import argparse
import json
import math
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

COMMON = {
    "schema_version",
    "record_type",
    "run_id",
    "strategy",
    "scenario_id",
    "privacy",
}
TYPES = {"run", "phase", "metric", "resource_sample", "event"}
ACCOUNTING = {"exclusive", "inclusive", "may-overlap", "aggregate-only"}
DESTINATION = r"(<[^>\n]+>|(?:\\.|[^\s()]|\([^()]*\))+)"
INLINE_LINK = re.compile(r"\]\(\s*" + DESTINATION + r"(?:\s+[^\n]*?)?\)")
DEFINITION = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*" + DESTINATION)
REFERENCE = re.compile(r"\[([^\]\n]+)\]\[([^\]\n]*)\]")


def prose_lines(text):
    """Keep line numbers and ignore fenced examples, including longer fences."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            if fence is None:
                fence = marker[1]
            elif (
                marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not marker[2].strip()
            ):
                fence = None
            continue
        if fence is None:
            yield number, line


def heading_anchors(text):
    used = set()
    for _, line in prose_lines(text):
        heading = re.match(r"^#{1,6}\s+(.+?)(?:\s+#+)?$", line)
        if heading:
            title = re.sub(r"<[^>]*>", "", heading[1].lower())
            title = re.sub(r"[^\w\- ]", "", title).replace(" ", "-")
            anchor, duplicate = title, 0
            while anchor in used:
                duplicate += 1
                anchor = f"{title}-{duplicate}"
            used.add(anchor)
        used.update(re.findall(r'<a\s+(?:id|name)=[\'"]([^\'"]+)', line))
    return used


def markdown_errors(root, pages):
    errors, count = [], 0
    anchors = {p.resolve(): heading_anchors(p.read_text()) for p in pages}
    for page in pages:
        lines = list(prose_lines(page.read_text()))
        definitions = {}
        targets = []
        for number, line in lines:
            definition = DEFINITION.match(line)
            if definition:
                definitions[definition[1].casefold()] = definition[2]
                targets.append((number, definition[2]))
                continue
            # Inline code can contain deliberately nonfunctional Markdown examples.
            line = re.sub(r"(`+).*?\1", "", line)
            targets.extend((number, match[1]) for match in INLINE_LINK.finditer(line))
        for number, line in lines:
            line = re.sub(r"(`+).*?\1", "", line)
            for match in REFERENCE.finditer(line):
                label = (match[2] or match[1]).casefold()
                if label not in definitions:
                    errors.append(
                        f"{page.relative_to(root)}:{number}: undefined reference {label!r}"
                    )
        for number, target in targets:
            target = re.sub(r"\\(.)", r"\1", target.strip("<>"))
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            count += 1
            destination = (
                (page.parent / unquote(parsed.path)).resolve()
                if parsed.path
                else page.resolve()
            )
            location = f"{page.relative_to(root)}:{number}"
            if not destination.is_relative_to(root):
                errors.append(
                    f"{location}: destination leaves the repository: {target}"
                )
            elif not destination.exists():
                errors.append(f"{location}: missing destination: {target}")
            elif (
                parsed.fragment
                and destination.suffix.lower() == ".md"
                and unquote(parsed.fragment) not in anchors.get(destination, set())
            ):
                errors.append(f"{location}: missing heading anchor: {target}")
    return errors, count


def nonnegative_integer(value):
    return type(value) is int and value >= 0


def reject_nonfinite(value):
    raise ValueError(f"nonstandard JSON constant: {value}")


def jsonl_errors(root, files):
    errors, count = [], 0
    all_runs = {}
    for path in files:
        runs = defaultdict(list)
        for number, line in enumerate(path.read_text().splitlines(), 1):
            location = f"{path.relative_to(root)}:{number}"
            try:
                record = json.loads(line, parse_constant=reject_nonfinite)
            except (ValueError, RecursionError) as error:
                errors.append(f"{location}: invalid JSON: {error}")
                continue
            count += 1
            if not isinstance(record, dict) or COMMON - record.keys():
                errors.append(f"{location}: expected an object with all common fields")
                continue
            if any(not isinstance(record[k], str) or not record[k] for k in COMMON):
                errors.append(f"{location}: common fields must be nonempty strings")
                continue
            if (
                record["schema_version"] != "cargo-ci-cache/v1"
                or record["privacy"] != "sanitized"
            ):
                errors.append(f"{location}: invalid schema version or privacy marker")
            if record["record_type"] not in TYPES:
                errors.append(f"{location}: unknown record type")
            runs[record["run_id"]].append((location, record))
        for run_id, rows in runs.items():
            if run_id in all_runs:
                errors.append(
                    f"{path.relative_to(root)}: run {run_id!r} is also in {all_runs[run_id]}"
                )
            all_runs[run_id] = path.relative_to(root)
            identities = [r for _, r in rows if r["record_type"] == "run"]
            if len(identities) != 1:
                errors.append(
                    f"{path.relative_to(root)}: {run_id}: expected exactly one run record"
                )
                continue
            identity = identities[0]
            phases = {}
            for location, row in rows:
                for field in ("strategy", "scenario_id", "cache_state", "trial"):
                    if row.get(field) != identity.get(field):
                        errors.append(f"{location}: inconsistent {field} within run")
                if "job_total_ms" in row and not nonnegative_integer(
                    row["job_total_ms"]
                ):
                    errors.append(f"{location}: invalid job_total_ms")
                kind = row["record_type"]
                if kind == "phase":
                    phase_id = row.get("phase_id")
                    if not isinstance(phase_id, str) or not phase_id:
                        errors.append(f"{location}: missing phase_id")
                    elif phase_id in phases:
                        errors.append(f"{location}: duplicate phase_id {phase_id!r}")
                    else:
                        phases[phase_id] = (location, row)
                    if not isinstance(row.get("phase"), str) or not row["phase"]:
                        errors.append(f"{location}: missing phase name")
                    if (
                        not isinstance(row.get("accounting"), str)
                        or row["accounting"] not in ACCOUNTING
                    ):
                        errors.append(f"{location}: invalid phase accounting")
                    for field in ("duration_ms", "start_offset_ms", "end_offset_ms"):
                        if (
                            field == "duration_ms" or field in row
                        ) and not nonnegative_integer(row.get(field)):
                            errors.append(f"{location}: invalid {field}")
                    start, end, duration = (
                        row.get(k)
                        for k in ("start_offset_ms", "end_offset_ms", "duration_ms")
                    )
                    if (
                        all(nonnegative_integer(v) for v in (start, end, duration))
                        and end - start != duration
                    ):
                        errors.append(f"{location}: interval does not match duration")
                    if row.get("phase") == "job_total" and duration != identity.get(
                        "job_total_ms"
                    ):
                        errors.append(
                            f"{location}: job phase disagrees with authoritative wall time"
                        )
                elif kind == "metric":
                    value = row.get("value")
                    if type(value) not in (int, float) or (
                        type(value) is float and not math.isfinite(value)
                    ):
                        errors.append(
                            f"{location}: metric value must be finite numeric data"
                        )
                    if not all(
                        isinstance(row.get(k), str) and row[k] for k in ("name", "unit")
                    ):
                        errors.append(f"{location}: metric requires name and unit")
                elif kind in {"event", "resource_sample"}:
                    for field in ("offset_ms", "interval_ms"):
                        if field in row and not nonnegative_integer(row[field]):
                            errors.append(f"{location}: invalid {field}")
                    if kind == "event" and (
                        not isinstance(row.get("event"), str) or not row["event"]
                    ):
                        errors.append(f"{location}: missing event name")
                    if "detail" in row and not isinstance(row["detail"], dict):
                        errors.append(f"{location}: event detail must be an object")
                    if kind == "resource_sample":
                        for field, value in row.items():
                            if field.endswith("_percent") and (
                                type(value) not in (int, float) or not 0 <= value <= 100
                            ):
                                errors.append(
                                    f"{location}: invalid resource percentage {field}"
                                )
            for phase_id, (location, phase) in phases.items():
                seen = {phase_id}
                parent = phase.get("parent_phase_id")
                while parent is not None:
                    if not isinstance(parent, str) or parent not in phases:
                        errors.append(f"{location}: missing parent phase")
                        break
                    if parent in seen:
                        errors.append(f"{location}: cycle in parent phases")
                        break
                    seen.add(parent)
                    parent = phases[parent][1].get("parent_phase_id")
    return errors, count


def check(root):
    inventory = (
        subprocess.check_output(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                "*.md",
                "*.jsonl",
            ],
            cwd=root,
        )
        .decode()
        .split("\0")
    )
    paths = [
        root / name
        for name in sorted(set(inventory))
        if name and (root / name).is_file()
    ]
    pages = [p for p in paths if p.suffix == ".md"]
    data = [p for p in paths if p.suffix == ".jsonl"]
    errors, links = markdown_errors(root, pages)
    data_errors, records = jsonl_errors(root, data)
    print(
        f"Checked {len(pages)} Markdown pages, {links} local destinations, and {records} JSONL records"
    )
    for error in errors + data_errors:
        print(error)
    return bool(errors or data_errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    raise SystemExit(check(parser.parse_args().root.resolve()))
