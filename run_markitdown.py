#!/usr/bin/env python3
"""Convert a benchmark corpus with Microsoft MarkItDown (plain local conversion).

Usage:
    <venv python> -I run_markitdown.py <inputDir> <outDir> [--timeout SECONDS]

Every file under <inputDir> is converted, walking sub-folders in sorted order.
Skipped: dotfiles, dot-folders, any folder named "ground-truth", folders that
are symbolic links, entries that are not regular files (or are broken links),
and <outDir> itself when it lies inside <inputDir>.

Each file is converted with

    MarkItDown(enable_plugins=False).convert(pathlib.Path(file))

which is what the `markitdown <file>` command does by default: built-in
converters only, no plugins, no LLM client (so no image descriptions), no Azure
Document Intelligence or Content Understanding, data URIs truncated. The path is
passed as a pathlib.Path, so it is always read as a local file, never fetched.

Outputs, at each file's path relative to <inputDir>:
    <outDir>/<file>.markitdown.md    the Markdown exactly as MarkItDown returned
                                     it, written as UTF-8 with no newline changes
    <outDir>/<file>.markitdown.json  status, error, elapsedMs, MarkItDown and
                                     Python versions, format library versions,
                                     input size and SHA-256, captured warnings

A failure on one file never stops the run. An exception, a timeout or a crash of
the conversion process is recorded in that file's .json ("status" is "error",
"timeout" or "crashed") and no .md is written for it; a stale .md from an earlier
run is removed. A successful conversion that yields no text (for example a
scanned PDF) is "ok" with an empty .md. Every input has a .json, so read the
.json files, not the .md files, to see every result.

Timing: files are converted one at a time in a worker process that has already
imported MarkItDown, created the MarkItDown instance and converted a tiny
in-memory CSV once (warm-up). elapsedMs is time.perf_counter() around the
convert() call alone. The one-time startup cost is recorded as startupMs.

Absolute paths in error messages, tracebacks and warnings are replaced with
<inputDir>, <venv>, <python>, <runnerDir> or ~, so the .json files can be shared.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import multiprocessing
import os
import re
import sys
import time
import traceback
from pathlib import Path

MD_SUFFIX = ".markitdown.md"
JSON_SUFFIX = ".markitdown.json"
SKIP_DIR_NAMES = {"ground-truth"}
DEFAULT_TIMEOUT_S = 300.0
STARTUP_TIMEOUT_S = 300.0
MAX_WARNINGS = 50
MAX_WARNING_CHARS = 500

# Versions recorded in every .json: MarkItDown, its file-type detector and the
# libraries it uses for pdf, docx, xlsx, xls, pptx, csv and json.
RECORDED_PACKAGES = (
    "markitdown",
    "magika",
    "onnxruntime",
    "charset-normalizer",
    "pdfminer.six",
    "pdfplumber",
    "pypdfium2",
    "mammoth",
    "markdownify",
    "beautifulsoup4",
    "lxml",
    "python-pptx",
    "pillow",
    "openpyxl",
    "xlrd",
    "pandas",
    "numpy",
)

# The conversion settings, recorded verbatim in every .json.
SETTINGS = {
    "call": "MarkItDown(enable_plugins=False).convert(pathlib.Path(file))",
    "enable_builtins": True,
    "enable_plugins": False,
    "llm_client": None,
    "docintel_endpoint": None,
    "cu_endpoint": None,
    "keep_data_uris": False,
    "stream_info": None,
}

_SURROGATES = re.compile("[\ud800-\udfff]")


def _ms(start: float, end: float) -> float:
    return round((end - start) * 1000.0, 3)


# ---------------------------------------------------------------------------
# Worker process: imports MarkItDown once and converts the paths it is sent.
# ---------------------------------------------------------------------------


class _ListHandler(logging.Handler):
    """Keeps WARNING and higher log records (pdfminer, openpyxl...) as text."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = record.getMessage()
        except Exception:  # a malformed log call must not break a conversion
            text = str(record.msg)
        self.messages.append(f"log {record.name} {record.levelname}: {text}")


