from pypy.rlib.btree import BTreeNode
from pypy.rlib.rdomain import BaseFiniteDomain, ConsistencyError


class AbstractConstraint:
    
    def __init__(self, variables):
        """variables is a list of variables which appear in the formula"""
        assert isinstance(variables, list)

        self._variables = variables

    def revise(self, domains):
        "domains : {'var':Domain}"
        return False

    def estimate_cost(self, domains):
        cost = 1
        for var in self._variables:
            dom = domains[var]
            assert isinstance(dom, BaseFiniteDomain)
            cost = cost * dom.size()
        return cost


class Quadruple(BTreeNode):
    def __init__(self, key, varname, values, index):
        BTreeNode.__init__( self, key )
        self.var = varname
        self.values = values
        self.index = index

class Expression(AbstractConstraint):
    """A constraint represented as a functional expression."""

    def __init__(self, variables):
        AbstractConstraint.__init__(self, variables)
        self.doms = {}
        
    def filter_func(self, kwargs):
        return False

    def _init_result_cache(self):
        """key = (variable,value), value = [has_success,has_failure]"""
        result_cache = {}
        for var in self._variables:
            result_cache[var] = {}
        return result_cache

    def _assign_values(self, doms):
        kwargs = {}
        sorted_vars = None
        for variable in self._variables:
            domain = doms[variable]
            assert isinstance(domain, BaseFiniteDomain)
            values = domain.get_values()
            node = Quadruple(domain.size(),
                             variable,
                             values,
                             0)
            if sorted_vars is None:
                sorted_vars = node
            else:
                sorted_vars.add( node )
            kwargs[variable] = values[0]

        # get sorted variables to instanciate those with fewer possible values first
        assert sorted_vars is not None
        self._assign_values_state = sorted_vars.get_values()
        return kwargs
        
    def _next_value(self, kwargs):

        # try to instanciate the next variable
        variables = self._assign_values_state

        for curr in variables:
            if curr.index < curr.key:
                kwargs[curr.var] = curr.values[curr.index]
                curr.index += 1
                break
            else:
                curr.index = 0
                kwargs[curr.var] = curr.values[0]
        else:
            # it's over
            return None
        return kwargs

    def revise(self, doms):
        """generic propagation algorithm for n-ary expressions"""
        self.doms = doms
        maybe_entailed = True
        result_cache = self._init_result_cache()

        kwargs = self._assign_values(doms)

        while 1:
            kwargs = self._next_value(kwargs)
            if kwargs is None:
                break
                                   
            if maybe_entailed:
                for varname, val in kwargs.iteritems():
                    val_dict = result_cache[varname]
                    if val not in val_dict:
                        break
                else:
                    continue
            if self.filter_func(kwargs):
                for var, val in kwargs.items():
                    var_dict = result_cache[var]
                    var_dict[val] = True
            else:
                maybe_entailed = False

        try: # XXX domains in rlib, too
            for varname, keep in result_cache.items():
                domain = doms[varname]
                assert isinstance(domain, BaseFiniteDomain)
                domain.remove_values([val
                                      for val in domain.get_values()
                                      if val not in keep])
        except KeyError:
            # There are no more value in result_cache
            pass

        return maybe_entailed
        

    def __repr__(self):
        return '<%s>' % self.formula

    
#--- Alldistinct

class VarDom(BTreeNode):
    def __init__(self, key, var, dom):
        BTreeNode.__init__(self, key)
        self.var = var
        self.dom = dom

class AllDistinct(AbstractConstraint):
    """Contraint: all values must be distinct"""

    def __init__(self, variables):
        AbstractConstraint.__init__(self, variables)
        # worst case complexity
        self._cost = len(self._variables) * (len(self._variables) - 1) / 2

    def estimate_cost(self, domains):
        return self._cost
        
    def revise(self, doms):

        sorted_vars = None
        for var in self._variables:
            dom = doms[var]
            assert isinstance(dom, BaseFiniteDomain)
            node = VarDom(dom.size(), var, dom)
            if sorted_vars is None:
                sorted_vars = node
            else:
                sorted_vars.add(node)

        assert sorted_vars is not None
        variables = sorted_vars.get_values()
        
        # if a domain has a size of 1,
        # then the value must be removed from the other domains
        for var_dom in variables:
            if var_dom.dom.size() == 1:
                #print "AllDistinct removes values"
                for var_dom2 in variables:
                    if var_dom2.var != var_dom.var:
                        try:
                            var_dom2.dom.remove_value(var_dom.dom.get_values()[0])
                        except KeyError, e:
                            # we ignore errors caused by the removal of
                            # non existing values
                            pass

        # if there are less values than variables, the constraint fails
        values = {}
        for var_dom in variables:
            for val in var_dom.dom.get_values():
                values[val] = 0

        if len(values) < len(variables):
            #print "AllDistinct failed"
            raise ConsistencyError

        # the constraint is entailed if all domains have a size of 1
        for var_dom in variables:
            if not var_dom.dom.size() == 1:
                return False

        #print "All distinct entailed"
        return True



#--- Binary expressions

class BinaryExpression(Expression):
    """A binary constraint represented as a python expression

    This implementation uses a narrowing algorithm optimized for
    binary constraints."""
    
    def __init__(self, variables):
        assert len(variables) == 2
        Expression.__init__(self, variables)

    def revise(self, domains):
        """specialized pruning algorithm for binary expressions
        Runs much faster than the generic version"""
        self.doms = domains
        maybe_entailed = True
        var1 = self._variables[0]
        dom1 = domains[var1]
        values1 = dom1.get_values()
        var2 = self._variables[1]
        dom2 = domains[var2]
        values2 = dom2.get_values()
        if dom2.size() < dom1.size():
            var1, var2 = var2, var1
            dom1, dom2 = dom2, dom1
            values1, values2 = values2, values1
            
        kwargs = {}
        keep1 = {}
        keep2 = {}
        maybe_entailed = True
        # iterate for all values
        for val1 in values1:
            kwargs[var1] = val1
            for val2 in values2:
                kwargs[var2] = val2
                if val1 in keep1 and val2 in keep2 and not maybe_entailed:
                    continue
                if self.filter_func(kwargs):
                    keep1[val1] = 1
                    keep2[val2] = 1
                else:
                    maybe_entailed = False

        dom1.remove_values([val for val in values1 if val not in keep1])
        dom2.remove_values([val for val in values2 if val not in keep2])

        return maybe_entailed


class BinEq(BinaryExpression):
    def filter_func(self, kwargs):
        values = kwargs.values()
        return values[0]==values[1]

class BinLt(BinaryExpression):
    def filter_func(self, kwargs):
        values = kwargs.values()
        return values[0] < values[1]
