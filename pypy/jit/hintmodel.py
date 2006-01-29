from pypy.annotation import model as annmodel
from pypy.annotation.pairtype import pair, pairtype
from pypy.jit.hintbookkeeper import getbookkeeper
from pypy.rpython.lltypesystem import lltype

UNARY_OPERATIONS = """same_as hint getfield setfield getsubstruct getarraysize getarrayitem setarrayitem
                      cast_pointer
                      direct_call
                      int_is_true int_neg
                      uint_is_true
                      cast_int_to_uint
                      cast_char_to_int
                      cast_bool_to_int""".split()

BINARY_OPERATIONS = """int_add int_sub int_mul int_and int_rshift int_floordiv
                       int_gt int_lt int_le int_ge int_eq int_ne
                       uint_gt uint_lt uint_le uint_ge uint_eq uint_ne""".split()

class OriginTreeNode(object):

    fixed = False

    def __init__(self, origins=None):
        if origins is None:
            origins = {}
        self.origins = origins

    def merge(self, nodes):
        self.origins.update(nodes)

    def visit(self, seen=None):
        if seen is None:
            seen = {}
        yield self
        for o in self.origins:
            if o not in seen:
                seen[o] = True
                for o1 in o.visit(seen):
                    yield o1

    def __repr__(self):
        return "O" + (self.fixed and "f" or "")
                    
class SomeLLAbstractValue(annmodel.SomeObject):

    def __init__(self, T):
        self.concretetype = T
        assert self.__class__ != SomeLLAbstractValue

    def reorigin(self, bookkeeper):
        return self

class SomeLLAbstractConstant(SomeLLAbstractValue):

    def __init__(self, T, origins):
        SomeLLAbstractValue.__init__(self, T)
        self.origins = origins

    def reorigin(self, bookkeeper):
        origin = bookkeeper.myorigin()
        origin.merge(self.origins)
        return SomeLLAbstractConstant(self.concretetype, {origin: True})

class SomeLLConcreteValue(SomeLLAbstractValue):
    pass

class SomeLLAbstractVariable(SomeLLAbstractValue):
    pass

class SomeLLAbstractContainer(SomeLLAbstractValue):

    def __init__(self, contentdef):
        self.contentdef = contentdef
        self.concretetype = lltype.Ptr(contentdef.T)

# ____________________________________________________________
# operations

class __extend__(SomeLLAbstractValue):

    def same_as(hs_v1):
        return hs_v1

class __extend__(SomeLLAbstractConstant):

    def hint(hs_c1, hs_flags):
        if hs_flags.const.get('variable', False): # only for testing purposes!!!
            return SomeLLAbstractVariable(hs_c1.concretetype)
        assert hs_flags.const['concrete']
        for o in hs_c1.origins:
            for o1 in o.visit():
                o1.fixed = True
        return SomeLLConcreteValue(hs_c1.concretetype)

    def getfield(hs_c1, hs_fieldname):
        S = hs_c1.concretetype.TO
        FIELD_TYPE = getattr(S, hs_fieldname.const)
        if S._hints.get('immutable', False):
            origin = getbookkeeper().myorigin()
            origin.merge(hs_c1.origins)
            return SomeLLAbstractConstant(FIELD_TYPE, {origin: True})
        else:
            return SomeLLAbstractVariable(FIELD_TYPE)

    def getarrayitem(hs_c1, hs_index):
        A = hs_c1.concretetype.TO
        READ_TYPE = A.OF
        if A._hints.get('immutable', False):
            origin = getbookkeeper().myorigin()
            origin.merge(hs_c1.origins)
            return SomeLLAbstractConstant(READ_TYPE, {origin: True})
        else:
            return SomeLLAbstractVariable(READ_TYPE)

    def getsubstruct(hs_c1, hs_fieldname):
        S = hs_c1.concretetype.TO
        SUB_TYPE = getattr(S, hs_fieldname.const)
        origin = getbookkeeper().myorigin()
        origin.merge(hs_c1.origins)
        return SomeLLAbstractConstant(lltype.Ptr(SUB_TYPE), {origin: True})

    def getarraysize(hs_c1):
        origin = getbookkeeper().myorigin()
        origin.merge(hs_c1.origins)
        return SomeLLAbstractConstant(lltype.Signed, {origin: True})

    def direct_call(hs_f1, *args_hs):
        bookkeeper = getbookkeeper()
        fnobj = hs_f1.const._obj
        if (getattr(bookkeeper.annotator.policy, 'oopspec', False) and
            hasattr(fnobj._callable, 'oopspec')):
            # try to handle the call as a high-level operation
            try:
                return handle_highlevel_operation(bookkeeper, fnobj._callable,
                                                  *args_hs)
            except NotImplementedError:
                pass
        # normal call
        if not hasattr(fnobj, 'graph'):
            raise NotImplementedError("XXX call to externals or primitives")
        hs_res = bookkeeper.annotator.recursivecall(fnobj.graph,
                                                    bookkeeper.position_key,
                                                    args_hs)
        if isinstance(hs_res, SomeLLAbstractValue):
            hs_res = hs_res.reorigin(bookkeeper)
        #else: it's a SomeImpossibleValue
        return hs_res

    def int_neg(hs_c1):
        origin = getbookkeeper().myorigin()
        origin.merge(hs_c1.origins)
        return SomeLLAbstractConstant(lltype.Signed, {origin: True})

    cast_bool_to_int = cast_char_to_int = int_neg

    def int_is_true(hs_c1):
        origin = getbookkeeper().myorigin()
        origin.merge(hs_c1.origins)
        return SomeLLAbstractConstant(lltype.Bool, {origin: True})

    uint_is_true = int_is_true

