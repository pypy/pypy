# -*- coding: utf-8 -*-
import py
from pypy.interpreter.pyparser import pyparse
from pypy.interpreter.pyparser.pygram import syms, tokens
from pypy.interpreter.pyparser.error import SyntaxError, IndentationError, TabError
from pypy.interpreter.astcompiler import consts


class TestPythonParserWithoutSpace:

    def setup_class(self):
        self.parser = pyparse.PythonParser(None)

    def parse(self, source, mode="exec", info=None):
        if info is None:
            info = pyparse.CompileInfo("<test>", mode)
        return self.parser.parse_source(source, info)

    def test_with_and_as(self):
        py.test.raises(SyntaxError, self.parse, "with = 23")
        py.test.raises(SyntaxError, self.parse, "as = 2")

    def test_dont_imply_dedent(self):
        info = pyparse.CompileInfo("<test>", "single",
                                   consts.PyCF_DONT_IMPLY_DEDENT)
        self.parse('if 1:\n  x\n', info=info)
        self.parse('x = 5 ', info=info)

    def test_clear_state(self):
        assert self.parser.root is None
        tree = self.parse("name = 32")
        assert self.parser.root is None

    def test_encoding_pep3120(self):
        info = pyparse.CompileInfo("<test>", "exec")
        tree = self.parse("""foo = '日本'""", info=info)
        assert info.encoding == 'utf-8'

    def test_unicode_identifier(self):
        tree = self.parse("a日本 = 32")
        tree = self.parse("日本 = 32")

    def test_syntax_error(self):
        parse = self.parse
        exc = py.test.raises(SyntaxError, parse, "name another for").value
        assert exc.msg == "invalid syntax"
        assert exc.lineno == 1
        assert exc.offset == 5
        assert exc.text.startswith("name another for")
        exc = py.test.raises(SyntaxError, parse, "x = \"blah\n\n\n").value
        assert exc.msg == "EOL while scanning string literal"
        assert exc.lineno == 1
        assert exc.offset == 5
        exc = py.test.raises(SyntaxError, parse, "x = '''\n\n\n").value
        assert exc.msg == "EOF while scanning triple-quoted string literal"
        assert exc.lineno == 1
        assert exc.offset == 5
        assert exc.lastlineno == 3
        for input in ("())", "(()", "((", "))"):
            py.test.raises(SyntaxError, parse, input)
        exc = py.test.raises(SyntaxError, parse, "x = (\n\n(),\n(),").value
        assert exc.msg == "parenthesis is never closed"
        assert exc.lineno == 1
        assert exc.offset == 5
        assert exc.lastlineno == 5
        exc = py.test.raises(SyntaxError, parse, "abc)").value
        assert exc.msg == "unmatched ')'"
        assert exc.lineno == 1
        assert exc.offset == 4

    def test_is(self):
        self.parse("x is y")
        self.parse("x is not y")

    def test_indentation_error(self):
        parse = self.parse
        input = """
def f():
pass"""
        exc = py.test.raises(IndentationError, parse, input).value
        assert exc.msg == "expected an indented block"
        assert exc.lineno == 3
        assert exc.text.startswith("pass")
        assert exc.offset == 0
        input = "hi\n    indented"
        exc = py.test.raises(IndentationError, parse, input).value
        assert exc.msg == "unexpected indent"
        input = "def f():\n    pass\n  next_stmt"
        exc = py.test.raises(IndentationError, parse, input).value
        assert exc.msg == "unindent does not match any outer indentation level"
        assert exc.lineno == 3

    def test_taberror(self):
        src = """
if 1:
        pass
    \tpass
"""
        exc = py.test.raises(TabError, "self.parse(src)").value
        assert exc.msg == "inconsistent use of tabs and spaces in indentation"
        assert exc.lineno == 4
        assert exc.offset == 5
        assert exc.text == "    \tpass\n"

    def test_mac_newline(self):
        self.parse("this_is\ra_mac\rfile")

    def test_mode(self):
        assert self.parse("x = 43*54").type == syms.file_input
        tree = self.parse("43**54", "eval")
        assert tree.type == syms.eval_input
        py.test.raises(SyntaxError, self.parse, "x = 54", "eval")
        tree = self.parse("x = 43", "single")
        assert tree.type == syms.single_input

    def test_multiline_string(self):
        self.parse("''' \n '''")
        self.parse("r''' \n '''")

    def test_bytes_literal(self):
        self.parse('b" "')
        self.parse('br" "')
        self.parse('b""" """')
        self.parse("b''' '''")
        self.parse("br'\\\n'")

        py.test.raises(SyntaxError, self.parse, "b'a\\n")

    def test_new_octal_literal(self):
        self.parse('0o777')
        py.test.raises(SyntaxError, self.parse, '0o777L')
        py.test.raises(SyntaxError, self.parse, "0o778")

    def test_new_binary_literal(self):
        self.parse('0b1101')
        py.test.raises(SyntaxError, self.parse, '0b0l')
        py.test.raises(SyntaxError, self.parse, "0b112")

    def test_print_function(self):
        self.parse("from __future__ import print_function\nx = print\n")

    def test_universal_newlines(self):
        fmt = 'stuff = """hello%sworld"""'
        expected_tree = self.parse(fmt % '\n')
        for linefeed in ["\r\n","\r"]:
            tree = self.parse(fmt % linefeed)
            assert expected_tree == tree

    def test_py3k_reject_old_binary_literal(self):
        py.test.raises(SyntaxError, self.parse, '0777')

    def test_py3k_extended_unpacking(self):
        self.parse('a, *rest, b = 1, 2, 3, 4, 5')
        self.parse('(a, *rest, b) = 1, 2, 3, 4, 5')

    def test_u_triple_quote(self):
        self.parse('u""""""')
        self.parse('U""""""')
        self.parse("u''''''")
        self.parse("U''''''")

    def test_bad_single_statement(self):
        py.test.raises(SyntaxError, self.parse, '1\n2', "single")
        py.test.raises(SyntaxError, self.parse, 'a = 13\nb = 187', "single")
        py.test.raises(SyntaxError, self.parse, 'del x\ndel y', "single")
        py.test.raises(SyntaxError, self.parse, 'f()\ng()', "single")
        py.test.raises(SyntaxError, self.parse, 'f()\n# blah\nblah()', "single")
        py.test.raises(SyntaxError, self.parse, 'f()\nxy # blah\nblah()', "single")
        py.test.raises(SyntaxError, self.parse, 'x = 5 # comment\nx = 6\n', "single")
    
    def test_unpack(self):
        self.parse('[*{2}, 3, *[4]]')
        self.parse('{*{2}, 3, *[4]}')
        self.parse('{**{}, 3:4, **{5:6, 7:8}}')
        self.parse('f(2, *a, *b, **b, **c, **d)')

    def test_async_await(self):
        self.parse("async def coro(): await func")
        py.test.raises(SyntaxError, self.parse, 'await x')
        #Test as var and func name
        self.parse("async = 1")
        self.parse("await = 1")
        self.parse("def async(): pass")
        #async for
        self.parse("""async def foo():
    async for a in b:
        pass""")
        py.test.raises(SyntaxError, self.parse, 'def foo(): async for a in b: pass')
        #async with
        self.parse("""async def foo():
    async with a:
        pass""")
        py.test.raises(SyntaxError, self.parse, 'def foo(): async with a: pass')
        
        

