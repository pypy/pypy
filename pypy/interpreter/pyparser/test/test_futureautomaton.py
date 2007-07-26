import py
import pypy.interpreter.pyparser.future as future
from pypy.interpreter.astcompiler.consts import CO_GENERATOR_ALLOWED, \
    CO_FUTURE_DIVISION, CO_FUTURE_WITH_STATEMENT

def run(s):
    f = future.FutureAutomaton(s)
    try:
        f.start()
    except IndexError, future.DoneException:
        pass
    return f

def test_docstring():
    s = '"Docstring"\n'
    f = run(s)
    assert f.pos == len(s)

def test_comment():
    s = '# A comment about nothing ;\n'
    f = run(s)
    assert f.pos == len(s)

def test_tripledocstring():
    s = '''""" This is a
docstring with line
breaks in it. It even has a \n"""
'''
    f = run(s)
    assert f.pos == len(s)

def test_escapedquote_in_tripledocstring():
    s = '''""" This is a
docstring with line
breaks in it. \\"""It even has an escaped quote!"""
'''
    f = run(s)
    assert f.pos == len(s)



def test_empty_line():
    s = ' \t   \f \n   \n'
    f = run(s)
    assert f.pos == len(s)

def test_from():
    s = 'from  __future__ import division\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == CO_FUTURE_DIVISION

def test_froms():
    s = 'from  __future__ import division, generators, with_statement\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (CO_FUTURE_DIVISION |
                       CO_GENERATOR_ALLOWED |
                       CO_FUTURE_WITH_STATEMENT)

def test_from_as():
    s = 'from  __future__ import division as b\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == CO_FUTURE_DIVISION
    
def test_froms_as():
    s = 'from  __future__ import division as b, generators as c\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (CO_FUTURE_DIVISION |
                       CO_GENERATOR_ALLOWED)

def test_from_paren():
    s = 'from  __future__ import (division)\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == CO_FUTURE_DIVISION

def test_froms_paren():
    s = 'from  __future__ import (division, generators)\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (CO_FUTURE_DIVISION |
                       CO_GENERATOR_ALLOWED)

def test_froms_paren_as():
    s = 'from  __future__ import (division as b, generators,)\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (CO_FUTURE_DIVISION |
                       CO_GENERATOR_ALLOWED)

def test_multiline():
    s = '"abc" #def\n  #ghi\nfrom  __future__ import (division as b, generators,)\nfrom __future__ import with_statement\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (CO_FUTURE_DIVISION |
                       CO_GENERATOR_ALLOWED |
                       CO_FUTURE_WITH_STATEMENT)

def test_windows_style_lineendings():
    s = '"abc" #def\r\n  #ghi\r\nfrom  __future__ import (division as b, generators,)\r\nfrom __future__ import with_statement\r\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (CO_FUTURE_DIVISION |
                       CO_GENERATOR_ALLOWED |
                       CO_FUTURE_WITH_STATEMENT)

def test_mac_style_lineendings():
    s = '"abc" #def\r  #ghi\rfrom  __future__ import (division as b, generators,)\rfrom __future__ import with_statement\r'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (CO_FUTURE_DIVISION |
                       CO_GENERATOR_ALLOWED |
                       CO_FUTURE_WITH_STATEMENT)
def test_semicolon():
    s = '"abc" #def\n  #ghi\nfrom  __future__ import (division as b, generators,);  from __future__ import with_statement\n'
    f = run(s)
    assert f.pos == len(s)
    assert f.flags == (CO_FUTURE_DIVISION |
                       CO_GENERATOR_ALLOWED |
                       CO_FUTURE_WITH_STATEMENT)

def test_full_chain():
    s = '"abc" #def\n  #ghi\nfrom  __future__ import (division as b, generators,);  from __future__ import with_statement\n'
    flags = future.getFutures(s)
    assert flags == (CO_FUTURE_DIVISION |
                     CO_GENERATOR_ALLOWED |
                     CO_FUTURE_WITH_STATEMENT)

def test_intervening_code():
    s = 'from  __future__ import (division as b, generators,)\nfrom sys import modules\nfrom __future__ import with_statement\n'
    flags = future.getFutures(s)
    assert flags & CO_FUTURE_WITH_STATEMENT == 0
