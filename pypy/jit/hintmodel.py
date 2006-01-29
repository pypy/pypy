from pypy.annotation import model as annmodel
from pypy.annotation.pairtype import pair, pairtype
from pypy.jit.hintbookkeeper import getbookkeeper
from pypy.rpython.lltypesystem import lltype

UNARY_OPERATIONS = """same_as hint getfield setfield getsubstruct getarraysize getarrayitem setarrayitem
                      cast_pointer
                      direct_call
                      int_is_true int_neg
                      cast_char_to_int
                      cast_bool_to_int""".split()

BINARY_OPERATIONS = """int_add int_sub int_mul int_and int_rshift int_floordiv
                       int_gt int_lt int_le int_ge int_eq int_ne""".split()

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
        graph = hs_f1.const._obj.graph
        hs_res = bookkeeper.annotator.recursivecall(graph, bookkeeper.position_key, args_hs)
        if isinstance(hs_res, SomeLLAbstractValue):
            return hs_res.reorigin(bookkeeper)
        else:
            return hs_res # impossible value

    def int_neg(hs_c1):
        origin = getbookkeeper().myorigin()
        origin.merge(hs_c1.origins)
        return SomeLLAbstractConstant(lltype.Signed, {origin: True})

    cast_bool_to_int = cast_char_to_int = int_neg

    def int_is_true(hs_c1):
        origin = getbookkeeper().myorigin()
        origin.merge(hs_c1.origins)
        return SomeLLAbstractConstant(lltype.Bool, {origin: True})
    
        
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

    def int_gt((hs_c1, hs_c2)):
        origin = getbookkeeper().myorigin()
        origin.merge(hs_c1.origins)
        origin.merge(hs_c2.origins)
        return SomeLLAbstractConstant(lltype.Bool, {origin: True})

    int_lt = int_le = int_ge = int_eq = int_ne = int_gt

    def union((hs_c1, hs_c2)):
        assert hs_c1.concretetype == hs_c2.concretetype
        origins = annmodel.setunion(hs_c1.origins, hs_c2.origins)
        return SomeLLAbstractConstant(hs_c1.concretetype, origins)

class __extend__(pairtype(SomeLLAbstractConstant, SomeLLConcreteValue),
                 pairtype(SomeLLConcreteValue, SomeLLAbstractConstant),
                 pairtype(SomeLLConcreteValue, SomeLLConcreteValue)):

    def int_add((hs_c1, hs_c2)):
        return SomeLLConcreteValue(lltype.Signed)

    def int_eq((hs_c1, hs_c2)):
        return SomeLLConcreteValue(lltype.Bool)

class __extend__(pairtype(SomeLLAbstractContainer, SomeLLAbstractContainer)):

    def union((hs_cont1, hs_cont2)):
        return SomeLLAbstractContainer(hs_cont1.contentdef.union(hs_cont2.contentdef))
