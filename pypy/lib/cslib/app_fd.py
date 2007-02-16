"""Tools to work with finite domain variables and constraints

This module provides the following usable classes:
 * FiniteDomain: a class for storing FiniteDomains
 * Expression: a constraint represented as an expression
 * BinaryExpression: a binary constraint represented as an expression
 * various BasicConstraint classes

The Expression and BinaryExpression classes can be constructed using the
make_expression factory function.  """

import operator

from propagation import AbstractDomain, BasicConstraint, \
     ConsistencyFailure, AbstractConstraint


class FiniteDomain(AbstractDomain):
    """
    Variable Domain with a finite set of possible values
    """

    _copy_count = 0
    _write_count = 0
    
    def __init__(self, values):
        """values is a list of values in the domain
        This class uses a dictionnary to make sure that there are
        no duplicate values"""
        AbstractDomain.__init__(self)
        if isinstance(values, FiniteDomain):
            # do a copy on write
            self._cow = True
            values._cow = True
            FiniteDomain._copy_count += 1
            self._values = values._values
        else:
            assert len(values) > 0
            self.setValues(values)
            
        ##self.getValues = self._values.keys

    def setValues(self, values):
        self._cow = False
        FiniteDomain._write_count += 1
        self._values = {}
        for val in values:
            self._values[val] = 0
        
    def removeValue(self, value):
        """Remove value of domain and check for consistency"""
##         print "removing", value, "from", self._values.keys()
        if self._cow:
            self.setValues(self._values)
        del self._values[value]
        self._valueRemoved()

    def removeValues(self, values):
        """Remove values of domain and check for consistency"""
        if self._cow:
            self.setValues(self._values)
        if values:
##             print "removing", values, "from", self._values.keys()
            for val in values :
                del self._values[val]
            self._valueRemoved()
    __delitem__ = removeValue
    
    def size(self):
        """computes the size of a finite domain"""
        return len(self._values)
    __len__ = size
    
    def getValues(self):
        """return all the values in the domain"""
        return self._values.keys()

    def __iter__(self):
        return iter(self._values)
    
    def copy(self):
        """clone the domain"""
        return FiniteDomain(self)
    
    def __repr__(self):
        return '<FiniteDomain %s>' % str(self.getValues())

##
## Constraints
##    
class AllDistinct(AbstractConstraint):
    """Contraint: all values must be distinct"""

    def __init__(self, variables):
        assert len(variables)>1
        AbstractConstraint.__init__(self, variables)
        # worst case complexity
        self.__cost = len(variables) * (len(variables) - 1) / 2 

    def __repr__(self):
        return '<AllDistinct %s>' % str(self._variables)

    def estimateCost(self, domains):
        """return cost"""
        return self.__cost

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        variables = [(domains[variable].size(), variable, domains[variable])
                     for variable in self._variables]
        
        variables.sort()
        # if a domain has a size of 1,
        # then the value must be removed from the other domains
        for size, var, dom in variables:
            if dom.size() == 1:
                for _siz, _var, _dom in variables:
                    if _var != var:
                        try:
                            _dom.removeValue(dom.getValues()[0])
                        except KeyError:
                            # we ignore errors caused by the removal of
                            # non existing values
                            pass

        # if there are less values than variables, the constraint fails
        values = {}
        for size, var, dom in variables:
            for val in dom:
                values[val] = 0
        if len(values) < len(variables):
            raise ConsistencyFailure()
            
        # the constraint is entailed if all domains have a size of 1
        for variable in variables:
            if variable[2].size() != 1:
                return 0
        return 1




