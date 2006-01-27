# a) new requirement : be able to postpone asking fo the
# values of the domain

#-- Exceptions ---------------------------------------

class ConsistencyFailure(Exception):
    """The repository is not in a consistent state"""
    pass

class DomainlessVariables(Exception):
    """A constraint can't be defined on variables
       without a domain"""
    pass

#-- Domains --------------------------------------------

class AbstractDomain(object):
    """Implements the functionnality related to the changed flag.
    Can be used as a starting point for concrete domains"""

    #__implements__ = DomainInterface
    def __init__(self):
        self.__changed = 0

    def reset_flags(self):
        self.__changed = 0
    
    def has_changed(self):
        return self.__changed

    def _value_removed(self):
        """The implementation of remove_value should call this method"""
        self.__changed = 1
        if self.size() == 0:
            raise ConsistencyFailure()


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
        if isinstance(values,FiniteDomain):
            # do a copy on write
            self._cow = True
            values._cow = True
            FiniteDomain._copy_count += 1
            self._values = values._values
        else:
            # don't check this there (a)
            #assert len(values) > 0
            self.set_values(values)
            
        ##self.getValues = self._values.keys

    def set_values(self, values):
        self._cow = False
        FiniteDomain._write_count += 1
        self._values = set(values)
        
    def remove_value(self, value):
        """Remove value of domain and check for consistency"""
##         print "removing", value, "from", self._values.keys()
        if self._cow:
            self.set_values(self._values)
        del self._values[value]
        self._value_removed()

    def remove_values(self, values):
        """Remove values of domain and check for consistency"""
        if self._cow:
            self.set_values(self._values)
        if values:
##             print "removing", values, "from", self._values.keys()
            for val in values :
                self._values.remove(val)
            self._value_removed()
    __delitem__ = remove_value
    
    def size(self):
        """computes the size of a finite domain"""
        return len(self._values)
    __len__ = size
    
    def get_values(self):
        """return all the values in the domain
           in an indexable sequence"""
        return list(self._values)

    def __iter__(self):
        return iter(self._values)
    
    def copy(self):
        """clone the domain"""
        return FiniteDomain(self)
    
    def __repr__(self):
        return '<FiniteDomain %s>' % str(self.get_values())

    def __eq__(self, other):
        if other is None: return False
        return self._values == other._values

    def __ne__(self, other):
        return not self == other

    def intersection(self, other):
        if other is None: return self.get_values()
        return self._values & other._values


#-- Constraints ------------------------------------------

EmptyDom = FiniteDomain([])

class AbstractConstraint(object):
    
    def __init__(self, variables):
        """variables is a list of variables which appear in the formula"""
        self._names_to_vars = {}
        for var in variables:
            if var.dom == EmptyDom:
                raise DomainlessVariables
            self._names_to_vars[var.name] = var
        self._variables = variables

    def affectedVariables(self):
        """ Return a list of all variables affected by this constraint """
        return self._variables

    def isVariableRelevant(self, variable):
        return variable in self._variables

    def estimateCost(self, domains):
        """Return an estimate of the cost of the narrowing of the constraint"""
        return reduce(operator.mul,
                      [domains[var].size() for var in self._variables])


class BasicConstraint(object):
    """A BasicConstraint, which is never queued by the Repository
    A BasicConstraint affects only one variable, and will be entailed
    on the first call to narrow()"""
    
    def __init__(self, variable, reference, operator):
        """variables is a list of variables on which
        the constraint is applied"""
        self._variable = variable
        self._reference = reference
        self._operator = operator

    def __repr__(self):
        return '<%s %s %s>'% (self.__class__, self._variable, self._reference)

    def isVariableRelevant(self, variable):
        return variable == self._variable

    def estimateCost(self, domains):
        return 0 # get in the first place in the queue
    
    def affectedVariables(self):
        return [self._variable]
    
    def getVariable(self):
        return self._variable
        
    def narrow(self, domains):
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


def make_lambda_head(vars):
    var_ids = ','.join([var.name for var in vars])
    return 'lambda ' + var_ids + ':'

def expand_expr_template(expr, vars):
    for var in vars:
        expr.replace(var.name, var.name + '.val')
    return expr

class Expression(AbstractConstraint):
    """A constraint represented as a python expression."""
    _FILTER_CACHE = {}

    def __init__(self, variables, formula, typ='fd.Expression'):
        """variables is a list of variables which appear in the formula
        formula is a python expression that will be evaluated as a boolean"""
        self.formula = formula
        self.type = typ
        AbstractConstraint.__init__(self, variables)
        try:
            self.filterFunc = Expression._FILTER_CACHE[formula]
        except KeyError:
            self.filterFunc = eval(make_lambda_head(variables) \
                                   + expand_expr_template(formula, variables), {}, {})
            Expression._FILTER_CACHE[formula] = self.filterFunc

    def _init_result_cache(self):
        """key = (variable,value), value = [has_success,has_failure]"""
        result_cache = {}
        for var_name in self._variables:
            result_cache[var_name.name] = {}
        return result_cache


    def _assign_values(self):
        variables = []
        kwargs = {}
        for variable in self._variables:
            domain = variable.dom
            values = domain.get_values()
            variables.append((domain.size(), [variable, values, 0, len(values)]))
            kwargs[variable.name] = values[0]
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
            
        
    def narrow(self):
        # removed domain arg. (auc, ale)
        """generic narrowing algorithm for n-ary expressions"""
        maybe_entailed = 1
        ffunc = self.filterFunc
        result_cache = self._init_result_cache()
        for kwargs in self._assign_values():
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
                domain = self._names_to_vars[var].dom
                domain.remove_values([val for val in domain if val not in keep])
                
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
