import py
from pypy.interpreter.pyparser import future, pyparse
from pypy.interpreter.astcompiler import astbuilder
from pypy.tool import stdlib___future__ as fut

class F(object):
    pass

def run(space, source):
    parser = pyparse.PythonParser(space)
    info = pyparse.CompileInfo("<string>", "exec")
    tree = parser.parse_source(source, info)
    mod = astbuilder.ast_from_node(space, tree, info)
    f = F()
    f.flags, (f.lineno, f.col_offset) = \
        future.get_futures(future.futureFlags_2_5, mod)
    return f

def test_docstring(space):
    s = '"Docstring\\" "\nfrom  __future__ import division\n'
    f = run(space, s)
    assert f.flags == fut.CO_FUTURE_DIVISION
    assert f.lineno == 2
    assert f.col_offset == 0

def test_comment(space):
    s = '# A comment about nothing ;\n'
    f = run(space, s)
    assert f.lineno == -1
    assert f.col_offset == 0

def test_tripledocstring(space):
    s = '''""" This is a
docstring with line
breaks in it. It even has a \n"""
'''
    f = run(space, s)
    assert f.lineno == -1
    assert f.col_offset == 0

def test_escapedquote_in_tripledocstring(space):
    s = '''""" This is a
docstring with line
breaks in it. \\"""It even has an escaped quote!"""
'''
    f = run(space, s)
    assert f.lineno == -1
    assert f.col_offset == 0

def test_empty_line(space):
    s = ' \t   \f \n   \n'
    f = run(space, s)
    assert f.lineno == -1
    assert f.col_offset == 0

def test_from(space):
    s = 'from  __future__ import division\n'
    f = run(space, s)
    assert f.flags == fut.CO_FUTURE_DIVISION
    assert f.lineno == 1
    assert f.col_offset == 0

def test_froms(space):
    s = 'from  __future__ import division, generators, with_statement\n'
    f = run(space, s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED |
                       fut.CO_FUTURE_WITH_STATEMENT)
    assert f.lineno == 1
    assert f.col_offset == 0

def test_from_as(space):
    s = 'from  __future__ import division as b\n'
    f = run(space, s)
    assert f.flags == fut.CO_FUTURE_DIVISION
    assert f.lineno == 1
    assert f.col_offset == 0
    
def test_froms_as(space):
    s = 'from  __future__ import division as b, generators as c\n'
    f = run(space, s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED)
    assert f.lineno == 1
    assert f.col_offset == 0

def test_from_paren(space):
    s = 'from  __future__ import (division)\n'
    f = run(space, s)
    assert f.flags == fut.CO_FUTURE_DIVISION
    assert f.lineno == 1
    assert f.col_offset == 0

def test_froms_paren(space):
    s = 'from  __future__ import (division, generators)\n'
    f = run(space, s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED)
    assert f.lineno == 1
    assert f.col_offset == 0

def test_froms_paren_as(space):
    s = 'from  __future__ import (division as b, generators,)\n'
    f = run(space, s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED)
    assert f.lineno == 1
    assert f.col_offset == 0

def test_multiline(space):
    s = '"abc" #def\n  #ghi\nfrom  __future__ import (division as b, generators,)\nfrom __future__ import with_statement\n'
    f = run(space, s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED |
                       fut.CO_FUTURE_WITH_STATEMENT)
    assert f.lineno == 4
    assert f.col_offset == 0

def test_windows_style_lineendings(space):
    s = '"abc" #def\r\n  #ghi\r\nfrom  __future__ import (division as b, generators,)\r\nfrom __future__ import with_statement\r\n'
    f = run(space, s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED |
                       fut.CO_FUTURE_WITH_STATEMENT)
    assert f.lineno == 4
    assert f.col_offset == 0

def test_mac_style_lineendings(space):
    s = '"abc" #def\r  #ghi\rfrom  __future__ import (division as b, generators,)\rfrom __future__ import with_statement\r'
    f = run(space, s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED |
                       fut.CO_FUTURE_WITH_STATEMENT)
    assert f.lineno == 4
    assert f.col_offset == 0

def test_semicolon(space):
    s = '"abc" #def\n  #ghi\nfrom  __future__ import (division as b, generators,);  from __future__ import with_statement\n'
    f = run(space, s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED |
                       fut.CO_FUTURE_WITH_STATEMENT)
    assert f.lineno == 3
    assert f.col_offset == 55

def test_intervening_code(space):
    s = 'from  __future__ import (division as b, generators,)\nfrom sys import modules\nfrom __future__ import with_statement\n'
    f = run(space, s)
    assert f.flags & fut.CO_FUTURE_WITH_STATEMENT == 0
    assert f.lineno == 1
    assert f.col_offset == 0

def test_nonexisting(space):
    s = 'from  __future__ import non_existing_feature\n'
    f = run(space, s)
    assert f.flags == 0
    assert f.lineno == 1
    assert f.col_offset == 0

def test_from_import_abs_import(space):
    s = 'from  __future__ import absolute_import\n'
    f = run(space, s)
    assert f.flags == fut.CO_FUTURE_ABSOLUTE_IMPORT
    assert f.lineno == 1
    assert f.col_offset == 0

def test_raw_doc(space):
    s = 'r"Doc"\nfrom __future__ import with_statement\n'
    f = run(space, s)
    assert f.flags == fut.CO_FUTURE_WITH_STATEMENT
    assert f.lineno == 2
    assert f.col_offset == 0

def test_unicode_doc(space):
    s = 'u"Doc"\nfrom __future__ import with_statement\n'
    f = run(space, s)
    assert f.flags == fut.CO_FUTURE_WITH_STATEMENT
    assert f.lineno == 2
    assert f.col_offset == 0

def test_raw_unicode_doc(space):
    s = 'ur"Doc"\nfrom __future__ import with_statement\n'
    f = run(space, s)
    assert f.flags == fut.CO_FUTURE_WITH_STATEMENT

def test_continuation_line(space):
    s = "\\\nfrom __future__ import with_statement\n"
    f = run(space, s)
    assert f.flags == fut.CO_FUTURE_WITH_STATEMENT
    assert f.lineno == 2
    assert f.col_offset == 0

def test_continuation_lines(space):
    s = "\\\n  \t\\\nfrom __future__ import with_statement\n"
    f = run(space, s)
    assert f.flags == fut.CO_FUTURE_WITH_STATEMENT
    assert f.lineno == 3
    assert f.col_offset == 0

# This looks like a bug in cpython parser
# and would require extensive modifications
# to future.py in order to emulate the same behaviour
def test_continuation_lines_raise(space):
    py.test.skip("probably a CPython bug")
    s = "   \\\n  \t\\\nfrom __future__ import with_statement\n"
    try:
        f = run(space, s)
    except IndentationError, e:
        assert e.args == 'unexpected indent'
        assert f.flags == 0
        assert f.lineno == -1
        assert f.col_offset == 0
    else:
        raise AssertionError('IndentationError not raised')
    assert f.lineno == 2
    assert f.col_offset == 0
