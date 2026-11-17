"""
Pure-Python implementation of _tokenize.TokenizerIter for PyPy 3.12.
Provides the same interface as CPython's Python/Python-tokenize.c.
"""

import re
import functools
import itertools as _itertools
from token import (
    ENDMARKER, NAME, NUMBER, STRING, NEWLINE, INDENT, DEDENT,
    OP, AWAIT, ASYNC, FSTRING_START, FSTRING_MIDDLE, FSTRING_END,
    COMMENT, NL, ERRORTOKEN, ENCODING,
    EXACT_TOKEN_TYPES,
)


def _syntax_error(msg, lineno, offset):
    # tokenize.py's _generate_tokens_from_c_tokenizer reads .msg/.lineno/
    # .offset off a plain SyntaxError (matching CPython's C tokenizer,
    # which raises via PyErr_SyntaxLocationObject rather than the 4-tuple
    # constructor form) and re-raises as tokenize.TokenError.
    err = SyntaxError(msg)
    err.lineno = lineno
    err.offset = offset
    return err


# -- Regex patterns (adapted from tokenize.py) --------------------------------

def _group(*choices): return '(' + '|'.join(choices) + ')'
def _any(*choices):   return _group(*choices) + '*'
def _maybe(*choices): return _group(*choices) + '?'

Whitespace = r'[ \f\t]*'
Comment    = r'#[^\r\n]*'
Ignore     = Whitespace + _any(r'\\\r?\n' + Whitespace) + _maybe(Comment)
Name       = r'\w+'

Hexnumber  = r'0[xX](?:_?[0-9a-fA-F])+'
Binnumber  = r'0[bB](?:_?[01])+'
Octnumber  = r'0[oO](?:_?[0-7])+'
Decnumber  = r'(?:0(?:_?[0-9])*|[1-9](?:_?[0-9])*)'
Intnumber  = _group(Hexnumber, Binnumber, Octnumber, Decnumber)
Exponent   = r'[eE][-+]?[0-9](?:_?[0-9])*'
Pointfloat = _group(r'[0-9](?:_?[0-9])*\.(?:[0-9](?:_?[0-9])*)?',
                    r'\.[0-9](?:_?[0-9])*') + _maybe(Exponent)
Expfloat   = r'[0-9](?:_?[0-9])*' + Exponent
Floatnumber = _group(Pointfloat, Expfloat)
Imagnumber  = _group(r'[0-9](?:_?[0-9])*[jJ]', Floatnumber + r'[jJ]')
Number      = _group(Imagnumber, Floatnumber, Intnumber)


@functools.lru_cache(maxsize=None)
def _compile(expr):
    return re.compile(expr, re.UNICODE)


def _extend_name(text, end):
    """Return the end of an identifier that starts before `end`.

    re's \\w misses characters that are XID_Continue but not alphanumeric
    (combining marks, e.g. U+0301 or U+E0100), which the C tokenizer accepts
    inside a name.
    """
    n = len(text)
    while end < n and ('a' + text[end]).isidentifier():
        end += 1
    return end


def _all_string_prefixes():
    _valid = ['b', 'r', 'u', 'f', 'br', 'fr']
    result = {''}
    for prefix in _valid:
        for t in _itertools.permutations(prefix):
            for u in _itertools.product(*[(c, c.upper()) for c in t]):
                result.add(''.join(u))
    return result


_ALL_STRING_PREFIXES = _all_string_prefixes()
StringPrefix = _group(*_ALL_STRING_PREFIXES)

Single  = r"[^'\\]*(?:\\.[^'\\]*)*'"
Double  = r'[^"\\]*(?:\\.[^"\\]*)*"'
Single3 = r"[^'\\]*(?:(?:\\.|'(?!''))[^'\\]*)*'''"
Double3 = r'[^"\\]*(?:(?:\\.|"(?!""))[^"\\]*)*"""'
Triple  = _group(StringPrefix + "'''", StringPrefix + '"""')
String  = _group(StringPrefix + r"'[^\n'\\]*(?:\\.[^\n'\\]*)*'",
                 StringPrefix + r'"[^\n"\\]*(?:\\.[^\n"\\]*)*"')

Special  = _group(*map(re.escape, sorted(EXACT_TOKEN_TYPES, reverse=True)))
Funny    = _group(r'\r?\n', Special)
ContStr  = _group(StringPrefix + r"'[^\n'\\]*(?:\\.[^\n'\\]*)*" +
                  _group("'", r'\\\r?\n'),
                  StringPrefix + r'"[^\n"\\]*(?:\\.[^\n"\\]*)*' +
                  _group('"', r'\\\r?\n'))
