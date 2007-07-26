from pypy.lang.js.jsparser import parse
from pypy.lang.js.astbuilder import ASTBuilder
from pypy.lang.js import operations
from pypy.lang.js.operations import Call

def to_ast(s):
    print s
    tp = parse(s)
    print tp
    astb = ASTBuilder()
    astb.sourcename = "test"
    return astb.dispatch(tp)

def test_simple():
    yield to_ast, "1;"
    yield to_ast, "var x=1;"
    yield to_ast, "print(1);"
    yield to_ast, "x.y;"
    yield to_ast, "x[1];"
    yield to_ast, "true;"
    yield to_ast, "false;"
    yield to_ast, "null;"
    yield to_ast, "f();"
    yield to_ast, "new f();"    
    yield to_ast, "01;"
    yield to_ast, "0xFF;"

def test_funcvarfinder():
    pos = operations.Position()
    
def test_callcall():
    p = to_ast('x()()')
    c1 = p.body.nodes[0]
    assert isinstance(c1, Call)
    assert isinstance(c1.left, Call)

def test_sourcename():    
    p = to_ast('x()()').body
    assert p.sourcename == 'test'
