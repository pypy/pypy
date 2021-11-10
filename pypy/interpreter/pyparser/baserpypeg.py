""" Base class with all the support code of the rpython peg parser """

import io
import os
import sys

from pypy.interpreter.pyparser.pygram import tokens
from pypy.interpreter.pyparser.parser import Token
from pypy.interpreter.pyparser import pytokenizer as tokenize, pytoken
from pypy.interpreter.pyparser.error import SyntaxError, IndentationError

from pypy.interpreter.astcompiler import ast
from pypy.interpreter.astcompiler.astbuilder import parse_number, ASTBuilder
from pypy.interpreter.astcompiler import asthelpers # Side effects
from pypy.interpreter.astcompiler import consts, misc

from rpython.rlib.objectmodel import specialize

Load = ast.Load
Store = ast.Store
Del = ast.Del

class BaseMemoEntry(object):
    _attrs_ = ['endmark', 'next']
    def __init__(self, endmark, next):
        self.endmark = endmark
        self.next = next

def find_memo(tok, cls):
    memo = tok.memo
    while memo:
        if type(memo) is cls:
            return memo
        memo = memo.next
    return None

def shorttok(tok):
    return "%-25.25s" % ("%s.%s: %s:%r" % (tok.lineno, tok.column, tok.token_type, tok.value))

def log_start(self, method_name):
    fill = "  " * self._level
    print "%s%s() .... (looking at %s)" % (fill, method_name, self.showpeek())
    self._level += 1

def log_end(self, method_name, result):
    self._level -= 1
    fill = "  " * self._level
    print "%s... %s(%s) --> %s" % (fill, method_name, result)

def make_memo_class(method_name):
    class MemoEntry(BaseMemoEntry):
        _attrs_ = ['tree']
        def __init__(self, tree, endmark, next):
            BaseMemoEntry.__init__(self, endmark, next)
            self.tree = tree
    MemoEntry.__name__ += "_" + "method_name"
    return MemoEntry

def memoize(method):
    """Memoize a symbol method."""
    method_name = method.__name__
    MemoEntry = make_memo_class(method_name)

    def memoize_wrapper(self):
        tok = self.peek()
        memo = find_memo(tok, MemoEntry)
        # Fast path: cache hit, and not verbose.
        fill = ''
        if memo:
            assert isinstance(memo, MemoEntry)
            self._reset(memo.endmark)
            return memo.tree
        # Slow path: no cache hit, or verbose.
        verbose = self._verbose
        if verbose:
            fill = "  " * self._level
            print "%s%s() .... (looking at %s)" % (fill, method_name, self.showpeek())
            self._level += 1
        tree = method(self)
        if verbose:
            self._level -= 1
            print "%s... %s() --> %s" % (fill, method_name, tree)
        endmark = self._mark()
        tok.memo = MemoEntry(tree, endmark, tok.memo)
        return tree

    memoize_wrapper.__wrapped__ = method  # type: ignore
    return memoize_wrapper


