from pypy.interpreter import baseobjspace
from pypy.interpreter.function import Function

from pypy.interpreter.error import OperationError

from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.stringobject import W_StringObject

from pypy.module.cclp.types import W_CVar

def check_variables(space, w_variables, min_nb):
    if not isinstance(w_variables, W_ListObject):
        raise OperationError(space.w_TypeError,
                             space.wrap("variables must be in a list or tuple."))
    assert isinstance(w_variables, W_ListObject)
    if len(w_variables.wrappeditems) < min_nb:
        raise OperationError(space.w_RuntimeError,
                             space.wrap("there must be at least %s variables." % min_nb))
    return w_variables

def cvars_to_names(cvars):
    variables = []
    for w_var in cvars:
        assert isinstance(w_var, W_CVar)
        variables.append(w_var.w_nam)
    return variables


from pypy.module._cslib.constraint import interp_make_expression, \
     make_alldistinct as mkalldiff

def _make_expression(space, w_variables, w_formula, w_filter_func):
    """create a new constraint of type Expression or BinaryExpression
    The chosen class depends on the number of variables in the constraint"""
    w_variables = check_variables(space, w_variables, 1)
    assert isinstance(w_filter_func, Function)
    if not isinstance(w_formula, W_StringObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap("formula must be a string."))
    variables = cvars_to_names(w_variables.wrappeditems)
    return interp_make_expression(space, space.newlist(variables),
                                  w_formula, w_filter_func)
    
_make_expression.unwrap_spec = [baseobjspace.ObjSpace,
                                baseobjspace.W_Root,
                                baseobjspace.W_Root,
                                baseobjspace.W_Root]

def make_alldistinct(space, w_variables):
    w_variables = check_variables(space, w_variables, 2)
    variables = cvars_to_names(w_variables.wrappeditems)
    return mkalldiff(space, space.newlist(variables))

make_alldistinct.unwrap_spec = [baseobjspace.ObjSpace,
                                baseobjspace.W_Root]
