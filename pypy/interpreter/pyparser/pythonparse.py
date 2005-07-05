#!/usr/bin/env python
"""This module loads the python Grammar (2.3 or 2.4) and builds
the parser for this grammar in the global PYTHON_PARSER

helper functions are provided that use the grammar to parse
using file_input, single_input and eval_input targets
"""
from pypy.interpreter.error import OperationError, debug_print
from pypy.interpreter.pyparser.error import ParseError
from pypy.tool.option import Options

from pythonlexer import Source
import ebnfparse
import sys
import os
import grammar
import symbol

class PythonParser(object):
    """Wrapper class for python grammar"""
    def __init__(self, grammar_builder):
        self.items = grammar_builder.items
        self.rules = grammar_builder.rules
        # Build first sets for each rule (including anonymous ones)
        grammar.build_first_sets(self.items)

    def parse_source(self, textsrc, goal, builder=None):
        """Parse a python source according to goal"""
        lines = [line + '\n' for line in textsrc.split('\n')]
        if textsrc == '\n':
            lines.pop()
        else:
            last_line = lines[-1]
            lines[-1] = last_line[:-1]
        return self.parse_lines(lines, goal, builder)

    def parse_lines(self, lines, goal, builder=None):
        target = self.rules[goal]
        src = Source(lines)
        
        if builder is None:
            builder = grammar.BaseGrammarBuilder(debug=False, rules=self.rules)
        result = target.match(src, builder)
        # <HACK> XXX find a clean way to process encoding declarations
        builder.source_encoding = src.encoding
        # </HACK>
        if not result:
            line, lineno = src.debug()
            # XXX needs better error messages
            raise ParseError("error", lineno, -1, line)
            # return None
        return builder

PYTHON_VERSION = ".".join([str(i) for i in sys.version_info[:2]])
def get_grammar_file( version ):
    """returns the python grammar corresponding to our CPython version"""
    if version == "native":
        _ver = PYTHON_VERSION
    elif version in ("2.3","2.4"):
        _ver = version
    return os.path.join( os.path.dirname(__file__), "data", "Grammar" + _ver ), _ver

# unfortunately the command line options are not parsed yet
PYTHON_GRAMMAR, PYPY_VERSION = get_grammar_file( Options.version )

def python_grammar(fname):
    """returns a PythonParser build from the specified grammar file"""
    level = grammar.DEBUG
    grammar.DEBUG = 0
    gram = ebnfparse.parse_grammar( file(fname) )
    grammar.DEBUG = level
    return PythonParser(gram)

debug_print( "Loading grammar %s" % PYTHON_GRAMMAR )
PYTHON_PARSER = python_grammar( PYTHON_GRAMMAR )
_symbols = symbol.sym_name.keys()
_symbols.sort()

def add_symbol( sym ):
    if not hasattr(symbol, sym):
        nextval = _symbols[-1] + 1
        setattr(symbol, sym, nextval)
        _symbols.append(nextval)
        symbol.sym_name[nextval] = sym
        return nextval
    return 0

def reload_grammar( version ):
    """helper function to test with pypy different grammars"""
    global PYTHON_GRAMMAR, PYTHON_PARSER, PYPY_VERSION
    PYTHON_GRAMMAR, PYPY_VERSION = get_grammar_file( version )
    debug_print( "Reloading grammar %s" % PYTHON_GRAMMAR )
    PYTHON_PARSER = python_grammar( PYTHON_GRAMMAR )
    for rule in PYTHON_PARSER.rules:
        add_symbol( rule )
    

for rule in PYTHON_PARSER.rules:
    add_symbol( rule )


SYMBOLS = {}
# copies the numerical mapping between symbol name and symbol value
# into SYMBOLS
for k, v in symbol.sym_name.items():
    SYMBOLS[v] = k
SYMBOLS['UNKNOWN'] = -1



def parse_file_input(pyf, gram, builder=None):
    """Parse a python file"""
    return gram.parse_source( pyf.read(), "file_input", builder )
    
def parse_single_input(textsrc, gram, builder=None):
    """Parse a python single statement"""
    return gram.parse_source( textsrc, "single_input", builder )

def parse_eval_input(textsrc, gram, builder=None):
    """Parse a python expression"""
    return gram.parse_source( textsrc, "eval_input", builder )
