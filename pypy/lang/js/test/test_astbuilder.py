from pypy.lang.js.jsparser import parse
from pypy.lang.js.astbuilder import ASTBuilder
from pypy.lang.js import operations

def to_ast(s):
    ASTBuilder().dispatch(parse(s))

def test_simple():
    yield to_ast, "1;"
    yield to_ast, "var x=1;"
    yield to_ast, "print(1);"
    yield to_ast, "x.y;"
    yield to_ast, "x[1];"
    yield to_ast, "true;"
    yield to_ast, "false;"
    yield to_ast, "null;"    
    #yield to_ast, ""

def test_funcvarfinder():
    pos = operations.Position()
    
