__all__ = ["python_grammar", "PYTHON_GRAMMAR" ]

import os
import sys

_ver = ".".join([str(i) for i in sys.version_info[:2]])
PYTHON_GRAMMAR = os.path.join( os.path.dirname(__file__), "data", "Grammar" + _ver )

def python_grammar():
    """returns a """
    from ebnfparse import parse_grammar
    level = get_debug()
    set_debug( 0 )
    gram = parse_grammar( file(PYTHON_GRAMMAR) )
    set_debug( level )
    return gram

def get_debug():
    """Return debug level"""
    import grammar
    return grammar.DEBUG

def set_debug( level ):
    """sets debug mode to <level>"""
    import grammar
    grammar.DEBUG = level


def python_parse(filename):
    """parse <filename> using CPython's parser module and return nested tuples
    """
    pyf = file(filename)
    import parser
    tp2 = parser.suite(pyf.read())
    return tp2.totuple()
