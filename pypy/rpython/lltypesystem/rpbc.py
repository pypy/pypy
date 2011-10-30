import types
import sys
from pypy.tool.pairtype import pairtype, pair
from pypy.annotation import model as annmodel
from pypy.annotation import description
from pypy.objspace.flow.model import Constant, Variable
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Void, ForwardReference, Struct, Bool, Char, \
     Ptr, malloc, nullptr, Array, Signed, FuncType
from pypy.rpython.rmodel import Repr, TyperError, inputconst, inputdesc
from pypy.rpython.rpbc import samesig,\
     commonbase, allattributenames, adjust_shape, \
     AbstractClassesPBCRepr, AbstractMethodsPBCRepr, OverriddenFunctionPBCRepr, \
     AbstractMultipleFrozenPBCRepr, MethodOfFrozenPBCRepr, \
     AbstractFunctionsPBCRepr, AbstractMultipleUnrelatedFrozenPBCRepr, \
     SingleFrozenPBCRepr, none_frozen_pbc_repr, get_concrete_calltable
from pypy.rpython.lltypesystem import rclass, llmemory
from pypy.tool.sourcetools import has_varargs
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.debug import ll_assert

from pypy.rpython import callparse

def rtype_is_None(robj1, rnone2, hop, pos=0):
    if isinstance(robj1.lowleveltype, Ptr):
        v1 = hop.inputarg(robj1, pos)
        return hop.genop('ptr_iszero', [v1], resulttype=Bool)
    elif robj1.lowleveltype == llmemory.Address:
        v1 = hop.inputarg(robj1, pos)
        cnull = hop.inputconst(llmemory.Address, robj1.null_instance())
        return hop.genop('adr_eq', [v1, cnull], resulttype=Bool)
    elif robj1 == none_frozen_pbc_repr:
        return hop.inputconst(Bool, True)
    elif isinstance(robj1, SmallFunctionSetPBCRepr):
        if robj1.s_pbc.can_be_None:
            v1 = hop.inputarg(robj1, pos)
            return hop.genop('char_eq', [v1, inputconst(Char, '\000')],
                             resulttype=Bool)
        else:
            return inputconst(Bool, False)
    else:
        raise TyperError('rtype_is_None of %r' % (robj1))

# ____________________________________________________________

class MultipleFrozenPBCRepr(AbstractMultipleFrozenPBCRepr):
    """Representation selected for multiple non-callable pre-built constants."""
    def __init__(self, rtyper, access_set):
        self.rtyper = rtyper
        self.access_set = access_set
        self.pbc_type = ForwardReference()
        self.lowleveltype = Ptr(self.pbc_type)
        self.pbc_cache = {}

    def _setup_repr(self):
        llfields = self._setup_repr_fields()
        kwds = {'hints': {'immutable': True}}
        self.pbc_type.become(Struct('pbc', *llfields, **kwds))

    def create_instance(self):
        return malloc(self.pbc_type, immortal=True)

    def null_instance(self):
        return nullptr(self.pbc_type)

    def getfield(self, vpbc, attr, llops):
        mangled_name, r_value = self.fieldmap[attr]
        cmangledname = inputconst(Void, mangled_name)
        return llops.genop('getfield', [vpbc, cmangledname],
                           resulttype = r_value)


class MultipleUnrelatedFrozenPBCRepr(AbstractMultipleUnrelatedFrozenPBCRepr):
    """Representation selected for multiple non-callable pre-built constants
    with no common access set."""

    lowleveltype = llmemory.Address
    EMPTY = Struct('pbc', hints={'immutable': True})

    def convert_pbc(self, pbcptr):
        return llmemory.fakeaddress(pbcptr)

    def create_instance(self):
        return malloc(self.EMPTY, immortal=True)

    def null_instance(self):
        return llmemory.Address._defl()

class __extend__(pairtype(MultipleUnrelatedFrozenPBCRepr,
                          MultipleUnrelatedFrozenPBCRepr),
                 pairtype(MultipleUnrelatedFrozenPBCRepr,
                          SingleFrozenPBCRepr),
                 pairtype(SingleFrozenPBCRepr,
                          MultipleUnrelatedFrozenPBCRepr)):
    def rtype_is_((robj1, robj2), hop):
        if isinstance(robj1, MultipleUnrelatedFrozenPBCRepr):
            r = robj1
        else:
            r = robj2
        vlist = hop.inputargs(r, r)
        return hop.genop('adr_eq', vlist, resulttype=Bool)

