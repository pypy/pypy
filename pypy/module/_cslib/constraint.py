from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import baseobjspace, typedef, gateway
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.function import Function
from pypy.interpreter.error import OperationError

from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.dictobject import W_DictObject

from pypy.module._cslib.fd import _FiniteDomain
from pypy.rlib.cslib import rconstraint as rc

class W_AbstractConstraint(baseobjspace.Wrappable):
    
    def __init__(self, space, constraint):
        """variables is a list of variables which appear in the formula"""
        self.space = space
        assert isinstance( constraint, rc.AbstractConstraint )
        self.constraint = constraint

    def w_affected_variables(self):
        """ Return a list of all variables affected by this constraint """
        return self.space.wrap(self._variables)

    def affected_variables(self):
        return self._variables

    def w_revise(self, w_domains):
        assert isinstance(w_domains, W_DictObject)
        doms = {}
        spc = self.space
        for var, dom in w_domains.content.items():
            doms[spc.str_w(var)] = dom
        return self.space.newbool(self.revise(doms))

    def w_estimate_cost(self, w_domains):
        assert isinstance(w_domains, W_DictObject)
        cost = 1
        doms = w_domains.content
        for var in self._variables:
            dom = doms[self.space.wrap(var)]
            assert isinstance(dom, W_AbstractDomain)
            cost = cost * dom.size()
        return self.space.newint(cost)
                
W_AbstractConstraint.typedef = typedef.TypeDef(
    "W_AbstractConstraint")

class _Expression(rc.Expression):
    """A constraint represented as a python expression."""

    def __init__(self, space, w_variables, w_formula, w_filter_func):
        """variables is a list of variables which appear in the formula
        formula is a python expression that will be evaluated as a boolean"""
        self.space = space
        variables = []
        for w_var in space.unpackiterable( w_variables ):
            variables.append( space.str_w(w_var) )
        if len(variables)==0:
            raise OperationError( space.w_ValueError,
                                  space.wrap("need at least one variable") )
        rc.Expression.__init__(self, variables )
        self.formula = self.space.str_w(w_formula)
        # self.filter_func is a function taking keyword arguments and returning a boolean
        self.w_filter_func = w_filter_func

    def filter_func(self, kwargs):
        space = self.space
        w_kwargs = space.newdict()
        for var, value in kwargs.items():
            dom = self.doms[var]
            assert isinstance( dom, _FiniteDomain )
            w_val = dom.vlist[value]
            w_kwargs.content[space.wrap(var)] = w_val
        return space.is_true(space.call(self.w_filter_func,
                                        space.newlist([]),
                                        w_kwargs))


    def __repr__(self):
        return '<%s>' % self.formula

class _BinaryExpression(rc.BinaryExpression):
    """A constraint represented as a python expression."""

    def __init__(self, space, w_variables, w_formula, w_filter_func):
        """variables is a list of variables which appear in the formula
        formula is a python expression that will be evaluated as a boolean"""
        self.space = space
        variables = []
        for w_var in space.unpackiterable( w_variables ):
            variables.append( space.str_w(w_var) )
        if len(variables)==0:
            raise OperationError( space.w_ValueError,
                                  space.wrap("need at least one variable") )
        rc.BinaryExpression.__init__(self, variables )
        self.formula = self.space.str_w(w_formula)
        # self.filter_func is a function taking keyword arguments and returning a boolean
        self.w_filter_func = w_filter_func
        self.kwcache = {}

    def filter_func(self, kwargs):
        space = self.space
        var1 = self._variables[0]
        var2 = self._variables[1]
        arg1 = kwargs[var1]
        arg2 = kwargs[var2]
        t = (arg1,arg2)
        if t in self.kwcache:
            return self.kwcache[t]
        w_kwargs = space.newdict()
        
        dom = self.doms[var1]
        w_val = dom.vlist[arg1]
        w_kwargs.content[space.wrap(var1)] = w_val
        
        dom = self.doms[var2]
        w_val = dom.vlist[arg2]
        w_kwargs.content[space.wrap(var2)] = w_val
        
        res = space.is_true(space.call(self.w_filter_func,
                                       space.newlist([]),
                                       w_kwargs))
        self.kwcache[t] = res
        return res


class W_Expression(W_AbstractConstraint):

    def __init__(self, space, w_variables, w_formula, w_filter_func):
        if space.int_w(space.len(w_variables)) == 2:
            constraint = _BinaryExpression(space, w_variables, w_formula, w_filter_func)
        else:
            constraint = _Expression(space, w_variables, w_formula, w_filter_func)
        W_AbstractConstraint.__init__(self, space, constraint)


W_Expression.typedef = typedef.TypeDef("W_Expression",
    W_AbstractConstraint.typedef)
    

def interp_make_expression(space, w_variables, w_formula, w_callable):
    """create a new constraint of type Expression or BinaryExpression
    The chosen class depends on the number of variables in the constraint"""
    if not isinstance(w_formula, W_StringObject):
        raise OperationError(space.w_TypeError,
                             space.wrap('formula must be a string.'))
    return W_Expression(space, w_variables, w_formula, w_callable)


#--- Alldistinct

class _AllDistinct(rc.AllDistinct):
    """Contraint: all values must be distinct"""

    def __init__(self, space, w_variables):
        variables = []
        for w_var in space.unpackiterable( w_variables ):
            variables.append( space.str_w(w_var) )
        if len(variables)==0:
            raise OperationError( space.w_ValueError,
                                  space.wrap("need at least one variable") )
        rc.AllDistinct.__init__(self, variables)


class W_AllDistinct(W_AbstractConstraint):
    
    def __init__(self, space, w_variables):
        constraint = _AllDistinct(space, w_variables)
        W_AbstractConstraint.__init__(self, space, constraint)


W_AllDistinct.typedef = typedef.TypeDef(
    "W_AllDistinct", W_AbstractConstraint.typedef)

def make_alldistinct(space, w_variables):
    return space.wrap(W_AllDistinct(space, w_variables))

