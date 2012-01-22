import py
import pypy.interpreter.pyparser.future as future
from pypy.tool import stdlib___future__ as fut

def run(s):
    f = future.FutureAutomaton(future.futureFlags_2_7, s)
    try:
        f.start()
    except future.DoneException:
        pass
    return f

def test_docstring():
    s = '"Docstring\\" "\nfrom  __future__ import division\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_DIVISION
    assert f.lineno == 2
    assert f.col_offset == 0

def test_comment():
    s = '# A comment about nothing ;\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.lineno == -1
    assert f.col_offset == 0

def test_tripledocstring():
    s = '''""" This is a
docstring with line
breaks in it. It even has a \n"""
'''
    f = run(s)
    assert f.pos == len(s)
    assert f.lineno == -1
    assert f.col_offset == 0

def test_escapedquote_in_tripledocstring():
    s = '''""" This is a
docstring with line
breaks in it. \\"""It even has an escaped quote!"""
'''
    f = run(s)
    assert f.pos == len(s)
    assert f.lineno == -1
    assert f.col_offset == 0

def test_empty_line():
    s = ' \t   \f \n   \n'
    f = run(s)
    assert f.pos == len(s)
    assert f.lineno == -1
    assert f.col_offset == 0

def test_from():
    s = 'from  __future__ import division\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_DIVISION
    assert f.lineno == 1
    assert f.col_offset == 0

def test_froms():
    s = 'from  __future__ import division, generators, with_statement\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED |
                       fut.CO_FUTURE_WITH_STATEMENT)
    assert f.lineno == 1
    assert f.col_offset == 0

def test_from_as():
    s = 'from  __future__ import division as b\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_DIVISION
    assert f.lineno == 1
    assert f.col_offset == 0
    
def test_froms_as():
    s = 'from  __future__ import division as b, generators as c\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED)
    assert f.lineno == 1
    assert f.col_offset == 0

def test_from_paren():
    s = 'from  __future__ import (division)\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_DIVISION
    assert f.lineno == 1
    assert f.col_offset == 0

def test_froms_paren():
    s = 'from  __future__ import (division, generators)\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED)
    assert f.lineno == 1
    assert f.col_offset == 0

def test_froms_paren_as():
    s = 'from  __future__ import (division as b, generators,)\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED)
    assert f.lineno == 1
    assert f.col_offset == 0

def test_paren_with_newline():
    s = 'from __future__ import (division,\nabsolute_import)\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (fut.CO_FUTURE_DIVISION | fut.CO_FUTURE_ABSOLUTE_IMPORT)
    assert f.lineno == 1
    assert f.col_offset == 0

def test_multiline():
    s = '"abc" #def\n  #ghi\nfrom  __future__ import (division as b, generators,)\nfrom __future__ import with_statement\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED |
                       fut.CO_FUTURE_WITH_STATEMENT)
    assert f.lineno == 4
    assert f.col_offset == 0

def test_windows_style_lineendings():
    s = '"abc" #def\r\n  #ghi\r\nfrom  __future__ import (division as b, generators,)\r\nfrom __future__ import with_statement\r\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED |
                       fut.CO_FUTURE_WITH_STATEMENT)
    assert f.lineno == 4
    assert f.col_offset == 0

def test_mac_style_lineendings():
    s = '"abc" #def\r  #ghi\rfrom  __future__ import (division as b, generators,)\rfrom __future__ import with_statement\r'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED |
                       fut.CO_FUTURE_WITH_STATEMENT)
    assert f.lineno == 4
    assert f.col_offset == 0

def test_semicolon():
    s = '"abc" #def\n  #ghi\nfrom  __future__ import (division as b, generators,);  from __future__ import with_statement\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (fut.CO_FUTURE_DIVISION |
                       fut.CO_GENERATOR_ALLOWED |
                       fut.CO_FUTURE_WITH_STATEMENT)
    assert f.lineno == 3
    assert f.col_offset == 55

def test_full_chain():
    s = '"abc" #def\n  #ghi\nfrom  __future__ import (division as b, generators,);  from __future__ import with_statement\n'
    flags, pos = future.get_futures(future.futureFlags_2_5, s)
    assert flags == (fut.CO_FUTURE_DIVISION |
                     fut.CO_GENERATOR_ALLOWED |
                     fut.CO_FUTURE_WITH_STATEMENT)
    assert pos == (3, 55)

def test_intervening_code():
    s = 'from  __future__ import (division as b, generators,)\nfrom sys import modules\nfrom __future__ import with_statement\n'
    flags, pos = future.get_futures(future.futureFlags_2_5, s)
    assert flags & fut.CO_FUTURE_WITH_STATEMENT == 0
    assert pos == (1, 0)

def test_nonexisting():
    s = 'from  __future__ import non_existing_feature\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == 0
    assert f.lineno == 1
    assert f.col_offset == 0

def test_from_import_abs_import():
    s = 'from  __future__ import absolute_import\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_ABSOLUTE_IMPORT
    assert f.lineno == 1
    assert f.col_offset == 0

def test_raw_doc():
    s = 'r"Doc"\nfrom __future__ import with_statement\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_WITH_STATEMENT
    assert f.lineno == 2
    assert f.col_offset == 0

def test_unicode_doc():
    s = 'u"Doc"\nfrom __future__ import with_statement\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_WITH_STATEMENT
    assert f.lineno == 2
    assert f.col_offset == 0

def test_raw_unicode_doc():
    s = 'ru"Doc"\nfrom __future__ import with_statement\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_WITH_STATEMENT

def test_continuation_line():
    s = "\\\nfrom __future__ import with_statement\n"
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_WITH_STATEMENT
    assert f.lineno == 2
    assert f.col_offset == 0

def test_continuation_lines():
    s = "\\\n  \t\\\nfrom __future__ import with_statement\n"
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_WITH_STATEMENT
    assert f.lineno == 3
    assert f.col_offset == 0

def test_lots_of_continuation_lines():
    s = "\\\n\\\n\\\n\\\n\\\n\\\n\nfrom __future__ import with_statement\n"
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_WITH_STATEMENT
    assert f.lineno == 8
    assert f.col_offset == 0

# This looks like a bug in cpython parser
# and would require extensive modifications
# to future.py in order to emulate the same behaviour
def test_continuation_lines_raise():
    py.test.skip("probably a CPython bug")
    s = "   \\\n  \t\\\nfrom __future__ import with_statement\n"
    try:
        f = run(s)
    except IndentationError, e:
        assert e.args == 'unexpected indent'
        assert f.pos == len(s)
        assert f.flags == 0
        assert f.lineno == -1
        assert f.col_offset == 0
    else:
        raise AssertionError('IndentationError not raised')
    assert f.lineno == 2
    assert f.col_offset == 0

def test_continuation_lines_in_docstring_single_quoted():
    s = '"\\\n\\\n\\\n\\\n\\\n\\\n"\nfrom  __future__ import division\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_DIVISION
    assert f.lineno == 8
    assert f.col_offset == 0

def test_continuation_lines_in_docstring_triple_quoted():
    s = '"""\\\n\\\n\\\n\\\n\\\n\\\n"""\nfrom  __future__ import division\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == fut.CO_FUTURE_DIVISION
    assert f.lineno == 8
    assert f.col_offset == 0
