# -*- coding: utf-8 -*-
import pytest
from pypy.interpreter.pyparser import pyparse, pytokenizer
from pypy.interpreter.pyparser.error import SyntaxError, IndentationError, TabError
from pypy.interpreter.astcompiler import consts


class BaseTestPythonParser:
    spaceconfig = {}

    def setup_class(self):
        self.parser = pyparse.PegParser(self.space)

    def parse(self, source, mode="exec", info=None, flags=0):
        if info is None:
            info = pyparse.CompileInfo("<test>", mode, flags=flags)
        return self.parser.parse_source(source, info)

class TestPythonParser(BaseTestPythonParser):
    def test_encoding(self):
        info = pyparse.CompileInfo("<test>", "exec")
        self.parse("""# coding: latin-1
stuff = "nothing"
""", info=info)
        assert info.encoding == "iso-8859-1"
        sentence = u"u'Die Männer ärgern sich!'"
        input = (u"# coding: utf-7\nstuff = %s" % (sentence,)).encode("utf-7")
        self.parse(input, info=info)
        assert info.encoding == "utf-7"
        input = "# coding: iso-8859-15\nx"
        self.parse(input, info=info)
        assert info.encoding == "iso-8859-15"
        input = "\xEF\xBB\xBF# coding: utf-8\nx"
        self.parse(input, info=info)
        assert info.encoding == "utf-8"
        input = "\xEF\xBB\xBF# coding: latin-1\nx"
        exc = pytest.raises(SyntaxError, self.parse, input).value
        assert exc.msg == "UTF-8 BOM with latin-1 coding cookie"
        input = "\xEF\xBB\xBF# coding: UtF-8-yadda-YADDA\nx"
        self.parse(input)    # this does not raise
        input = "# coding: not-here"
        exc = pytest.raises(SyntaxError, self.parse, input).value
        assert exc.msg == "Unknown encoding: not-here"
        input = u"# coding: ascii\n\xe2".encode('utf-8')
        exc = pytest.raises(SyntaxError, self.parse, input).value
        assert exc.msg == ("'ascii' codec can't decode byte 0xc3 "
                           "in position 16: ordinal not in range(128)")

    def test_with_and_as(self):
        pytest.raises(SyntaxError, self.parse, "with = 23")
        pytest.raises(SyntaxError, self.parse, "as = 2")

    def test_dont_imply_dedent(self):
        info = pyparse.CompileInfo("<test>", "single",
                                   consts.PyCF_DONT_IMPLY_DEDENT)
        self.parse('if 1:\n  x\n', info=info)
        self.parse('x = 5 ', info=info)
        pytest.raises(SyntaxError, self.parse, "if 1:\n  x", info=info)
        excinfo = pytest.raises(SyntaxError, self.parse, "if 1:\n  x x\n", info=info)

    def test_encoding_pep3120(self):
        info = pyparse.CompileInfo("<test>", "exec")
        tree = self.parse("""foo = '日本'""", info=info)
        assert info.encoding == 'utf-8'

    def test_unicode_identifier(self):
        tree = self.parse("a日本 = 32")
        tree = self.parse("日本 = 32")

    def test_syntax_error(self):
        parse = self.parse
        exc = pytest.raises(SyntaxError, parse, "name another for").value
        assert exc.msg.startswith("invalid syntax")
        assert exc.lineno == 1
        assert exc.offset in (1, 6)
        assert exc.text.startswith("name another for")
        exc = pytest.raises(SyntaxError, parse, "x = \"blah\n\n\n").value
        assert exc.msg == "unterminated string literal (detected at line 1)"
        assert exc.lineno == exc.end_lineno == 1
        assert exc.offset == 5
        assert exc.end_offset == 10
        exc = pytest.raises(SyntaxError, parse, "x = '''\n\n\n").value
        assert exc.msg.startswith(pytokenizer.TRIPLE_QUOTE_UNTERMINATED_ERROR)
        assert exc.lineno == 1
        assert exc.offset == 5
        assert exc.end_lineno == 3
        for input in ("())", "(()", "((", "))"):
            pytest.raises(SyntaxError, parse, input)
        exc = pytest.raises(SyntaxError, parse, "x = (\n\n(),\n(),").value
        assert exc.msg == "'(' was never closed"
        assert exc.lineno == 1
        assert exc.offset == 5
        assert exc.end_lineno == 5
        exc = pytest.raises(SyntaxError, parse, "abc)").value
        assert exc.msg == "unmatched ')'"
        assert exc.lineno == 1
        assert exc.offset == 4
        exc = pytest.raises(SyntaxError, parse, "\\").value
        assert exc.msg == "unexpected end of file (EOF) in multi-line statement"
        assert exc.lineno == 1

    def test_is(self):
        self.parse("x is y")
        self.parse("x is not y")

    def test_indentation_error(self):
        parse = self.parse
        input = """
def f():
pass"""
        exc = pytest.raises(IndentationError, parse, input).value
        assert exc.msg == "expected an indented block after function definition on line 2"
        assert exc.lineno == 3
        assert exc.text.startswith("pass")
        assert exc.offset == 1
        input = "hi\n    indented"
        exc = pytest.raises(IndentationError, parse, input).value
        assert exc.msg == "unexpected indent"
        input = "def f():\n    pass\n  next_stmt"
        exc = pytest.raises(IndentationError, parse, input).value
        assert exc.msg == "unindent does not match any outer indentation level"
        assert exc.lineno == 3
        assert exc.offset == 3

        input = """
if 1\
        > 3:
pass"""
        exc = pytest.raises(IndentationError, parse, input).value
        assert exc.msg == "expected an indented block after 'if' statement on line 2"
        assert exc.lineno == 3
        assert exc.text.startswith("pass")
        assert exc.offset == 1

        input = """
if x > 1:
    pass
elif x < 1:
pass"""
        exc = pytest.raises(IndentationError, parse, input).value
        assert exc.msg == "expected an indented block after 'elif' statement on line 4"
        assert exc.lineno == 5
        assert exc.text.startswith("pass")
        assert exc.offset == 1


    def test_taberror(self):
        src = """
if 1:
        pass
    \tpass
"""
        exc = pytest.raises(TabError, "self.parse(src)").value
        assert exc.msg == "inconsistent use of tabs and spaces in indentation"
        assert exc.lineno == 4
        assert exc.offset == 5
        assert exc.text == "    \tpass\n"

    def test_mac_newline(self):
        self.parse("this_is\ra_mac\rfile")

    def test_multiline_string(self):
        self.parse("''' \n '''")
        self.parse("r''' \n '''")

    def test_bytes_literal(self):
        self.parse('b" "')
        self.parse('br" "')
        self.parse('b""" """')
        self.parse("b''' '''")
        self.parse("br'\\\n'")

        pytest.raises(SyntaxError, self.parse, "b'a\\n")

    def test_new_octal_literal(self):
        self.parse('0o777')
        pytest.raises(SyntaxError, self.parse, '0o777L')
        pytest.raises(SyntaxError, self.parse, "0o778")

    def test_new_binary_literal(self):
        self.parse('0b1101')
        pytest.raises(SyntaxError, self.parse, '0b0l')
        pytest.raises(SyntaxError, self.parse, "0b112")

    def test_print_function(self):
        self.parse("from __future__ import print_function\nx = print\n")

    def test_revdb_dollar_num(self):
        assert not self.space.config.translation.reverse_debugger
        pytest.raises(SyntaxError, self.parse, '$0')
        pytest.raises(SyntaxError, self.parse, '$0 + 5')
        pytest.raises(SyntaxError, self.parse,
                "from __future__ import print_function\nx = ($0, print)")

    def test_py3k_reject_old_binary_literal(self):
        pytest.raises(SyntaxError, self.parse, '0777')

    def test_py3k_extended_unpacking(self):
        self.parse('a, *rest, b = 1, 2, 3, 4, 5')
        self.parse('(a, *rest, b) = 1, 2, 3, 4, 5')

    def test_u_triple_quote(self):
        self.parse('u""""""')
        self.parse('U""""""')
        self.parse("u''''''")
        self.parse("U''''''")

    def test_bad_single_statement(self):
        pytest.raises(SyntaxError, self.parse, '1\n2', "single")
        pytest.raises(SyntaxError, self.parse, 'a = 13\nb = 187', "single")
        pytest.raises(SyntaxError, self.parse, 'del x\ndel y', "single")
        pytest.raises(SyntaxError, self.parse, 'f()\ng()', "single")
        pytest.raises(SyntaxError, self.parse, 'f()\n# blah\nblah()', "single")
        pytest.raises(SyntaxError, self.parse, 'f()\nxy # blah\nblah()', "single")
        pytest.raises(SyntaxError, self.parse, 'x = 5 # comment\nx = 6\n', "single")

    def test_unpack(self):
        self.parse('[*{2}, 3, *[4]]')
        self.parse('{*{2}, 3, *[4]}')
        self.parse('{**{}, 3:4, **{5:6, 7:8}}')
        self.parse('f(2, *a, *b, **b, **c, **d)')

    def test_async_await(self):
        self.parse("async def coro(): await func")
        self.parse("await x")
        #Test as var and func name
        with pytest.raises(SyntaxError):
            self.parse("async = 1")
        with pytest.raises(SyntaxError):
            self.parse("await = 1")
        with pytest.raises(SyntaxError):
            self.parse("def async(): pass")
        #async for
        self.parse("""async def foo():
    async for a in b:
        pass""")
        self.parse("""def foo():
    async for a in b:
        pass""")
        #async with
        self.parse("""async def foo():
    async with a:
        pass""")
        self.parse('''def foo():
        async with a:
            pass''')

    def test_async_await_hacks(self):
        def parse(source):
            return self.parse(source, flags=consts.PyCF_ASYNC_HACKS)

        # legal syntax
        parse("async def coro(): await func")

        # legal syntax for 3.6<=
        parse("async = 1")
        parse("await = 1")
        parse("def async(): pass")
        parse("def await(): pass")
        parse("""async def foo():
    async for a in b:
        pass""")

        # illegal syntax for 3.6<=
        with pytest.raises(SyntaxError):
            parse("await x")
        with pytest.raises(SyntaxError):
            parse("async for a in b: pass")
        with pytest.raises(SyntaxError):
            parse("def foo(): async for a in b: pass")
        with pytest.raises(SyntaxError):
            parse("def foo(): async for a in b: pass")

    def test_number_underscores(self):
        VALID_UNDERSCORE_LITERALS = [
            '0_0_0',
            '4_2',
            '1_0000_0000',
            '0b1001_0100',
            '0xffff_ffff',
            '0o5_7_7',
            '1_00_00.5',
            '1_00_00.5e5',
            '1_00_00e5_1',
            '1e1_0',
            '.1_4',
            '.1_4e1',
            '0b_0',
            '0x_f',
            '0o_5',
            '1_00_00j',
            '1_00_00.5j',
            '1_00_00e5_1j',
            '.1_4j',
            '(1_2.5+3_3j)',
            '(.5_6j)',
            '.2_3',
            '.2_3e4',
            '1.2_3',
            '1.2_3_4',
            '12.000_400',
            '1_2.3_4',
            '1_2.3_4e5_6',
        ]
        INVALID_UNDERSCORE_LITERALS = [
            # Trailing underscores:
            '0_',
            '42_',
            '1.4j_',
            '0x_',
            '0b1_',
            '0xf_',
            '0o5_',
            '0 if 1_Else 1',
            # Underscores in the base selector:
            '0_b0',
            '0_xf',
            '0_o5',
            # Old-style octal, still disallowed:
            '0_7',
            '09_99',
            # Multiple consecutive underscores:
            '4_______2',
            '0.1__4',
            '0.1__4j',
            '0b1001__0100',
            '0xffff__ffff',
            '0x___',
            '0o5__77',
            '1e1__0',
            '1e1__0j',
            # Underscore right before a dot:
            '1_.4',
            '1_.4j',
            # Underscore right after a dot:
            '1._4',
            '1._4j',
            '._5',
            '._5j',
            # Underscore right after a sign:
            '1.0e+_1',
            '1.0e+_1j',
            # Underscore right before j:
            '1.4_j',
            '1.4e5_j',
            # Underscore right before e:
            '1_e1',
            '1.4_e1',
            '1.4_e1j',
            # Underscore right after e:
            '1e_1',
            '1.4e_1',
            '1.4e_1j',
            # Complex cases with parens:
            '(1+1.5_j_)',
            '(1+1.5_j)',
            # Extra underscores around decimal part
            '._3',
            '._3e4',
            '1.2_',
            '1._3_4',
            '12._',
            '1_2._3',
        ]
        for x in VALID_UNDERSCORE_LITERALS:
            tree = self.parse(x)
        for x in INVALID_UNDERSCORE_LITERALS:
            print x
            pytest.raises(SyntaxError, self.parse, "x = %s" % x)

    def test_relaxed_decorators(self):
        self.parse("@(1 + 2)\ndef f(x): pass") # does not crash

    def test_universal_newlines(self):
        fmt = 'stuff = """hello%sworld"""'
        for linefeed in ["\r\n","\r"]:
            self.parse(fmt % linefeed)


    def test_error_forgotten_chars(self):
        info = pytest.raises(SyntaxError, self.parse, "if 1\n    print 4")
        assert "expected ':'" in info.value.msg
        assert info.value.lineno == 1
        info = pytest.raises(SyntaxError, self.parse, "for i in range(10)\n    print i")
        assert "expected ':'" in info.value.msg
        assert info.value.lineno == 1
        info = pytest.raises(SyntaxError, self.parse, "class A\n    print i")
        assert "expected ':'" in info.value.msg
        assert info.value.lineno == 1
        info = pytest.raises(SyntaxError, self.parse, "with a as b\n    print i")
        assert "expected ':'" in info.value.msg
        assert info.value.lineno == 1
        info = pytest.raises(SyntaxError, self.parse, "try:\n    1\nexcept\n    pass")
        assert "expected ':'" in info.value.msg
        assert info.value.lineno == 3
        info = pytest.raises(SyntaxError, self.parse, "try:\n    1\nexcept IndexError as e\n    pass")
        assert "expected ':'" in info.value.msg
        assert info.value.lineno == 3
        info = pytest.raises(SyntaxError, self.parse, "match x\n    case _:\n        pass")
        assert "expected ':'" in info.value.msg
        assert info.value.lineno == 1

        # the following should *not* contain expected ':'
        info = pytest.raises(SyntaxError, self.parse, "class A&B\n    print i")
        assert "expected ':'" not in info.value.msg # this must point to the 'range 10'
        info = pytest.raises(SyntaxError, self.parse, "for i in range 10\n    print i")
        assert "expected ':'" not in info.value.msg # this must point to the 'range 10'

    def test_positional_only_args(self):
        self.parse("def f(a, /): pass")

    def test_forgot_comma_wrong(self):
        info = pytest.raises(SyntaxError, self.parse, "with block ad something\n    print i")
        assert "invalid syntax" == info.value.msg

    def test_error_print_without_parens(self):
        info = pytest.raises(SyntaxError, self.parse, "print 1")
        assert "Missing parentheses in call to 'print'" in info.value.msg
        info = pytest.raises(SyntaxError, self.parse, "print 1)")
        assert "unmatched" in info.value.msg

    def test_end_location_unparenthized_genexp(self):
        info = pytest.raises(SyntaxError, self.parse, "f(x for x in range(10), 1)")
        assert "Generator expression must be parenthesized" in info.value.msg
        assert info.value.end_offset == 23
        info = pytest.raises(SyntaxError, self.parse, "f(x for x in range(10) if x != 2, 1)")
        assert "Generator expression must be parenthesized" in info.value.msg
        assert info.value.end_offset == 33
        info = pytest.raises(SyntaxError, self.parse, "f(1, x for x in range(10) if x != 2, 1)")
        assert "Generator expression must be parenthesized" in info.value.msg
        assert info.value.end_offset == 36