PseudoExtras = _group(r'\\\r?\n|\Z', Comment, Triple)
PseudoToken  = Whitespace + _group(PseudoExtras, Number, Funny, ContStr, Name)

endpats = {}
for _pfx in _ALL_STRING_PREFIXES:
    endpats[_pfx + "'"]   = Single
    endpats[_pfx + '"']   = Double
    endpats[_pfx + "'''"] = Single3
    endpats[_pfx + '"""'] = Double3
del _pfx

single_quoted = set()
triple_quoted = set()
for _t in _ALL_STRING_PREFIXES:
    for _u in (_t + '"', _t + "'"):
        single_quoted.add(_u)
    for _u in (_t + '"""', _t + "'''"):
        triple_quoted.add(_u)
del _t, _u

tabsize = 8


# -- F-string detection -------------------------------------------------------

def _fstring_info(s):
    """Return (prefix, quote) if s starts with an f-string, else (None, None)."""
    i = 0
    while i < len(s) and s[i] in 'fFrRbBuU':
        i += 1
    prefix = s[:i]
    if 'f' not in prefix.lower():
        return None, None
    rest = s[i:]
    if rest.startswith('"""') or rest.startswith("'''"):
        return prefix, rest[:3]
    if rest and rest[0] in '"\'':
        return prefix, rest[0]
    return None, None


# -- F-string extent scanner --------------------------------------------------

# _fstring_extent() results other than a real offset
_FS_MORE = -1    # the f-string is still open at the end of the text
_FS_EOL = -2     # a newline ended the literal part of a single-quoted f-string


def _fstring_extent(text, i, quote, raw):
    """Find the end of the f-string whose body starts at index `i` of `text`.

    `quote` is the opening quote, `raw` whether the prefix contains an r.
    Returns the index just past the closing quote, or _FS_MORE if more input is
    needed, or _FS_EOL if the literal part of a single-quoted f-string runs
    into a newline (an unterminated literal).

    Replacement fields are only scanned for nesting, not tokenized, but PEP 701
    lets them contain newlines, comments and strings that reuse the enclosing
    quote, so the scan has to know where it is: the stack holds one
    [in_format_spec, bracket_depth] entry per open field.  Quotes and '#' are
    literal text in a format spec but start a string or a comment in an
    expression, and the enclosing quote ends the f-string anywhere outside a
    string.
    """
    n = len(text)
    qlen = len(quote)
    stack = []
    while i < n:
        ch = text[i]
        in_spec = stack[-1][0] if stack else True

        if in_spec:                 # literal text of the f-string or of a spec
            if text.startswith(quote, i):
                return i + qlen
            if ch == '\\':
                nxt = text[i + 1:i + 2]
                if not nxt:
                    return _FS_MORE
                if nxt in '{}':
                    # a backslash never escapes a brace: f"\{x}" is a field
                    i += 1
                elif nxt == 'N' and not raw and text[i + 2:i + 3] == '{':
                    # \N{NAME}: those braces belong to the character name
                    j = text.find('}', i + 3)
                    if j < 0:
                        return _FS_MORE
                    i = j + 1
                else:
                    i += 2
            elif ch == '{':
                if not stack and text[i + 1:i + 2] == '{':
                    i += 2          # escaped {{ (no such escape in a spec)
                    continue
                if not stack and i + 1 == n:
                    return _FS_MORE
                stack.append([False, 0])
                i += 1
            elif ch == '}':
                if stack:
                    stack.pop()     # ends the format spec and its field
                    i += 1
                elif text[i + 1:i + 2] == '}':
                    i += 2          # escaped }}
                else:
                    i += 1          # stray '}'; leave the error to the parser
            elif ch == '\n' and qlen == 1:
                if not stack:
                    return _FS_EOL
                stack[-1][0] = False    # the spec ends; an expression resumes
                i += 1
            else:
                i += 1
            continue

        # expression part of a replacement field
        field = stack[-1]
        if ch == '\\':
            if i + 1 == n:
                return _FS_MORE
            i += 2
            continue
        if ch == '#':
            j = text.find('\n', i)
            if j < 0:
                return _FS_MORE
            i = j
            continue
        if ch == '"' or ch == "'":
            i = _nested_string_extent(text, i)
            if i < 0:
                return i
            continue
        if ch in '([{':
            field[1] += 1
        elif ch in ')]':
            field[1] -= 1
        elif ch == '}':
            if field[1]:
                field[1] -= 1
            else:
                stack.pop()
        elif ch == ':' and not field[1]:
            field[0] = True         # the format spec starts here
        i += 1

    return _FS_MORE


