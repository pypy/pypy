from pypy.annotation import model as annmodel
from pypy.annotation.pairtype import pair, pairtype
from pypy.jit.hintannotator.bookkeeper import getbookkeeper
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
                       char_gt char_lt char_le char_ge char_eq char_ne
                       int_gt int_lt int_le int_ge int_eq int_ne
                       uint_gt uint_lt uint_le uint_ge uint_eq uint_ne
                       getarrayitem""".split()

class HintError(Exception):
    pass

class OriginFlags(object):

    fixed = False
    read_positions = None

    def __repr__(self):
        if self.fixed:
            s = "fixed "
        else:
            s = ""
        return "<%sorigin>" % (s,)

    def read_fixed(self):
        if self.read_positions is None:
            self.read_positions = {}
        self.read_positions[getbookkeeper().position_key] = True
        return self.fixed

    def set_fixed(self):
        if not self.fixed:
            self.fixed = True
            if self.read_positions:
                annotator = getbookkeeper().annotator
                for p in self.read_positions:
                    annotator.reflowfromposition(p)

class SomeLLAbstractValue(annmodel.SomeObject):

    def __init__(self, T):
        self.concretetype = T
        assert self.__class__ != SomeLLAbstractValue

class SomeLLAbstractConstant(SomeLLAbstractValue):

    def __init__(self, T, origins, eager_concrete=False):
        SomeLLAbstractValue.__init__(self, T)
        self.origins = origins
        self.eager_concrete = eager_concrete

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

    def is_fixed(self):
        for o in self.origins:
            if not o.fixed:
                return False
        return True

    def annotationcolor(self):
        """Compute the color of the variables with this annotation
        for the pygame viewer
        """
        if self.eager_concrete:
            return (0,100,0)     # green
        elif self.is_fixed():
            return (50,140,0)    # green-dark-cyan
        else:
            return None
    annotationcolor = property(annotationcolor)

class SomeLLAbstractVariable(SomeLLAbstractValue):
    pass

class SomeLLAbstractContainer(SomeLLAbstractValue):

    def __init__(self, contentdef):
        self.contentdef = contentdef
        self.concretetype = lltype.Ptr(contentdef.T)

    def annotationcolor(self):
        """Compute the color of the variables with this annotation
        for the pygame viewer
        """
        if getattr(self.contentdef, 'degenerated', False):
            return None
        else:
            return (0,60,160)  # blue
    annotationcolor = property(annotationcolor)


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
        return SomeLLAbstractConstant(hs_v1.concretetype, d, eager_concrete=hs_v1.eager_concrete)
    else:
        return hs_v1

# ____________________________________________________________
# operations

class __extend__(SomeLLAbstractValue):

    def define_unary(TYPE):
        def var_unary(hs_v):
            return SomeLLAbstractVariable(TYPE)
        return var_unary

    int_neg = define_unary(lltype.Signed)
    uint_is_true = int_is_true = define_unary(lltype.Bool)

    def same_as(hs_v1):
        return hs_v1

    def hint(hs_v1, hs_flags):
        if hs_flags.const.get('variable', False): # only for testing purposes!!!
            return SomeLLAbstractVariable(hs_c1.concretetype)
        if hs_flags.const.get('concrete', False):
            raise HintError("cannot make a concrete from %r" % (hs_v1,))
        if hs_flags.const.get('forget', False):
            XXX    # not implemented

    def getfield(hs_v1, hs_fieldname):
        S = hs_v1.concretetype.TO
        FIELD_TYPE = getattr(S, hs_fieldname.const)
        return SomeLLAbstractVariable(FIELD_TYPE)

    def setfield(hs_v1, hs_fieldname, hs_value):
        pass

    def getsubstruct(hs_v1, hs_fieldname):
        S = hs_v1.concretetype.TO
        FIELD_TYPE = getattr(S, hs_fieldname.const)
        return SomeLLAbstractVariable(lltype.Ptr(FIELD_TYPE))

class __extend__(SomeLLAbstractConstant):

    def hint(hs_c1, hs_flags):
        if hs_flags.const.get('variable', False): # only for testing purposes!!!
            return SomeLLAbstractVariable(hs_c1.concretetype)
        if hs_flags.const.get('concrete', False):
            for o in hs_c1.origins:
                o.set_fixed()
            hs_concrete = reorigin(hs_c1)
            hs_concrete.eager_concrete = True
            return hs_concrete 
        if hs_flags.const.get('forget', False):
            assert isinstance(hs_c1, SomeLLAbstractConstant)
            return reorigin(hs_c1)

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
        desc = bookkeeper.getdesc(fnobj.graph)
        key = None
        alt_name = None
        if bookkeeper.myorigin().read_fixed():
            key = 'fixed'
            alt_name = fnobj.graph.name + '_HFixed'
        else:
            key = []
            specialize = False
            for i, arg_hs in enumerate(args_hs):
                if isinstance(arg_hs, SomeLLAbstractConstant) and arg_hs.eager_concrete:
                    key.append('E')
                    specialize = True
                else:
                    key.append('x')
            if specialize:
                key = ''.join(key)
                alt_name = fnobj.graph.name + '_H'+key
            else:
                key = None
                                    
        input_args_hs = list(args_hs)
        graph = desc.specialize(input_args_hs, key=key, alt_name=alt_name)

        # propagate fixing of arguments in the function to the caller
        for inp_arg_hs, arg_hs in zip(input_args_hs, args_hs):
            if isinstance(arg_hs, SomeLLAbstractConstant):
                assert len(inp_arg_hs.origins) == 1
                [o] = inp_arg_hs.origins.keys()
                if o.read_fixed():
                    for o in arg_hs.origins:
                        o.set_fixed()
        
        hs_res = bookkeeper.annotator.recursivecall(graph,
                                                    bookkeeper.position_key,
                                                    input_args_hs)
        # look on which input args the hs_res result depends on
        if isinstance(hs_res, SomeLLAbstractConstant):
            deps_hs = []
            for hs_inputarg, hs_arg in zip(input_args_hs, args_hs):
                if isinstance(hs_inputarg, SomeLLAbstractConstant):
                    assert len(hs_inputarg.origins) == 1
                    [o] = hs_inputarg.origins.keys()
                    if o in hs_res.origins:
                        deps_hs.append(hs_arg)
            if key == 'fixed':
                deps_hs.append(hs_res)
            hs_res = reorigin(hs_res, *deps_hs)

        # we need to make sure that hs_res does not become temporarily less
        # general as a result of calling another specialized version of the
        # function
        return annmodel.unionof(hs_res, bookkeeper.current_op_binding())

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

    def define_unary(TYPE):
        def const_unary(hs_c1):
            d = setadd(hs_c1.origins, getbookkeeper().myorigin())
            return SomeLLAbstractConstant(TYPE, d, eager_concrete=hs_c1.eager_concrete)
        return const_unary

    cast_int_to_char = define_unary(lltype.Char)
    
    cast_uint_to_int = cast_bool_to_int = cast_char_to_int = int_neg = define_unary(lltype.Signed)

    cast_int_to_uint = define_unary(lltype.Unsigned)

    uint_is_true = int_is_true = define_unary(lltype.Bool)
    
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

    def define_binary(TYPE):
        def var_binary((hs_v1, hs_v2)):
            return SomeLLAbstractVariable(TYPE)
        return var_binary

    int_mul = int_mod = int_sub = int_add = define_binary(lltype.Signed)
    int_floordiv = int_rshift = int_and = int_add 

    uint_mul = uint_mod = uint_sub = uint_add = define_binary(lltype.Unsigned)
    uint_floordiv = uint_rshift = uint_and = uint_add

    int_lt = int_le = int_ge = int_ne = int_gt = int_eq = define_binary(lltype.Bool)
    uint_lt = uint_le = uint_ge = uint_ne = uint_gt = uint_eq = int_eq

    char_gt = char_lt = char_le = char_ge = char_eq = char_ne = int_eq

    def getarrayitem((hs_v1, hs_v2)):
        return SomeLLAbstractVariable(hs_v1.concretetype.TO.OF)

    def union((hs_v1, hs_v2)):
        raise annmodel.UnionError("%s %s don't mix" % (hs_v1, hs_v2))

class __extend__(pairtype(SomeLLAbstractVariable, SomeLLAbstractConstant),
                 pairtype(SomeLLAbstractConstant, SomeLLAbstractVariable)):

    def union((hs_v1, hs_v2)):
        assert hs_v1.concretetype == hs_v2.concretetype
        if getattr(hs_v1, 'eager_concrete', False) or getattr(hs_v2, 'eager_concrete', False):
            raise annmodel.UnionError("%s %s don't mix" % (hs_v1, hs_v2))
        return SomeLLAbstractVariable(hs_v1.concretetype)

class __extend__(pairtype(SomeLLAbstractConstant, SomeLLAbstractConstant)):

    def define_binary(TYPE):
        def const_binary((hs_c1, hs_c2)):
            d = newset(hs_c1.origins, hs_c2.origins,
                       {getbookkeeper().myorigin(): True})
            return SomeLLAbstractConstant(TYPE, d, eager_concrete= hs_c1.eager_concrete or hs_c2.eager_concrete)
        return const_binary
            
    int_mul = int_mod = int_sub = int_add = define_binary(lltype.Signed)
    int_floordiv = int_rshift = int_and = int_add 

    uint_mul = uint_mod = uint_sub = uint_add = define_binary(lltype.Unsigned)
    uint_floordiv = uint_rshift = uint_and = uint_add

    int_lt = int_le = int_ge = int_ne = int_gt = int_eq = define_binary(lltype.Bool)
    uint_lt = uint_le = uint_ge = uint_ne = uint_gt = uint_eq = int_eq

    char_gt = char_lt = char_le = char_ge = char_eq = char_ne = int_eq

    def union((hs_c1, hs_c2)):
        assert hs_c1.concretetype == hs_c2.concretetype
        d = newset(hs_c1.origins, hs_c2.origins)
        return SomeLLAbstractConstant(hs_c1.concretetype, d, eager_concrete=hs_c1.eager_concrete and hs_c2.eager_concrete)

    def getarrayitem((hs_c1, hs_index)):
        A = hs_c1.concretetype.TO
        READ_TYPE = A.OF
        if A._hints.get('immutable', False):
            d = newset(hs_c1.origins, hs_index.origins,
                       {getbookkeeper().myorigin(): True})
            return SomeLLAbstractConstant(READ_TYPE, d, eager_concrete=hs_c1.eager_concrete)
        else:
            return SomeLLAbstractVariable(READ_TYPE)

class __extend__(pairtype(SomeLLAbstractContainer, SomeLLAbstractContainer)):

    def union((hs_cont1, hs_cont2)):
        contentdef = hs_cont1.contentdef.union(hs_cont2.contentdef)
        return SomeLLAbstractContainer(contentdef)

class __extend__(pairtype(SomeLLAbstractContainer, SomeLLAbstractValue)):
    def union((hs_cont1, hs_val2)):
        hs_cont1.contentdef.mark_degenerated()
        assert hs_cont1.concretetype == hs_val2.concretetype
        return SomeLLAbstractVariable(hs_cont1.concretetype)

class __extend__(pairtype(SomeLLAbstractValue, SomeLLAbstractContainer)):
    def union((hs_val1, hs_cont2)):
        return pair(hs_cont2, hs_val1).union()

class __extend__(pairtype(SomeLLAbstractContainer, SomeLLAbstractConstant)):

    def getarrayitem((hs_a1, hs_index)):
        hs_res = hs_a1.contentdef.read_item()
        return reorigin(hs_res, hs_res, hs_index)


# ____________________________________________________________

def handle_highlevel_operation(bookkeeper, ll_func, *args_hs):
    if getattr(bookkeeper.annotator.policy, 'novirtualcontainer', False):
        # "blue variables" disabled, we just return a red var all the time.
        RESULT = bookkeeper.current_op_concretetype()
        if RESULT is lltype.Void:
            return None
        else:
            return SomeLLAbstractVariable(RESULT)

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
        from pypy.jit.hintannotator.vlist import oop_newlist
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