class TestPythonParserRevDB(TestPythonParser):
    spaceconfig = {"translation.reverse_debugger": True}

    def setup_class(self):
        self.parser = pyparse.PegParser(self.space)

    def test_revdb_dollar_num(self):
        self.parse('$0')
        self.parse('$5')
        self.parse('$42')
        self.parse('2+$42.attrname')
        self.parse("from __future__ import print_function\nx = ($0, print)")
        pytest.raises(SyntaxError, self.parse, '$')
        pytest.raises(SyntaxError, self.parse, '$a')
        pytest.raises(SyntaxError, self.parse, '$.5')


class TestPythonPegParser(BaseTestPythonParser):
    spaceconfig = {}

    def setup_class(self):
        self.parser = pyparse.PegParser(self.space)

    def test_crash_with(self):
        # used to crash
        pytest.raises(SyntaxError, self.parse,
                "async with a:\n    pass", "single",
                flags=consts.PyCF_DONT_IMPLY_DEDENT | consts.PyCF_ALLOW_TOP_LEVEL_AWAIT)

    def test_crash_eval_empty(self):
        # used to crash
        pytest.raises(SyntaxError, self.parse,
                       '', 'eval', flags=consts.PyCF_DONT_IMPLY_DEDENT)


    def test_dont_imply_dedent_ignored_on_exec(self):
        self.parse(
            "if 1: \n pass", "exec",
            flags=consts.PyCF_DONT_IMPLY_DEDENT)

    def test_pattern_matching_experiment(self):
        self.parse("""match x:
                case 1:
                    print('hello')""")

    def test_nonparen_genexp_in_call(self):
        with pytest.raises(SyntaxError) as info:
            self.parse("""\
f(x for x in l)
if 1:
pass
""")
        assert info.value.msg == "expected an indented block after 'if' statement on line 2"
        with pytest.raises(SyntaxError) as info:
            self.parse("""f(1, x for x in y for z in a if

   b)""")
        assert info.value.msg == 'Generator expression must be parenthesized'
        assert info.value.lineno == 1
        assert info.value.offset == 6
        assert info.value.end_lineno == 3
        assert info.value.end_offset == 5


    def test_end_positions(self):
        # this is really an AST test
        ast = self.parse("45 * a", "eval")
        assert ast.body.end_col_offset == 6

    def test_match_deeply_nested(self):
        self.parse("""
match x:
    case [[[[[[[[[[[[[[[[[[[[[[[[[[[[]]]]]]]]]]]]]]]]]]]]]]]]]]]]:
        pass
""")

