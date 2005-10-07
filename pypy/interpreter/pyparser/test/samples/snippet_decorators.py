# Function(Decorators([Name('foo')]), 'f', ['a', 'b'], [], 0, None, Stmt([Pass()]))
@foo
def f(a, b):
    pass

@accepts(int, (int,float))
@returns((int,float))
def func0(arg1, arg2):
    return arg1 * arg2


## Stmt([Function(Decorators([CallFunc(Getattr(Getattr(Name('mod1'), 'mod2'), 'accepts'), [Name('int'), Tuple([Name('int'), Name('float')])], None, None),
##                            CallFunc(Getattr(Getattr(Name('mod1'), 'mod2'), 'returns'), [Tuple([Name('int'), Name('float')])], None, None)]),
##                'func', ['arg1', 'arg2'], [], 0, None, Stmt([Return(Mul((Name('arg1'), Name('arg2'))))]))])
@mod1.mod2.accepts(int, (int,float))
@mod1.mod2.returns((int,float))
def func(arg1, arg2):
    return arg1 * arg2
