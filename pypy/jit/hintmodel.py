from pypy.annotation import model as annmodel
from pypy.annotation.pairtype import pair, pairtype
from pypy.jit.hintbookkeeper import getbookkeeper
from pypy.rpython.lltypesystem import lltype

UNARY_OPERATIONS = """same_as hint getfield setfield getsubstruct getarraysize setarrayitem
                      cast_pointer
                      direct_call
                      int_is_true int_neg
                      uint_is_true
                      cast_int_to_char
                      cast_int_to_uint
                      cast_uint_to_int
                      cast_char_to_int
                      cast_bool_to_int""".split()

BINARY_OPERATIONS = """int_add int_sub int_mul int_mod int_and int_rshift int_floordiv
                       uint_add uint_sub uint_mul uint_mod uint_and uint_rshift uint_floordiv
                       int_gt int_lt int_le int_ge int_eq int_ne
                       uint_gt uint_lt uint_le uint_ge uint_eq uint_ne
                       getarrayitem""".split()

class OriginFlags(object):

    fixed = False

    def __repr__(self):
        if self.fixed:
            s = "fixed "
        else:
            s = ""
        return "<%sorigin>" % (s,)

class SomeLLAbstractValue(annmodel.SomeObject):

    def __init__(self, T):
        self.concretetype = T
        assert self.__class__ != SomeLLAbstractValue

class SomeLLAbstractConstant(SomeLLAbstractValue):

    def __init__(self, T, origins):
        SomeLLAbstractValue.__init__(self, T)
        self.origins = origins

    def fmt_origins(self, origins):
        counts = {}
        for o in origins:
            x = repr(o)
            counts[x] = counts.get(x, 0) + 1
        items = counts.items()
        items.sort()
        lst = []
        for key, count in items:
            s = ''
            if count > 1:
                s += '%d*' % count
            s += key
            lst.append(s)
        return '<%s>' % (', '.join(lst),)

    def annotationcolor(self):
        """Compute the color of the variables with this annotation
        for the pygame viewer
        """
        for o in self.origins:
            if not o.fixed:
                return None
        return (50,140,0)
    annotationcolor = property(annotationcolor)

class SomeLLConcreteValue(SomeLLAbstractValue):
    annotationcolor = (0,100,0)

class SomeLLAbstractVariable(SomeLLAbstractValue):
    pass

class SomeLLAbstractContainer(SomeLLAbstractValue):
    annotationcolor = (0,60,160)

    def __init__(self, contentdef):
        self.contentdef = contentdef
        self.concretetype = lltype.Ptr(contentdef.T)


setunion = annmodel.setunion

def setadd(set, newitem):
    if newitem not in set:
        set = set.copy()
        set[newitem] = True
    return set

def newset(set, *sets):
    set = set.copy()
    for s2 in sets:
        set.update(s2)
    return set

def reorigin(hs_v1, *deps_hs):
    """Make a copy of hs_v1 with its origins removed and replaced by myorigin().
    Optionally, the origins of other annotations can also be added.
    """
    if isinstance(hs_v1, SomeLLAbstractConstant):
        deps_origins = [hs_dep.origins for hs_dep in deps_hs
                        if isinstance(hs_dep, SomeLLAbstractConstant)]
        d = newset({getbookkeeper().myorigin(): True},
                   *deps_origins)
        return SomeLLAbstractConstant(hs_v1.concretetype, d)
    else:
        return hs_v1

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
            o.fixed = True
        return SomeLLConcreteValue(hs_c1.concretetype)

    def getfield(hs_c1, hs_fieldname):
        S = hs_c1.concretetype.TO
        FIELD_TYPE = getattr(S, hs_fieldname.const)
        if S._hints.get('immutable', False):
            d = setadd(hs_c1.origins, getbookkeeper().myorigin())
            return SomeLLAbstractConstant(FIELD_TYPE, d)
        else:
            return SomeLLAbstractVariable(FIELD_TYPE)

    def getsubstruct(hs_c1, hs_fieldname):
        S = hs_c1.concretetype.TO
        SUB_TYPE = getattr(S, hs_fieldname.const)
        d = setadd(hs_c1.origins, getbookkeeper().myorigin())
        return SomeLLAbstractConstant(lltype.Ptr(SUB_TYPE), d)

    def getarraysize(hs_c1):
        d = setadd(hs_c1.origins, getbookkeeper().myorigin())
        return SomeLLAbstractConstant(lltype.Signed, d)

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
        # don't try to annotate suggested_primitive graphs
        if getattr(getattr(fnobj, '_callable', None), 'suggested_primitive', False):
            return SomeLLAbstractVariable(lltype.typeOf(fnobj).RESULT)
        # normal call
        if not hasattr(fnobj, 'graph'):
            raise NotImplementedError("XXX call to externals or primitives")
        hs_res = bookkeeper.annotator.recursivecall(fnobj.graph,
                                                    bookkeeper.position_key,
                                                    args_hs)
        # for now, keep the origins of 'hs_res' in the new result:
        return reorigin(hs_res, hs_res)

    def unary_char(hs_c1):
        d = setadd(hs_c1.origins, getbookkeeper().myorigin())
        return SomeLLAbstractConstant(lltype.Char, d)

    cast_int_to_char = unary_char
    
    def unary_int(hs_c1):
        d = setadd(hs_c1.origins, getbookkeeper().myorigin())
        return SomeLLAbstractConstant(lltype.Signed, d)

    cast_uint_to_int = cast_bool_to_int = cast_char_to_int = int_neg = unary_int

    def int_is_true(hs_c1):
        d = setadd(hs_c1.origins, getbookkeeper().myorigin())
        return SomeLLAbstractConstant(lltype.Bool, d)

    uint_is_true = int_is_true

