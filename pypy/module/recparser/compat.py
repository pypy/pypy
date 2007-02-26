"""Compatibility layer for CPython's parser module"""

from pythonparse import parse_python_source
from pythonutil import PYTHON_PARSER
from compiler import transformer, compile as pycompile

def suite( source ):
    strings = [line+'\n' for line in source.split('\n')]
    builder = parse_python_source( strings, PYTHON_PARSER, "file_input" )
    nested_tuples = builder.stack[-1].as_tuple()
    if builder.source_encoding is not None:
        return (symbol.encoding_decl, nested_tuples, builder.source_encoding)
    else:
        return (None, nested_tuples, None)
    return nested_tuples

def expr( source ):
    strings = [line+'\n' for line in source.split('\n')]
    builder = parse_python_source( strings, PYTHON_PARSER, "eval_input" )
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
