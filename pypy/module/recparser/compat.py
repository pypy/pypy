"""Compatibility layer for CPython's parser module"""

from pythonparse import parse_python_source
from pypy.module.recparser import PYTHON_PARSER
from compiler import transformer, compile as pycompile
 
def suite( source ):
    builder = parse_python_source( source, PYTHON_PARSER, "file_input" )
    return builder.stack[-1]

def expr( source ):
    builder = parse_python_source( source, PYTHON_PARSER, "eval_input" )
    return builder.stack[-1]

def ast2tuple(node, line_info=False):
    """Quick dummy implementation of parser.ast2tuple(tree) function"""
    tuples = node.totuple(line_info)
    return tuples
