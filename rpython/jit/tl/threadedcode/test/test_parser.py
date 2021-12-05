from rpython.jit.tl.threadedcode.parser import parse, _parse, \
    Program, BinOp, Variable, ConstInt, Assignment, Function, FunApp

def test_binop():
    assert parse('y + 1') == Program([BinOp("+", Variable("y"), ConstInt(1))])
    assert parse('y - 1') == Program([BinOp("-", Variable("y"), ConstInt(1))])
    assert parse('y < 1') == Program([BinOp("<", Variable("y"), ConstInt(1))])
    assert parse('y == 1') == Program([BinOp("==", Variable("y"), ConstInt(1))])

def test_parentheses():
    assert parse('(x)') == Program([Variable('x')])

def test_let():
    assert parse('let x = 1 in x + 1') == Program(
        [Assignment('x', ConstInt(1)),
         BinOp('+', Variable('x'), ConstInt(1))])

def test_letrec():
    assert parse('let rec f x y = 1;; f 1 2') == Program(
        [Function('f', ['x', 'y'], ConstInt(1)),
         FunApp(Variable('f'), [ConstInt(1), ConstInt(2)])])
