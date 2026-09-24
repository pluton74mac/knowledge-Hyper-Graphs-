"""The four console scripts of DESIGN §10.4: ``khg-validate``, ``khg-convert``, ``khg-migrate`` and
``khg-conformance``.

- ``khg-validate PATH`` prints the ``validate()`` result on stdout, one line per finding or ``--json``. Exit 1 when a
  finding is an error.
- ``khg-convert IN OUT --to hif|khg-json|khg-jsonl`` validates IN (a C1 container or a ``khg-hif/1.0.0`` file)
  through its kind's pipeline, then writes OUT: HIF from ``to_hif`` in the layout of the packaged HIF files, or the
  canonical container that ``record.write_container`` writes. Exit 1 when IN fails validation or the conversion
  raises ``ValidationError``; nothing is written then.
- ``khg-migrate IN OUT --from v0-sample`` writes the migrated container (OUT), the generated schema
  (``--schema-out``) and the F report (``--report``, else stdout) in the layout of the committed goldens (§11.3).
  Exit 1 when the migration refuses IN.
- ``khg-conformance --factory MODULE:CALLABLE`` runs the C2 suite and writes the EARL report (``--report``, else
  stdout). Exit 1 when a scenario is ``failed`` or ``cantTell``; ``inapplicable`` is not a failure.

Every command exits with 0 on success, 1 when its input fails and 2 on a usage or I/O error: bad or conflicting
options (an output named twice, or naming a file the command reads; a container file name that ends in neither
``.json`` nor ``.jsonl``, DESIGN §14 ruling 4), a file that cannot be read or written (standard output closed by its
reader too), an argument file (``--schema``, ``--base``, ``--doc-texts``) that fails validation, a factory that
cannot be loaded. Results go to stdout and diagnostics to stderr. Output files are UTF-8 with ``\\n`` line ends and
are replaced atomically, and only once all of a command's outputs are written; a new file gets the permissions the
umask allows and an existing one keeps its own, as with shell redirection.
``python -m khg_contracts.cli COMMAND [ARGS]`` runs a command (``validate``, ``convert``, ``migrate`` or
``conformance``) without its console script.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import os
import secrets
import stat
import sys
from collections import Counter
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, NoReturn, Optional, Sequence, TextIO

from .errors import ValidationError

__all__ = ["COMMANDS", "conformance_main", "convert_main", "main", "migrate_main", "validate_main"]

#: The exit statuses of §10.4.
OK, INVALID, USAGE = 0, 1, 2
#: The targets of ``khg-convert --to``.
TARGETS = ("hif", "khg-json", "khg-jsonl")

Argv = Optional[Sequence[str]]

# ------------------------------------------------------------------------------------------------ output


def _write(stream: TextIO, text: str) -> None:
    """Write ``text``, backslash-escaping what the stream's encoding cannot carry."""
    try:
        stream.write(text)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "ascii"
        stream.write(text.encode(encoding, "backslashreplace").decode(encoding))


def _say(line: str) -> None:
    """A result line on stdout."""
    _write(sys.stdout, line + "\n")


def _warn(line: str) -> None:
    """A diagnostic line on stderr."""
    _write(sys.stderr, line + "\n")


def _say_json(obj: Any) -> None:
    """``obj`` as JSON on stdout, with a one-space indent; non-ASCII characters are kept, or escaped when stdout
    cannot carry them."""
    try:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1) + "\n")
    except UnicodeEncodeError:
        sys.stdout.write(json.dumps(obj, indent=1) + "\n")


def _staged(path: str, text: str) -> str:
    """``text`` written, as UTF-8 with ``\\n`` line ends, to a new temporary file beside ``path``; returns its name.
    It gets the permissions that the umask allows, or the mode of an existing regular file at ``path``, as shell
    redirection gives (a private or read-only output stays so)."""
    target = os.fspath(path)
    tmp = os.path.join(os.path.dirname(target) or ".", f".khg-{secrets.token_hex(8)}.tmp")
    fh = open(tmp, "x", encoding="utf-8", newline="\n")
    try:
        with fh:
            fh.write(text)
        try:
            st = os.stat(target)
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISREG(st.st_mode):
                os.chmod(tmp, stat.S_IMODE(st.st_mode))
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise
    return tmp


