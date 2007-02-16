from _cslib import FiniteDomain, _make_expression, AllDistinct


def make_expression(variables, formula):
    func = 'lambda %s:%s' % (','.join(variables),
                             formula)
    return _make_expression(variables, formula, eval(func))