class TestPythonParserWithSpace:

    def setup_class(self):
        self.parser = pyparse.PythonParser(self.space)

    def parse(self, source, mode="exec", info=None):
        if info is None:
            info = pyparse.CompileInfo("<test>", mode)
        return self.parser.parse_source(source, info)

    def test_encoding(self):
        info = pyparse.CompileInfo("<test>", "exec")
        tree = self.parse("""# coding: latin-1
stuff = "nothing"
""", info=info)
        assert tree.type == syms.file_input
        assert info.encoding == "iso-8859-1"
        sentence = u"'Die Männer ärgen sich!'"
        input = (u"# coding: utf-7\nstuff = %s" % (sentence,)).encode("utf-7")
        tree = self.parse(input, info=info)
        assert info.encoding == "utf-7"
        input = "# coding: iso-8859-15\nx"
        self.parse(input, info=info)
        assert info.encoding == "iso-8859-15"
        input = "\xEF\xBB\xBF# coding: utf-8\nx"
        self.parse(input, info=info)
        assert info.encoding == "utf-8"
        #
        info.flags |= consts.PyCF_SOURCE_IS_UTF8
        input = "#\nx"
        info.encoding = None
        self.parse(input, info=info)
        assert info.encoding == "utf-8"
        input = "# coding: latin1\nquux"
        self.parse(input, info=info)
        assert info.encoding == "latin1"
        info.flags |= consts.PyCF_IGNORE_COOKIE
        self.parse(input, info=info)
        assert info.encoding == "utf-8"
        info.flags &= ~(consts.PyCF_SOURCE_IS_UTF8 | consts.PyCF_IGNORE_COOKIE)
        #
        input = "\xEF\xBB\xBF# coding: latin-1\nx"
        exc = py.test.raises(SyntaxError, self.parse, input).value
        assert exc.msg == "UTF-8 BOM with latin-1 coding cookie"
        input = "# coding: not-here"
        exc = py.test.raises(SyntaxError, self.parse, input).value
        assert exc.msg == "Unknown encoding: not-here"
        input = u"# coding: ascii\n\xe2".encode('utf-8')
        exc = py.test.raises(SyntaxError, self.parse, input).value
        assert exc.msg == ("'ascii' codec can't decode byte 0xc3 "
                           "in position 16: ordinal not in range(128)")
