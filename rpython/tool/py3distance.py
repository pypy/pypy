"""Measure how far the RPython tree is from being importable on Python 3.

This is a reporting tool, not a porting tool.  It counts occurrences of
constructs that are valid Python 2 but are either a syntax error on Python 3
or silently mean something else there.  The point is to have a single number
per category so that individual clean-up changes can state what they remove,
and so that a checkout can be prevented from drifting back.

Everything it counts is a construct with a spelling that is valid and
semantically identical on both Python 2 and Python 3, so every count can be
driven to zero without ever forking the source.

Usage::

    python rpython/tool/py3distance.py                 # report, whole tree
    python rpython/tool/py3distance.py rpython/rlib    # report, subtree
    python rpython/tool/py3distance.py --check origin/main

``--check`` re-runs the report against a git ref and fails if any category
grew.  It stores no baseline: the comparison is always against a ref, so
independent changes never conflict over a checked-in number.

Runs on Python 2.7 and on Python 3.  The tokenizer is grammar-agnostic, so a
Python 3 host can measure Python 2 sources and vice versa.
"""

from __future__ import print_function

import io
import os
import re
import subprocess
import sys
import tokenize
import warnings

# Files that are deliberately written in Python 2 syntax because they are
# fixtures testing that the flow space accepts it.  They must never be ported.
EXCLUDED = (
    'rpython/annotator/test/test_annrpython_py2.py',
    'rpython/flowspace/test/test_objspace_py2.py',
    'rpython/translator/test/snippet_py2.py',
)

PY2_STDLIB = (
    '__builtin__ UserDict UserList UserString StringIO cStringIO cPickle '
    'ConfigParser Queue SocketServer Cookie cookielib copy_reg thread '
    'dummy_thread urllib2 urlparse HTMLParser htmlentitydefs commands md5 '
    'sha new sets whichdb anydbm dumbdbm exceptions'
).split()

PY2_BUILTINS = (
    'long unicode basestring unichr xrange cmp execfile raw_input apply '
    'buffer reload intern'
).split()


def count_bare_tuple_comprehensions(tokens):
    """Count list comprehensions iterating over an unparenthesized tuple.

    Python 2 accepts '[c for c in "a", "b"]'; Python 3 needs the tuple in
    parentheses.  Only list comprehensions ever allowed it.
    """
    hits = 0
    # one frame per open bracket: [bracket, seen 'for', inside the iterable]
    stack = []
    for ttype, tstr, _, _, _ in tokens:
        if ttype != tokenize.OP and ttype != tokenize.NAME:
            continue
        if tstr in '([{' and ttype == tokenize.OP:
            stack.append([tstr, False, False])
            continue
        if not stack:
            continue
        frame = stack[-1]
        if tstr in ')]}' and ttype == tokenize.OP:
            stack.pop()
        elif frame[0] != '[':
            continue
        elif tstr == 'for':
            frame[1], frame[2] = True, False
        elif tstr == 'in' and frame[1]:
            frame[2] = True
        elif tstr == 'if':
            frame[2] = False
        elif tstr == ',' and frame[2]:
            hits += 1
            frame[1] = frame[2] = False
    return hits


def count_tuple_prints(tokens):
    """Count print(a, b) calls in modules without print_function.

    Python 2 prints the tuple '(a, b)' there, Python 3 prints 'a b'.  Both
    parse, so nothing else notices.
    """
    names = [tstr for ttype, tstr, _, _, _ in tokens if ttype == tokenize.NAME]
    for i in range(len(names) - 3):
        if (names[i] == 'from' and names[i + 1] == '__future__' and
                'print_function' in names[i + 2:i + 12]):
            return 0
    hits = 0
    at_start = True
    for i, (ttype, tstr, _, _, _) in enumerate(tokens):
        if ttype in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
            at_start = True
            continue
        if ttype in (tokenize.NL, tokenize.COMMENT):
            continue
        if (at_start and ttype == tokenize.NAME and tstr == 'print' and
                tokens[i + 1][1] == '('):
            depth = 0
            for ttype2, tstr2, _, _, _ in tokens[i + 1:]:
                if ttype2 != tokenize.OP:
                    continue
                if tstr2 in '([{':
                    depth += 1
                elif tstr2 in ')]}':
                    depth -= 1
                    if depth == 0:
                        break
                elif tstr2 == ',' and depth == 1:
                    hits += 1
                    break
        at_start = False
    return hits