class __extend__(pairtype(MultipleFrozenPBCRepr,
                          MultipleUnrelatedFrozenPBCRepr)):
    def convert_from_to((robj1, robj2), v, llops):
        return llops.genop('cast_ptr_to_adr', [v], resulttype=llmemory.Address)

# ____________________________________________________________

class FunctionsPBCRepr(AbstractFunctionsPBCRepr):
    """Representation selected for a PBC of function(s)."""

    def setup_specfunc(self):
        fields = []
        for row in self.uniquerows:
            fields.append((row.attrname, row.fntype))
        kwds = {'hints': {'immutable': True}}
        return Ptr(Struct('specfunc', *fields, **kwds))
        
    def create_specfunc(self):
        return malloc(self.lowleveltype.TO, immortal=True)

    def get_specfunc_row(self, llop, v, c_rowname, resulttype):
        return llop.genop('getfield', [v, c_rowname], resulttype=resulttype)

class SmallFunctionSetPBCRepr(Repr):
    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        self.callfamily = s_pbc.any_description().getcallfamily()
        concretetable, uniquerows = get_concrete_calltable(self.rtyper,
                                                           self.callfamily)
        assert len(uniquerows) == 1
        self.lowleveltype = Char
        self.pointer_repr = FunctionsPBCRepr(rtyper, s_pbc)
        self._conversion_tables = {}
        self._compression_function = None
        self._dispatch_cache = {}

    def _setup_repr(self):
        if self.s_pbc.subset_of:
            assert self.s_pbc.can_be_None == self.s_pbc.subset_of.can_be_None
            r = self.rtyper.getrepr(self.s_pbc.subset_of)
            if r is not self:
                r.setup()
                self.descriptions = r.descriptions
                self.c_pointer_table = r.c_pointer_table
                return
        self.descriptions = list(self.s_pbc.descriptions)
        if self.s_pbc.can_be_None:
            self.descriptions.insert(0, None)
        POINTER_TABLE = Array(self.pointer_repr.lowleveltype,
                              hints={'nolength': True})
        pointer_table = malloc(POINTER_TABLE, len(self.descriptions),
                               immortal=True)
        for i, desc in enumerate(self.descriptions):
            if desc is not None:
                pointer_table[i] = self.pointer_repr.convert_desc(desc)
            else:
                pointer_table[i] = self.pointer_repr.convert_const(None)
        self.c_pointer_table = inputconst(Ptr(POINTER_TABLE), pointer_table)

    def get_s_callable(self):
        return self.s_pbc

    def get_r_implfunc(self):
        return self, 0

    def get_s_signatures(self, shape):
        funcdesc = self.s_pbc.any_description()
        return funcdesc.get_s_signatures(shape)

    def convert_desc(self, funcdesc):
        return chr(self.descriptions.index(funcdesc))

    def convert_const(self, value):
        if isinstance(value, types.MethodType) and value.im_self is None:
            value = value.im_func   # unbound method -> bare function
        if value is None:
            return chr(0)
        funcdesc = self.rtyper.annotator.bookkeeper.getdesc(value)
        return self.convert_desc(funcdesc)