def _nested_string_extent(text, i):
    """Skip the string literal whose opening quote is at index `i` of `text`.

    Its prefix, if any, is the run of letters just before the quote.  Returns
    the index just past the string, or _FS_MORE/_FS_EOL as above.
    """
    n = len(text)
    j = i
    while j > 0 and i - j < 3 and text[j - 1].isalpha():
        j -= 1
    prefix = text[j:i]
    while prefix and prefix not in _ALL_STRING_PREFIXES:
        prefix = prefix[1:]
    ch = text[i]
    quote = ch * 3 if text[i:i + 3] == ch * 3 else ch
    k = i + len(quote)
    if 'f' in prefix.lower():
        return _fstring_extent(text, k, quote, 'r' in prefix.lower())
    qlen = len(quote)
    while k < n:
        c = text[k]
        if c == '\\':                   # escapes the quote even in raw strings
            if k + 1 >= n:
                return _FS_MORE
            k += 2
            continue
        if text.startswith(quote, k):
            return k + qlen
        if c == '\n' and qlen == 1:
            return _FS_EOL
        k += 1
    return _FS_MORE


# -- F-string body scanner ----------------------------------------------------

class _FStr:
    """Cursor for scanning text in a (possibly nested) f-string body."""

    __slots__ = ('body', 'pos', 'row', 'col', 'source_lines', 'n', 'multiline',
                 'raw')

    def __init__(self, body, start_row, start_col, source_lines,
                 multiline=False, raw=False):
        self.body = body
        self.pos = 0
        self.row = start_row
        self.col = start_col
        self.source_lines = source_lines
        self.n = len(body)
        # True for a triple-quoted f-string, where a newline is literal text;
        # in a single-quoted one a newline inside a field is an NL token.
        self.multiline = multiline
        self.raw = raw          # no \N{NAME} escapes in a raw f-string

    def named_escape(self):
        """If a \\N{NAME} escape starts here, return it, else ''."""
        if (self.raw or self.peek() != '\\' or self.peek(1) != 'N'
                or self.peek(2) != '{'):
            return ''
        j = self.pos - 1
        while j >= 0 and self.body[j] == '\\':
            j -= 1
        if (self.pos - 1 - j) % 2:
            return ''           # this backslash is itself escaped
        end = self.body.find('}', self.pos + 3)
        if end < 0:
            return ''
        return self.body[self.pos:end + 1]

    def src_line(self, r=None, end_r=None):
        if r is None:
            r = self.row
        sl = self.source_lines
        if not sl:
            return ''
        if end_r is not None and end_r > r:
            return ''.join(sl[r - 1:min(end_r, len(sl))])
        if 1 <= r <= len(sl):
            return sl[r - 1]
        return ''

    def peek(self, offset=0):
        i = self.pos + offset
        if i < self.n:
            return self.body[i]
        return ''

    def at_end(self):
        return self.pos >= self.n

    def advance(self):
        ch = self.body[self.pos]
        self.pos += 1
        if ch == '\n':
            self.row += 1
            self.col = 0
        else:
            self.col += 1
        return ch

    def advance_by(self, text):
        """Advance cursor by the characters in text."""
        for ch in text:
            self.pos += 1
            if ch == '\n':
                self.row += 1
                self.col = 0
            else:
                self.col += 1

    def match_pseudo(self):
        return _compile(PseudoToken).match(self.body, self.pos)


