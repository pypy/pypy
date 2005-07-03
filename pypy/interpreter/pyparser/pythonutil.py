__all__ = ["python_parse", "pypy_parse", "ast_single_input", "ast_file_input",
           "ast_eval_input" ]

from compiler.transformer import Transformer
import parser
import symbol

import pythonparse
from tuplebuilder import TupleBuilder

PYTHON_PARSER = pythonparse.PYTHON_PARSER
TARGET_DICT = {
    'exec'   : "file_input",
    'eval'   : "eval_input",
    'single' : "single_input",
    }

## convenience functions around CPython's parser functions
def python_parsefile(filename, lineno=False):
    """parse <filename> using CPython's parser module and return nested tuples
    """
    pyf = file(filename)
    source = pyf.read()
    pyf.close()
    return python_parse(source, 'exec', lineno)

def python_parse(source, mode='exec', lineno=False):
    """parse python source using CPython's parser module and return
    nested tuples
    """
    if mode == 'exec':
        tp = parser.suite(source)
    else:
        tp = parser.expr(source)
    return tp.totuple()

## convenience functions around recparser functions
def pypy_parsefile(filename, lineno=False):
    """parse <filename> using PyPy's parser module and return
    a tuple of three elements :
     - The encoding declaration symbol or None if there were no encoding
       statement
     - The TupleBuilder's stack top element (instance of
       tuplebuilder.StackElement which is a wrapper of some nested tuples
       like those returned by the CPython's parser)
     - The encoding string or None if there were no encoding statement
    nested tuples
    """
    pyf = file(filename)
    source = pyf.read()
    pyf.close()
    return pypy_parse(source, 'exec', lineno)

def pypy_parse(source, mode='exec', lineno=False):
    """parse <source> using PyPy's parser module and return
    a tuple of three elements :
     - The encoding declaration symbol or None if there were no encoding
       statement
     - The TupleBuilder's stack top element (instance of
       tuplebuilder.StackElement which is a wrapper of some nested tuples
       like those returned by the CPython's parser)
     - The encoding string or None if there were no encoding statement
    nested tuples
    """
    builder = TupleBuilder(PYTHON_PARSER.rules, lineno=False)
    # make the annotator life easier (don't use str.splitlines())
    strings = [line + '\n' for line in source.split('\n')]
    # finalize the last line 
    if not source.endswith('\n'):
        last_line = strings[-1]
        strings[-1] = last_line[:-1]
    else:
        strings.pop()
    target_rule = TARGET_DICT[mode]
    pythonparse.parse_python_source(strings, PYTHON_PARSER,
                                    target_rule, builder)
##     if builder.error_occured():
##         line, lineno, offset, filename = builder.get_error()
##         raise SyntaxError(line, lineno, offset, filename)
##     # stack_element is a tuplerbuilder.StackElement's instance
    stack_element = builder.stack[-1]
    # convert the stack element into nested tuples
    # XXX : the annotator can't follow this call
    nested_tuples = stack_element.as_tuple(lineno)
    if builder.source_encoding is not None:
        return (symbol.encoding_decl, nested_tuples, builder.source_encoding)
    else:
        return nested_tuples

## convenience functions for computing AST objects using recparser
def ast_from_input(input, mode):
    tuples = pypy_parse(input, mode, True)
    transformer = Transformer()
    ast = transformer.compile_node(tuples)
    return ast

## TARGET FOR ANNOTATORS #############################################
def annotateme(strings):
    """This function has no other role than testing the parser's annotation

    annotateme() is basically the same code that pypy_parse(), but with the
    following differences :
     - directly take a list of strings rather than a filename in input
       in order to avoid using file() (which is faked for now)
       
     - returns a tuplebuilder.StackElement instead of the *real* nested
       tuples (StackElement is only a wrapper class around these tuples)

    """
    builder = TupleBuilder(PYTHON_PARSER.rules, lineno=False)
    pythonparse.parse_python_source(strings, PYTHON_PARSER, 'file_input', builder)
    nested_tuples = builder.stack[-1]
    if builder.source_encoding is not None:
        return (symbol.encoding_decl, nested_tuples, builder.source_encoding)
    else:
        return (None, nested_tuples, None)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print "python parse.py [-d N] test_file.py"
        sys.exit(1)
    if sys.argv[1] == "-d":
        debug_level = int(sys.argv[2])
        test_file = sys.argv[3]
    else:
        test_file = sys.argv[1]
    print "-"*20
    print
    print "pyparse \n", pypy_parsefile(test_file)
    print "parser  \n", python_parsefile(test_file)
