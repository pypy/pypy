from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import baseobjspace, typedef, gateway
from pypy.interpreter.gateway import interp2app

from pypy.objspace.std.listobject import W_ListObject

from pypy.objspace.constraint.computationspace import W_ComputationSpace
from pypy.objspace.constraint.computationspace import W_Constraint

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
        assert self._space.is_true(self._space.ge(self._space.len(w_variables),
                                                  self._space.newint(1)))
        self._names_to_vars = {}
        for var in w_variables.wrappeditems:
            self._names_to_vars[var.name_w()] = var
        self._variables = w_variables.wrappeditems #unwrap once ...

    def w_affected_variables(self):
        """ Return a list of all variables affected by this constraint """
        return self._space.newlist(self._variables)

    def affected_variables(self):
        return self._variables

    def w_knows_var(self, w_variable):
        return self._space.newbool(variable in self._variables)

    def w_estimate_cost(self, w_cs):
        """Return an estimate of the cost of the narrowing of the constraint"""
        assert isinstance(w_cs, W_ComputationSpace)
        return self._space.newint(self.estimate_cost_w(w_cs))

    def w_revise(self, w_cs):
        assert isinstance(w_cs, W_ComputationSpace)
        return self._space.newbool(self.revise(w_cs))

    def estimate_cost_w(self, w_cs):
        assert isinstance(w_cs, W_ComputationSpace)
        return reduce(operator.mul,
                      [w_cs.w_dom(var).size()
                       for var in self._variables])

    def __eq__(self, other): #FIXME and parent
        if not isinstance(other, self.__class__): return False
        return self._variables == other._variables
    
W_AbstractConstraint.typedef = typedef.TypeDef("W_AbstractConstraint",
    affected_variables = interp2app(W_AbstractConstraint.w_affected_variables),
    knows_var = interp2app(W_AbstractConstraint.w_knows_var),
    estimate_cost = interp2app(W_AbstractConstraint.w_estimate_cost),
    revise = interp2app(W_AbstractConstraint.w_revise)) 


class W_AllDistinct(W_AbstractConstraint):
    """Contraint: all values must be distinct"""

    def __init__(self, object_space, w_variables):
        W_AbstractConstraint.__init__(self, object_space, w_variables)
        # worst case complexity
        self.__cost = len(w_variables.wrappeditems) * (len(w_variables.wrappeditems) - 1) / 2

    def estimate_cost_w(self, w_cs):
        assert isinstance(w_cs, W_ComputationSpace)
        return self.__cost

    def test_solution(self, sol):
        """test a solution against this constraint
        accept a mapping of variable names to value"""
        values = sol.items()
        value_set = set(values)
        return len(value_set) == len(sol)

    def revise(self, w_cs):
        assert isinstance(w_cs, W_ComputationSpace)
        variables = [(self._space.int_w(w_cs.w_dom(variable).w_size()),
                      variable, w_cs.w_dom(variable))
                     for variable in self._variables]
        
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

        # the constraint is entailed if all domains have a size of 1
        for variable in variables:
            if self._space.is_true(self._space.ne(variable[2].w_size(), self._space.newint(1))):
                return False

        # Question : did we *really* completely check
        # our own alldistinctness predicate ?
            
        return True

W_AllDistinct.typedef = typedef.TypeDef(
    "W_AllDistinct", W_AbstractConstraint.typedef,
    estimate_cost = interp2app(W_AllDistinct.w_estimate_cost),
    revise = interp2app(W_AllDistinct.w_revise))

# function bolted into the space to serve as constructor
def make_alldistinct(object_space, w_variables):
    return object_space.wrap(W_AllDistinct(object_space, w_variables))
app_make_alldistinct = gateway.interp2app(make_alldistinct)


def make_filter(object_space, w_variables, w_formula):
    """NOT RPYTHON"""
    var_ids = ','.join([object_space.str_w(var.w_name)
                        for var in w_variables.wrappeditems])
    func_head = 'lambda ' + var_ids + ':'
    func_obj = eval(func_head + object_space.str_w(w_formula), {}, {})
    return func_obj
app_make_filter = gateway.interp2app(make_filter)

class W_Expression(W_AbstractConstraint):
    """A constraint represented as a python expression."""

    def __init__(self, object_space, w_variables, w_formula):
        """variables is a list of variables which appear in the formula
        formula is a python expression that will be evaluated as a boolean"""
        W_AbstractConstraint.__init__(self, object_space, w_variables)
        self.formula = self._space.str_w(w_formula)
        self.filter_func = make_filter(self._space, w_variables, w_formula)

    def test_solution(self, sol ):
        """test a solution against this constraint 
        accept a mapping of variable names to value"""
        args = []
        for var in self._variables:
            args.append( sol[var.w_name] )
        return self.filterFunc( *args )

    def _init_result_cache(self):
        """key = (variable,value), value = [has_success,has_failure]"""
        result_cache = self._space.newdict({})
        for var in self._variables:
            result_cache.content[var.w_name] = self._space.newdict({})
        return result_cache

    def _assign_values(self, w_cs):
        variables = []
        kwargs = self._space.newdict({})
        for variable in self._variables:
            domain = w_cs.w_dom(variable)
            values = domain.w_get_values()
            variables.append((self._space.int_w(domain.w_size()),
                              [variable, values, self._space.newint(0),
                               self._space.len(values)]))
            kwargs.content[variable.w_name] = values.wrappeditems[0]
        # sort variables to instanciate those with fewer possible values first
        variables.sort()

        go_on = 1
        while go_on:
            yield kwargs
            # try to instanciate the next variable
            for size, curr in variables:
                if self._space.int_w(curr[2]) + 1 < self._space.int_w(curr[-1]):
                    curr[2] = self._space.add(curr[2], self._space.newint(1))
                    kwargs.content[curr[0].w_name] = curr[1].wrappeditems[self._space.int_w(curr[2])]
                    break
                else:
                    curr[2] = self._space.newint(0)
                    kwargs.content[curr[0].w_name] = curr[1].wrappeditems[0]
            else:
                # it's over
                go_on = 0
        
    def revise(self, w_cs):
        """generic propagation algorithm for n-ary expressions"""
        assert isinstance(w_cs, W_ComputationSpace)
        maybe_entailed = True
        ffunc = self.filter_func
        result_cache = self._init_result_cache()
        for kwargs in self._assign_values(w_cs):
            if maybe_entailed:
                for varname, val in kwargs.content.iteritems():
                    if val not in result_cache.content[varname].content:
                        break
                else:
                    continue
            if self._space.is_true(self._space.call(self._space.wrap(ffunc),
                                                    self._space.newlist([]), kwargs)):
                for var, val in kwargs.content.items():
                    result_cache.content[var].content[val] = self._space.w_True
            else:
                maybe_entailed = False
                
        try:
            for varname, keep in result_cache.content.items():
                print keep
                domain = w_cs.w_dom(self._names_to_vars[self._space.str_w(varname)])
                domain.w_remove_values(self._space.newlist([val
                                                            for val in domain._values
                                                            if val not in keep.content]))
                
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
    return W_Expression(o_space, w_variables, w_formula)
    if o_space.eq_w(o_space.len(w_variables), o_space.newint(2)):
        return W_BinaryExpression(o_space, w_variables, w_formula)
    else:
        return W_Expression(o_space, w_variables, w_formula)
app_make_expression = gateway.interp2app(make_expression)

