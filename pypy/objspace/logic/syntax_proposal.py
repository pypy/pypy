def foo_explicit(x,y):
    """straightforward version. Just a new builtin to add The name of
    the builtin can be discussed (current implementation uses
    'newvar')
    """
    X = logicvar()
    Y = logicvar()
    unify(X, x)
    unify(Y, y)
    return X+Y


def foo_let(x, y):
    """requires adding a new node in the AST
    the scoping rules need to be clarified
    """
    let X, Y:
        unify(X, x)
        unify(Y, y)
        xx = X
        return X+Y
    print X #-> raises name error
    print xx # no NameError (?)

def foo_logic_kw(x,y):
    """needs a new keyword
    the logic keyword does not introduce a new scope (compare with let above)"""
    logic X,Y 
    unify(X, x)
    unify(Y, y)
    return X+Y

def foo_with(x,y):
    """requires python 2.5
    we need logic to be a built in context manager
    scoping rules are those of with"""
    with logic(X, Y):
        unify(X, x)
        unify(Y, y)
        return X+Y
    print X #-> raises name error ???    
    
@logic('X','Y')
def foo_decorator(x,y):
    """can this work at all ? The decorator would add local variables
    to the function with the provided names, initialized as logic
    variable"""
    unify(X, x)
    unify(Y, y)
    return X+Y


def foo_question_mark(x,y):
    """introduce a new symbol '?'
    """
    X, Y = ?, ?
    unify(X, x)
    unify(Y, y)
    return X+Y

def foo_singleton(x,y):
    """similar to foo_question_mark, but Unknown can clash with
    existing code, and is longer to type"""
    X, Y = Unknown, Unknown
    unify(X, x)
    unify(Y, y)
    return X+Y

def foo_equal_question_mark(x,y):
    """introduces a new token '=?' without a right hand part
    """
    X, Y =?
    unify(X, x)
    unify(Y, y)
    return X+Y


def foo_visual_basic(x,y):
    """for completeness, april fool was just a few days ago, please
    bear with us"""
    Dim X, Y as LogicalVariables
    unify(X, x)
    unify(Y, y)
    return X+Y

def foo_strange_question_mark(x,y): # ?????
    """semantics are not totally clear yet, and auc feels this is not
    going to match real life use cases. """
    x = ?W
    ?Z
    unify(?X, x)
    unify(?Y, y)
    return ?X + ?Y