def _scan_body(fs):
    """Yield FSTRING_MIDDLE and expression tokens for the f-string body."""
    seg_row, seg_col = fs.row, fs.col
    seg = []

    while not fs.at_end():
        ch = fs.peek()

        escape = fs.named_escape()
        if escape:
            # \N{NAME} names a character: its braces are not a field, and like
            # {{ and }} the escape ends this segment.
            seg.append(escape)
            fs.advance_by(escape)
            yield (FSTRING_MIDDLE, ''.join(seg),
                   (seg_row, seg_col), (fs.row, fs.col),
                   fs.src_line(seg_row, fs.row))
            seg = []
            seg_row, seg_col = fs.row, fs.col
        elif ch == '{':
            if fs.peek(1) == '{':
                # {{ collapses to a single { that ENDS this segment; the end
                # column is the first brace + 1 and the second brace column is
                # absorbed (a new segment starts after both).  Matches CPython.
                seg.append('{')
                yield (FSTRING_MIDDLE, ''.join(seg),
                       (seg_row, seg_col), (fs.row, fs.col + 1),
                       fs.src_line(seg_row, fs.row))
                fs.advance()
                fs.advance()
                seg = []
                seg_row, seg_col = fs.row, fs.col
            else:
                # Start of expression
                if seg:
                    yield (FSTRING_MIDDLE, ''.join(seg),
                           (seg_row, seg_col), (fs.row, fs.col),
                           fs.src_line(seg_row, fs.row))
                    seg = []
                open_r, open_c = fs.row, fs.col
                fs.advance()
                yield (OP, '{', (open_r, open_c), (fs.row, fs.col),
                       fs.src_line(open_r))
                yield from _scan_expr(fs)
                seg_row, seg_col = fs.row, fs.col
        elif ch == '}':
            if fs.peek(1) == '}':
                # }} collapses to a single } that ENDS this segment (see above)
                seg.append('}')
                yield (FSTRING_MIDDLE, ''.join(seg),
                       (seg_row, seg_col), (fs.row, fs.col + 1),
                       fs.src_line(seg_row, fs.row))
                fs.advance()
                fs.advance()
                seg = []
                seg_row, seg_col = fs.row, fs.col
            else:
                # Stray } (shouldn't happen in valid body)
                seg.append(ch)
                fs.advance()
        else:
            seg.append(ch)
            fs.advance()

    if seg:
        yield (FSTRING_MIDDLE, ''.join(seg),
               (seg_row, seg_col), (fs.row, fs.col),
               fs.src_line(seg_row, fs.row))


