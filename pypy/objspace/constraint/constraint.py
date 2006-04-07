from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import baseobjspace, typedef, gateway
from pypy.interpreter.gateway import interp2app

from pypy.objspace.std.listobject import W_ListObject

from pypy.objspace.constraint.computationspace import W_ComputationSpace
from pypy.objspace.constraint.computationspace import W_Constraint


#from variable import NoDom
import operator

#-- Exceptions ---------------------------------------

class ConsistencyFailure(Exception):
    """The repository is not in a consistent state"""
    pass

class DomainlessVariables(Exception):
    """A constraint can't be defined on variables
       without a domain"""
    pass

#-- Constraints ------------------------------------------


class W_AbstractConstraint(W_Constraint):
    
    def __init__(self, object_space, w_variables):
        """variables is a list of variables which appear in the formula"""
        W_Constraint.__init__(self, object_space)
        assert isinstance(w_variables, W_ListObject)
        assert self._space.is_true(self._space.ge(self._space.len(w_variables), self._space.newint(1)))
        self._names_to_vars = {}
        for var in w_variables.wrappeditems:
            self._names_to_vars[var.name] = var
        self._variables = w_variables

    def w_affected_variables(self):
        """ Return a list of all variables affected by this constraint """
        return self._variables

    def w_is_variable_relevant(self, w_variable):
        return variable in self._variables

    def w_estimate_cost(self, w_cs):
        """Return an estimate of the cost of the narrowing of the constraint"""
        assert isinstance(w_cs, W_ComputationSpace)
        return reduce(operator.mul,
                      [w_cs.w_dom(var).size()
                       for var in self._variables])

    def __eq__(self, other): #FIXME and parent
        if not isinstance(other, self.__class__): return False
        return self._variables == other._variables
    
W_AbstractConstraint.typedef = typedef.TypeDef("W_AbstractConstraint",
    affected_variables = interp2app(W_AbstractConstraint.w_affected_variables),
    is_variable_relevant = interp2app(W_AbstractConstraint.w_is_variable_relevant),
    estimate_cost = interp2app(W_AbstractConstraint.w_estimate_cost),
    copy_to = interp2app(W_AbstractConstraint.w_copy_to),
    revise = interp2app(W_AbstractConstraint.w_revise)
) 



def make_lambda_head(space, w_vars):
    var_ids = ','.join([space.str_w(var.name) for var in w_vars.wrappeditems])
    return 'lambda ' + var_ids + ':'

def expand_expr_template(space, w_expr, w_vars):
    return space.str_w(w_expr)
    for w_var in w_vars.wrappeditems:
        expr.replace(w_var.name, w_var.name + '.val')
    return expr


class W_AllDistinct(W_AbstractConstraint):
    """Contraint: all values must be distinct"""

    def __init__(self, object_space, w_variables):
        W_AbstractConstraint.__init__(self, object_space, w_variables)
        assert len(w_variables.wrappeditems)>1
        # worst case complexity
        self.__cost = len(w_variables.wrappeditems) * (len(w_variables.wrappeditems) - 1) / 2

    def w__repr__(self):
        return self._space.newstring('<AllDistinct %s>' % str(self._variables))

    def w_estimate_cost(self, w_cs):
        assert isinstance(w_cs, W_ComputationSpace)
        return self._space.newint(self.__cost)

    def test_solution(self, sol):
        """test a solution against this constraint
        accept a mapping of variable names to value"""
        values = sol.items()
        value_set = set(values)
        return len(value_set) == len(sol)

    def w_revise(self, w_cs):
        assert isinstance(w_cs, W_ComputationSpace)
        variables = [(self._space.int_w(w_cs.w_dom(variable).w_size()),
                      variable, w_cs.w_dom(variable))
                     for variable in self._variables.wrappeditems]
        
        variables.sort()
        # if a domain has a size of 1,
        # then the value must be removed from the other domains
        for size, var, dom in variables:
            if self._space.eq_w(dom.w_size(), self._space.newint(1)):
                print "AllDistinct removes values"
                for _siz, _var, _dom in variables:
                    if not self._space.eq_w(_var, var):
                        try:
                            _dom.w_remove_value(dom.w_get_values().wrappeditems[0])
                        except KeyError:
                            # we ignore errors caused by the removal of
                            # non existing values
                            pass

        # if there are less values than variables, the constraint fails
        values = {}
        for size, var, dom in variables:
            for val in dom.w_get_values().wrappeditems:
                values[val] = 0
        if len(values) < len(variables):
            print "AllDistinct failed"
            raise OperationError(self._space.w_RuntimeError,
                                 self._space.wrap("Consistency Failure"))
