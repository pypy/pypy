from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import baseobjspace, typedef, gateway
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.function import Function

from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.stringobject import W_StringObject

from pypy.objspace.constraint.computationspace import W_ComputationSpace

from pypy.objspace.cclp.types import W_Constraint, W_CVar as W_Variable

from pypy.objspace.std.model import StdObjSpaceMultiMethod

from pypy.objspace.constraint.btree import BTree
from pypy.objspace.constraint.util import sort, reverse

all_mms = {}


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
        assert isinstance(w_variable, W_Variable)
        return self._space.newbool(w_variable in self._variables)

    def w_revise(self):
        return self._space.newbool(self.revise())
            
    
W_AbstractConstraint.typedef = typedef.TypeDef(
    "W_AbstractConstraint",
    W_Constraint.typedef,                                           
    affected_variables = interp2app(W_AbstractConstraint.w_affected_variables),
    knows_var = interp2app(W_AbstractConstraint.w_knows_var),
    revise = interp2app(W_AbstractConstraint.w_revise)) 



from pypy.module.__builtin__.compiling import eval as ev
def make_filter__List_String(object_space, w_variables, w_formula):
    """NOT RPYTHON"""
    assert isinstance(w_variables, W_ListObject)
    assert isinstance(w_formula, W_StringObject)
    items = object_space.unpackiterable(w_variables)
    for it in items:
        assert isinstance(it, W_Variable)
    var_ids = ','.join([var.name_w()
                        for var in items]) 
    func_head = 'lambda ' + var_ids + ':'
    expr = func_head + object_space.str_w(w_formula)
    func_obj = ev(object_space, object_space.wrap(expr), object_space.newdict([]),
                                 object_space.newdict([]))
    assert isinstance(func_obj, Function)
    return func_obj

make_filter_mm = StdObjSpaceMultiMethod('make_filter', 2)
make_filter_mm.register(make_filter__List_String, W_ListObject, W_StringObject)
all_mms['make_filter'] = make_filter_mm

class W_Expression(W_AbstractConstraint):
    """A constraint represented as a python expression."""

    def __init__(self, object_space, w_variables, w_formula):
        """variables is a list of variables which appear in the formula
        formula is a python expression that will be evaluated as a boolean"""
        W_AbstractConstraint.__init__(self, object_space, w_variables)
        self.formula = self._space.str_w(w_formula)
        # self.filter_func is a function taking keyword arguments and returning a boolean
        self.filter_func = self._space.make_filter(w_variables, w_formula)

    def test_solution(self, sol_dict):
        """test a solution against this constraint 
        accept a mapping of variable names to value"""
        args = []
        for var in self._variables:
            assert isinstance(var, W_Variable)
            args.append(sol_dict[var.w_name()])
        return self.filter_func(*args)

    def _init_result_cache(self):
        """key = (variable,value), value = [has_success,has_failure]"""
        result_cache = self._space.newdict([])
        for var in self._variables:
            assert isinstance(var, W_Variable)
            result_cache.content[var.w_name()] = self._space.newdict([])
        return result_cache

    def _assign_values(self):
        variables = []
        kwargs = self._space.newdict([])
        for variable in self._variables:
            assert isinstance(variable, W_Variable)
            domain = variable.w_dom
            values = domain.get_values()
            variables.append((domain.size(), [variable.w_name(), values, 0, len(values)]))
            kwargs.content[variable.w_name()] = values[0]
        # sort variables to instanciate those with fewer possible values first
        sort(variables)
        self._assign_values_state = variables
        return kwargs 
        
    def _next_value(self, kwargs):

        # try to instanciate the next variable
        variables = self._assign_values_state

        for _, curr in variables:
            w_name = curr[0]
            dom_values = curr[1] 
            dom_index = curr[2]
            dom_len = curr[3]
            if dom_index < dom_len:
                kwargs.content[w_name] = dom_values[curr[2]]
                curr[2] = dom_index + 1
                break
            else:
                curr[2] = 0
                kwargs.content[w_name] = dom_values[0]
        else:
            # it's over
            raise StopIteration
        return kwargs

    def revise(self):
        """generic propagation algorithm for n-ary expressions"""
        maybe_entailed = True
        ffunc = self.filter_func
        result_cache = self._init_result_cache()

        kwargs = self._assign_values()
        while 1:
            try:
                kwargs = self._next_value(kwargs)
            except StopIteration:
                break
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
                domain = self._names_to_vars[self._space.str_w(varname)].w_dom
                domain.remove_values([val
                                      for val in domain._values.content.keys()
                                      if val not in keep.content])
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
    


def make_expression(o_space, w_variables, w_formula):
    """create a new constraint of type Expression or BinaryExpression
    The chosen class depends on the number of variables in the constraint"""
    assert len(w_variables.wrappeditems) > 0
    return W_Expression(o_space, w_variables, w_formula)
app_make_expression = gateway.interp2app(make_expression)


class W_AllDistinct(W_AbstractConstraint):
    """Contraint: all values must be distinct"""

    def __init__(self, object_space, w_variables):
        W_AbstractConstraint.__init__(self, object_space, w_variables)
        # worst case complexity
        #self.__cost = len(w_variables.wrappeditems) * (len(w_variables.wrappeditems) - 1) / 2

    def revise(self):
        _spc = self._space

        ord_vars = BTree()
        for variable in self._variables:
            ord_vars.add((variable.w_dom).size(),
                         (variable, variable.w_dom))

        variables = ord_vars.values()
        
##         variables = [(_spc.int_w(w_cs.w_dom(variable).w_size()),
##                       variable, w_cs.w_dom(variable))
##                      for variable in self._variables]
##         variables.sort()
        
        # if a domain has a size of 1,
        # then the value must be removed from the other domains
        for var, dom in variables:
            if dom.size() == 1:
                #print "AllDistinct removes values"
                for _var, _dom in variables:
                    if not _var._same_as(var):
                        try:
                            _dom.remove_value(dom.get_values()[0])
                        except KeyError, e:
                            # we ignore errors caused by the removal of
                            # non existing values
                            pass

        # if there are less values than variables, the constraint fails
        values = {}
        for var, dom in variables:
            for val in dom.w_get_values().wrappeditems:
                values[val] = 0

        if len(values) < len(variables):
            #print "AllDistinct failed"
            raise OperationError(_spc.w_RuntimeError,
                                 _spc.wrap("ConsistencyFailure"))

        # the constraint is entailed if all domains have a size of 1
        for _var, dom in variables:
            if not dom.size() == 1:
                return False

        # Question : did we *really* completely check
        # our own alldistinctness predicate ?
        #print "All distinct entailed"
        return True

W_AllDistinct.typedef = typedef.TypeDef(
    "W_AllDistinct", W_AbstractConstraint.typedef,
    revise = interp2app(W_AllDistinct.w_revise))

# function bolted into the space to serve as constructor
def make_alldistinct(object_space, w_variables):
    assert len(w_variables.wrappeditems) > 0
    return object_space.wrap(W_AllDistinct(object_space, w_variables))
app_make_alldistinct = gateway.interp2app(make_alldistinct)