class __extend__(SomeLLConcreteValue):

    def cast_int_to_uint(hs_cv1):
        return SomeLLConcreteValue(lltype.Unsigned)

    def unary_int(hs_cv1):
        return SomeLLConcreteValue(lltype.Signed)

    cast_uint_to_int = cast_bool_to_int = cast_char_to_int = int_neg = unary_int

    def unary_char(hs_c1):
        return SomeLLConcreteValue(lltype.Char)

    cast_int_to_char = unary_char
 
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

    def getarrayitem((hs_v1, hs_v2)):
        return SomeLLAbstractVariable(hs_v1.concretetype.TO.OF)

    def union((hs_v1, hs_v2)):
        raise annmodel.UnionError("%s %s don't mix" % (hs_v1, hs_v2))

class __extend__(pairtype(SomeLLAbstractVariable, SomeLLAbstractConstant),
                 pairtype(SomeLLAbstractConstant, SomeLLAbstractVariable)):

    def union((hs_v1, hs_v2)):
        assert hs_v1.concretetype == hs_v2.concretetype
        return SomeLLAbstractVariable(hs_v1.concretetype)

class __extend__(pairtype(SomeLLAbstractConstant, SomeLLAbstractConstant)):

    def int_add((hs_c1, hs_c2)):
        d = newset(hs_c1.origins, hs_c2.origins,
                   {getbookkeeper().myorigin(): True})
        return SomeLLAbstractConstant(lltype.Signed, d)

    int_floordiv = int_rshift = int_and = int_mul = int_mod = int_sub = int_add

    def uint_add((hs_c1, hs_c2)):
        d = newset(hs_c1.origins, hs_c2.origins,
                   {getbookkeeper().myorigin(): True})
        return SomeLLAbstractConstant(lltype.Unsigned, d)
    
    uint_floordiv = uint_rshift = uint_and = uint_mul = uint_mod = uint_sub = uint_add

    def int_eq((hs_c1, hs_c2)):
        d = newset(hs_c1.origins, hs_c2.origins,
                   {getbookkeeper().myorigin(): True})
        return SomeLLAbstractConstant(lltype.Bool, d)

    int_lt = int_le = int_ge = int_ne = int_gt = int_eq
    uint_lt = uint_le = uint_ge = uint_ne = uint_gt = uint_eq = int_eq

    def union((hs_c1, hs_c2)):
        assert hs_c1.concretetype == hs_c2.concretetype
        d = newset(hs_c1.origins, hs_c2.origins)
        return SomeLLAbstractConstant(hs_c1.concretetype, d)

    def getarrayitem((hs_c1, hs_index)):
        A = hs_c1.concretetype.TO
        READ_TYPE = A.OF
        if A._hints.get('immutable', False):
            d = newset(hs_c1.origins, hs_index.origins,
                       {getbookkeeper().myorigin(): True})
            return SomeLLAbstractConstant(READ_TYPE, d)
        else:
            return SomeLLAbstractVariable(READ_TYPE)

class __extend__(pairtype(SomeLLAbstractConstant, SomeLLConcreteValue),
                 pairtype(SomeLLConcreteValue, SomeLLAbstractConstant),
                 pairtype(SomeLLConcreteValue, SomeLLConcreteValue)):

    def int_add((hs_c1, hs_c2)):
        return SomeLLConcreteValue(lltype.Signed)

    int_floordiv = int_rshift = int_and = int_mul = int_mod = int_sub = int_add

    def uint_add((hs_c1, hs_c2)):
        return SomeLLConcreteValue(lltype.Unsigned)

    uint_floordiv = uint_rshift = uint_and = uint_mul = uint_mod = uint_sub = uint_add

    def int_eq((hs_c1, hs_c2)):
        return SomeLLConcreteValue(lltype.Bool)

    int_lt = int_le = int_ge = int_ne = int_gt = int_eq
    uint_lt = uint_le = uint_ge = uint_ne = uint_gt = uint_eq = int_eq

    def getarrayitem((hs_c1, hs_index)):
        return SomeLLConcreteValue(hs_c1.concretetype.TO.OF)

class __extend__(pairtype(SomeLLConcreteValue, SomeLLAbstractConstant),
                 pairtype(SomeLLAbstractConstant, SomeLLConcreteValue)):

    def union((hs_c1, hs_c2)):
        assert hs_c1.concretetype == hs_c2.concretetype
        #if hasattr(hs_c1, 'const') or hasattr(hs_c2, 'const'):
        return SomeLLConcreteValue(hs_c1.concretetype) # MAYBE
        #else:
        #    raise annmodel.UnionError("%s %s don't mix, unless the constant is constant" % (hs_c1, hs_c2))

class __extend__(pairtype(SomeLLAbstractContainer, SomeLLAbstractContainer)):

    def union((hs_cont1, hs_cont2)):
        return SomeLLAbstractContainer(hs_cont1.contentdef.union(hs_cont2.contentdef))

class __extend__(pairtype(SomeLLAbstractContainer, SomeLLAbstractConstant)):

    def getarrayitem((hs_a1, hs_index)):
        hs_res = hs_a1.contentdef.read_item()
        return reorigin(hs_res, hs_index)


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