class __extend__(SomeLLConcreteValue):

    def cast_int_to_uint(hs_cv1):
        return SomeLLConcreteValue(lltype.Unsigned)

    def int_neg(hs_cv1):
        return SomeLLConcreteValue(lltype.Signed)

    cast_bool_to_int = cast_char_to_int = int_neg

    def int_is_true(hs_cv1):
        return SomeLLConcreteValue(lltype.Bool)

    uint_is_true = int_is_true
    
class __extend__(SomeLLAbstractContainer):

    def setfield(hs_s1, hs_fieldname, hs_value):
        hs_s1.contentdef.generalize_field(hs_fieldname.const, hs_value)

    def getfield(hs_s1, hs_fieldname):
        return hs_s1.contentdef.read_field(hs_fieldname.const)

    getsubstruct = getfield

    def setarrayitem(hs_a1, hs_index, hs_value):
        hs_a1.contentdef.generalize_item(hs_value)

    def getarrayitem(hs_a1, hs_index):
        return hs_a1.contentdef.read_item()

    def getarraysize(hs_a1):
        origin = getbookkeeper().myorigin()
        return SomeLLAbstractConstant(lltype.Signed, {origin: True})

    def cast_pointer(hs_s1):
        TO = getbookkeeper().current_op_concretetype()
        res_vstruct =hs_s1.contentdef.cast(TO)
        return SomeLLAbstractContainer(res_vstruct)

# ____________________________________________________________
# binary

class __extend__(pairtype(SomeLLAbstractValue, SomeLLAbstractValue)):

    def int_add((hs_v1, hs_v2)):
        return SomeLLAbstractVariable(lltype.Signed)

    def union((hs_v1, hs_v2)):
        raise annmodel.UnionError("%s %s don't mix" % (hs_v1, hs_v2))

class __extend__(pairtype(SomeLLAbstractVariable, SomeLLAbstractConstant),
                 pairtype(SomeLLAbstractConstant, SomeLLAbstractVariable)):

    def union((hs_v1, hs_v2)):
        assert hs_v1.concretetype == hs_v2.concretetype
        return SomeLLAbstractVariable(hs_v1.concretetype)

class __extend__(pairtype(SomeLLAbstractConstant, SomeLLAbstractConstant)):

    def int_add((hs_c1, hs_c2)):
        origin = getbookkeeper().myorigin()
        origin.merge(hs_c1.origins)
        origin.merge(hs_c2.origins)
        return SomeLLAbstractConstant(lltype.Signed, {origin: True})

    int_floordiv = int_rshift = int_and = int_mul = int_sub = int_add

    def int_eq((hs_c1, hs_c2)):
        origin = getbookkeeper().myorigin()
        origin.merge(hs_c1.origins)
        origin.merge(hs_c2.origins)
        return SomeLLAbstractConstant(lltype.Bool, {origin: True})

    int_lt = int_le = int_ge = int_ne = int_gt = int_eq
    uint_lt = uint_le = uint_ge = uint_ne = uint_gt = uint_eq = int_eq

    def union((hs_c1, hs_c2)):
        assert hs_c1.concretetype == hs_c2.concretetype
        origins = annmodel.setunion(hs_c1.origins, hs_c2.origins)
        return SomeLLAbstractConstant(hs_c1.concretetype, origins)

class __extend__(pairtype(SomeLLAbstractConstant, SomeLLConcreteValue),
                 pairtype(SomeLLConcreteValue, SomeLLAbstractConstant),
                 pairtype(SomeLLConcreteValue, SomeLLConcreteValue)):

    def int_add((hs_c1, hs_c2)):
        return SomeLLConcreteValue(lltype.Signed)

    int_floordiv = int_rshift = int_and = int_mul = int_sub = int_add

    def int_eq((hs_c1, hs_c2)):
        return SomeLLConcreteValue(lltype.Bool)

    int_lt = int_le = int_ge = int_ne = int_gt = int_eq
    uint_lt = uint_le = uint_ge = uint_ne = uint_gt = uint_eq = int_eq

class __extend__(pairtype(SomeLLAbstractContainer, SomeLLAbstractContainer)):

    def union((hs_cont1, hs_cont2)):
        return SomeLLAbstractContainer(hs_cont1.contentdef.union(hs_cont2.contentdef))

# ____________________________________________________________

def handle_highlevel_operation(bookkeeper, ll_func, *args_hs):
    # parse the oopspec and fill in the arguments
    operation_name, args = ll_func.oopspec.split('(', 1)
    assert args.endswith(')')
    args = args[:-1] + ','     # trailing comma to force tuple syntax
    argnames = ll_func.func_code.co_varnames[:len(args_hs)]
    d = dict(zip(argnames, args_hs))
    argtuple = eval(args, d)
    args_hs = []
    for hs in argtuple:
        if not isinstance(hs, SomeLLAbstractValue):
            hs = bookkeeper.immutablevalue(hs)
        args_hs.append(hs)
    # end of rather XXX'edly hackish parsing

    if operation_name == 'newlist':
        from pypy.jit.hintvlist import oop_newlist
        handler = oop_newlist
    else:
        # dispatch on the 'self' argument if it is virtual
        hs_self = args_hs[0]
        args_hs = args_hs[1:]
        type_name, operation_name = operation_name.split('.')
        if not isinstance(hs_self, SomeLLAbstractContainer):
            raise NotImplementedError
        if getattr(hs_self.contentdef, 'type_name', None) != type_name:
            raise NotImplementedError
        try:
            handler = getattr(hs_self.contentdef, 'oop_' + operation_name)
        except AttributeError:
            bookkeeper.warning('missing handler: oop_%s' % (operation_name,))
            raise NotImplementedError

    hs_result = handler(*args_hs)   # which may raise NotImplementedError
    return hs_result
