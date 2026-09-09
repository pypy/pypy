#!/usr/bin/env python3
"""Compare PyPy's PEG grammar with the CPython grammar it was forked from.

Actions differ by design (C in CPython, RPython in PyPy), so only the rule
names and the structure of each alternative are compared.  Rules that PyPy
deliberately writes differently are listed in KNOWN_DIFFERENCES and skipped.

Usage, from the repository root:

    python3 lib-python/check_grammar_drift.py            # download for the
                                                         # CPYTHON_VERSION in
                                                         # pypy/module/sys/version.py
    python3 lib-python/check_grammar_drift.py --version 3.12.14
    python3 lib-python/check_grammar_drift.py --gram ~/oss/cpython/Grammar/python.gram

Exit status is 1 when a difference outside KNOWN_DIFFERENCES is found.
"""

import argparse
import os
import re
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PYPY_GRAM = os.path.join(ROOT, "pypy", "interpreter", "pyparser", "tools",
                         "python-in-rpython.gram")
VERSION_PY = os.path.join(ROOT, "pypy", "module", "sys", "version.py")
URL = "https://raw.githubusercontent.com/python/cpython/v%s/Grammar/python.gram"

# rule name -> why PyPy differs
KNOWN_DIFFERENCES = {
    "start": "PyPy entry point",
    "string": "renamed to string_ in PyPy",
    "string_": "renamed from string",
    "strings": "uses string_",
    "statement_newline": "PyPy rules end with ENDMARKER",
    "simple_stmt": "no &'type' lookahead needed",
    "atom": "'$NUM' revdb extension",
    "augassign": "rpython hack, wraps the operator in a list",
    "noteq_bitwise_or": "no '<>' barry_as_FLUFL support",
    "dotted_name": "left recursion written out",
    "decorators": "PyPy decorator rules",
    "decorator": "PyPy decorator rules",
    "dec_primary": "PyPy decorator rules",
    "dec_maybe_call": "PyPy decorator rules",
    "invalid_arguments": "first alternative split in two for rpython typing",
    "invalid_kwarg": "True/False/None handled in kwarg_illegal_assignment",
    "invalid_match_stmt": "!':' instead of NEWLINE, same message",
    "invalid_case_block": "!':' instead of NEWLINE, same message",
    "invalid_kvpair": "no &('}'|',') lookahead, same message",
    "invalid_double_starred_kvpairs": "extra 'expression =' diagnostic",
}

RULE_RE = re.compile(r"^([a-z_][a-z0-9_]*)\s*(\[|\(memo\)|:)")


def parse_grammar(path):
    """Return {rule name: [alternative, ...]} with actions stripped."""
    rules = {}
    name = None
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("@"):
                continue
            m = RULE_RE.match(line)
            if m:
                name = m.group(1)
                rules[name] = []
                body = line.split(":", 1)[1].strip() if ":" in line else ""
                if body:
                    rules[name].append(body)
            elif name is None:
                continue
            elif stripped.startswith("|"):
                rules[name].append(stripped[1:].strip())
            elif rules[name]:
                rules[name][-1] += " " + stripped
    return {name: [normalize(alt) for alt in alts if normalize(alt)]
            for name, alts in rules.items()}


def normalize(alt):
    alt = alt.split("{", 1)[0]                 # drop the action
    alt = re.sub(r"\b[a-z_][a-z0-9_]*(\[[^\]]*\])?=", "", alt)  # drop bindings
    return " ".join(alt.split())


def cpython_version():
    with open(VERSION_PY) as f:
        for line in f:
            m = re.match(r"CPYTHON_VERSION\s*=\s*\((\d+),\s*(\d+),\s*(\d+)", line)
            if m:
                return ".".join(m.groups())
    sys.exit("cannot find CPYTHON_VERSION in %s" % VERSION_PY)


def download(version):
    path = os.path.join(tempfile.gettempdir(), "python-%s.gram" % version)
    if not os.path.exists(path):
        url = URL % version
        print("downloading", url)
        urllib.request.urlretrieve(url, path)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gram", help="local copy of CPython's python.gram")
    parser.add_argument("--version", help="CPython tag to download, e.g. 3.12.14")
    parser.add_argument("--show-known", action="store_true",
                        help="also print the known differences")
    args = parser.parse_args()

    if args.gram:
        cpath = args.gram
    else:
        cpath = download(args.version or cpython_version())
    cpython = parse_grammar(cpath)
    pypy = parse_grammar(PYPY_GRAM)

    drift = 0
    for name in sorted(set(cpython) ^ set(pypy)):
        where = "cpython" if name in cpython else "pypy"
        if name in KNOWN_DIFFERENCES:
            if args.show_known:
                print("known: %s only in %s (%s)" % (name, where, KNOWN_DIFFERENCES[name]))
            continue
        drift += 1
        print("rule %s only in %s" % (name, where))

    for name in sorted(set(cpython) & set(pypy)):
        c_alts, p_alts = cpython[name], pypy[name]
        if c_alts == p_alts:
            continue
        if name in KNOWN_DIFFERENCES:
            if args.show_known:
                print("known: %s differs (%s)" % (name, KNOWN_DIFFERENCES[name]))
            continue
        drift += 1
        print("rule %s differs:" % name)
        for alt in c_alts:
            if alt not in p_alts:
                print("    cpython: | " + alt)
        for alt in p_alts:
            if alt not in c_alts:
                print("    pypy:    | " + alt)
        if sorted(c_alts) == sorted(p_alts):
            print("    (same alternatives, different order)")

    print("%d rule(s) drifted from %s" % (drift, cpath))
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
