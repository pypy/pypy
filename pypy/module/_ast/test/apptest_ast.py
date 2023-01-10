import ast

def test_match_args():
    assert ast.If.__match_args__ == ('test', 'body', 'orelse')

def test_match_args_Load():
    assert ast.Load.__match_args__ == ()

def test_patma_ast():
    def f(x):
        match x:
            case ast.Constant(a, b): return a, b
    assert f(ast.Constant(5)) == (5, None)

