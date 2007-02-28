"""Compatibility layer for CPython's parser module"""

from pypy.interpreter.pyparser.tuplebuilder import TupleBuilder
from pythonparse import make_pyparser
from pythonutil import pypy_parse
import symbol # XXX use PYTHON_PARSER.symbols ?
from compiler import transformer, compile as pycompile

PYTHON_PARSER = make_pyparser()

def suite( source ):
    strings = [line+'\n' for line in source.split('\n')]
    builder = TupleBuilder(PYTHON_PARSER)
    PYTHON_PARSER.parse_source(source, 'exec', builder)
    nested_tuples = builder.stack[-1].as_tuple()
    if builder.source_encoding is not None:
        return (symbol.encoding_decl, nested_tuples, builder.source_encoding)
    else:
        return (None, nested_tuples, None)
    return nested_tuples

def expr( source ):
    strings = [line+'\n' for line in source.split('\n')]
    builder = TupleBuilder(PYTHON_PARSER)
    PYTHON_PARSER.parse_source(source, 'eval', builder)
    nested_tuples = builder.stack[-1].as_tuple()
    if builder.source_encoding is not None:
        return (symbol.encoding_decl, nested_tuples, builder.source_encoding)
    else:
        return (None, nested_tuples, None)
    return nested_tuples

def ast2tuple(node, line_info=False):
    """Quick dummy implementation of parser.ast2tuple(tree) function"""
    tuples = node.totuple(line_info)
    return tuples