#            raise ConsistencyFailure()

        # the constraint is entailed if all domains have a size of 1
        for variable in variables:
            if self._space.is_true(self._space.ne(variable[2].w_size(), self._space.newint(1))):
                return self._space.newint(0)

        # Question : did we *really* completely check
        # our own alldistinctness predicate ?
            
        return self._space.newint(1)

W_AllDistinct.typedef = typedef.TypeDef(
    "W_AllDistinct", W_AbstractConstraint.typedef,
    estimate_cost = interp2app(W_AllDistinct.w_estimate_cost),
    revise = interp2app(W_AllDistinct.w_revise),
    __repr__ = interp2app(W_AllDistinct.w__repr__)
    )

# function bolted into the space to serve as constructor
def make_alldistinct(objectspace, w_variables):
    return objectspace.wrap(W_AllDistinct(objectspace, w_variables))
app_make_alldistinct = gateway.interp2app(make_alldistinct)

class W_Expression(W_AbstractConstraint):
    """A constraint represented as a python expression."""
    _FILTER_CACHE = {}

    def __init__(self, o_space, w_variables, w_formula):
        """variables is a list of variables which appear in the formula
        formula is a python expression that will be evaluated as a boolean"""
        self.formula = w_formula
        W_AbstractConstraint.__init__(self, o_space, w_variables)
        self.filter_func = eval(make_lambda_head(self._space, w_variables) \
                                + self._space.str_w(w_formula), {}, {})

    def test_solution(self, sol ):
        """test a solution against this constraint 
        accept a mapping of variable names to value"""
        args = []
        for var in self._variables:
            args.append( sol[var.name] )
        return self.filterFunc( *args )

    def _init_result_cache(self):
        """key = (variable,value), value = [has_success,has_failure]"""
        result_cache = {}
        for var_name in self._variables.wrappeditems:
            result_cache[self._space.str_w(var_name.name)] = {}
        return result_cache


    def _assign_values(self, w_cs):
        variables = []
        kwargs = {}
        for variable in self._variables.wrappeditems:
            domain = w_cs.w_dom(variable)
            values = domain.w_get_values()
            variables.append((self._space.int_w(domain.w_size()),
                              [variable, values, 0,
                               self._space.len(values)]))
            kwargs[self._space.str_w(variable.name)] = values.wrappeditems[0]
        # sort variables to instanciate those with fewer possible values first
        variables.sort()

        go_on = 1
        while go_on:
            yield kwargs
            # try to instanciate the next variable
            for size, curr in variables:
                if (curr[2] + 1) < curr[-1]:
                    curr[2] += 1
                    kwargs[curr[0].name] = curr[1][curr[2]]
                    break
                else:
                    curr[2] = 0
                    kwargs[curr[0].name] = curr[1][0]
            else:
                # it's over
                go_on = 0
        
    def w_revise(self, w_cs):
        """generic propagation algorithm for n-ary expressions"""
        assert isinstance(w_cs, W_ComputationSpace)
        maybe_entailed = 1
        ffunc = self.filter_func
        result_cache = self._init_result_cache()
        for kwargs in self._assign_values(w_cs):
            if maybe_entailed:
                for var, val in kwargs.iteritems():
                    if val not in result_cache[var]:
                        break
                else:
                    continue
            if ffunc(**kwargs):
                for var, val in kwargs.items():
                    result_cache[var][val] = 1
            else:
                maybe_entailed = 0
                
        try:
            for var, keep in result_cache.iteritems():
                domain = w_cs.w_dom(self._names_to_vars[var])
                domain.remove_values([val for val in domain if val not in keep])
                
        except ConsistencyFailure:
            raise ConsistencyFailure('Inconsistency while applying %s' % \
                                     repr(self))
        except KeyError:
            # There are no more value in result_cache
            pass

        return maybe_entailed
        

    def __repr__(self):
        return '<%s>' % self.formula

W_Expression.typedef = typedef.TypeDef("W_Expression",
    W_AbstractConstraint.typedef,
    revise = interp2app(W_Expression.w_revise))