##     def convert_to_concrete_llfn(self, v, shape, index, llop):
##         return v

    def rtype_simple_call(self, hop):
        return self.call('simple_call', hop)

    def rtype_call_args(self, hop):
        return self.call('call_args', hop)

    def dispatcher(self, shape, index, argtypes, resulttype):
        key = shape, index, tuple(argtypes), resulttype
        if key in self._dispatch_cache:
            return self._dispatch_cache[key]
        from pypy.translator.unsimplify import varoftype
        from pypy.objspace.flow.model import FunctionGraph, Link, Block, SpaceOperation
        inputargs = [varoftype(t) for t in [Char] + argtypes]
        startblock = Block(inputargs)
        startblock.exitswitch = inputargs[0]
        graph = FunctionGraph("dispatcher", startblock, varoftype(resulttype))
        row_of_graphs = self.callfamily.calltables[shape][index]
        links = []
        descs = list(self.s_pbc.descriptions)
        if self.s_pbc.can_be_None:
            descs.insert(0, None)
        for desc in descs:
            if desc is None:
                continue
            args_v = [varoftype(t) for t in argtypes]
            b = Block(args_v)
            llfn = self.rtyper.getcallable(row_of_graphs[desc])
            v_fn = inputconst(typeOf(llfn), llfn)
            v_result = varoftype(resulttype)
            b.operations.append(
                SpaceOperation("direct_call", [v_fn] + args_v, v_result))
            b.closeblock(Link([v_result], graph.returnblock))
            i = self.descriptions.index(desc)
            links.append(Link(inputargs[1:], b, chr(i)))
            links[-1].llexitcase = chr(i)
        startblock.closeblock(*links)
        self.rtyper.annotator.translator.graphs.append(graph)
        ll_ret = self.rtyper.type_system.getcallable(graph)
        #FTYPE = FuncType
        c_ret = self._dispatch_cache[key] = inputconst(typeOf(ll_ret), ll_ret)
        return c_ret

    def call(self, opname, hop):
        bk = self.rtyper.annotator.bookkeeper
        args = bk.build_args(opname, hop.args_s[1:])
        s_pbc = hop.args_s[0]   # possibly more precise than self.s_pbc
        descs = list(s_pbc.descriptions)
        vfcs = description.FunctionDesc.variant_for_call_site
        shape, index = vfcs(bk, self.callfamily, descs, args, hop.spaceop)
        row_of_graphs = self.callfamily.calltables[shape][index]
        anygraph = row_of_graphs.itervalues().next()  # pick any witness
        vlist = [hop.inputarg(self, arg=0)]
        vlist += callparse.callparse(self.rtyper, anygraph, hop, opname)
        rresult = callparse.getrresult(self.rtyper, anygraph)
        hop.exception_is_here()
        v_dispatcher = self.dispatcher(shape, index, [v.concretetype for v in vlist[1:]], rresult.lowleveltype)
        v_result = hop.genop('direct_call', [v_dispatcher] + vlist,
                             resulttype=rresult)
        return hop.llops.convertvar(v_result, rresult, hop.r_result)

    def rtype_is_true(self, hop):
        if not self.s_pbc.can_be_None:
            return inputconst(Bool, True)
        else:
            v1, = hop.inputargs(self)
            return hop.genop('char_ne', [v1, inputconst(Char, '\000')],
                         resulttype=Bool)

##     def rtype_simple_call(self, hop):
##         v_index = hop.inputarg(self, arg=0)
##         v_ptr = hop.llops.convertvar(v_index, self, self.pointer_repr)
##         hop2 = hop.copy()
##         hop2.args_r[0] = self.pointer_repr
##         hop2.args_v[0] = v_ptr
##         return hop2.dispatch()

##     rtype_call_args = rtype_simple_call

class __extend__(pairtype(SmallFunctionSetPBCRepr, FunctionsPBCRepr)):
    def convert_from_to((r_set, r_ptr), v, llops):
        if r_ptr.lowleveltype is Void:
            return inputconst(Void, None)
        else:
            assert v.concretetype is Char
            v_int = llops.genop('cast_char_to_int', [v],
                                resulttype=Signed)
            return llops.genop('getarrayitem', [r_set.c_pointer_table, v_int],
                               resulttype=r_ptr.lowleveltype)

def compression_function(r_set):
    if r_set._compression_function is None:
        table = []
        for i, p in enumerate(r_set.c_pointer_table.value):
            table.append((chr(i), p))
        last_c, last_p = table[-1]
        unroll_table = unrolling_iterable(table[:-1])
        def ll_compress(fnptr):
            for c, p in unroll_table:
                if fnptr == p:
                    return c
            else:
                ll_assert(fnptr == last_p, "unexpected function pointer")
                return last_c
        r_set._compression_function = ll_compress
    return r_set._compression_function

class __extend__(pairtype(FunctionsPBCRepr, SmallFunctionSetPBCRepr)):
    def convert_from_to((r_ptr, r_set), v, llops):
        if r_ptr.lowleveltype is Void:
            desc, = r_ptr.s_pbc.descriptions
            return inputconst(Char, r_set.convert_desc(desc))
        else:
            ll_compress = compression_function(r_set)
            return llops.gendirectcall(ll_compress, v)

def conversion_table(r_from, r_to):
    if r_to in r_from._conversion_tables:
        return r_from._conversion_tables[r_to]
    else:
        t = malloc(Array(Char, hints={'nolength': True}),
                   len(r_from.descriptions), immortal=True)
        l = []
        for i, d in enumerate(r_from.descriptions):
            if d in r_to.descriptions:
                j = r_to.descriptions.index(d)
                l.append(j)
                t[i] = chr(j)
            else:
                l.append(None)
        if l == range(len(r_from.descriptions)):
            r = None
        else:
            r = inputconst(Ptr(Array(Char)), t)
        r_from._conversion_tables[r_to] = r
        return r