# (name, matcher, description).  A regex is matched against the source with
# comments dropped and string contents blanked out, so occurrences inside
# docstrings or C source templates are not counted.  A function gets the
# token list instead.
CATEGORIES = [
    ('tuple_params',
     re.compile(r'\bdef\s+\w+\s*\(\s*(?:[^()]*?,\s*)?\('),
     'def f((a, b)): tuple parameter unpacking'),
    ('lambda_tuple_params',
     re.compile(r'\blambda\s*\('),
     'lambda (a, b): tuple parameter unpacking'),
    ('print_statement',
     re.compile(r'(?m)^\s*print(?:\s+[^\s=(]|\s*$|\s*>>)'),
     'print statement instead of print function'),
    ('exec_statement',
     re.compile(r'(?m)^\s*exec\s+[^\s(]'),
     'exec statement instead of exec function'),
    ('raise_comma',
     # allows a subscript, as in 'raise info[0], info[1], info[2]', but
     # not a call, so that 'raise Error(a, b)' is not counted
     re.compile(r'(?m)^[ \t]*raise[ \t]+[\w.]+(?:\[[^]\n]*\])?[ \t]*,'),
     'raise E, v instead of raise E(v)'),
    ('octal_literal',
     # (?<![eE][+-]) so that the tail of a float like 6.5e+04 is not counted
     re.compile(r'(?<![\w.])(?<![eE][+-])0[0-7]+(?![\w.])'),
     '0755 instead of 0o755'),
    ('long_literal',
     re.compile(r'(?<![\w.])(?:0[xX][0-9a-fA-F]+|\d+)[lL](?![\w])'),
     '10L / 0xffL long literal suffix'),
    ('backtick_repr',
     re.compile(r'`'),
     '`x` instead of repr(x)'),
    ('ne_operator',
     re.compile(r'<>'),
     '<> instead of !='),
    ('has_key',
     re.compile(r'\.has_key\s*\('),
     'd.has_key(k) instead of k in d'),
    ('dict_iter_methods',
     re.compile(r'\.iter(?:items|keys|values)\s*\('),
     'd.iteritems() and friends'),
    ('metaclass_attr',
     re.compile(r'(?m)^\s*__metaclass__\s*='),
     '__metaclass__ = M class attribute'),
    ('py2_stdlib_import',
     re.compile(r'(?m)^\s*(?:import|from)\s+(?:%s)\b' % '|'.join(PY2_STDLIB)),
     'import of a module renamed in Python 3'),
    ('py2_builtin',
     re.compile(r'(?<![\w.])(?:%s)(?![\w])' % '|'.join(PY2_BUILTINS)),
     'use of a builtin removed in Python 3'),
    ('ur_prefix',
     re.compile(r'(?<![\w.])[uU][rR](?=[\'"])'),
     'ur"..." string prefix, a syntax error on Python 3'),
    ('bare_tuple_listcomp',
     count_bare_tuple_comprehensions,
     '[x for x in a, b] instead of [x for x in (a, b)]'),
    ('tuple_print',
     count_tuple_prints,
     'print(a, b) without print_function: prints a tuple on Python 2'),
]


UR_PREFIX = re.compile(r'(?<![\w.])[uU](?=[rR][\'"])')


def tokenize_source(source):
    """Return the token list, or None if the source cannot be tokenized."""
    # the tokenizer of Python 3.12+ rejects the ur prefix outright; tokenize
    # it as r instead, leaving the u outside the token so that columns stay
    # put and blanking keeps it
    source = UR_PREFIX.sub(' ', source)
    try:
        readline = io.StringIO(source).readline
        return list(tokenize.generate_tokens(readline))
    except Exception:
        return None


def blank_strings_and_comments(source, tokens):
    """Return source with comments dropped and string contents blanked.

    Keeps line and column structure so that line-anchored patterns still
    work, and keeps a string's prefix and quotes so that the prefix can be
    matched.  Returns the source unchanged if it could not be tokenized.
    """
    if tokens is None:
        return source
    lines = source.split('\n')
    out = [list(line) for line in lines]
    for ttype, tstr, start, end, _ in tokens:
        if ttype not in (tokenize.STRING, tokenize.COMMENT):
            continue
        (srow, scol), (erow, ecol) = start, end
        if ttype == tokenize.STRING:
            # Python 3's tokenizer reads ur"..." as a NAME and a STRING, so
            # the prefix survives there anyway; keep it on Python 2 too
            prefix = len(tstr) - len(tstr.lstrip('bBuUrR'))
            quote = 3 if tstr[prefix:prefix + 3] in ('"""', "'''") else 1
            scol += prefix + quote
            ecol -= quote
        for row in range(srow, erow + 1):
            if row - 1 >= len(out):
                break
            line = out[row - 1]
            lo = scol if row == srow else 0
            hi = ecol if row == erow else len(line)
            for col in range(lo, min(hi, len(line))):
                if line[col] != ' ':
                    line[col] = 'x'
    return '\n'.join(''.join(line) for line in out)