def _write_files(outputs: Sequence[tuple[str, str]]) -> None:
    """Write each ``(path, text)``, replacing the files atomically. Every text goes to a temporary file first
    (``_staged``), and the files are replaced only once all are written, so a text that cannot be written leaves
    every output as it was. Exit 2 names a path that cannot be written."""
    staged: list[tuple[str, str]] = []
    try:
        for path, text in outputs:
            try:
                staged.append((_staged(path, text), path))
            except OSError as e:
                raise _Exit(USAGE, _cannot("write", path, e)) from None
        while staged:
            tmp, path = staged[0]
            try:
                os.replace(tmp, path)
            except OSError as e:
                raise _Exit(USAGE, _cannot("write", path, e)) from None
            staged.pop(0)
    finally:
        for tmp, _ in staged:
            with contextlib.suppress(OSError):
                os.remove(tmp)


def _container_text(container: Mapping[str, Any], fmt: str) -> str:
    """The canonical text of a container, after the V and C checks (``ValidationError``), as
    ``record.write_container`` writes it."""
    from . import record

    found = record.check_container(container)
    if any(f["severity"] == "error" for f in found):
        raise ValidationError.from_findings(found)
    return record.serialize(container, format=fmt)


def _finding(f: Mapping[str, Any]) -> str:
    """``<severity> <code> at <path>: <message>`` (without ``at`` for the document root)."""
    line = f"{f.get('severity', 'error')} {f.get('code', '')}"
    if f.get("path"):
        line += f" at {f['path']}"
    message = str(f.get("message") or "").replace("\r", " ").replace("\n", " ")
    return f"{line}: {message}" if message else line


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _verdict(kind: str | None, findings: Iterable[Mapping[str, Any]]) -> str:
    """``valid (<kind>; <n> errors, <m> warnings)``, or ``invalid (...)`` when a finding is an error."""
    counts = Counter(str(f.get("severity", "error")) for f in findings)
    errors, warnings = counts.pop("error", 0), counts.pop("warning", 0)
    parts = [_plural(errors, "error"), _plural(warnings, "warning")]
    parts += [f"{n} {severity}" for severity, n in sorted(counts.items())]
    return f"{'invalid' if errors else 'valid'} ({kind or 'unknown kind'}; {', '.join(parts)})"


# ------------------------------------------------------------------------------------------------ plumbing


class _Exit(Exception):
    """Ends a command with ``status``; each of ``lines`` goes to stderr after the program name."""

    def __init__(self, status: int, *lines: str):
        super().__init__(*lines)
        self.status = status
        self.lines = lines


class _Parser(argparse.ArgumentParser):
    """An ``ArgumentParser`` that raises ``_Exit`` instead of exiting, so that each main returns its status. argparse
    has printed the help (status 0), or the usage and the error (status 2), by then."""

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if message:
            _write(sys.stderr, message)
        raise _Exit(status)


def _parser(prog: str, description: str, fails: str) -> _Parser:
    return _Parser(prog=prog, description=description, allow_abbrev=False,
                   epilog=f"Exit status: 0 on success, 1 when {fails}, 2 on a usage or I/O error.")


def _main(parser: _Parser, command: Callable[[_Parser, argparse.Namespace], int], argv: Argv) -> int:
    try:
        status = command(parser, parser.parse_args(argv))
        sys.stdout.flush()  # a reader that closed stdout shows here when the output was buffered
        return status
    except _Exit as e:
        for line in e.lines:
            _warn(f"{parser.prog}: {line}")
        return e.status
    except BrokenPipeError as e:
        _drop_stdout()
        _warn(f"{parser.prog}: cannot write the standard output: {e.strerror or e}")
        return USAGE


