
from pypy.interpreter.pyparser.pythonparse import PYTHON_PARSER
from pypy.interpreter.pyparser.astbuilder import AstBuilder
from pypy.interpreter.pyparser.pythonutil import ast_from_input
from pypy.interpreter.stablecompiler.transformer import Transformer
import py.test

expr1 = "x = a + 1"



def ast_parse_expr( expr ):
    builder = AstBuilder()
    PYTHON_PARSER.parse_source( expr, "single_input", builder )
    return builder

def tuple_parse_expr( expr ):
    t = Transformer()
    return ast_from_input( expr, "single", t )

def test_expr1():
    py.test.skip("work in progress")
    r1 = ast_parse_expr( expr1 )
    ast = tuple_parse_expr( expr1 )
    print ast
    
