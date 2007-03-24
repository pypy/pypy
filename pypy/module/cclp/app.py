# NOT_RPYTHON

from cclp import _make_expression

def make_expression(variables, formula):
    func = 'lambda %s:%s' % (','.join([name_of(var)
                                       for var in variables]),
                             formula)
    return _make_expression(variables, formula, eval(func))