## myf = open('convlog.txt', 'w')

class __extend__(pairtype(SmallFunctionSetPBCRepr, SmallFunctionSetPBCRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        c_table = conversion_table(r_from, r_to)
        if c_table:
            assert v.concretetype is Char
##             from pypy.rpython.lltypesystem.rstr import string_repr
##             s = repr(llops.rtyper.annotator.annotated.get(llops.originalblock))
##             if 'LOAD_GLOBAL' in s:
##                 import pdb; pdb.set_trace()
##             print >> myf, 'static small conv', s
##             print 'static small conv', s
##             llops.genop('debug_print',
##                         [Constant(string_repr.convert_const("dynamic small conv" + s),
##                                   string_repr.lowleveltype)])
            v_int = llops.genop('cast_char_to_int', [v],
                                resulttype=Signed)
            return llops.genop('getarrayitem', [c_table, v_int],
                               resulttype=Char)
        else:
            return v

class MethodsPBCRepr(AbstractMethodsPBCRepr):
    """Representation selected for a PBC of the form {func: classdef...}.
    It assumes that all the methods come from the same name in a base
    classdef."""

    def rtype_simple_call(self, hop):
        return self.redispatch_call(hop, call_args=False)

    def rtype_call_args(self, hop):
        return self.redispatch_call(hop, call_args=True)

    def redispatch_call(self, hop, call_args):
        r_class = self.r_im_self.rclass
        mangled_name, r_func = r_class.clsfields[self.methodname]
        assert isinstance(r_func, (FunctionsPBCRepr,
                                   OverriddenFunctionPBCRepr,
                                   SmallFunctionSetPBCRepr))
        # s_func = r_func.s_pbc -- not precise enough, see
        # test_precise_method_call_1.  Build a more precise one...
        funcdescs = [desc.funcdesc for desc in hop.args_s[0].descriptions]
        s_func = annmodel.SomePBC(funcdescs, subset_of=r_func.s_pbc)
        v_im_self = hop.inputarg(self, arg=0)
        v_cls = self.r_im_self.getfield(v_im_self, '__class__', hop.llops)
        v_func = r_class.getclsfield(v_cls, self.methodname, hop.llops)

        hop2 = self.add_instance_arg_to_hop(hop, call_args)
        opname = 'simple_call'
        if call_args:
            opname = 'call_args'
        hop2.forced_opname = opname

        hop2.v_s_insertfirstarg(v_func, s_func)   # insert 'function'

        if type(hop2.args_r[0]) is SmallFunctionSetPBCRepr and type(r_func) is FunctionsPBCRepr:
            hop2.args_r[0] = FunctionsPBCRepr(self.rtyper, s_func)
        else:
            hop2.args_v[0] = hop2.llops.convertvar(hop2.args_v[0], r_func, hop2.args_r[0])

        # now hop2 looks like simple_call(function, self, args...)
        return hop2.dispatch()


# ____________________________________________________________


class ClassesPBCRepr(AbstractClassesPBCRepr):
    """Representation selected for a PBC of class(es)."""

    # no __init__ here, AbstractClassesPBCRepr.__init__ is good enough

    def _instantiate_runtime_class(self, hop, vtypeptr, r_instance):
        from pypy.rpython.lltypesystem.rbuiltin import ll_instantiate
        v_inst1 = hop.gendirectcall(ll_instantiate, vtypeptr)
        return hop.genop('cast_pointer', [v_inst1], resulttype = r_instance)

    def getlowleveltype(self):
        return rclass.CLASSTYPE


# ____________________________________________________________

##def rtype_call_memo(hop): 
##    memo_table = hop.args_v[0].value
##    if memo_table.s_result.is_constant():
##        return hop.inputconst(hop.r_result, memo_table.s_result.const)
##    fieldname = memo_table.fieldname 
##    assert hop.nb_args == 2, "XXX"  

##    r_pbc = hop.args_r[1]
##    assert isinstance(r_pbc, (MultipleFrozenPBCRepr, ClassesPBCRepr))
##    v_table, v_pbc = hop.inputargs(Void, r_pbc)
##    return r_pbc.getfield(v_pbc, fieldname, hop.llops)