def _drop_stdout() -> None:
    """Point the standard output at ``os.devnull`` after its reader went away, so that the flush at exit does not
    fail again; nothing when it is not a file (a test's capture)."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(devnull, sys.stdout.fileno())
        finally:
            os.close(devnull)
    except (OSError, ValueError):
        pass


def _cannot(verb: str, path: Any, e: OSError) -> str:
    return f"cannot {verb} {path}: {e.strerror or e}"


def _same_file(a: str, b: str) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:  # one of them does not exist yet
        return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def _distinct_outputs(parser: _Parser, inputs: Iterable[tuple[str, str | None]],
                      outputs: Iterable[tuple[str, str | None]]) -> None:
    """A usage error (exit 2, nothing written) when an output is also another output or a file the command reads:
    one of them would be lost."""
    named = [(option, path) for option, path in inputs if path is not None]
    for option, path in outputs:
        if path is None:
            continue
        for other_option, other in named:
            if _same_file(path, other):
                parser.error(f"{option} {path} is the file of {other_option} {other}")
        named.append((option, path))


def _container_name(parser: _Parser, path: str) -> None:
    """A usage error unless ``path`` ends in ``.json`` or ``.jsonl``, the suffixes by which ``record.read_container``
    reads a container (§14 ruling 4)."""
    if not path.endswith((".json", ".jsonl")):
        parser.error(f"OUT {path}: a container file name ends in .json (one JSON document) or .jsonl (JSON lines)")


def _refused(name: str, e: ValidationError) -> list[str]:
    """The lines of a ``ValidationError`` on the document ``name``: its findings, else its message."""
    found = e.info.get("findings") or []
    return [f"{name}: {_finding(f)}" for f in found] or [f"{name}: {e}"]


def _argument(option: str, path: str, load: Callable[[str], Any], what: str) -> Any:
    """``load(path)`` for an argument file; exit 2 when it cannot be read or fails validation, since the input cannot
    be checked or converted with it."""
    try:
        return load(path)
    except OSError as e:
        raise _Exit(USAGE, f"{option}: {_cannot('read', path, e)}") from None
    except ValidationError as e:
        raise _Exit(USAGE, *_refused(path, e), f"{option}: {path} is not {what}") from None
    except ValueError as e:  # a container named by another suffix than .json or .jsonl (§14 ruling 4)
        raise _Exit(USAGE, f"{option}: {e}") from None


def _schema_argument(path: str | None) -> Any:
    """The ``--schema`` file as a ``Schema`` (J, V and M), or None."""
    if path is None:
        return None
    from .schema import load_schema
    return _argument("--schema", path, load_schema, "a valid relation-type schema")


# ------------------------------------------------------------------------------------------------ khg-validate


def _validate_parser() -> _Parser:
    from .validate import ENGINES, KINDS

    p = _parser("khg-validate", "Validate a C1 record or container, a HIF file, a role-convention file, a "
                "relation-type schema, a C3 queue or a C4 items file through the layers of its kind, and print the "
                "validate() result: one line per finding and a verdict, or {ok, findings} as JSON.",
                "a finding is an error")
    p.add_argument("path", metavar="PATH", help="the file to validate (a .jsonl file is read line by line)")
    p.add_argument("--kind", choices=("auto", *KINDS), default="auto",
                   help="the kind of PATH (default: auto, told from its content)")
    p.add_argument("--schema", metavar="P", help="the relation-type schema (default: the one PATH embeds)")
    p.add_argument("--doc-texts", metavar="P", dest="doc_texts",
                   help="a khg-doc-texts file with the source texts, for the evidence span check")
    p.add_argument("--base", metavar="P", nargs="+", action="extend", default=[],
                   help="a base container that a queue names (repeatable)")
    p.add_argument("--engine", choices=ENGINES, default="jsonschema",
                   help="the JSON Schema engine (default: jsonschema, which reports every violation)")
    p.add_argument("--json", action="store_true", help="print the result as JSON")
    return p


def _validate(parser: _Parser, args: argparse.Namespace) -> int:
    from . import jsonio, record, validate

    schema = _schema_argument(args.schema)
    texts = None if args.doc_texts is None else _argument("--doc-texts", args.doc_texts, jsonio.load,
                                                           "a JSON object")
    bases = [_argument("--base", p, record.read_container, "a C1 container") for p in args.base]
    try:
        report = validate.run(args.path, kind=args.kind, schema=schema, doc_texts=texts, bases=bases or None,
                              engine=args.engine)
    except OSError as e:
        raise _Exit(USAGE, _cannot("read", args.path, e)) from None
    result = report.result()
    if args.json:
        _say_json(result)
    else:
        for f in result["findings"]:
            _say(f"{args.path}: {_finding(f)}")
        _say(f"{args.path}: {_verdict(report.kind, result['findings'])}")
    return OK if result["ok"] else INVALID


def validate_main(argv: Sequence[str] | None = None) -> int:
    """``khg-validate PATH [--kind K] [--schema P] [--doc-texts P] [--base P ...] [--engine E] [--json]`` (§10.4):
    print the ``validate()`` result; 0 without error findings, 1 with one, 2 on a usage or I/O error."""
    return _main(_validate_parser(), _validate, argv)


# ------------------------------------------------------------------------------------------------ khg-convert


def _relation_list(text: str) -> list[str]:
    """``--relations R,...``: relation ids separated by commas."""
    names = [n.strip() for n in text.split(",")]
    if not all(names):
        raise argparse.ArgumentTypeError(f"{text!r} is not a comma-separated list of relation ids")
    return names


def _convert_parser() -> _Parser:
    from .hif import LITERAL_NODES

    p = _parser("khg-convert", "Convert a C1 container (.khg.json or .khg.jsonl) or a khg-hif/1.0.0 file into "
                "role-aware HIF or a C1 container. IN is validated first, and nothing is written when it fails.",
                "IN fails validation or cannot be converted")
    p.add_argument("input", metavar="IN", help="a C1 container or a khg-hif/1.0.0 file")
    p.add_argument("output", metavar="OUT", help="the file to write (a .jsonl name only for --to khg-jsonl)")
    p.add_argument("--to", required=True, choices=TARGETS,
                   help="hif, or a C1 container as one JSON document (khg-json) or as JSON lines (khg-jsonl)")
    p.add_argument("--schema", metavar="P", help="the relation-type schema (default: the one IN embeds)")
    p.add_argument("--relations", metavar="R,...", type=_relation_list,
                   help="with --to hif: export the closed slice of these relations")
    p.add_argument("--literal-nodes", choices=LITERAL_NODES, dest="literal_nodes",
                   help="with --to hif: one literal node per value (shared, the default) or per binding")
    p.add_argument("--schema-document", action="store_true", dest="schema_document",
                   help="with --to hif: inline the schema as khg-schema-document")
    return p


def _check_convert_options(parser: _Parser, args: argparse.Namespace) -> None:
    hif_only = [option for option, value in (("--relations", args.relations), ("--literal-nodes", args.literal_nodes),
                                             ("--schema-document", args.schema_document or None)) if value is not None]
    if args.to != "hif" and hif_only:
        parser.error(f"{', '.join(hif_only)}: only with --to hif")
    if (args.to == "khg-jsonl") != args.output.endswith(".jsonl"):
        parser.error(f"OUT {args.output} does not fit --to {args.to}: a .jsonl file is read line by line, so only "
                     f"--to khg-jsonl writes one")
    if args.to == "khg-json":
        _container_name(parser, args.output)
    _distinct_outputs(parser, [("IN", args.input), ("--schema", args.schema)], [("OUT", args.output)])


def _checked_input(prog: str, path: str, schema: Any) -> str:
    """Validate IN through its kind's pipeline and return the kind, ``container`` or ``hif``; the warnings go to
    stderr. Exit 1 when IN fails, or is neither a container nor a HIF file."""
    from . import validate

    try:
        report = validate.run(path, schema=schema)
        if report.kind == "role-convention":  # a HIF file without khg-profile: under the profile it is P001
            report = validate.run(path, kind="hif", schema=schema)
    except OSError as e:
        raise _Exit(USAGE, _cannot("read", path, e)) from None
    if report.kind not in (None, "container", "hif"):
        article = "an" if str(report.kind)[:1] in ("a", "e", "i", "o", "u") else "a"  # a C4 file is "an item file"
        raise _Exit(INVALID, f"{path} is {article} {report.kind} file: khg-convert reads a C1 container or a "
                             f"khg-hif file")
    lines = [f"{path}: {_finding(f)}" for f in report.findings]
    if not report.ok:
        raise _Exit(INVALID, *lines, f"{path}: {_verdict(report.kind, report.findings)}; nothing written")
    for line in lines:
        _warn(f"{prog}: {line}")
    return str(report.kind)


def _carried_schema(kind: str, doc: Any, path: str) -> Any:
    """The relation-type schema IN embeds: a container's ``relation-schema`` record, a HIF file's
    ``khg-schema-document``."""
    from .validate.context import Context

    schema, found = Context(kind=kind, doc=doc).relation_schema()
    if schema is None:
        raise _Exit(INVALID, *[f"{path}: {_finding(f)}" for f in found])
    return schema


def _convert(parser: _Parser, args: argparse.Namespace) -> int:
    from . import hif, jsonio, record
    from .migrate.layout import LAYOUT, dumps

    _check_convert_options(parser, args)
    schema = _schema_argument(args.schema)
    kind = _checked_input(parser.prog, args.input, schema)
    try:
        source = record.read_container(args.input) if kind == "container" else jsonio.load(args.input)
    except OSError as e:
        raise _Exit(USAGE, _cannot("read", args.input, e)) from None
    except ValidationError:
        raise
    except ValueError as e:  # a container is read by its suffix, .json or .jsonl (§14 ruling 4)
        raise _Exit(USAGE, f"IN {e}") from None
    try:
        container = source if kind == "container" else hif.from_hif(source, schema)
        if args.to == "hif":
            sch = schema if schema is not None else _carried_schema(kind, source, args.input)
            unknown = [r for r in args.relations or () if not sch.has_relation(r)]
            if unknown:
                parser.error(f"--relations: {', '.join(unknown)} not declared in {sch.ref}")
            doc = hif.to_hif(container, sch, relations=args.relations, literal_nodes=args.literal_nodes or "shared",
                             schema_document=args.schema_document)
            text = dumps(doc, compact=LAYOUT["hif"])
        else:
            text = _container_text(container, "jsonl" if args.to == "khg-jsonl" else "json")
    except ValidationError as e:
        raise _Exit(INVALID, *_refused(args.input, e), f"{args.input} cannot be converted; nothing written") from None
    _write_files([(args.output, text)])
    _warn(f"{parser.prog}: wrote {args.output} ({args.to} from the {kind} {args.input})")
    return OK


def convert_main(argv: Sequence[str] | None = None) -> int:
    """``khg-convert IN OUT --to hif|khg-json|khg-jsonl [--schema P] [--relations R,...] [--literal-nodes M]
    [--schema-document]`` (§10.4): validate IN, then write it converted; 0 on success, 1 when IN fails validation
    or cannot be converted, 2 on a usage or I/O error."""
    return _main(_convert_parser(), _convert, argv)


# ------------------------------------------------------------------------------------------------ khg-migrate


def _migrate_parser() -> _Parser:
    from .migrate import MIGRATIONS

    p = _parser("khg-migrate", "Migrate a file of an earlier format to khg-record/1.0.0. v0-sample is the format of "
                "the knowledge base's schemas/sample.hif.json. The outputs have the layout of the committed "
                "goldens.", "the migration refuses IN")
    p.add_argument("input", metavar="IN", help="the file to migrate")
    p.add_argument("output", metavar="OUT", help="the migrated C1 container (.khg.json, or .khg.jsonl for lines)")
    p.add_argument("--from", dest="source", required=True, choices=sorted(MIGRATIONS), help="the format of IN")
    p.add_argument("--schema-out", metavar="P", dest="schema_out", help="write the generated relation-type schema to P")
    p.add_argument("--report", metavar="P", help="write the migration report to P (default: stdout)")
    return p


def _migrate(parser: _Parser, args: argparse.Namespace) -> int:
    from .migrate import LAYOUT, MIGRATIONS, dumps

    _container_name(parser, args.output)
    _distinct_outputs(parser, [("IN", args.input)], [("OUT", args.output), ("--schema-out", args.schema_out),
                                                     ("--report", args.report)])
    try:
        schema, container, report = MIGRATIONS[args.source](args.input)
        if args.output.endswith(".jsonl"):
            outputs = [(args.output, _container_text(container, "jsonl"))]
        else:
            outputs = [(args.output, dumps(container, compact=LAYOUT["container"]))]
    except OSError as e:
        raise _Exit(USAGE, _cannot("read", args.input, e)) from None
    except ValidationError as e:
        raise _Exit(INVALID, *_refused(args.input, e),
                    f"{args.input} cannot be migrated from {args.source}; nothing written") from None
    if args.schema_out:
        outputs.append((args.schema_out, dumps(schema, compact=LAYOUT["schema"])))
    if args.report:
        outputs.append((args.report, dumps(report, compact=LAYOUT["report"])))
    _write_files(outputs)
    if not args.report:
        _say_json(report)
    _warn(f"{parser.prog}: wrote {', '.join(path for path, _ in outputs)}")
    return OK


def migrate_main(argv: Sequence[str] | None = None) -> int:
    """``khg-migrate IN OUT --from v0-sample [--schema-out P] [--report P]`` (§10.4, §11.3): write the container,
    the generated schema and the F report; 0 on success, 1 when the migration refuses IN, 2 on a usage or I/O
    error."""
    return _main(_migrate_parser(), _migrate, argv)


# ------------------------------------------------------------------------------------------------ khg-conformance


def _flag_set(text: str) -> frozenset[str]:
    """``--capabilities FLAGS``: capability flags separated by commas (an empty value is no flag)."""
    from .store import FLAGS

    names = frozenset(n.strip() for n in text.split(",") if n.strip())
    unknown = sorted(names - set(FLAGS))
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown flags {', '.join(unknown)}; the flags are {', '.join(FLAGS)}")
    return names


def _conformance_parser() -> _Parser:
    p = _parser("khg-conformance", "Run the C2 conformance suite (khg-scenario/1.0.0) on stores from a factory and "
                "write the EARL report. A store passes when no applicable scenario fails; a scenario whose "
                "capability flags the store lacks is inapplicable, which is not a failure.",
                "a scenario is failed or cantTell")
    p.add_argument("--factory", required=True, metavar="MODULE:CALLABLE",
                   help="factory(schema, clock) returns an empty store, e.g. khg_contracts.store:memory_factory "
                        "(MODULE must be importable)")
    p.add_argument("--only", metavar="GLOB", action="append",
                   help="run only the scenarios whose id matches GLOB, e.g. 'S-KEY-*' (repeatable)")
    p.add_argument("--capabilities", metavar="FLAGS", type=_flag_set,
                   help="comma-separated capability flags: test the store as if it declared only these")
    p.add_argument("--report", metavar="PATH", help="write the EARL JSON report to PATH (default: stdout)")
    return p


def _factory(spec: str) -> Callable[..., Any]:
    """The callable that ``MODULE:CALLABLE`` names (CALLABLE may be dotted); exit 2 when it cannot be loaded."""
    module_name, sep, attribute = spec.partition(":")
    if not (sep and module_name and attribute):
        raise _Exit(USAGE, f"--factory {spec!r} is not MODULE:CALLABLE")
    try:
        obj: Any = importlib.import_module(module_name)
    except Exception as e:  # noqa: BLE001 - ImportError, or whatever the module raised while it was imported
        raise _Exit(USAGE, f"--factory: cannot import {module_name}: {type(e).__name__}: {e}") from None
    for part in attribute.split("."):
        try:
            obj = getattr(obj, part)
        except AttributeError:
            raise _Exit(USAGE, f"--factory: {module_name} has no attribute {attribute}") from None
    if not callable(obj):
        raise _Exit(USAGE, f"--factory: {spec} is not callable")
    return obj


def _conformance(parser: _Parser, args: argparse.Namespace) -> int:
    from .store import conformance

    factory = _factory(args.factory)
    only: str | list[str] | None = None
    if args.only:
        only = args.only[0] if len(args.only) == 1 else list(args.only)
        if not conformance.select(conformance.suite().scenarios, only):
            parser.error(f"--only {' '.join(args.only)} matches no scenario")
    try:
        report = conformance.run(factory, only=only, capabilities=args.capabilities)
    except Exception as e:  # noqa: BLE001 - the probe store (the factory or info()) failed before any scenario ran
        raise _Exit(INVALID, f"the store could not be probed: {type(e).__name__}: {e}") from None
    if args.report:
        _write_files([(args.report, conformance.to_json(report))])
    else:
        _say_json(report)
    summary, suite = report["summary"], report["suite"]
    counts = ", ".join(f"{summary[outcome]} {outcome}" for outcome in conformance.OUTCOMES)
    _warn(f"{parser.prog}: {report['subject']['title']}: {counts} "
          f"({suite['selected']} of {suite['scenarios']} scenarios)")
    for assertion in report["@graph"]:
        result = assertion["result"]
        if result["outcome"] in ("failed", "cantTell"):
            _warn(f"{parser.prog}: {result['outcome']} {assertion['test']['identifier']}: {result.get('info', '')}")
    return INVALID if summary["failed"] or summary["cantTell"] else OK


def conformance_main(argv: Sequence[str] | None = None) -> int:
    """``khg-conformance --factory MODULE:CALLABLE [--only GLOB] [--capabilities FLAGS] [--report PATH]`` (§10.4):
    run the C2 suite; 0 when every scenario is passed or inapplicable, 1 when one is failed or cantTell, 2 on a
    usage or I/O error."""
    return _main(_conformance_parser(), _conformance, argv)


# ------------------------------------------------------------------------------------------------ python -m


COMMANDS: Mapping[str, Callable[[Argv], int]] = MappingProxyType({
    "validate": validate_main,
    "convert": convert_main,
    "migrate": migrate_main,
    "conformance": conformance_main,
})


def main(argv: Sequence[str] | None = None) -> int:
    """``python -m khg_contracts.cli COMMAND [ARGS]``: run ``khg-<COMMAND>`` with ARGS."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in COMMANDS:
        return COMMANDS[args[0]](args[1:])
    usage = f"usage: python -m khg_contracts.cli {{{','.join(COMMANDS)}}} [ARGS ...]"
    if args[:1] in (["-h"], ["--help"]):
        _say(usage)
        _say("Runs khg-COMMAND with ARGS; 'python -m khg_contracts.cli COMMAND --help' describes one.")
        return OK
    _warn(usage)
    _warn(f"khg_contracts.cli: error: {'unknown command ' + repr(args[0]) if args else 'a command is required'}")
    return USAGE


if __name__ == "__main__":
    raise SystemExit(main())
