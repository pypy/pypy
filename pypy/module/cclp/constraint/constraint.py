from pypy.rlib.objectmodel import we_are_translated
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import baseobjspace, typedef, gateway
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.function import Function

from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.dictobject import W_DictObject

from pypy.module.cclp.types import W_Constraint, W_AbstractDomain, W_Root, \
     W_Var, W_CVar as W_Variable

from pypy.objspace.std.model import StdObjSpaceMultiMethod

from pypy.module.cclp.constraint.btree import BTree
#from pypy.objspace.constraint.util import sort

all_mms = {}


class W_AbstractConstraint(W_Constraint):
    
    def __init__(self, object_space, w_variables):
        """variables is a list of variables which appear in the formula"""
        W_Constraint.__init__(self, object_space)
        assert isinstance(w_variables, W_ListObject)
        assert self._space.is_true(self._space.ge(self._space.len(w_variables),
                                                  self._space.newint(1)))
        self._names_to_vars = {}
        for var in w_variables.wrappeditems:
            assert isinstance(var, W_Var)
            self._names_to_vars[var.name_w()] = var
        self._variables = w_variables.wrappeditems #unwrap once ...

    def w_affected_variables(self):
        """ Return a list of all variables affected by this constraint """
        return self._space.newlist(self._variables)

    def affected_variables(self):
        return self._variables

    def w_revise(self):
        return self._space.newbool(self.revise())
                
W_AbstractConstraint.typedef = typedef.TypeDef(
    "W_AbstractConstraint",
    W_Constraint.typedef,                                           
    affected_variables = interp2app(W_AbstractConstraint.w_affected_variables),
    revise = interp2app(W_AbstractConstraint.w_revise)) 



from pypy.module.__builtin__.compiling import eval as ev
def make_filter__List_String(object_space, w_variables, w_formula):
    """NOT RPYTHON"""
    assert isinstance(w_variables, W_ListObject)
    assert isinstance(w_formula, W_StringObject)
    items = object_space.unpackiterable(w_variables)
    lst = []
    for it in items:
        assert isinstance(it, W_Variable)
        lst.append(it.name_w())
    var_ids = ','.join(lst) #[var.name_w()
                        # for var in items]) 
    func_head = 'lambda ' + var_ids + ':'
    expr = func_head + object_space.str_w(w_formula)
    func_obj = ev(object_space, object_space.wrap(expr), object_space.newdict(),
                                 object_space.newdict())
    assert isinstance(func_obj, Function)
    return func_obj

make_filter_mm = StdObjSpaceMultiMethod('make_filter', 2)
make_filter_mm.register(make_filter__List_String, W_ListObject, W_StringObject)
all_mms['make_filter'] = make_filter_mm

class Quadruple(W_Root):
    def __init__(self, zero, one, two, three):
        self.zero = zero
        self.one = one
        self.two = two
        self.three = three

class W_Expression(W_AbstractConstraint):
    """A constraint represented as a python expression."""

    def __init__(self, object_space, w_variables, w_formula):
        """variables is a list of variables which appear in the formula
        formula is a python expression that will be evaluated as a boolean"""
        W_AbstractConstraint.__init__(self, object_space, w_variables)
        self.formula = self._space.str_w(w_formula)
        # self.filter_func is a function taking keyword arguments and returning a boolean
        self.filter_func = self._space.make_filter(w_variables, w_formula)

    def copy(self):
        if we_are_translated():
            raise NotImplementedError
        else:
            newvars = [var.copy(self._space) for var in self._variables]
            const = W_Expression(self._space, self._space.newlist(newvars), self._space.wrap(self.formula))
            return const

    def _init_result_cache(self):
        """key = (variable,value), value = [has_success,has_failure]"""
        result_cache = self._space.newdict()
        for var in self._variables:
            assert isinstance(var, W_Variable)
            self._space.setitem(result_cache, var.w_name(), self._space.newdict())
        return result_cache

    def _assign_values(self):
        kwargs = self._space.newdict()
        variables = BTree()
        for variable in self._variables:
            assert isinstance(variable, W_Variable)
            domain = variable.w_dom
            assert isinstance(domain, W_AbstractDomain)
            values = domain.get_values()
            assert isinstance(values, list)
            ds = domain.size()
            assert isinstance(ds, int)
            w_name = variable.w_name()
            lval = len(values)
            variables.add(ds, Quadruple(w_name, values, 0, lval))
            # was meant to be:
            #variables.append((domain.size(),
            #                  [w_name, values, 0, len(values)]))
            first_value = values[0]
            assert isinstance(first_value, W_Root)
            kwargs.content[variable.w_name()] = first_value
        # get sorted variables to instanciate those with fewer possible values first
        variables = variables.values()
        self._assign_values_state = variables
        return kwargs 
        
    def _next_value(self, kwargs):

        # try to instanciate the next variable
        variables = self._assign_values_state

        for curr in variables:
            assert isinstance(curr, Quadruple)
            w_name = curr.zero
            dom_values = curr.one
            dom_index = curr.two
            dom_len = curr.three
            assert isinstance(w_name, W_StringObject)
            assert isinstance(dom_values, list)
            assert isinstance(dom_index, int)
            assert isinstance(dom_len, int)
            if dom_index < dom_len:
                kwargs.content[w_name] = dom_values[dom_index]
                curr.two = dom_index + 1
                break
            else:
                curr.two = 0
                kwargs.content[w_name] = dom_values[0]
        else:
            # it's over
            raise StopIteration
        return kwargs

    def revise(self):
        """generic propagation algorithm for n-ary expressions"""
        sp = self._space
        maybe_entailed = True
        ffunc = self.filter_func
        result_cache = self._init_result_cache()
        assert isinstance(result_cache, W_DictObject)

        kwargs = self._assign_values()
        assert isinstance(kwargs, W_DictObject)
        while 1:
            try:
                kwargs = self._next_value(kwargs)
                assert isinstance(kwargs, W_DictObject)
            except StopIteration:
                break
            if maybe_entailed:
                for varname, val in kwargs.content.iteritems():
                    val_dict = result_cache.content[varname]
                    assert isinstance(val_dict, W_DictObject)
                    if val not in val_dict.content:
                        break
                else:
                    continue
            if sp.is_true(sp.call(sp.wrap(ffunc),
                                  sp.newlist([]), kwargs)):
                for var, val in kwargs.content.items():
                    var_dict = result_cache.content[var]
                    assert isinstance(var_dict, W_DictObject)
                    var_dict.content[val] = sp.w_True
            else:
                maybe_entailed = False

        try:
            for varname, keep in result_cache.content.items():
                var = self._names_to_vars[sp.str_w(varname)]
                assert isinstance(var, W_Variable)
                assert isinstance(keep, W_DictObject)
                domain = var.w_dom
                assert isinstance(domain, W_AbstractDomain)
                domain.remove_values([val
                                      for val in domain._values.content.keys()
                                      if val not in keep.content])
        except KeyError:
            # There are no more value in result_cache
            pass

        return maybe_entailed
        

    def __repr__(self):
        return '<%s>' % self.formula