class _Capture:
    """Collects Python warnings and log records emitted during one conversion."""

    def __enter__(self) -> "_Capture":
        import warnings

        self._catcher = warnings.catch_warnings(record=True)
        self._caught = self._catcher.__enter__()
        warnings.simplefilter("always")
        self._handler = _ListHandler()
        logging.getLogger().addHandler(self._handler)
        return self

    def __exit__(self, *exc_info: object) -> bool:
        logging.getLogger().removeHandler(self._handler)
        self._catcher.__exit__(*exc_info)
        return False

    def messages(self) -> list[str]:
        items = [f"{w.category.__name__}: {w.message}" for w in self._caught]
        items += self._handler.messages
        counts: dict[str, int] = {}
        for item in items:
            if len(item) > MAX_WARNING_CHARS:
                item = item[: MAX_WARNING_CHARS - 3] + "..."
            counts[item] = counts.get(item, 0) + 1
        out = [text if n == 1 else f"{text} (x{n})" for text, n in counts.items()]
        if len(out) > MAX_WARNINGS:
            extra = len(out) - MAX_WARNINGS
            out = out[:MAX_WARNINGS] + [f"... and {extra} more distinct messages"]
        return out


def _failure_traceback(exc: BaseException) -> str:
    """The traceback, plus those of each converter attempt MarkItDown wraps."""
    text = traceback.format_exc()
    for attempt in getattr(exc, "attempts", None) or []:
        exc_info = getattr(attempt, "exc_info", None)
        if exc_info:
            name = type(attempt.converter).__name__
            text += f"\n--- {name} attempt ---\n"
            text += "".join(traceback.format_exception(*exc_info))
    return text


def _worker_main(conn) -> None:
    try:
        import io
        import platform
        from importlib import metadata

        t0 = time.perf_counter()
        import markitdown
        from markitdown import MarkItDown, StreamInfo

        t1 = time.perf_counter()
        md = MarkItDown(enable_plugins=False)
        t2 = time.perf_counter()
        with _Capture():
            md.convert_stream(
                io.BytesIO(b"id,name\n1,warm-up\n"),
                stream_info=StreamInfo(extension=".csv"),
            )
        t3 = time.perf_counter()

        def version(dist: str) -> str | None:
            try:
                return metadata.version(dist)
            except metadata.PackageNotFoundError:
                return None

        conn.send(
            {
                "type": "ready",
                "markitdownVersion": markitdown.__version__,
                "pythonVersion": platform.python_version(),
                "platform": platform.platform(),
                "packages": {name: version(name) for name in RECORDED_PACKAGES},
                "startupMs": {
                    "import": _ms(t0, t1),
                    "init": _ms(t1, t2),
                    "warmup": _ms(t2, t3),
                },
                # Used only to shorten paths in messages; never written out.
                "prefixes": {"venv": sys.prefix, "python": sys.base_prefix},
            }
        )
    except BaseException:
        conn.send({"type": "startup-error", "traceback": traceback.format_exc()})
        return

    while True:
        try:
            job = conn.recv()
        except EOFError:
            return
        if job is None:
            return
        capture = _Capture()
        with capture:
            start = time.perf_counter()
            try:
                result = md.convert(Path(job))
                reply = {
                    "ok": True,
                    "elapsedMs": _ms(start, time.perf_counter()),
                    "markdown": result.markdown,
                }
            except Exception as exc:
                reply = {
                    "ok": False,
                    "elapsedMs": _ms(start, time.perf_counter()),
                    "errorType": type(exc).__name__,
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": _failure_traceback(exc),
                }
        reply["warnings"] = capture.messages()
        conn.send(reply)


# ---------------------------------------------------------------------------
# Parent process: walks the corpus, drives the worker, writes the outputs.
# ---------------------------------------------------------------------------


class _Worker:
    """One MarkItDown worker process. Replaced after a timeout or a crash."""

    def __init__(self, ctx) -> None:
        self.conn, child_conn = ctx.Pipe()
        self.proc = ctx.Process(
            target=_worker_main, args=(child_conn,), name="markitdown-worker", daemon=True
        )
        self.proc.start()
        child_conn.close()
        message = None
        if self.conn.poll(STARTUP_TIMEOUT_S):
            try:
                message = self.conn.recv()
            except EOFError:
                pass
        if not isinstance(message, dict) or message.get("type") != "ready":
            self.stop(kill=True)
            if isinstance(message, dict) and "traceback" in message:
                detail = message["traceback"]
            elif message is None and self.proc.exitcode is None:
                detail = f"no answer within {STARTUP_TIMEOUT_S:g} s"
            else:
                detail = f"exit code {self.proc.exitcode}"
            raise RuntimeError(
                "The MarkItDown worker could not start. Run this script with the "
                "benchmark venv's python (markitdown must be importable).\n" + detail
            )
        self.info = message

    def convert(self, path: str, timeout: float) -> tuple[dict | None, str | None]:
        try:
            self.conn.send(path)
        except (BrokenPipeError, OSError):
            self.stop(kill=True)
            return None, "crashed"
        if not self.conn.poll(timeout):
            self.stop(kill=True)
            return None, "timeout"
        try:
            return self.conn.recv(), None
        except EOFError:
            self.stop(kill=True)
            return None, "crashed"

    def stop(self, kill: bool = False) -> None:
        if self.proc.is_alive():
            if kill:
                self.proc.kill()
            else:
                try:
                    self.conn.send(None)
                except (BrokenPipeError, OSError):
                    self.proc.kill()
            self.proc.join(10)
            if self.proc.is_alive():
                self.proc.kill()
                self.proc.join(10)
        self.conn.close()


