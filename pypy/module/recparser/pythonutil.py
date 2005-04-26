__all__ = [ "parse_file_input", "parse_single_input", "parse_eval_input",
            "python_grammar", "PYTHON_GRAMMAR" ]

from pythonparse import parse_file_input, parse_single_input, parse_eval_input
import os
import sys

_ver = ".".join([str(i) for i in sys.version_info[:2]])
PYTHON_GRAMMAR = os.path.join( os.path.dirname(__file__), "Grammar" + _ver )

def python_grammar():
    """returns a """
    from ebnf import parse_grammar
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


def _get_encoding(builder):
    if hasattr(builder, '_source_encoding'):
        return builder._source_encoding
    return None

def pypy_parse(filename):
    """parse <filename> using PyPy's parser module and return nested tuples
    """
    pyf = file(filename)
    builder = parse_file_input(pyf, python_grammar())
    pyf.close()
    if builder.stack:
        # print builder.stack[-1]
        root_node = builder.stack[-1]
        nested_tuples = root_node.totuple()
        source_encoding = _get_encoding(builder)
        if source_encoding is None:
            return nested_tuples
        else:
            return (323, nested_tuples, source_encoding)
    return None # XXX raise an exception instead