class Expression(AbstractConstraint):
    """A constraint represented as a python expression."""
    _FILTER_CACHE = {}

    def __init__(self, variables, formula, type='fd.Expression'):
        """variables is a list of variables which appear in the formula
        formula is a python expression that will be evaluated as a boolean"""
        AbstractConstraint.__init__(self, variables)
        self.formula = formula
        self.type = type
        try:
            self.filterFunc = Expression._FILTER_CACHE[formula]
        except KeyError:
            self.filterFunc = eval('lambda %s: %s' % \
                                        (','.join(variables), formula), {}, {})
            Expression._FILTER_CACHE[formula] = self.filterFunc

    def _init_result_cache(self):
        """key = (variable,value), value = [has_success,has_failure]"""
        result_cache = {}
        for var_name in self._variables:
            result_cache[var_name] = {}
        return result_cache


    def _assign_values(self, domains):
        variables = []
        kwargs = {}
        for variable in self._variables:
            domain = domains[variable]
            values = domain.get_values()
            variables.append((domain.size(), [variable, values, 0, len(values)]))
            kwargs[variable] = values[0]
        # sort variables to instanciate those with fewer possible values first
        variables.sort()

        go_on = 1
        while go_on:
            yield kwargs
            # try to instanciate the next variable
            for size, curr in variables:
                if (curr[2] + 1) < curr[-1]:
                    curr[2] += 1
                    kwargs[curr[0]] = curr[1][curr[2]]
                    break
                else:
                    curr[2] = 0
                    kwargs[curr[0]] = curr[1][0]
            else:
                # it's over
                go_on = 0
            
        
    def narrow(self, domains):
        """generic narrowing algorithm for n-ary expressions"""
        maybe_entailed = 1
        ffunc = self.filterFunc
        result_cache = self._init_result_cache()
        for kwargs in self._assign_values(domains):
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
                domain = domains[var]
                domain.remove_values([val for val in domain.get_values()
                                      if val not in keep])                
        except ConsistencyFailure:
            raise ConsistencyFailure('Inconsistency while applying %s' % \
                                     repr(self))
        except KeyError:
            # There are no more value in result_cache
            pass

        return maybe_entailed

    def __repr__(self):
        return '<%s "%s">' % (self.type, self.formula)

class BinaryExpression(Expression):
    """A binary constraint represented as a python expression

    This implementation uses a narrowing algorithm optimized for
    binary constraints."""
    
    def __init__(self, variables, formula, type = 'fd.BinaryExpression'):
        assert len(variables) == 2
        Expression.__init__(self, variables, formula, type)

    def narrow(self, domains):
        """specialized narrowing algorithm for binary expressions
        Runs much faster than the generic version"""
        maybe_entailed = 1
        var1 = self._variables[0]
        dom1 = domains[var1]
        values1 = dom1.get_values()
        var2 = self._variables[1]
        dom2 = domains[var2]
        values2 = dom2.get_values()
        ffunc = self.filterFunc
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


def make_expression(variables, formula, constraint_type=None):
    """create a new constraint of type Expression or BinaryExpression
    The chosen class depends on the number of variables in the constraint"""
    # encode unicode
    vars = []
    for var in variables:
        if type(var) == type(u''):
            vars.append(var.encode())
        else:
            vars.append(var)
    if len(vars) == 2:
        if constraint_type is not None:
            return BinaryExpression(vars, formula, constraint_type)
        else:
            return BinaryExpression(vars, formula)

    else:
        if constraint_type is not None:
            return Expression(vars, formula, constraint_type)
        else:
            return Expression(vars, formula)


class Equals(BasicConstraint):
    """A basic constraint variable == constant value"""
    def __init__(self, variable, reference):
        BasicConstraint.__init__(self, variable, reference, operator.eq)

class NotEquals(BasicConstraint):
    """A basic constraint variable != constant value"""
    def __init__(self, variable, reference):
        BasicConstraint.__init__(self, variable, reference, operator.ne)

class LesserThan(BasicConstraint):
    """A basic constraint variable < constant value"""
    def __init__(self, variable, reference):
        BasicConstraint.__init__(self, variable, reference, operator.lt)

class LesserOrEqual(BasicConstraint):
    """A basic constraint variable <= constant value"""
    def __init__(self, variable, reference):
        BasicConstraint.__init__(self, variable, reference, operator.le)

class GreaterThan(BasicConstraint):
    """A basic constraint variable > constant value"""
    def __init__(self, variable, reference):
        BasicConstraint.__init__(self, variable, reference, operator.gt)

class GreaterOrEqual(BasicConstraint):
    """A basic constraint variable >= constant value"""
    def __init__(self, variable, reference):
        BasicConstraint.__init__(self, variable, reference, operator.ge)

def _in(v, set):
    """test presence of v in set"""
    return v in set

class InSet(BasicConstraint):
    """A basic contraint variable in set value"""
    def __init__(self, variable, set):
        BasicConstraint.__init__(self, variable, set, _in )