def memoize_left_rec(method):
    """Memoize a left-recursive symbol method."""
    method_name = method.__name__
    MemoEntry = make_memo_class(method_name)

    def memoize_left_rec_wrapper(self):
        mark = self._mark()
        tok = self.peek()
        memo = find_memo(tok, MemoEntry)
        # Fast path: cache hit
        if memo:
            assert isinstance(memo, MemoEntry)
            self._reset(memo.endmark)
            return memo.tree
        fill = "  " * self._level
        # key not in cache
        verbose = self._verbose
        if verbose:
            print "%s%s .... (looking at %s)" % (fill, method_name, self.showpeek())
        self._level += 1

        # For left-recursive rules we manipulate the cache and
        # loop until the rule shows no progress, then pick the
        # previous result.  For an explanation why this works, see
        # https://github.com/PhilippeSigaud/Pegged/wiki/Left-Recursion
        # (But we use the memoization cache instead of a static
        # variable; perhaps this is similar to a paper by Warth et al.
        # (http://web.cs.ucla.edu/~todd/research/pub.php?id=pepm08).

        # Prime the cache with a failure.
        memo = tok.memo = MemoEntry(None, mark, tok.memo)
        lastresult, lastmark = None, mark
        depth = 0
        if verbose:
            print "%sRecursive %s at %s depth %s" % (fill, method_name, mark, depth)

        while True:
            self._reset(mark)
            self.in_recursive_rule += 1
            try:
                result = method(self)
            finally:
                self.in_recursive_rule -= 1
            endmark = self._mark()
            depth += 1
            if verbose:
                print "%sRecursive %s at %s depth %s: %.200s to %s" % (fill, method_name, mark, depth, result, endmark)
            if not result:
                if verbose:
                    print "%sFail with %.200s to %s" % (fill, lastresult, lastmark)
                break
            if endmark <= lastmark:
                if verbose:
                    print "%sBailing with %.200s to %s" % (fill, lastresult, lastmark)
                break
            memo.tree, memo.endmark = lastresult, lastmark = result, endmark

        self._reset(lastmark)
        tree = lastresult

        self._level -= 1
        if verbose:
            print "%s... %s() --> %s [cached]" % (fill, method_name, tree)
        if tree:
            endmark = self._mark()
        else:
            endmark = mark
            self._reset(endmark)
        memo.tree, memo.endmark = tree, endmark
        return tree

    memoize_left_rec_wrapper.__wrapped__ = method  # type: ignore
    return memoize_left_rec_wrapper

def isspace(s):
    res = True
    for c in s:
        if not c.isspace():
            res = False
    return res

class NameDefaultPair(object):
    def __init__(self, arg, value):
        self.arg = arg
        self.value = value

class StarEtc(object):
    def __init__(self, vararg, kwonlyargs, kwarg):
        self.vararg = vararg
        self.kwonlyargs = kwonlyargs
        self.kwarg = kwarg

class SlashWithDefault(object):
    def __init__(self, plain_names, names_with_defaults):
        self.plain_names = plain_names
        self.names_with_defaults = names_with_defaults

class DictDisplaysEntry(object):
    def __init__(self, key, value):
        self.key = key
        self.value = value

class CmpopExprPair(object):
    def __init__(self, cmpop, expr):
        self.cmpop = cmpop
        self.expr = expr

