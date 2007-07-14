"""Compatibility layer for CPython's parser module"""

from pypy.interpreter.pyparser.tuplebuilder import TupleBuilder
from pythonparse import make_pyparser
from pythonutil import pypy_parse
import symbol # XXX use PYTHON_PARSER.symbols ?
from compiler import transformer, compile as pycompile

_PARSER = None

def get_parser():
    if not _PARSER:
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=False)
        _PARSER = make_pyparser(config.objspace.pyversion)
    return _PARSER

def suite( source ):
    strings = [line+'\n' for line in source.split('\n')]
    parser = get_parser()
    builder = TupleBuilder(parser)
    parser.parse_source(source, 'exec', builder)
    nested_tuples = builder.stack[-1].as_tuple()
    if builder.source_encoding is not None:
        return (symbol.encoding_decl, nested_tuples, builder.source_encoding)
    else:
        return (None, nested_tuples, None)
    return nested_tuples

def expr( source ):
    strings = [line+'\n' for line in source.split('\n')]
    parser = get_parser()
    builder = TupleBuilder(parser)
    parser.parse_source(source, 'eval', builder)
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
