__all__ = ["python_parse", "pypy_parse"]

import parser

import pythonparse
from tuplebuilder import TupleBuilder
from astbuilder import AstBuilder

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
    if mode == 'eval':
        tp = parser.expr(source)
    else:
        tp = parser.suite(source)
    return parser.ast2tuple(tp, line_info=lineno)

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

def internal_pypy_parse(source, mode='exec', lineno=False, flags=0, space=None,
                        parser = PYTHON_PARSER):
    """This function has no other role than testing the parser's annotation

    annotateme() is basically the same code that pypy_parse(), but with the
    following differences :

     - returns a tuplebuilder.StackElement instead of the *real* nested
       tuples (StackElement is only a wrapper class around these tuples)

    """
    builder = TupleBuilder(parser.rules, lineno=False)
    if space is not None:
        builder.space = space
    target_rule = TARGET_DICT[mode]
    parser.parse_source(source, target_rule, builder, flags)
    stack_element = builder.stack[-1]
    return (builder.source_encoding, stack_element)

def parse_result_to_nested_tuples(parse_result, lineno=False):
    """NOT_RPYTHON"""
    source_encoding, stack_element = parse_result
    nested_tuples = stack_element.as_tuple(lineno)
    return nested_tuples

def pypy_parse(source, mode='exec', lineno=False, flags=0, parser = PYTHON_PARSER):
    """
    NOT_RPYTHON !
    parse <source> using PyPy's parser module and return
    a tuple of three elements :
     - The encoding declaration symbol or None if there were no encoding
       statement
     - The TupleBuilder's stack top element (instance of
       tuplebuilder.StackElement which is a wrapper of some nested tuples
       like those returned by the CPython's parser)
     - The encoding string or None if there were no encoding statement
    nested tuples
    """
    source_encoding, stack_element = internal_pypy_parse(source, mode, lineno=lineno,
                                                         flags=lineno, parser = parser)
    # convert the stack element into nested tuples (caution, the annotator
    # can't follow this call)
    return parse_result_to_nested_tuples((source_encoding, stack_element), lineno=lineno)

## convenience functions for computing AST objects using recparser
def ast_from_input(input, mode, transformer, parser = PYTHON_PARSER):
    """converts a source input into an AST

     - input : the source to be converted
     - mode : 'exec', 'eval' or 'single'
     - transformer : the transfomer instance to use to convert
                     the nested tuples into the AST
     XXX: transformer could be instantiated here but we don't want
          here to explicitly import compiler or stablecompiler or
          etc. This is to be fixed in a clean way
    """
    tuples = pypy_parse(input, mode, True, parser)
    ast = transformer.compile_node(tuples)
    return ast

def target_ast_compile(space, input, mode):
    from pypy.interpreter.astcompiler import ast, misc, pycodegen
    builder = AstBuilder(rules=None, debug=0, space=space)
    target = TARGET_DICT[mode]
    PYTHON_PARSER.parse_source(input, target, builder)
    ast_tree = builder.rule_stack[-1]
    misc.set_filename("<?>", ast_tree)
    if mode=="single":
        codegenerator = pycodegen.InteractiveCodeGenerator(space,ast_tree)
    elif mode=="eval":
        codegenerator = pycodegen.ExpressionCodeGenerator(space,ast_tree)
    elif mode=="exec":
        codegenerator = pycodegen.ModuleCodeGenerator(space,ast_tree)
    else:
        raise ValueError("incorrect mode")
    code1 = codegenerator.getCode()
    return code1


def internal_pypy_parse_to_ast(source, mode='exec', lineno=False, flags=0):
    builder = AstBuilder()
    target_rule = TARGET_DICT[mode]
    PYTHON_PARSER.parse_source(source, target_rule, builder, flags)
    ast_tree = builder.rule_stack[-1]
    return (builder.source_encoding, ast_tree)


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
