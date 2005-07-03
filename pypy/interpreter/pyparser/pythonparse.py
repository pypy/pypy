#!/usr/bin/env python
"""This module loads the python Grammar (2.3 or 2.4) and builds
the parser for this grammar in the global PYTHON_PARSER

helper functions are provided that use the grammar to parse
using file_input, single_input and eval_input targets
"""
from pypy.interpreter.error import OperationError, debug_print

from pythonlexer import Source
import ebnfparse
import sys
import os
import grammar

# parse the python grammar corresponding to our CPython version
_ver = ".".join([str(i) for i in sys.version_info[:2]])
PYTHON_GRAMMAR = os.path.join( os.path.dirname(__file__), "data", "Grammar" + _ver )

def python_grammar():
    """returns a """
    level = grammar.DEBUG
    grammar.DEBUG = 0
    gram = ebnfparse.parse_grammar( file(PYTHON_GRAMMAR) )
    grammar.DEBUG = level
    # Build first sets for each rule (including anonymous ones)
    grammar.build_first_sets(gram.items)
    return gram

debug_print( "Loading grammar %s" % PYTHON_GRAMMAR )
PYTHON_PARSER = python_grammar()

class BuilderError(SyntaxError):
    def __init__(self, line, lineno):
        self.filename = 'XXX.py'
        self.line = self.text = line
        self.lineno = lineno
        self.offset = -1
        self.msg = "SyntaxError at line %d: %r" % (self.lineno, self.line)

def parse_python_source(textsrc, gram, goal, builder=None):
    """Parse a python source according to goal"""
    target = gram.rules[goal]
    src = Source(textsrc)
    if builder is None:
        builder = grammar.BaseGrammarBuilder(debug=False, rules=gram.rules)
    result = target.match(src, builder)
    # <HACK> XXX find a clean way to process encoding declarations
    builder.source_encoding = src.encoding
    # </HACK>
    if not result:
        # raising a SyntaxError here is not annotable, and it can
        # probably be handled in an other way
        line, lineno = src.debug()
        raise BuilderError(line, lineno)
        # return None
    return builder

def parse_file_input(pyf, gram, builder=None):
    """Parse a python file"""
    return parse_python_source( pyf.read(), gram, "file_input", builder )
    
def parse_single_input(textsrc, gram, builder=None):
    """Parse a python single statement"""
    return parse_python_source( textsrc, gram, "single_input", builder )

def parse_eval_input(textsrc, gram, builder=None):
    """Parse a python expression"""
    return parse_python_source( textsrc, gram, "eval_input", builder )