def read(path):
    with io.open(path, encoding='latin-1') as f:
        return f.read()


def iter_files(roots):
    for root in roots:
        if os.path.isfile(root):
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != '__pycache__']
            for name in sorted(filenames):
                if not name.endswith('.py'):
                    continue
                path = os.path.join(dirpath, name)
                if path.replace(os.sep, '/') in EXCLUDED:
                    continue
                yield path


def measure(roots):
    """Return {category: (hits, files)} plus the py3 syntax-error count."""
    counts = dict((name, [0, 0]) for name, _, _ in CATEGORIES)
    counts['py3_syntax_error'] = [0, 0]
    for path in iter_files(roots):
        source = read(path)
        tokens = tokenize_source(source)
        code = blank_strings_and_comments(source, tokens)
        for name, matcher, _ in CATEGORIES:
            if hasattr(matcher, 'findall'):
                n = len(matcher.findall(code))
            elif tokens is not None:
                n = matcher(tokens)
            else:
                n = 0
            if n:
                counts[name][0] += n
                counts[name][1] += 1
        if sys.version_info[0] >= 3:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    compile(source, path, 'exec', dont_inherit=True)
            except SyntaxError:
                counts['py3_syntax_error'][0] += 1
                counts['py3_syntax_error'][1] += 1
            except Exception:
                pass
    return counts


DESCRIPTIONS = dict((name, doc) for name, _, doc in CATEGORIES)
DESCRIPTIONS['py3_syntax_error'] = 'files that do not parse on Python 3'


def report(counts, out=sys.stdout):
    order = [name for name, _, _ in CATEGORIES] + ['py3_syntax_error']
    width = max(len(name) for name in order)
    print('%-*s %8s %7s  %s' % (width, 'category', 'hits', 'files', 'meaning'),
          file=out)
    print('-' * (width + 60), file=out)
    total = 0
    for name in order:
        hits, files = counts[name]
        total += hits
        print('%-*s %8d %7d  %s' % (width, name, hits, files,
                                    DESCRIPTIONS[name]), file=out)
    print('-' * (width + 60), file=out)
    print('%-*s %8d' % (width, 'total', total), file=out)
    return total


def measure_ref(ref, roots):
    """Measure the tree as of a git ref, in a temporary worktree."""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix='py3distance-')
    try:
        subprocess.check_call(
            ['git', 'worktree', 'add', '--detach', '--quiet', tmp, ref])
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            return measure(roots)
        finally:
            os.chdir(cwd)
    finally:
        subprocess.call(['git', 'worktree', 'remove', '--force', tmp],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    args = list(argv[1:])
    ref = None
    if '--check' in args:
        i = args.index('--check')
        args.pop(i)
        if i >= len(args):
            print('--check needs a git ref', file=sys.stderr)
            return 2
        ref = args.pop(i)
    roots = args or ['rpython']

    counts = measure(roots)
    total = report(counts)
    if ref is None:
        return 0

    before = measure_ref(ref, roots)
    print(file=sys.stdout)
    print('comparing against %s:' % ref)
    grew = []
    for name in sorted(counts):
        delta = counts[name][0] - before[name][0]
        if delta > 0:
            grew.append((name, before[name][0], counts[name][0]))
        elif delta < 0:
            print('  %-24s %6d -> %-6d (%+d)'
                  % (name, before[name][0], counts[name][0], delta))
    if grew:
        print()
        for name, was, now in grew:
            print('  REGRESSION %-20s %6d -> %-6d (+%d)'
                  % (name, was, now, now - was))
        print('\nEverything counted here has a spelling that means the same'
              ' thing on both\nversions, so this can be fixed without'
              ' forking the source.')
        sys.stdout.flush()
        return 1
    print('  no category grew (total %d)' % total)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