def _scan_expr(fs):
    """
    Yield tokens for the f-string expression from current pos to matching }.
    Handles conversion (!r/!s/!a), format spec (:), debug (=), nested strings.
    Exits after consuming the closing }.
    """
    paren_depth = 0

    while not fs.at_end():
        # Newlines inside expressions become NL tokens
        if fs.peek() == '\n':
            nl_r, nl_c = fs.row, fs.col
            fs.advance()
            yield (NL, '\n', (nl_r, nl_c), (nl_r, nl_c + 1),
                   fs.src_line(nl_r))
            continue

        # Try pseudo-token match (handles whitespace prefix automatically)
        pm = fs.match_pseudo()
        if not pm:
            err_r, err_c = fs.row, fs.col
            ch = fs.advance()
            yield (ERRORTOKEN, ch, (err_r, err_c), (fs.row, fs.col),
                   fs.src_line(err_r))
            continue

        tok_start, tok_end = pm.span(1)
        if tok_start == tok_end:
            # Empty match (e.g. \Z); just advance one char
            if not fs.at_end():
                fs.advance()
            break

        # Advance past any leading whitespace (pos..tok_start)
        while fs.pos < tok_start:
            fs.advance()

        raw_tok = fs.body[tok_start:tok_end]
        initial = raw_tok[0]

        # --- Special cases at depth 0 ---

        # Closing brace at depth 0: end of expression
        if initial == '}' and paren_depth == 0:
            close_r, close_c = fs.row, fs.col
            fs.advance()
            yield (OP, '}', (close_r, close_c), (fs.row, fs.col),
                   fs.src_line(close_r))
            return

        # Colon at depth 0: format spec follows.  A ':=' here is a colon and
        # a spec starting with '=', not a walrus (which needs parentheses).
        if initial == ':' and paren_depth == 0:
            col_r, col_c = fs.row, fs.col
            fs.advance()
            yield (OP, ':', (col_r, col_c), (fs.row, fs.col),
                   fs.src_line(col_r))
            yield from _scan_format_spec(fs)
            return

        # Conversion specifier !r/!s/!a at depth 0
        if initial == '!' and paren_depth == 0:
            nch = fs.peek(1)
            if nch in ('r', 's', 'a'):
                nnch = fs.peek(2)
                if nnch in ('}', ':', '\n', ''):
                    bang_r, bang_c = fs.row, fs.col
                    fs.advance()
                    yield (OP, '!', (bang_r, bang_c), (fs.row, fs.col),
                           fs.src_line(bang_r))
                    name_r, name_c = fs.row, fs.col
                    fs.advance()
                    yield (NAME, nch, (name_r, name_c), (fs.row, fs.col),
                           fs.src_line(name_r))
                    continue

        # Debug expression = at depth 0 (not ==, !=, <=, >=, :=)
        if (initial == '=' and raw_tok == '=' and paren_depth == 0):
            eq_r, eq_c = fs.row, fs.col
            fs.advance()
            yield (OP, '=', (eq_r, eq_c), (fs.row, fs.col), fs.src_line(eq_r))
            continue

        # --- Record token start position ---
        tok_r, tok_c = fs.row, fs.col

        # --- Triple-quoted string / f-string ---
        if raw_tok in triple_quoted:
            # PseudoToken matched only the PREFIX+QUOTES; find the body+end
            prefix, quote = _fstring_info(raw_tok)
            endprog_key = raw_tok
            endprog = _compile(endpats.get(endprog_key, Double3))
            fs.advance_by(raw_tok)
            endm = endprog.match(fs.body, fs.pos)
            if endm:
                body_and_close = fs.body[fs.pos:endm.end(0)]
                full_tok = raw_tok + body_and_close
                fs.advance_by(body_and_close)
                if prefix is not None:
                    yield from _fstring_tokens(full_tok, tok_r, tok_c,
                                               fs.source_lines)
                else:
                    yield (STRING, full_tok, (tok_r, tok_c),
                           (fs.row, fs.col), fs.src_line(tok_r, fs.row))
            else:
                # Unterminated triple-quoted string: just yield what we have
                yield (ERRORTOKEN, raw_tok, (tok_r, tok_c),
                       (fs.row, fs.col), fs.src_line(tok_r))
            continue

        # --- Single-quoted string / f-string ---
        if (initial in single_quoted or
                raw_tok[:2] in single_quoted or
                raw_tok[:3] in single_quoted):
            prefix, quote = _fstring_info(raw_tok)
            fs.advance_by(raw_tok)
            if prefix is not None:
                yield from _fstring_tokens(raw_tok, tok_r, tok_c,
                                           fs.source_lines)
            else:
                yield (STRING, raw_tok, (tok_r, tok_c),
                       (fs.row, fs.col), fs.src_line(tok_r))
            continue

        # --- Newline (inside paren) ---
        if initial in '\r\n':
            fs.advance_by(raw_tok)
            yield (NL, raw_tok, (tok_r, tok_c), (fs.row, fs.col),
                   fs.src_line(tok_r))
            continue

        # --- Comment ---
        if initial == '#':
            fs.advance_by(raw_tok)
            # Comments inside f-string expressions are syntax errors in 3.12,
            # but we emit them for robustness.
            yield (COMMENT, raw_tok, (tok_r, tok_c), (fs.row, fs.col),
                   fs.src_line(tok_r))
            continue

        # --- Identifier ---
        if raw_tok.replace('_', 'a').isidentifier():
            raw_tok = fs.body[tok_start:_extend_name(fs.body, tok_end)]
            fs.advance_by(raw_tok)
            yield (NAME, raw_tok, (tok_r, tok_c), (fs.row, fs.col),
                   fs.src_line(tok_r))
            continue

        # --- Number ---
        if initial in '0123456789' or (initial == '.' and raw_tok not in ('.', '...')):
            fs.advance_by(raw_tok)
            yield (NUMBER, raw_tok, (tok_r, tok_c), (fs.row, fs.col),
                   fs.src_line(tok_r))
            continue

        # --- Punctuation / operators ---
        fs.advance_by(raw_tok)
        if initial in '([{':
            paren_depth += 1
        elif initial in ')]}':
            paren_depth -= 1
        yield (OP, raw_tok, (tok_r, tok_c), (fs.row, fs.col),
               fs.src_line(tok_r))