class Parser:
    """Parsing base class."""

    # KEYWORDS: ClassVar[Tuple[str, ...]]

    # SOFT_KEYWORDS: ClassVar[Tuple[str, ...]]

    def __init__(self, space, tokenlist, compile_info, verbose=False):
        # initialize tokenization stuff
        self._tokens = []
        self._lines = {}
        self._path = "" # XXX
        self.type_ignores = []
        self.compile_info = compile_info
        for tok in tokenlist:
            # Special handling for TYPE_IGNOREs
            if tok.token_type == tokens.TYPE_IGNORE:
                self.type_ignores.append(tok)
                continue
            if tok.token_type in (tokens.NL, tokens.COMMENT):
                continue
            if tok.token_type == tokens.ERRORTOKEN and isspace(tok.value):
                continue
            if (
                tok.token_type == tokens.NEWLINE
                and self._tokens
                and self._tokens[-1].token_type == tokens.NEWLINE
            ):
                continue
            if tok.token_type == tokens.NAME:
                index = self.KEYWORD_INDICES.get(tok.value, -1)
                if index != -1:
                    tok.token_type = index
            tok.memo = None
            self._tokens.append(tok)
            if not self._path and tok.line and tok.lineno not in self._lines:
                self._lines[tok.lineno] = tok.line
        self._index = 0
        self._highwatermark = 0

        # parser stuff
        self._verbose = verbose
        self._level = 0
        self._cache = {}
        # Integer tracking wether we are in a left recursive rule or not. Can be useful
        # for error reporting.
        self.in_recursive_rule = 0

        self.call_invalid_rules = False

        self.py_version = (3, 9)
        self.space = space

    def recursive_parse_to_ast(self, str, info):
        from pypy.interpreter.pyparser import pytokenizer as tokenize
        from pypy.interpreter.pyparser import rpypegparse
        tokenlist = tokenize.generate_tokens(str.splitlines(), 0)
        parser = rpypegparse.PythonParser(self.space, tokenlist, self.compile_info, verbose=False)
        return parser.eval()

    def deprecation_warn(self, msg, tok):
        from pypy.interpreter import error
        from pypy.module._warnings.interp_warnings import warn_explicit
        space = self.space
        try:
            warn_explicit(
                space, space.newtext(msg),
                space.w_DeprecationWarning,
                space.newtext(self.compile_info.filename),
                tok.lineno,
                space.w_None,
                space.w_None,
                space.w_None,
                space.w_None,
                )
        except error.OperationError as e:
            if e.match(space, space.w_DeprecationWarning):
                self.raise_syntax_error_known_location(msg, tok)
            else:
                raise


    def parse(self, entry):
        res = entry()
        if res is not None:
            return res
        self.reset()
        self.call_invalid_rules = True
        entry() # usually raises

    def reset(self):
        self._index = 0
        self._highwatermark = 0

        self._verbose = False
        self._level = 0
        self._cache = {}
        for tok in self._tokens:
            tok.memo = None
        self.in_recursive_rule = 0


    # tokenizer methods

    def _mark(self):
        return self._index

    def getnext(self):
        """Return the next token and updates the index."""
        cached = not self._index == len(self._tokens)
        tok = self.peek()
        self._index += 1
        self._highwatermark = max(self._highwatermark, self._index)
        if self._verbose:
            self.report(cached, False)
        return tok

    def peek(self):
        """Return the next token *without* updating the index."""
        assert self._index < len(self._tokens)
        return self._tokens[self._index]

    def diagnose(self):
        return self._tokens[self._highwatermark]

    def get_last_non_whitespace_token(self):
        tok = self._tokens[0]
        for index in range(self._index - 1, -1, -1):
            tok = self._tokens[index]
            if tok.token_type != tokens.ENDMARKER and (
                tok.token_type < tokens.NEWLINE or tok.token_type > tokens.DEDENT
            ):
                break
        return tok

    def get_lines(self, line_numbers):
        """Retrieve source lines corresponding to line numbers."""
        if self._lines:
            lines = self._lines
        else:
            assert 0
            n = len(line_numbers)
            lines = {}
            count = 0
            seen = 0
            with open(self._path) as f:
                for l in f:
                    count += 1
                    if count in line_numbers:
                        seen += 1
                        lines[count] = l
                        if seen == n:
                            break

        return [lines[n] for n in line_numbers]

    def _reset(self, index):
        if index == self._index:
            return
        assert 0 <= index <= len(self._tokens), (index, len(self._tokens))
        old_index = self._index
        self._index = index
        if self._verbose:
            self.report(True, index < old_index)

    def report(self, cached, back):
        if back:
            fill = "-" * self._index + "-"
        elif cached:
            fill = "-" * self._index + ">"
        else:
            fill = "-" * self._index + "*"
        if self._index == 0:
            print("%s (Bof)" % fill)
        else:
            tok = self._tokens[self._index - 1]
            print "%s %s" % (fill, shorttok(tok))
    # parser methods

    def start(self):
        pass

    def showpeek(self):
        tok = self.peek()
        return shorttok(tok)

    def name(self):
        tok = self.peek()
        if tok.token_type == tokens.NAME:
            self.getnext()
            return ast.Name(
                    id=self.new_identifier(tok.value),
                    ctx=Load,
                    lineno=tok.lineno,
                    col_offset=tok.column,
                    end_lineno=tok.end_lineno,
                    end_col_offset=tok.end_column,
                )
        return None

    def number(self):
        tok = self.peek()
        if tok.token_type == tokens.NUMBER:
            return self.getnext()
        return None

    def string(self):
        tok = self.peek()
        if tok.token_type == tokens.STRING:
            return self.getnext()
        return None

    def op(self):
        tok = self.peek()
        if tok.token_type == tokens.OP:
            return self.getnext()
        return None

    def type_comment(self):
        tok = self.peek()
        space = self.space
        if tok.token_type == tokens.TYPE_COMMENT:
            return space.newtext(self.getnext().value)
        return space.w_None

    def soft_keyword(self):
        tok = self.peek()
        if tok.token_type == tokens.NAME and tok.value in self.SOFT_KEYWORDS:
            self.getnext()
            return ast.Name(
                    id=self.new_identifier(tok.value),
                    ctx=Load,
                    lineno=tok.lineno,
                    col_offset=tok.column,
                    end_lineno=tok.end_lineno,
                    end_col_offset=tok.end_column,
                )
        return None

    def expect(self, type):
        tok = self.peek()
        if tok.value == type:
            return self.getnext()
        if type in pytoken.python_opmap:
            if tok.token_type == pytoken.python_opmap[type]:
                return self.getnext()
        if type in pytoken.python_tokens:
            if tok.token_type == pytoken.python_tokens[type]:
                return self.getnext()
        if tok.token_type == tokens.OP and tok.value == type:
            return self.getnext()
        return None

    def expect_type(self, type):
        tok = self.peek()
        if tok.token_type == type:
            return self.getnext()

    def expect_forced(self, res, expectation):
        if res is None:
            self.raise_syntax_error("expected " + expectation)
        return res

    def positive_lookahead(self, func, *args):
        mark = self._mark()
        ok = func(self, *args)
        self._reset(mark)
        return ok

    def negative_lookahead(self, func, *args):
        mark = self._mark()
        ok = func(self, *args)
        self._reset(mark)
        return not ok

    @specialize.argtype(3)
    def check_version(self, min_version, error_msg, node):
        """Check that the python version is high enough for a rule to apply.

        """
        if (self.py_version[0] >= min_version[0] or
            (self.py_version[0] == self.min_version[0] and
                self.py_version[1] >= min_version[1])):
            return node
        else:
            self.raise_syntax_error_known_location(
                "%s only supported in Python %s and above." % (error_msg, min_version),
                node)

    def raise_indentation_error(self, msg):
        """Raise an indentation error."""
        self._raise_syntax_error(msg, cls=IndentationError)

    def get_expr_name(self, node):
        """Get a descriptive name for an expression."""
        return node._get_descr(self.space)

    def set_expr_context(self, node, context):
        """Set the context (Load, Store, Del) of an ast node."""
        try:
            node.set_context(self.space, context)
        except ast.UnacceptableExpressionContext as e:
            self.raise_syntax_error_known_location(e.msg, e.node)
        except misc.ForbiddenNameAssignment as e:
            self.raise_syntax_error_known_location("cannot assign to %s" % (e.name,), e.node)
        return node

    def check_for_forbidden_assignment_target(self, name):
        from pypy.interpreter.astcompiler import misc # Side effects
        if name is None:
            return None
        assert isinstance(name, ast.Name)
        id = name.id
        try:
            misc.check_forbidden_name(self.space, id)
        except misc.ForbiddenNameAssignment as e:
            self.raise_syntax_error_known_location(
                "cannot assign to %s" % (e.name,), name)
        return id

    def check_repeated_keywords(self, args):
        if not args or not args.keywords:
            return None
        keywords = args.keywords
        if len(keywords) == 1:
            return keywords
        d = {}
        for keyword in keywords:
            assert isinstance(keyword, ast.keyword)
            if keyword.arg is None:
                # **arg
                continue
            if keyword.arg in d:
                self.raise_syntax_error_known_location(
                    "keyword argument repeated: '%s'" % keyword.arg, keyword)
            d[keyword.arg] = None
        return keywords

    def get_last_target(self, for_if_clauses):
        if not for_if_clauses:
            return None
        last = for_if_clauses[-1]
        assert isinstance(last, ast.comprehension)
        return last.target

    def check_last_keyword_no_arg(self, args):
        if not args.keywords:
            return False
        kw = args.keywords[-1]
        assert isinstance(kw, ast.keyword)
        return kw.arg is None

    def new_identifier(self, name):
        return misc.new_identifier(self.space, name)

    def ensure_real(self, number_str):
        number = ast.literal_eval(number_str)
        if number is not complex:
            self.raise_syntax_error("real number required in complex literal")
        return number

    def ensure_imaginary(self, number_str):
        number = ast.literal_eval(number_str)
        if number is not complex:
            self.raise_syntax_error("imaginary  number required in complex literal")
        return number

    def generate_ast_for_string(self, tokens):
        """Generate AST nodes for strings."""
        from pypy.interpreter.pyparser.parser import Nonterminal, Terminal
        from pypy.interpreter.astcompiler.fstring import string_parse_literal
        # bit of a hack, allow fstrings to keep using the old interface
        return string_parse_literal(
            self,
            tokens)

    def extract_import_level(self, tokens):
        """Extract the relative import level from the tokens preceding the module name.

        '.' count for one and '...' for 3.

        """
        level = 0
        for t in tokens:
            if t.value == ".":
                level += 1
            else:
                level += 3
        return level

    def set_decorators(self,
        target,
        decorators
    ):
        """Set the decorators on a function or class definition."""
        # for rpython
        if isinstance(target, ast.FunctionDef):
            target.decorator_list = decorators
        elif isinstance(target, ast.AsyncFunctionDef):
            target.decorator_list = decorators
        else:
            assert isinstance(target, ast.ClassDef)
            target.decorator_list = decorators
        return target

    def get_comparison_ops(self, pairs):
        return [p.cmpop for p in pairs]

    def get_comparators(self, pairs):
        return [p.expr for p in pairs]

    def set_arg_type_comment(self, arg, type_comment):
        if type_comment:
            arg.type_comment = type_comment
        return arg

    def name_default_pair(self, arg, value, type_comment):
        self.set_arg_type_comment(arg, type_comment)
        return NameDefaultPair(arg, value)

    def make_star_etc(self, a, b, c):
        return StarEtc(a, b, c)

    def make_slash_with_default(self, plain_names, names_with_default):
        return SlashWithDefault(plain_names, names_with_default)

    def dict_display_entry(self, key, value):
        return DictDisplaysEntry(key, value)

    def cmpop_expr_pair(self, cmpop, expr):
        return CmpopExprPair(cmpop, expr)

    def dummy_name(self, *args):
        return ast.Name(
                id="dummy%s" % (len(args), ),
                ctx=Load,
                lineno=1,
                col_offset=0,
                end_lineno=1,
                end_col_offset=0,
            )

    def get_names(self, names_with_defaults):
        if names_with_defaults is None:
            return []
        return [p.arg for p in names_with_defaults]

    def get_defaults(self, names_with_defaults):
        if names_with_defaults is None:
            return []
        return [p.value for p in names_with_defaults]

    def make_posonlyargs(self, slash_without_default, slash_with_default):
        if slash_without_default is not None:
            return slash_without_default
        elif slash_with_default is not None:
            names = self.get_names(slash_with_default.names_with_defaults)
            return slash_with_default.plain_names + names
        else:
            return []

    def make_posargs(self, plain_names, names_with_default):
        if plain_names is None:
            plain_names = []
        names = self.get_names(names_with_default)
        return plain_names + names

    def make_arguments(self,
        slash_without_default,
        slash_with_default,
        plain_names,
        names_with_default,
        star_etc,
    ):
        """Build a function definition arguments."""
        posonlyargs = self.make_posonlyargs(
            slash_without_default, slash_with_default)
        posargs = self.make_posargs(plain_names, names_with_default)

        posdefaults = (
            self.get_defaults(slash_with_default.names_with_defaults)
                if slash_with_default else []
            + self.get_defaults(names_with_default)
        )

        vararg = star_etc.vararg if star_etc else None

        kwonlyargs = self.get_names(star_etc.kwonlyargs) if star_etc else []
        kwdefaults = self.get_defaults(star_etc.kwonlyargs) if star_etc else []
        kwarg = star_etc.kwarg if star_etc else None

        return ast.arguments(
            posonlyargs=posonlyargs if posonlyargs else None,
            args=posargs if posargs else None,
            defaults=posdefaults if posdefaults else None,
            vararg=vararg,
            kwonlyargs=kwonlyargs if kwonlyargs else None,
            kw_defaults=kwdefaults if kwdefaults else None,
            kwarg=kwarg
        )

    def _raise_syntax_error(
        self,
        message,
        start_lineno=-1,
        start_col_offset=-1,
        end_lineno=-1,
        end_col_offset=-1,
        cls=SyntaxError,
    ):
        line_from_token = start_lineno == -1 and end_lineno == -1
        tok = self.diagnose()
        if start_lineno == -1:
            start_lineno = tok.lineno
            start_col_offset = tok.column
        if end_lineno == -1:
            end_lineno = tok.end_lineno
            end_column = tok.end_column

        if line_from_token:
            line = tok.line
        else:
            # End is used only to get the proper text
            line = "".join(
                self.get_lines(range(start_lineno, end_lineno + 1))
            )

        raise cls(
            message,
            start_lineno, start_col_offset + 1, line, self.compile_info.filename, lastlineno=end_lineno
        )

    @specialize.argtype(1)
    def extract_pos_start(self, node_or_tok):
        if isinstance(node_or_tok, ast.AST):
            return node_or_tok.lineno, node_or_tok.col_offset
        else:
            assert isinstance(node_or_tok, Token)
            return node_or_tok.lineno, node_or_tok.column

    @specialize.argtype(1)
    def extract_pos_end(self, node_or_tok):
        if isinstance(node_or_tok, ast.AST):
            return node_or_tok.end_lineno, node_or_tok.end_col_offset
        else:
            assert isinstance(node_or_tok, Token)
            return node_or_tok.end_lineno, node_or_tok.end_column

    @specialize.argtype(2, 3)
    def raise_syntax_error_known_range(
        self,
        message,
        start_node_or_tok,
        end_node_or_tok,
    ):
        start_lineno, start_col_offset = self.extract_pos_start(start_node_or_tok)
        end_lineno, end_col_offset = self.extract_pos_end(end_node_or_tok)
        self._raise_syntax_error(message, start_lineno, start_col_offset, end_lineno, end_col_offset)

    @specialize.argtype(2)
    def raise_syntax_error_starting_from(
        self,
        message,
        start_node_or_tok,
    ):
        start_lineno, start_col_offset = self.extract_pos_start(start_node_or_tok)
        self._raise_syntax_error(message, start_lineno, start_col_offset, -1, -1)

    def raise_syntax_error(self, message):
        self._raise_syntax_error(message)

    @specialize.argtype(2)
    def raise_syntax_error_known_location(
            self,
            message,
            node_or_tok,
        ):
        """Raise a syntax error that occured at a given AST node or Token."""
        start_lineno, start_col_offset = self.extract_pos_start(node_or_tok)
        end_lineno, end_col_offset = self.extract_pos_end(node_or_tok)
        self._raise_syntax_error(message, start_lineno, start_col_offset, end_lineno, end_col_offset)

    def make_type_ignores(self):
        type_ignores = []
        for type_ignore in self.type_ignores:
            tag = self.space.newtext(type_ignore.value)
            type_ignores.append(ast.TypeIgnore(type_ignore.lineno, tag))
        return type_ignores

    def check_barry(self, tok):
        flufl = self.compile_info.flags & consts.CO_FUTURE_BARRY_AS_BDFL
        if flufl and tok.value == '!=':
            self.raise_syntax_error_known_location("with Barry as BDFL, use '<>' instead of '!='", tok)
        elif not flufl and tok.value == '<>':
            self.raise_syntax_error_known_location('invalid syntax', tok)
        return tok

    def kwarg_illegal_assignment(self, a, b):
        space = self.space
        if isinstance(a, ast.Constant):
            if space.is_w(a.value, space.w_True):
                error = "True"
            elif space.is_w(a.value, space.w_False):
                error = "False"
            elif space.is_w(a.value, space.w_None):
                error = "None"
            else:
                error = None
            if error is not None:
                self.raise_syntax_error_known_range(
                    "cannot assign to " + error, a, b,
                )
        self.raise_syntax_error_known_range(
            'expression cannot contain assignment, perhaps you meant "=="?', a, b,
        )

    def revdbmetavar(self, num, *LOCATIONS):
        if not self.space.config.translation.reverse_debugger:
            self.raise_syntax_error_known_location("Unkown character", *LOCATIONS)
        return ast.RevDBMetaVar(num, *LOCATIONS)