# completely unported
class BinaryExpression(W_Expression):
    """A binary constraint represented as a python expression

    This implementation uses a narrowing algorithm optimized for
    binary constraints."""
    
    def __init__(self, variables, formula, type = 'fd.BinaryExpression'):
        assert len(variables) == 2
        Expression.__init__(self, variables, formula, type)

    def copy_to(self, space):
        raise NotImplementedError

    def w_revise(self, domains):
        """specialized narrowing algorithm for binary expressions
        Runs much faster than the generic version"""
        maybe_entailed = 1
        var1 = self._variables[0]
        dom1 = domains[var1]
        values1 = dom1.get_values()
        var2 = self._variables[1]
        dom2 = domains[var2]
        values2 = dom2.get_values()
        ffunc = self.filter_func
        if dom2.size() < dom1.size():
            var1, var2 = var2, var1
            dom1, dom2 = dom2, dom1
            values1, values2 = values2, values1
            
        kwargs = {}
        keep1 = {}
        keep2 = {}
        maybe_entailed = 1
        try:
            # iterate for all values
            for val1 in values1:
                kwargs[var1] = val1
                for val2 in values2:
                    kwargs[var2] = val2
                    if val1 in keep1 and val2 in keep2 and maybe_entailed == 0:
                        continue
                    if ffunc(**kwargs):
                        keep1[val1] = 1
                        keep2[val2] = 1
                    else:
                        maybe_entailed = 0

            dom1.remove_values([val for val in values1 if val not in keep1])
            dom2.remove_values([val for val in values2 if val not in keep2])
            
        except ConsistencyFailure:
            raise ConsistencyFailure('Inconsistency while applying %s' % \
                                     repr(self))
        except Exception:
            print self, kwargs
            raise 
        return maybe_entailed


def make_expression(o_space, w_variables, w_formula):
    """create a new constraint of type Expression or BinaryExpression
    The chosen class depends on the number of variables in the constraint"""
    # encode unicode
    if o_space.eq_w(o_space.len(w_variables), o_space.newint(2)):
        return W_BinaryExpression(o_space, w_variables, w_formula)
    else:
        return W_Expression(o_space, w_variables, w_formula)


app_make_expression = gateway.interp2app(make_expression)

# have a look at this later ... (really needed ?)
class W_BasicConstraint(W_Constraint):
    """A BasicConstraint, which is never queued by the Repository
    A BasicConstraint affects only one variable, and will be entailed
    on the first call to narrow()"""
    
    def __init__(self, object_space, variable, reference, operator):
        """variables is a list of variables on which
        the constraint is applied"""
        W_Constraint.__init__(self, object_space)
        self._variable = variable
        self._reference = reference
        self._operator = operator

    def __repr__(self):
        return '<%s %s %s>'% (self.__class__, self._variable, self._reference)

    def w_is_variable_relevant(self, w_variable):
        return variable == self._variable

    def w_estimate_cost(self):
        return self._space.newint(0) # get in the first place in the queue
    
    def w_affected_variables(self):
        return [self._variable]
    
    def getVariable(self):
        return self._variable
        
    def w_revise(self, w_domains):
        domain = domains[self._variable]
        operator = self._operator
        ref = self._reference
        try:
            for val in domain.get_values() :
                if not operator(val, ref) :
                    domain.remove_value(val)
        except ConsistencyFailure:
            raise ConsistencyFailure('inconsistency while applying %s' % \
                                     repr(self))
        return 1

    def __eq__(self, other):
        raise NotImplementedError

W_BasicConstraint.typedef = typedef.TypeDef(
    "W_BasicConstraint",
    affected_variables = interp2app(W_BasicConstraint.w_affected_variables),
    is_variable_relevant = interp2app(W_BasicConstraint.w_is_variable_relevant),
    estimate_cost = interp2app(W_BasicConstraint.w_estimate_cost),
    copy_to = interp2app(W_BasicConstraint.w_copy_to),
    revise = interp2app(W_BasicConstraint.w_revise)
    )
class W_Equals(W_BasicConstraint):
    """A basic constraint variable == constant value"""
    def __init__(self, variable, reference):
        W_BasicConstraint.__init__(self, variable, reference, operator.eq)

class W_NotEquals(W_BasicConstraint):
    """A basic constraint variable != constant value"""
    def __init__(self, variable, reference):
        W_BasicConstraint.__init__(self, variable, reference, operator.ne)

class W_LesserThan(W_BasicConstraint):
    """A basic constraint variable < constant value"""
    def __init__(self, variable, reference):
        W_BasicConstraint.__init__(self, variable, reference, operator.lt)

class W_LesserOrEqual(W_BasicConstraint):
    """A basic constraint variable <= constant value"""
    def __init__(self, variable, reference):
        W_BasicConstraint.__init__(self, variable, reference, operator.le)

class W_GreaterThan(W_BasicConstraint):
    """A basic constraint variable > constant value"""
    def __init__(self, variable, reference):
        W_BasicConstraint.__init__(self, variable, reference, operator.gt)

class W_GreaterOrEqual(W_BasicConstraint):
    """A basic constraint variable >= constant value"""
    def __init__(self, variable, reference):
        W_BasicConstraint.__init__(self, variable, reference, operator.ge)