def _scan_format_spec(fs):
    """
    Yield tokens for a format spec (after :), up to and including the }.
    The format spec content is emitted as FSTRING_MIDDLE.
    Nested {expr} inside are tokenized recursively via _scan_expr.
    """
    seg_row, seg_col = fs.row, fs.col
    seg = []

    while not fs.at_end():
        ch = fs.peek()

        escape = fs.named_escape()
        if escape:
            # see _scan_body()
            seg.append(escape)
            fs.advance_by(escape)
            yield (FSTRING_MIDDLE, ''.join(seg),
                   (seg_row, seg_col), (fs.row, fs.col),
                   fs.src_line(seg_row, fs.row))
            seg = []
            seg_row, seg_col = fs.row, fs.col
        elif ch == '{':
            # A format spec has no '{{' escape: a brace always opens a nested
            # field.  CPython emits the preceding literal run even when it is
            # empty if the next character is another brace.
            if seg or fs.peek(1) == '{':
                yield (FSTRING_MIDDLE, ''.join(seg),
                       (seg_row, seg_col), (fs.row, fs.col),
                       fs.src_line(seg_row, fs.row))
                seg = []
            open_r, open_c = fs.row, fs.col
            fs.advance()
            yield (OP, '{', (open_r, open_c), (fs.row, fs.col),
                   fs.src_line(open_r))
            yield from _scan_expr(fs)
            seg_row, seg_col = fs.row, fs.col
        elif ch == '}':
            # Likewise no '}}' escape: this ends the spec.  Its literal run is
            # always emitted, even when empty -- CPython does, and without it
            # untokenize() would glue this '}' to the previous one.
            close_r, close_c = fs.row, fs.col
            yield (FSTRING_MIDDLE, ''.join(seg),
                   (seg_row, seg_col), (close_r, close_c),
                   fs.src_line(seg_row, fs.row))
            seg = []
            fs.advance()
            yield (OP, '}', (close_r, close_c), (fs.row, fs.col),
                   fs.src_line(close_r))
            return
        elif ch == '\n' and not fs.multiline:
            # In a single-quoted f-string a newline ends the format spec --
            # the field itself may still span lines (PEP 701) -- and what
            # follows is tokenized as an expression again, as CPython does.
            yield (FSTRING_MIDDLE, ''.join(seg),
                   (seg_row, seg_col), (fs.row, fs.col),
                   fs.src_line(seg_row, fs.row))
            seg = []
            nl_r, nl_c = fs.row, fs.col
            fs.advance()
            yield (NL, '\n', (nl_r, nl_c), (nl_r, nl_c + 1),
                   fs.src_line(nl_r))
            yield from _scan_expr(fs)
            return
        else:
            seg.append(ch)
            fs.advance()


def _fstring_tokens(token, srow, scol, source_lines):
    """
    Expand a complete f-string token into FSTRING_START / body / FSTRING_END.

    token: complete f-string text (prefix + quotes + body + quotes)
    srow, scol: 1-based row, 0-based column of the first char
    source_lines: list of source lines (for the 'line' field of each token)
    """
    prefix, quote = _fstring_info(token)
    if prefix is None:
        # Shouldn't happen, but fall back to STRING
        sl = source_lines[srow - 1] if source_lines and srow <= len(source_lines) else ''
        yield (STRING, token, (srow, scol), (srow, scol + len(token)), sl)
        return

    fstart = prefix + quote
    body_offset = len(fstart)
    body = token[body_offset:len(token) - len(quote)]

    sl0 = source_lines[srow - 1] if source_lines and srow <= len(source_lines) else ''
    yield (FSTRING_START, fstart,
           (srow, scol), (srow, scol + body_offset), sl0)

    fs = _FStr(body, srow, scol + body_offset, source_lines,
               multiline=len(quote) == 3, raw='r' in prefix.lower())
    yield from _scan_body(fs)

    end_r, end_c = fs.row, fs.col
    sl_end = source_lines[end_r - 1] if source_lines and end_r <= len(source_lines) else ''
    yield (FSTRING_END, quote,
           (end_r, end_c), (end_r, end_c + len(quote)), sl_end)


# -- Main tokenizer generator -------------------------------------------------