def _iter_inputs(in_dir: Path, out_dir: Path, skipped: list[str]):
    out_real = out_dir.resolve()
    for root, dirs, files in os.walk(in_dir):
        root_path = Path(root)
        keep = []
        for name in sorted(dirs):
            path = root_path / name
            rel = path.relative_to(in_dir).as_posix()
            if name.startswith(".") or name.lower() in SKIP_DIR_NAMES:
                skipped.append(rel + "/")
            elif path.is_symlink():
                skipped.append(rel + "/ (symbolic link)")
            elif path.resolve() == out_real:
                skipped.append(rel + "/ (outDir)")
            else:
                keep.append(name)
        dirs[:] = keep
        for name in sorted(files):
            path = root_path / name
            rel = path.relative_to(in_dir).as_posix()
            if name.startswith("."):
                skipped.append(rel)
            elif not path.is_file():
                skipped.append(rel + " (not a regular file, or a broken link)")
            else:
                yield path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utf8(text: str) -> tuple[bytes, int]:
    """UTF-8 bytes of text; lone surrogates (not encodable) become U+FFFD."""
    try:
        return text.encode("utf-8"), 0
    except UnicodeEncodeError:
        fixed, count = _SURROGATES.subn("\N{REPLACEMENT CHARACTER}", text)
        return fixed.encode("utf-8"), count


def _write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)