W_Expression.typedef = typedef.TypeDef("W_Expression",
    W_AbstractConstraint.typedef,
    revise = interp2app(W_Expression.w_revise))
    


def make_expression(space, w_variables, w_formula):
    """create a new constraint of type Expression or BinaryExpression
    The chosen class depends on the number of variables in the constraint"""
    assert isinstance(w_variables, W_ListObject)
    assert isinstance(w_formula, W_StringObject)
    assert len(w_variables.wrappeditems) > 0
    return W_Expression(space, w_variables, w_formula)
make_expression.unwrap_spec = [baseobjspace.ObjSpace,
                               baseobjspace.W_Root,
                               baseobjspace.W_Root]


class W_AllDistinct(W_AbstractConstraint):
    """Contraint: all values must be distinct"""

    def __init__(self, object_space, w_variables):
        W_AbstractConstraint.__init__(self, object_space, w_variables)
        # worst case complexity
        #self.__cost = len(w_variables.wrappeditems) * (len(w_variables.wrappeditems) - 1) / 2

    def copy(self):
        if we_are_translated():
            raise NotImplementedError
        else:
            newvars = [var.copy(self._space) for var in self._variables]
            const = W_AllDistinct(self._space, self._space.newlist(newvars))
            return const

    def revise(self):
        _spc = self._space

        ord_vars = BTree()
        for var in self._variables:
            assert isinstance(var, W_Variable)
            dom = var.w_dom
            assert isinstance(dom, W_AbstractDomain)
            sz = dom.size()
            ord_vars.add(sz, var)
        variables = ord_vars.values()
        
        # if a domain has a size of 1,
        # then the value must be removed from the other domains
        for var in variables:
            assert isinstance(var, W_Variable)
            dom = var.w_dom
            assert isinstance(dom, W_AbstractDomain)
            if dom.size() == 1:
                #print "AllDistinct removes values"
                for _var in variables:
                    assert isinstance(_var, W_Variable)
                    _dom = _var.w_dom
                    assert isinstance(_dom, W_AbstractDomain)
                    if not _var._same_as(var):
                        try:
                            _dom.remove_value(dom.get_values()[0])
                        except KeyError, e:
                            # we ignore errors caused by the removal of
                            # non existing values
                            pass

        # if there are less values than variables, the constraint fails
        values = {}
        for var in variables:
            assert isinstance(var, W_Variable)
            dom = var.w_dom
            assert isinstance(dom, W_AbstractDomain)
            for val in dom.w_get_values().wrappeditems:
                values[val] = 0

        if len(values) < len(variables):
            #print "AllDistinct failed"
            raise OperationError(_spc.w_RuntimeError,
                                 _spc.wrap("ConsistencyFailure"))

        # the constraint is entailed if all domains have a size of 1
        for var in variables:
            assert isinstance(var, W_Variable)
            dom = var.w_dom
            assert isinstance(dom, W_AbstractDomain)
            if not dom.size() == 1:
                return False

        # Question : did we *really* completely check
        # our own alldistinctness predicate ?
        #print "All distinct entailed"
        return True

W_AllDistinct.typedef = typedef.TypeDef(
    "W_AllDistinct", W_AbstractConstraint.typedef,
    revise = interp2app(W_AllDistinct.w_revise))

#function bolted into the space to serve as constructor
def make_alldistinct(object_space, w_variables):
    assert isinstance(w_variables, W_ListObject)
    assert len(w_variables.wrappeditems) > 0
    return object_space.wrap(W_AllDistinct(object_space, w_variables))
make_alldistinct.unwrap_spec = [baseobjspace.ObjSpace,
                               baseobjspace.W_Root]