class TestIncompleteInput(object):
    def setup_class(self):
        self.parser = pyparse.PegParser(self.space)

    def parse(self, source):
        info = pyparse.CompileInfo("<test>", "single", flags=consts.PyCF_ALLOW_INCOMPLETE_INPUT)
        return self.parser.parse_source(source, info)

    def check_incomplete(self, inputstring):
        self.check_error(inputstring, "incomplete input")

    def check_error(self, inputstring, msgfragment='', lineno=-1, offset=-1):
        with pytest.raises(SyntaxError) as info:
            self.parse(inputstring)
        assert msgfragment in info.value.msg
        return info.value.msg

    def test_simple(self):
        self.parse("a")

    def test_expression(self):
        self.check_incomplete("a +")

    def test_if(self):
        self.check_incomplete("if 1:")

    def test_nested(self):
        self.check_incomplete("def f(x):\n    if 1:")

    def test_real_error(self):
        msg = self.check_error("a b c de")
        assert "incomplete source" not in msg

    def test_triplequote(self):
        msg = self.check_incomplete("a = '''")

    def test_triplequote(self):
        msg = self.check_incomplete("a = '''\nabc\def")

    def test_augmented_assignment(self):
        msg = self.check_error("(y for y in (1,2)) += 10")
        assert "'generator expression'" in msg

    def test_parenthesized(self):
        self.check_incomplete("(a **")

    def test_ifelse(self):
        self.check_incomplete("if 9==3:\n   pass\nelse:")