def _generate(readline, encoding, extra_tokens):
    """
    Tokenize Python source.  Adapted from the Python 3.11 pure-Python
    tokenizer with f-string expansion for 3.12 compatibility.
    """
    lnum = parenlev = continued = 0
    contstr = ''
    needcont = False
    contline = None
    indents = [0]
    source_lines = []   # accumulated for f-string position info

    # Typing hint: line is str after decoding
    last_line = ''
    line = ''
    endprog = _compile(Single)  # placeholder
    strstart = (0, 0)

    def read_line():
        try:
            data = readline()
        except StopIteration:
            data = b'' if encoding else ''
        if encoding is not None:
            # bytes mode (tokenize): readline must yield bytes
            if not isinstance(data, (bytes, bytearray)):
                raise TypeError("readline() returned a non-bytes object")
            return data.decode(encoding)
        # str mode (generate_tokens): readline must yield str
        if not isinstance(data, str):
            raise TypeError("readline() returned a non-string object")
        return data

    while True:
        last_line = line
        line = read_line()

        source_lines.append(line)
        lnum += 1
        pos, maxpos = 0, len(line)

        if contstr:                                    # continued string
            if not line:
                raise _syntax_error("unterminated triple-quoted string literal",
                                    strstart[0], strstart[1])
            endmatch = endprog.match(line)
            if endmatch:
                pos = end = endmatch.end(0)
                full_str = contstr + line[:end]
                prefix, _ = _fstring_info(full_str)
                if prefix is not None:
                    yield from _fstring_tokens(full_str, strstart[0], strstart[1],
                                               source_lines)
                else:
                    yield (STRING, full_str, strstart, (lnum, end),
                           contline + line)
                contstr = ''
                needcont = False
                contline = None
            elif needcont and line[-2:] != '\\\n' and line[-3:] != '\\\r\n':
                yield (ERRORTOKEN, contstr + line, strstart, (lnum, len(line)),
                       contline)
                contstr = ''
                contline = None
                continue
            else:
                contstr = contstr + line
                contline = contline + line
                continue

        elif parenlev == 0 and not continued:          # new statement
            if not line:
                break
            column = 0
            while pos < maxpos:
                c = line[pos]
                if c == ' ':
                    column += 1
                elif c == '\t':
                    column = (column // tabsize + 1) * tabsize
                elif c == '\f':
                    column = 0
                else:
                    break
                pos += 1
            if pos == maxpos:
                # whitespace-only final line without a trailing newline: the C
                # tokenizer still emits a width-1 virtual NL before ENDMARKER
                if extra_tokens and line:
                    yield (NL, '', (lnum, pos), (lnum, pos + 1), line)
                break

            if line[pos] in '#\r\n':
                if line[pos] == '#':
                    comment_token = line[pos:].rstrip('\r\n')
                    if extra_tokens:
                        yield (COMMENT, comment_token,
                               (lnum, pos), (lnum, pos + len(comment_token)), line)
                    pos += len(comment_token)
                if extra_tokens:
                    # a missing trailing newline still counts as a width-1 NL
                    nl_end = len(line) + (0 if line.endswith(('\n', '\r')) else 1)
                    yield (NL, line[pos:],
                           (lnum, pos), (lnum, nl_end), line)
                continue

            if column > indents[-1]:
                indents.append(column)
                yield (INDENT, line[:pos], (lnum, 0), (lnum, pos), line)
            while column < indents[-1]:
                if column not in indents:
                    stripped = line.rstrip('\r\n')
                    raise IndentationError(
                        "unindent does not match any outer indentation level",
                        ("<string>", lnum, len(stripped) + 1, stripped))
                indents = indents[:-1]
                yield (DEDENT, '', (lnum, pos), (lnum, pos), line)

        else:                                          # continued statement
            if not line:
                raise _syntax_error("unexpected EOF in multi-line statement", lnum, 0)
            continued = 0

        while pos < maxpos:
            pseudomatch = _compile(PseudoToken).match(line, pos)
            if pseudomatch:
                start, end = pseudomatch.span(1)
                spos, epos, pos = (lnum, start), (lnum, end), end
                if start == end:
                    continue
                token, initial = line[start:end], line[start]

                fprefix, fquote = _fstring_info(line[start:])
                if fprefix is not None:
                    # An f-string cannot be matched with a regex (PEP 701: its
                    # fields can hold strings reusing the enclosing quote, and
                    # can span lines), so find its end by scanning, reading
                    # more lines as needed.
                    text = line
                    bstart = start + len(fprefix) + len(fquote)
                    fraw = 'r' in fprefix.lower()
                    fstart_lnum = lnum
                    while True:
                        res = _fstring_extent(text, bstart, fquote, fraw)
                        if res != _FS_MORE:
                            break
                        nextline = read_line()
                        if not nextline:
                            break
                        source_lines.append(nextline)
                        lnum += 1
                        text += nextline
                    if res < 0:
                        raise _syntax_error(
                            "unterminated %sf-string literal (detected at"
                            " line %d)" % ('triple-quoted '
                                           if len(fquote) == 3 else '', lnum),
                            fstart_lnum, start + 1)
                    yield from _fstring_tokens(text[start:res], fstart_lnum,
                                               start, source_lines)
                    nl = text.rfind('\n', 0, res)
                    if nl < 0:
                        pos = res
                    else:
                        line = text[nl + 1:]
                        maxpos = len(line)
                        pos = res - (nl + 1)
                    continue

                if (initial in '0123456789' or
                        (initial == '.' and token not in ('.', '...'))):
                    yield (NUMBER, token, spos, epos, line)

                elif initial in '\r\n':
                    if parenlev > 0:
                        if extra_tokens:
                            yield (NL, token, spos, epos, line)
                    else:
                        yield (NEWLINE, token, spos, epos, line)

                elif initial == '#':
                    if extra_tokens:
                        yield (COMMENT, token, spos, epos, line)

                elif token in triple_quoted:
                    endprog = _compile(endpats[token])
                    endmatch = endprog.match(line, pos)
                    if endmatch:
                        pos = endmatch.end(0)
                        token = line[start:pos]
                        prefix, _ = _fstring_info(token)
                        if prefix is not None:
                            yield from _fstring_tokens(token, lnum, start,
                                                       source_lines)
                        else:
                            yield (STRING, token, spos, (lnum, pos), line)
                    else:
                        strstart = (lnum, start)
                        contstr = line[start:]
                        contline = line
                        break

                elif (initial in single_quoted or
                      token[:2] in single_quoted or
                      token[:3] in single_quoted):
                    if token[-1] == '\n':              # continued string
                        strstart = (lnum, start)
                        endprog = _compile(
                            endpats.get(initial) or
                            endpats.get(token[1]) or
                            endpats.get(token[2]))
                        contstr = line[start:]
                        needcont = True
                        contline = line
                        break
                    else:
                        prefix, _ = _fstring_info(token)
                        if prefix is not None:
                            yield from _fstring_tokens(token, lnum, start,
                                                       source_lines)
                        else:
                            yield (STRING, token, spos, epos, line)

                elif initial.isidentifier():
                    if end < maxpos:
                        end = _extend_name(line, end)
                        token, epos, pos = line[start:end], (lnum, end), end
                    yield (NAME, token, spos, epos, line)

                elif initial == '\\':
                    continued = 1

                else:
                    if initial in '([{':
                        parenlev += 1
                    elif initial in ')]}':
                        # don't go negative on an unmatched close bracket, or
                        # EOF gets misread as an unterminated continued statement
                        if parenlev > 0:
                            parenlev -= 1
                    yield (OP, token, spos, epos, line)
            else:
                yield (ERRORTOKEN, line[pos], (lnum, pos), (lnum, pos + 1), line)
                pos += 1

    # Implicit NEWLINE if the last line didn't end with one
    if last_line and last_line[-1] not in '\r\n':
        if not last_line.strip().startswith('#'):
            last_lnum = lnum - 1
            yield (NEWLINE, '',
                   (last_lnum, len(last_line)),
                   (last_lnum, len(last_line) + 1), last_line)

    for _ in indents[1:]:
        yield (DEDENT, '', (lnum, 0), (lnum, 0), '')

    # ENDMARKER sits on the line after the last content line.  When we broke on
    # an empty readline (EOF), lnum already counts that empty line; when we broke
    # on a content line (e.g. whitespace-only, no trailing newline), it doesn't.
    endmarker_lnum = lnum
    if extra_tokens and line != '':
        endmarker_lnum += 1
    yield (ENDMARKER, '', (endmarker_lnum, 0), (endmarker_lnum, 0), '')


# -- Public API ---------------------------------------------------------------

class TokenizerIter:
    """
    Iterator that tokenizes Python source code, matching CPython 3.12's
    _tokenize.TokenizerIter interface.

    TokenizerIter(readline, *, extra_tokens=False, encoding='utf-8')

    readline must be a callable returning one line at a time (str or bytes).
    Each iteration yields a 5-tuple:
        (type, string, (start_row, start_col), (end_row, end_col), line)
    """

    def __init__(self, readline, *, extra_tokens=False, encoding=None):
        # encoding=None means str mode (readline yields str, no decoding);
        # an explicit encoding means bytes mode.  This mirrors CPython, where
        # tokenize() passes encoding and generate_tokens() does not.
        self._iter = _generate(readline, encoding, extra_tokens)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iter)