class _Redactor:
    """Replaces local absolute paths with short placeholders."""

    def __init__(self, in_dir: Path) -> None:
        self.pairs: list[tuple[str, str]] = []
        self.add(os.path.abspath(in_dir), "<inputDir>")
        self.add(os.path.realpath(in_dir), "<inputDir>")
        self.add(os.path.dirname(os.path.abspath(__file__)), "<runnerDir>")
        self.add(os.path.expanduser("~"), "~")

    def add(self, prefix: str | None, label: str) -> None:
        if not prefix:
            return
        for variant in (prefix, os.path.realpath(prefix)):
            if len(variant) > 1 and (variant, label) not in self.pairs:
                self.pairs.append((variant, label))
        self.pairs.sort(key=lambda pair: len(pair[0]), reverse=True)

    def __call__(self, text: str | None) -> str | None:
        if text is None:
            return None
        for prefix, label in self.pairs:
            text = text.replace(prefix, label)
        return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_markitdown.py",
        description="Convert every corpus file with Microsoft MarkItDown "
        "(plain local conversion) and record timing, versions and errors.",
    )
    parser.add_argument("input_dir", metavar="inputDir")
    parser.add_argument("out_dir", metavar="outDir")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        metavar="SECONDS",
        help="per-file limit; on expiry the conversion process is killed and the "
        f"file is recorded as 'timeout' (default {DEFAULT_TIMEOUT_S:g})",
    )
    args = parser.parse_args(argv)

    in_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    if not in_dir.is_dir():
        print(f"error: inputDir is not a directory: {in_dir}", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("error: --timeout must be greater than 0", file=sys.stderr)
        return 2
    if out_dir.resolve() == in_dir.resolve():
        print("error: outDir must be different from inputDir", file=sys.stderr)
        return 2

    skipped: list[str] = []
    files = list(_iter_inputs(in_dir, out_dir, skipped))
    if not files:
        print(f"error: no input files under {in_dir}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)

    redact = _Redactor(in_dir)
    ctx = multiprocessing.get_context("spawn")
    worker: _Worker | None = None
    counts: dict[str, int] = {}
    total = len(files)
    run_start = time.perf_counter()
    print(f"MarkItDown benchmark run: {total} file(s) from {in_dir} -> {out_dir}", flush=True)

    try:
        for index, path in enumerate(files, 1):
            rel = path.relative_to(in_dir)
            target_dir = out_dir / rel.parent
            target_dir.mkdir(parents=True, exist_ok=True)
            md_path = target_dir / (rel.name + MD_SUFFIX)
            json_path = target_dir / (rel.name + JSON_SUFFIX)

            try:
                input_bytes: int | None = path.stat().st_size
                input_sha256: str | None = _sha256(path)
            except OSError:
                input_bytes, input_sha256 = None, None

            if worker is None:
                worker = _Worker(ctx)
                redact.add(worker.info["prefixes"]["venv"], "<venv>")
                redact.add(worker.info["prefixes"]["python"], "<python>")
                start = worker.info["startupMs"]
                print(
                    f"  worker ready: markitdown {worker.info['markitdownVersion']}, "
                    f"Python {worker.info['pythonVersion']} (import {start['import']:.0f} ms, "
                    f"init {start['init']:.0f} ms, warm-up {start['warmup']:.0f} ms)",
                    flush=True,
                )
            info = worker.info
            reply, failure = worker.convert(os.path.abspath(path), args.timeout)
            if failure is not None:
                exit_code = worker.proc.exitcode
                worker = None

            notes: list[str] = []
            markdown_bytes: bytes | None = None
            output_chars: int | None = None
            if failure == "timeout":
                status, elapsed, error_type, tb = "timeout", None, "Timeout", None
                error = (
                    f"Timeout: no result within {args.timeout:g} s; "
                    "the conversion process was killed"
                )
            elif failure == "crashed":
                status, elapsed, error_type, tb = "crashed", None, "WorkerCrash", None
                error = (
                    "WorkerCrash: the conversion process exited with code "
                    f"{exit_code} before returning a result"
                )
            elif reply["ok"]:
                status, elapsed, error_type, error, tb = "ok", reply["elapsedMs"], None, None, None
                output_chars = len(reply["markdown"])
                markdown_bytes, replaced = _utf8(reply["markdown"])
                if replaced:
                    notes.append(
                        f"runner: {replaced} lone surrogate code point(s) replaced with "
                        "U+FFFD to write valid UTF-8 (the markitdown command would fail "
                        "to write this output)"
                    )
            else:
                status, elapsed = "error", reply["elapsedMs"]
                error_type, error, tb = reply["errorType"], reply["error"], reply["traceback"]

            if markdown_bytes is not None:
                _write_atomic(md_path, markdown_bytes)
            elif md_path.exists():
                md_path.unlink()

            warnings_out = [redact(w) for w in (reply or {}).get("warnings", [])] + notes
            record = {
                "tool": "markitdown",
                "file": rel.as_posix(),
                "status": status,
                "error": redact(error),
                "errorType": error_type,
                "elapsedMs": elapsed,
                "elapsedMsScope": "MarkItDown.convert() call only, in a started and warmed-up process",
                "markdownFile": md_path.name if markdown_bytes is not None else None,
                "outputChars": output_chars,
                "outputBytes": len(markdown_bytes) if markdown_bytes is not None else None,
                "inputBytes": input_bytes,
                "inputSha256": input_sha256,
                "warnings": warnings_out,
                "markitdownVersion": info["markitdownVersion"],
                "pythonVersion": info["pythonVersion"],
                "packages": info["packages"],
                "settings": SETTINGS,
                "startupMs": info["startupMs"],
                "timeoutSeconds": args.timeout,
                "platform": info["platform"],
                "convertedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "traceback": redact(tb),
            }
            json_bytes, _ = _utf8(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
            _write_atomic(json_path, json_bytes)

            counts[status] = counts.get(status, 0) + 1
            shown = f"{elapsed:10.1f} ms" if elapsed is not None else " " * 13
            size = f"{output_chars} chars" if output_chars is not None else (error_type or "")
            print(f"[{index}/{total}] {status:<7} {shown}  {rel.as_posix()}  ({size})", flush=True)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        if worker is not None:
            worker.stop()

    summary = ", ".join(f"{n} {status}" for status, n in sorted(counts.items()))
    print(f"Done in {time.perf_counter() - run_start:.1f} s: {summary}", flush=True)
    if skipped:
        print(f"Skipped {len(skipped)}: " + ", ".join(skipped), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
