import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop, LL_OPERATIONS
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant, \
     c_last_exception, FunctionGraph, Block, Link, checkgraph
from pypy.translator.unsimplify import varoftype
from pypy.translator.unsimplify import insert_empty_block
from pypy.translator.unsimplify import insert_empty_startblock
from pypy.translator.unsimplify import starts_with_empty_block
from pypy.translator.unsimplify import remove_empty_startblock
from pypy.translator.translator import graphof
from pypy.translator.backendopt.support import var_needsgc
from pypy.translator.backendopt import inline
from pypy.translator.backendopt import graphanalyze
from pypy.translator.backendopt.canraise import RaiseAnalyzer
from pypy.translator.backendopt.ssa import DataFlowFamilyBuilder
from pypy.annotation import model as annmodel
from pypy.rpython import rmodel, rptr, annlowlevel, typesystem
from pypy.rpython.memory import gc, lladdress
from pypy.rpython.memory.gcheader import GCHeaderBuilder
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.rpython.extregistry import ExtRegistryEntry
import sets, os

def var_ispyobj(var):
    if hasattr(var, 'concretetype'):
        if isinstance(var.concretetype, lltype.Ptr):
            return var.concretetype.TO._gckind == 'cpy'
        else:
            return False
    else:
        # assume PyObjPtr
        return True

PyObjPtr = lltype.Ptr(lltype.PyObject)


class GCTransformer(object):
    finished_helpers = False

    def __init__(self, translator, inline=False):
        self.translator = translator
        self.seen_graphs = {}
        self.minimal_transform = {}
        if translator:
            self.mixlevelannotator = MixLevelHelperAnnotator(translator.rtyper)
        else:
            self.mixlevelannotator = None
        self.inline = inline
        if translator and inline:
            self.lltype_to_classdef = translator.rtyper.lltype_to_classdef_mapping()
        self.graphs_to_inline = {}
        if self.MinimalGCTransformer:
            self.minimalgctransformer = self.MinimalGCTransformer(self)
        else:
            self.minimalgctransformer = None

    def get_lltype_of_exception_value(self):
        if self.translator is not None:
            exceptiondata = self.translator.rtyper.getexceptiondata()
            return exceptiondata.lltype_of_exception_value
        else:
            return lltype.Ptr(lltype.PyObject)

    def need_minimal_transform(self, graph):
        self.seen_graphs[graph] = True
        self.minimal_transform[graph] = True

    def transform(self, graphs):
        for graph in graphs:
            self.transform_graph(graph)

    def transform_graph(self, graph):
        if graph in self.minimal_transform:
            if self.minimalgctransformer:
                self.minimalgctransformer.transform_graph(graph)
            del self.minimal_transform[graph]
            return
        if graph in self.seen_graphs:
            return
        self.seen_graphs[graph] = True
        self.links_to_split = {} # link -> vars to pop_alive across the link

        # for sanity, we need an empty block at the start of the graph
        if not starts_with_empty_block(graph):
            insert_empty_startblock(self.translator.annotator, graph)
        is_borrowed = self.compute_borrowed_vars(graph)

        for block in graph.iterblocks():
            self.transform_block(block, is_borrowed)
        for link, livecounts in self.links_to_split.iteritems():
            newops = []
            for var, livecount in livecounts.iteritems():
                for i in range(livecount):
                    newops.extend(self.pop_alive(var))
                for i in range(-livecount):
                    newops.extend(self.push_alive(var))
            if newops:
                if link.prevblock.exitswitch is None:
                    link.prevblock.operations.extend(newops)
                else:
                    insert_empty_block(self.translator.annotator, link, newops)

        # remove the empty block at the start of the graph, which should
        # still be empty (but let's check)
        if starts_with_empty_block(graph):
            remove_empty_startblock(graph)

        self.links_to_split = None
        v = Variable('vanishing_exc_value')
        v.concretetype = self.get_lltype_of_exception_value()
        graph.exc_cleanup = (v, self.pop_alive(v))
        return is_borrowed    # xxx for tests only

    def compute_borrowed_vars(self, graph):
        # the input args are borrowed, and stay borrowed for as long as they
        # are not merged with other values.
        var_families = DataFlowFamilyBuilder(graph).get_variable_families()
        borrowed_reps = {}
        for v in graph.getargs():
            borrowed_reps[var_families.find_rep(v)] = True
        # no support for returning borrowed values so far
        retvar = graph.getreturnvar()

        def is_borrowed(v1):
            return (var_families.find_rep(v1) in borrowed_reps
                    and v1 is not retvar)
        return is_borrowed

    def inline_helpers(self, graph):
        if self.inline:
            raise_analyzer = RaiseAnalyzer(self.translator)
            for inline_graph in self.graphs_to_inline:
                try:
                    # XXX quite inefficient: we go over the function lots of times
                    inline.inline_function(self.translator, inline_graph, graph,
                                           self.lltype_to_classdef,
                                           raise_analyzer)
                except inline.CannotInline, e:
                    print 'CANNOT INLINE:', e
                    print '\t%s into %s' % (inline_graph, graph)
            checkgraph(graph)

    def transform_block(self, block, is_borrowed):
        newops = []
        livevars = [var for var in block.inputargs if var_needsgc(var)
                                                   and not is_borrowed(var)]
        newops = []
        # XXX this is getting obscure.  Maybe we should use the basic
        # graph-transforming capabilities of the RTyper instead, as we
        # seem to run into all the same problems as the ones we already
        # had to solve there.
        for i, op in enumerate(block.operations):
            num_ops_after_exc_raising = 0
            ops, index = self.replacement_operations(op, livevars, block)
            if not ops:
                continue # may happen when we eat gc_protect/gc_unprotect.
            newops.extend(ops)
            origname = op.opname
            op = ops[index]
            if var_needsgc(op.result):
                if var_ispyobj(op.result):
                    if op.opname in ('getfield', 'getarrayitem', 'same_as',
                                     'cast_pointer', 'getsubstruct'):
                        # XXX more operations?
                        lst = list(self.push_alive(op.result))
                        newops.extend(lst)
                elif op.opname not in ('direct_call', 'indirect_call'):
                    lst = list(self.push_alive(op.result))
                    newops.extend(lst)
                if not is_borrowed(op.result):
                    livevars.append(op.result)
        if len(block.exits) == 0:
            # everything is fine already for returnblocks and exceptblocks
            pass
        else:
            assert block.exitswitch is not c_last_exception
            deadinallexits = sets.Set(livevars)
            for link in block.exits:
                deadinallexits.difference_update(sets.Set(link.args))
            for var in deadinallexits:
                newops.extend(self.pop_alive(var))
            for link in block.exits:
                livecounts = dict.fromkeys(sets.Set(livevars) - deadinallexits, 1)
                for v, v2 in zip(link.args, link.target.inputargs):
                    if is_borrowed(v2):
                        continue
                    if v in livecounts:
                        livecounts[v] -= 1
                    elif var_needsgc(v):
                        # 'v' is typically a Constant here, but it can be
                        # a borrowed variable going into a non-borrowed one
                        livecounts[v] = -1
                self.links_to_split[link] = livecounts
        if newops:
            block.operations = newops

    def replacement_operations(self, op, livevars, block):
        m = getattr(self, 'replace_' + op.opname, None)
        if m:
            r = m(op, livevars, block)
            if not isinstance(r, tuple):
                return r, -1
            else:
                return r
        else:
            return [op], 0

    def push_alive(self, var):
        if var_ispyobj(var):
            return self.push_alive_pyobj(var)
        else:
            return self.push_alive_nopyobj(var)

    def push_alive_nopyobj(self, var):
        result = varoftype(lltype.Void)
        return [SpaceOperation("gc_push_alive", [var], result)]

    def push_alive_pyobj(self, var):
        result = varoftype(lltype.Void)
        lst = []
        if hasattr(var, 'concretetype') and var.concretetype != PyObjPtr:
            res = varoftype(PyObjPtr)
            lst.append(SpaceOperation("cast_pointer", [var], res))
            var = res
        lst.append(SpaceOperation("gc_push_alive_pyobj", [var], result))
        return lst

    def pop_alive(self, var):
        if var_ispyobj(var):
            return self.pop_alive_pyobj(var)
        else:
            return self.pop_alive_nopyobj(var)

    def pop_alive_nopyobj(self, var):
        result = varoftype(lltype.Void)
        return [SpaceOperation("gc_pop_alive", [var], result)]

    def pop_alive_pyobj(self, var):
        result = varoftype(lltype.Void)
        lst = []
        if hasattr(var, 'concretetype') and var.concretetype != PyObjPtr:
            res = varoftype(PyObjPtr)
            lst.append(SpaceOperation("cast_pointer", [var], res))
            var = res
        lst.append(SpaceOperation("gc_pop_alive_pyobj", [var], result))
        return lst

    def replace_gc_protect(self, op, livevars, block):
        """ protect this object from gc (make it immortal). the specific
        gctransformer needs to overwrite this"""
        raise NotImplementedError("gc_protect does not make sense for this gc")

    def replace_gc_unprotect(self, op, livevars, block):
        """ get this object back into gc control. the specific gctransformer
        needs to overwrite this"""
        raise NotImplementedError("gc_protect does not make sense for this gc")

    def replace_setfield(self, op, livevars, block):
        if not var_ispyobj(op.args[2]):
            return [op]
        oldval = varoftype(op.args[2].concretetype)
        getoldvalop = SpaceOperation("getfield",
                                     [op.args[0], op.args[1]], oldval)
        result = [getoldvalop]
        result.extend(self.push_alive(op.args[2]))
        result.append(op)
        result.extend(self.pop_alive(oldval))
        return result

    def replace_setarrayitem(self, op, livevars, block):
        if not var_ispyobj(op.args[2]):
            return [op]
        oldval = varoftype(op.args[2].concretetype)
        getoldvalop = SpaceOperation("getarrayitem",
                                     [op.args[0], op.args[1]], oldval)
        result = [getoldvalop]
        result.extend(self.push_alive(op.args[2]))
        result.append(op)
        result.extend(self.pop_alive(oldval))
        return result

    def replace_safe_call(self, op, livevars, block):
        return [SpaceOperation("direct_call", op.args, op.result)]

    def annotate_helper(self, ll_helper, ll_args, ll_result, inline=False):
        assert not self.finished_helpers
        args_s = map(annmodel.lltype_to_annotation, ll_args)
        s_result = annmodel.lltype_to_annotation(ll_result)
        graph = self.mixlevelannotator.getgraph(ll_helper, args_s, s_result)
        # the produced graphs does not need to be fully transformed
        self.need_minimal_transform(graph)
        if inline:
            self.graphs_to_inline[graph] = True
        return self.mixlevelannotator.graph2delayed(graph)

    def inittime_helper(self, ll_helper, ll_args, ll_result):
        ptr = self.annotate_helper(ll_helper, ll_args, ll_result, inline=True)
        return Constant(ptr, lltype.typeOf(ptr))

    def finish_helpers(self):
        if self.translator is not None:
            self.mixlevelannotator.finish_annotate()
        self.finished_helpers = True
        if self.translator is not None:
            self.mixlevelannotator.finish_rtype()

    def finish_tables(self):
        pass

    def finish(self):
        self.finish_helpers()
        self.finish_tables()

class MinimalGCTransformer(GCTransformer):
    def __init__(self, parenttransformer):
        GCTransformer.__init__(self, parenttransformer.translator)
        self.parenttransformer = parenttransformer

    def push_alive(self, var):
        return []

    def pop_alive(self, var):
        return []

GCTransformer.MinimalGCTransformer = MinimalGCTransformer
MinimalGCTransformer.MinimalGCTransformer = None

# ----------------------------------------------------------------

class LLTransformerOp(object):
    """Objects that can be called in ll functions.
    Their calls are replaced by a simple operation of the GC transformer,
    e.g. ll_pop_alive.
    """
    def __init__(self, transformer_method, see_type=None):
        self.transformer_method = transformer_method
        self.see_type = see_type

class LLTransformerOpEntry(ExtRegistryEntry):
    "Annotation and specialization of LLTransformerOp() instances."
    _type_ = LLTransformerOp

    def compute_result_annotation(self, s_arg):
        op = self.instance   # the LLTransformerOp instance
        if op.see_type is not None:
            assert isinstance(s_arg, annmodel.SomePtr)
            PTRTYPE = s_arg.ll_ptrtype
            if PTRTYPE.TO is not lltype.PyObject:
                # look for and annotate a dynamic deallocator if necessary;
                # doing so implicitly in specialize_call() is too late.
                op.see_type(PTRTYPE.TO)
        return annmodel.s_None

    def specialize_call(self, hop):
        op = self.instance   # the LLTransformerOp instance
        newops = op.transformer_method(hop.args_v[0])
        hop.llops.extend(newops)
        hop.exception_cannot_occur()
        return hop.inputconst(hop.r_result.lowleveltype, hop.s_result.const)

# ----------------------------------------------------------------

def ll_call_destructor(destrptr, destr_v):
    try:
        destrptr(destr_v)
    except:
        try:
            os.write(2, "a destructor raised an exception, ignoring it\n")
        except:
            pass

def _static_deallocator_body_for_type(v, TYPE, depth=1):
    if isinstance(TYPE, lltype.Array):
        inner = list(_static_deallocator_body_for_type('v_%i'%depth, TYPE.OF, depth+1))
        if inner:
            yield '    '*depth + 'i_%d = 0'%(depth,)
            yield '    '*depth + 'l_%d = len(%s)'%(depth, v)
            yield '    '*depth + 'while i_%d < l_%d:'%(depth, depth)
            yield '    '*depth + '    v_%d = %s[i_%d]'%(depth, v, depth)
            for line in inner:
                yield line
            yield '    '*depth + '    i_%d += 1'%(depth,)
    elif isinstance(TYPE, lltype.Struct):
        for name in TYPE._names:
            inner = list(_static_deallocator_body_for_type(
                v + '_' + name, TYPE._flds[name], depth))
            if inner:
                yield '    '*depth + v + '_' + name + ' = ' + v + '.' + name
                for line in inner:
                    yield line
    elif isinstance(TYPE, lltype.Ptr) and TYPE._needsgc():
        yield '    '*depth + 'pop_alive(%s)'%v

counts = {}

def print_call_chain(ob):
    import sys
    f = sys._getframe(1)
    stack = []
    flag = False
    while f:
        if f.f_locals.get('self') is ob:
            stack.append((f.f_code.co_name, f.f_locals.get('TYPE')))
            if not flag:
                counts[f.f_code.co_name] = counts.get(f.f_code.co_name, 0) + 1
                print counts
                flag = True
        f = f.f_back
    stack.reverse()
    for i, (a, b) in enumerate(stack):
        print ' '*i, a, repr(b)[:100-i-len(a)], id(b)

ADDRESS_VOID_FUNC = lltype.FuncType([llmemory.Address], lltype.Void)

def get_rtti(TYPE):
    if isinstance(TYPE, lltype.RttiStruct):
        try:
            return lltype.getRuntimeTypeInfo(TYPE)
        except ValueError:
            pass
    return None



class RefcountingGCTransformer(GCTransformer):

    HDR = lltype.Struct("header", ("refcount", lltype.Signed))

    def __init__(self, translator):
        super(RefcountingGCTransformer, self).__init__(translator, inline=True)
        self.gcheaderbuilder = GCHeaderBuilder(self.HDR)
        gc_header_offset = self.gcheaderbuilder.size_gc_header
        self.deallocator_graphs_needing_transforming = []
        # create incref graph
        def ll_incref(adr):
            if adr:
                gcheader = adr - gc_header_offset
                gcheader.signed[0] = gcheader.signed[0] + 1
        def ll_decref(adr, dealloc):
            if adr:
                gcheader = adr - gc_header_offset
                refcount = gcheader.signed[0] - 1
                gcheader.signed[0] = refcount
                if refcount == 0:
                    dealloc(adr)
        def ll_decref_simple(adr):
            if adr:
                gcheader = adr - gc_header_offset
                refcount = gcheader.signed[0] - 1
                if refcount == 0:
                    llop.gc_free(lltype.Void, adr)
                else:
                    gcheader.signed[0] = refcount
        def ll_no_pointer_dealloc(adr):
            llop.gc_free(lltype.Void, adr)
        if self.translator:
            self.increfptr = self.inittime_helper(
                ll_incref, [llmemory.Address], lltype.Void)
            self.decref_ptr = self.inittime_helper(
                ll_decref, [llmemory.Address, lltype.Ptr(ADDRESS_VOID_FUNC)],
                lltype.Void)
            self.decref_simple_ptr = self.inittime_helper(
                ll_decref_simple, [llmemory.Address], lltype.Void)
            self.no_pointer_dealloc_ptr = self.inittime_helper(
                ll_no_pointer_dealloc, [llmemory.Address], lltype.Void)
            self.mixlevelannotator.finish()   # for now
        # cache graphs:
        self.decref_funcptrs = {}
        self.static_deallocator_funcptrs = {}
        self.dynamic_deallocator_funcptrs = {}
        self.queryptr2dynamic_deallocator_funcptr = {}
        

    def push_alive_nopyobj(self, var):
        adr1 = varoftype(llmemory.Address)
        result = [SpaceOperation("cast_ptr_to_adr", [var], adr1)]
        result.append(SpaceOperation("direct_call", [self.increfptr, adr1],
                                     varoftype(lltype.Void)))
        return result

    def pop_alive_nopyobj(self, var):
        PTRTYPE = var.concretetype
        adr1 = varoftype(llmemory.Address)
        result = [SpaceOperation("cast_ptr_to_adr", [var], adr1)]

        dealloc_fptr = self.dynamic_deallocation_funcptr_for_type(PTRTYPE.TO)
        if dealloc_fptr is self.no_pointer_dealloc_ptr.value:
            # simple case
            result.append(SpaceOperation("direct_call",
                                         [self.decref_simple_ptr, adr1],
                                         varoftype(lltype.Void)))
        else:
            cdealloc_fptr = rmodel.inputconst(
                lltype.typeOf(dealloc_fptr), dealloc_fptr)
            result.append(SpaceOperation("direct_call",
                                        [self.decref_ptr, adr1, cdealloc_fptr],
                                         varoftype(lltype.Void)))
        return result

    def replace_gc_protect(self, op, livevars, block):
        """ protect this object from gc (make it immortal) """
        newops = self.push_alive(op.args[0])
        newops[-1].result = op.result
        return newops

    def replace_gc_unprotect(self, op, livevars, block):
        """ get this object back into gc control """
        newops = self.pop_alive(op.args[0])
        newops[-1].result = op.result
        return newops

    def replace_setfield(self, op, livevars, block):
        if not var_needsgc(op.args[2]):
            return [op]
        oldval = varoftype(op.args[2].concretetype)
        getoldvalop = SpaceOperation("getfield",
                                     [op.args[0], op.args[1]], oldval)
        result = [getoldvalop]
        result.extend(self.push_alive(op.args[2]))
        result.append(op)
        result.extend(self.pop_alive(oldval))
        return result

    def replace_setarrayitem(self, op, livevars, block):
        if not var_needsgc(op.args[2]):
            return [op]
        oldval = varoftype(op.args[2].concretetype)
        getoldvalop = SpaceOperation("getarrayitem",
                                     [op.args[0], op.args[1]], oldval)
        result = [getoldvalop]
        result.extend(self.push_alive(op.args[2]))
        result.append(op)
        result.extend(self.pop_alive(oldval))
        return result

##    -- maybe add this for tests and for consistency --
##    def consider_constant(self, TYPE, value):
##        p = value._as_ptr()
##        if not self.gcheaderbuilder.get_header(p):
##            hdr = new_header(p)
##            hdr.refcount = sys.maxint // 2

    def static_deallocation_funcptr_for_type(self, TYPE):
        if TYPE in self.static_deallocator_funcptrs:
            return self.static_deallocator_funcptrs[TYPE]
        #print_call_chain(self)

        rtti = get_rtti(TYPE) 
        if rtti is not None and hasattr(rtti._obj, 'destructor_funcptr'):
            destrptr = rtti._obj.destructor_funcptr
            DESTR_ARG = lltype.typeOf(destrptr).TO.ARGS[0]
        else:
            destrptr = None
            DESTR_ARG = None

        if destrptr is None and not find_gc_ptrs_in_type(TYPE):
            #print repr(TYPE)[:80], 'is dealloc easy'
            p = self.no_pointer_dealloc_ptr.value
            self.static_deallocator_funcptrs[TYPE] = p
            return p

        if destrptr is not None:
            body = '\n'.join(_static_deallocator_body_for_type('v', TYPE, 3))
            src = """
def ll_deallocator(addr):
    exc_instance = llop.gc_fetch_exception(EXC_INSTANCE_TYPE)
    try:
        v = cast_adr_to_ptr(addr, PTR_TYPE)
        gcheader = addr - gc_header_offset
        # refcount is at zero, temporarily bump it to 1:
        gcheader.signed[0] = 1
        destr_v = cast_pointer(DESTR_ARG, v)
        ll_call_destructor(destrptr, destr_v)
        refcount = gcheader.signed[0] - 1
        gcheader.signed[0] = refcount
        if refcount == 0:
%s
            llop.gc_free(lltype.Void, addr)
    except:
        pass
    llop.gc_restore_exception(lltype.Void, exc_instance)
    pop_alive(exc_instance)
    # XXX layering of exceptiontransform versus gcpolicy

""" % (body, )
        else:
            call_del = None
            body = '\n'.join(_static_deallocator_body_for_type('v', TYPE))
            src = ('def ll_deallocator(addr):\n    v = cast_adr_to_ptr(addr, PTR_TYPE)\n' +
                   body + '\n    llop.gc_free(lltype.Void, addr)\n')
        d = {'pop_alive': LLTransformerOp(self.pop_alive,
                                  self.dynamic_deallocation_funcptr_for_type),
             'llop': llop,
             'lltype': lltype,
             'destrptr': destrptr,
             'gc_header_offset': self.gcheaderbuilder.size_gc_header,
             'cast_adr_to_ptr': llmemory.cast_adr_to_ptr,
             'cast_pointer': lltype.cast_pointer,
             'PTR_TYPE': lltype.Ptr(TYPE),
             'DESTR_ARG': DESTR_ARG,
             'EXC_INSTANCE_TYPE': self.translator.rtyper.exceptiondata.lltype_of_exception_value,
             'll_call_destructor': ll_call_destructor}
        exec src in d
        this = d['ll_deallocator']
        fptr = self.annotate_helper(this, [llmemory.Address], lltype.Void)
        self.static_deallocator_funcptrs[TYPE] = fptr
        for p in find_gc_ptrs_in_type(TYPE):
            self.static_deallocation_funcptr_for_type(p.TO)
        return fptr

    def dynamic_deallocation_funcptr_for_type(self, TYPE):
        if TYPE in self.dynamic_deallocator_funcptrs:
            return self.dynamic_deallocator_funcptrs[TYPE]
        #print_call_chain(self)

        rtti = get_rtti(TYPE)
        if rtti is None:
            p = self.static_deallocation_funcptr_for_type(TYPE)
            self.dynamic_deallocator_funcptrs[TYPE] = p
            return p
            
        queryptr = rtti._obj.query_funcptr
        if queryptr._obj in self.queryptr2dynamic_deallocator_funcptr:
            return self.queryptr2dynamic_deallocator_funcptr[queryptr._obj]
        
        RTTI_PTR = lltype.Ptr(lltype.RuntimeTypeInfo)
        QUERY_ARG_TYPE = lltype.typeOf(queryptr).TO.ARGS[0]
        gc_header_offset = self.gcheaderbuilder.size_gc_header
        def ll_dealloc(addr):
            # bump refcount to 1
            gcheader = addr - gc_header_offset
            gcheader.signed[0] = 1
            v = llmemory.cast_adr_to_ptr(addr, QUERY_ARG_TYPE)
            rtti = queryptr(v)
            gcheader.signed[0] = 0
            llop.gc_call_rtti_destructor(lltype.Void, rtti, addr)
        fptr = self.annotate_helper(ll_dealloc, [llmemory.Address], lltype.Void)
        self.dynamic_deallocator_funcptrs[TYPE] = fptr
        self.queryptr2dynamic_deallocator_funcptr[queryptr._obj] = fptr
        return fptr

    def replace_gc_deallocate(self, op, livevars, block):
        TYPE = op.args[0].value
        v_addr = op.args[1]
        dealloc_fptr = self.dynamic_deallocation_funcptr_for_type(TYPE)
        cdealloc_fptr = rmodel.inputconst(
            lltype.typeOf(dealloc_fptr), dealloc_fptr)
        return [SpaceOperation("direct_call", [cdealloc_fptr,
                                               v_addr],
                               varoftype(lltype.Void))]

def find_gc_ptrs_in_type(TYPE):
    if isinstance(TYPE, lltype.Array):
        return find_gc_ptrs_in_type(TYPE.OF)
    elif isinstance(TYPE, lltype.Struct):
        result = []
        for name in TYPE._names:
            result.extend(find_gc_ptrs_in_type(TYPE._flds[name]))
        return result
    elif isinstance(TYPE, lltype.Ptr) and TYPE._needsgc():
        return [TYPE]
    elif isinstance(TYPE, lltype.GcOpaqueType):
        # heuristic: in theory the same problem exists with OpaqueType, but
        # we use OpaqueType for other things too that we know are safely
        # empty of further gc pointers
        raise Exception("don't know what is in %r" % (TYPE,))
    else:
        return []

def type_contains_pyobjs(TYPE):
    if isinstance(TYPE, lltype.Array):
        return type_contains_pyobjs(TYPE.OF)
    elif isinstance(TYPE, lltype.Struct):
        result = []
        for name in TYPE._names:
            if type_contains_pyobjs(TYPE._flds[name]):
                return True
        return False
    elif isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'cpy':
        return True
    else:
        return False


class BoehmGCTransformer(GCTransformer):
    def __init__(self, translator, inline=False):
        super(BoehmGCTransformer, self).__init__(translator, inline=inline)
        self.finalizer_funcptrs = {}

    def push_alive_nopyobj(self, var):
        return []

    def pop_alive_nopyobj(self, var):
        return []

    def replace_gc_protect(self, op, livevars, block):
        """ for boehm it is enough to do nothing"""
        return [SpaceOperation("same_as", [Constant(None, lltype.Void)], op.result)]

    def replace_gc_unprotect(self, op, livevars, block):
        """ for boehm it is enough to do nothing"""
        return [SpaceOperation("same_as", [Constant(None, lltype.Void)], op.result)]

    def finalizer_funcptr_for_type(self, TYPE):
        if TYPE in self.finalizer_funcptrs:
            return self.finalizer_funcptrs[TYPE]

        rtti = get_rtti(TYPE)
        if rtti is not None and hasattr(rtti._obj, 'destructor_funcptr'):
            destrptr = rtti._obj.destructor_funcptr
            DESTR_ARG = lltype.typeOf(destrptr).TO.ARGS[0]
        else:
            destrptr = None
            DESTR_ARG = None

        if type_contains_pyobjs(TYPE):
            if destrptr:
                raise Exception("can't mix PyObjects and __del__ with Boehm")

            static_body = '\n'.join(_static_deallocator_body_for_type('v', TYPE))
            d = {'pop_alive': LLTransformerOp(self.pop_alive),
                 'PTR_TYPE':lltype.Ptr(TYPE),
                 'cast_adr_to_ptr': llmemory.cast_adr_to_ptr}
            src = ("def ll_finalizer(addr):\n"
                   "    v = cast_adr_to_ptr(addr, PTR_TYPE)\n"
                   "%s\n")%(static_body,)
            exec src in d
            fptr = self.annotate_helper(d['ll_finalizer'], [llmemory.Address], lltype.Void)
        elif destrptr:
            EXC_INSTANCE_TYPE = self.translator.rtyper.exceptiondata.lltype_of_exception_value
            def ll_finalizer(addr):
                exc_instance = llop.gc_fetch_exception(EXC_INSTANCE_TYPE)
                v = llmemory.cast_adr_to_ptr(addr, DESTR_ARG)
                ll_call_destructor(destrptr, v)
                llop.gc_restore_exception(lltype.Void, exc_instance)
            fptr = self.annotate_helper(ll_finalizer, [llmemory.Address], lltype.Void)
        else:
            fptr = None

        self.finalizer_funcptrs[TYPE] = fptr
        return fptr


def gc_pointers_inside(v, adr):
    t = lltype.typeOf(v)
    if isinstance(t, lltype.Struct):
        for n, t2 in t._flds.iteritems():
            if isinstance(t2, lltype.Ptr) and t2.TO._gckind == 'gc':
                yield adr + llmemory.offsetof(t, n)
            elif isinstance(t2, (lltype.Array, lltype.Struct)):
                for a in gc_pointers_inside(getattr(v, n), adr + llmemory.offsetof(t, n)):
                    yield a
    elif isinstance(t, lltype.Array):
        if isinstance(t.OF, lltype.Ptr) and t2._needsgc():
            for i in range(len(v.items)):
                yield adr + llmemory.itemoffsetof(t, i)
        elif isinstance(t.OF, lltype.Struct):
            for i in range(len(v.items)):
                for a in gc_pointers_inside(v.items[i], adr + llmemory.itemoffsetof(t, i)):
                    yield a


class CollectAnalyzer(graphanalyze.GraphAnalyzer):
    def operation_is_true(self, op):
        return op.opname in ("malloc", "malloc_varsize", "gc__collect",
                             "gc_x_become")

class FrameworkGCTransformer(GCTransformer):
    use_stackless = False
    extra_static_slots = 0
    finished_tables = False

    from pypy.rpython.memory.gc import MarkSweepGC as GCClass
    GC_PARAMS = {'start_heap_size': 8*1024*1024 # XXX adjust
                 }
    
    def __init__(self, translator):
        from pypy.rpython.memory.support import get_address_linked_list
        super(FrameworkGCTransformer, self).__init__(translator, inline=True)
        AddressLinkedList = get_address_linked_list()
        GCClass = self.GCClass
        self.finalizer_funcptrs = {}
        self.FINALIZERTYPE = lltype.Ptr(ADDRESS_VOID_FUNC)
        class GCData(object):
            # types of the GC information tables
            OFFSETS_TO_GC_PTR = lltype.Array(lltype.Signed)
            TYPE_INFO = lltype.Struct("type_info",
                ("isvarsize",   lltype.Bool),
                ("finalyzer",   self.FINALIZERTYPE),
                ("fixedsize",   lltype.Signed),
                ("ofstoptrs",   lltype.Ptr(OFFSETS_TO_GC_PTR)),
                ("varitemsize", lltype.Signed),
                ("ofstovar",    lltype.Signed),
                ("ofstolength", lltype.Signed),
                ("varofstoptrs",lltype.Ptr(OFFSETS_TO_GC_PTR)),
                )
            TYPE_INFO_TABLE = lltype.Array(TYPE_INFO)

        def q_is_varsize(typeid):
            return gcdata.type_info_table[typeid].isvarsize

        def q_finalyzer(typeid):
            return gcdata.type_info_table[typeid].finalyzer

        def q_offsets_to_gc_pointers(typeid):
            return gcdata.type_info_table[typeid].ofstoptrs

        def q_fixed_size(typeid):
            return gcdata.type_info_table[typeid].fixedsize

        def q_varsize_item_sizes(typeid):
            return gcdata.type_info_table[typeid].varitemsize

        def q_varsize_offset_to_variable_part(typeid):
            return gcdata.type_info_table[typeid].ofstovar

        def q_varsize_offset_to_length(typeid):
            return gcdata.type_info_table[typeid].ofstolength

        def q_varsize_offsets_to_gcpointers_in_var_part(typeid):
            return gcdata.type_info_table[typeid].varofstoptrs

        gcdata = GCData()
        # set up dummy a table, to be overwritten with the real one in finish()
        gcdata.type_info_table = lltype.malloc(GCData.TYPE_INFO_TABLE, 0,
                                               immortal=True)
        gcdata.static_roots = lltype.malloc(lltype.Array(llmemory.Address), 0,
                                            immortal=True)
        # initialize the following two fields with a random non-NULL address,
        # to make the annotator happy.  The fields are patched in finish()
        # to point to a real array (not 'static_roots', another one).
        a_random_address = llmemory.cast_ptr_to_adr(gcdata.type_info_table)
        gcdata.static_root_start = a_random_address   # patched in finish()
        gcdata.static_root_end = a_random_address     # patched in finish()
        self.gcdata = gcdata
        self.type_info_list = []
        self.id_of_type = {}      # {LLTYPE: type_id}
        self.seen_roots = {}
        self.static_gc_roots = []
        self.addresses_of_static_ptrs_in_nongc = []
        self.offsettable_cache = {}
        self.malloc_fnptr_cache = {}

        sizeofaddr = llmemory.sizeof(llmemory.Address)

        StackRootIterator = self.build_stack_root_iterator()
        gcdata.gc = GCClass(AddressLinkedList, get_roots=StackRootIterator, **self.GC_PARAMS)

        def frameworkgc_setup():
            # run-time initialization code
            StackRootIterator.setup_root_stack()
            gcdata.gc.setup()
            gcdata.gc.set_query_functions(
                q_is_varsize,
                q_finalyzer,
                q_offsets_to_gc_pointers,
                q_fixed_size,
                q_varsize_item_sizes,
                q_varsize_offset_to_variable_part,
                q_varsize_offset_to_length,
                q_varsize_offsets_to_gcpointers_in_var_part)

        bk = self.translator.annotator.bookkeeper

        # the point of this little dance is to not annotate
        # self.gcdata.type_info_table as a constant.
        data_classdef = bk.getuniqueclassdef(GCData)
        data_classdef.generalize_attr(
            'type_info_table',
            annmodel.SomePtr(lltype.Ptr(GCData.TYPE_INFO_TABLE)))
        data_classdef.generalize_attr(
            'static_roots',
            annmodel.SomePtr(lltype.Ptr(lltype.Array(llmemory.Address))))
        data_classdef.generalize_attr(
            'static_root_start',
            annmodel.SomeAddress())
        data_classdef.generalize_attr(
            'static_root_end',
            annmodel.SomeAddress())
        
        annhelper = annlowlevel.MixLevelHelperAnnotator(self.translator.rtyper)

        def getfn(ll_function, args_s, s_result, inline=False,
                  minimal_transform=True):
            graph = annhelper.getgraph(ll_function, args_s, s_result)
            if minimal_transform:
                self.need_minimal_transform(graph)
            if inline:
                self.graphs_to_inline[graph] = True
            return annhelper.graph2const(graph)

        self.frameworkgc_setup_ptr = getfn(frameworkgc_setup, [],
                                           annmodel.s_None)
        if StackRootIterator.push_root is None:
            self.push_root_ptr = None
        else:
            self.push_root_ptr = getfn(StackRootIterator.push_root,
                                       [annmodel.SomeAddress()],
                                       annmodel.s_None,
                                       inline = True)
        if StackRootIterator.pop_root is None:
            self.pop_root_ptr = None
        else:
            self.pop_root_ptr = getfn(StackRootIterator.pop_root, [],
                                      annmodel.s_None,
                                      inline = True)

        classdef = bk.getuniqueclassdef(GCClass)
        s_gc = annmodel.SomeInstance(classdef)
        s_gcref = annmodel.SomePtr(llmemory.GCREF)
        self.malloc_fixedsize_ptr = getfn(
            GCClass.malloc_fixedsize.im_func,
            [s_gc, annmodel.SomeInteger(nonneg=True),
             annmodel.SomeInteger(nonneg=True),
             annmodel.SomeBool(), annmodel.SomeBool()], s_gcref,
            inline = False)
        self.malloc_varsize_ptr = getfn(
            GCClass.malloc_varsize.im_func,
            [s_gc] + [annmodel.SomeInteger(nonneg=True) for i in range(5)]
            + [annmodel.SomeBool(), annmodel.SomeBool()], s_gcref)
        self.collect_ptr = getfn(GCClass.collect.im_func,
            [s_gc], annmodel.s_None)

        statics_s = (annmodel.SomeInteger(),)*GCClass.STATISTICS_NUMBERS
        self.statistics_ptr = getfn(GCClass.statistics.im_func,
                                    [s_gc], annmodel.SomeTuple(statics_s))

        # experimental gc_x_* operations
        s_x_pool  = annmodel.SomePtr(gc.X_POOL_PTR)
        s_x_clone = annmodel.SomePtr(gc.X_CLONE_PTR)
        # the x_*() methods use some regular mallocs that must be
        # transformed in the normal way
        self.x_swap_pool_ptr = getfn(GCClass.x_swap_pool.im_func,
                                     [s_gc, s_x_pool],
                                     s_x_pool,
                                     minimal_transform = False)
        self.x_clone_ptr = getfn(GCClass.x_clone.im_func,
                                 [s_gc, s_x_clone],
                                 annmodel.s_None,
                                 minimal_transform = False)

        self.x_become_ptr = getfn(
            GCClass.x_become.im_func,
            [s_gc, annmodel.SomeAddress(), annmodel.SomeAddress()],
            annmodel.s_None)

        annhelper.finish()   # at this point, annotate all mix-level helpers
        annhelper.backend_optimize()

        self.collect_analyzer = CollectAnalyzer(self.translator)
        self.collect_analyzer.analyze_all()

        s_gc = self.translator.annotator.bookkeeper.valueoftype(GCClass)
        r_gc = self.translator.rtyper.getrepr(s_gc)
        self.c_const_gc = rmodel.inputconst(r_gc, self.gcdata.gc)

        HDR = self._gc_HDR = self.gcdata.gc.gcheaderbuilder.HDR
        self._gc_fields = fields = []
        for fldname in HDR._names:
            FLDTYPE = getattr(HDR, fldname)
            fields.append(('_' + fldname, FLDTYPE))

    def build_stack_root_iterator(self):
        gcdata = self.gcdata
        sizeofaddr = llmemory.sizeof(llmemory.Address)
        rootstacksize = sizeofaddr * 163840    # XXX adjust

        class StackRootIterator:
            _alloc_flavor_ = 'raw'
            def setup_root_stack():
                stackbase = lladdress.raw_malloc(rootstacksize)
                gcdata.root_stack_top  = stackbase
                gcdata.root_stack_base = stackbase
                i = 0
                while i < len(gcdata.static_roots):
                    StackRootIterator.push_root(gcdata.static_roots[i])
                    i += 1
            setup_root_stack = staticmethod(setup_root_stack)

            def push_root(addr):
                top = gcdata.root_stack_top
                top.address[0] = addr
                gcdata.root_stack_top = top + sizeofaddr
            push_root = staticmethod(push_root)

            def pop_root():
                gcdata.root_stack_top -= sizeofaddr
            pop_root = staticmethod(pop_root)

            def __init__(self):
                self.stack_current = gcdata.root_stack_top
                self.static_current = gcdata.static_root_start

            def pop(self):
                while self.static_current != gcdata.static_root_end:
                    result = self.static_current
                    self.static_current += sizeofaddr
                    if result.address[0].address[0] != llmemory.NULL:
                        return result.address[0]
                while self.stack_current != gcdata.root_stack_base:
                    self.stack_current -= sizeofaddr
                    if self.stack_current.address[0] != llmemory.NULL:
                        return self.stack_current
                return llmemory.NULL

        return StackRootIterator

    def get_type_id(self, TYPE):
        try:
            return self.id_of_type[TYPE]
        except KeyError:
            assert not self.finished_tables
            assert isinstance(TYPE, (lltype.GcStruct, lltype.GcArray))
            # Record the new type_id description as a small dict for now.
            # It will be turned into a Struct("type_info") in finish()
            type_id = len(self.type_info_list)
            info = {}
            self.type_info_list.append(info)
            self.id_of_type[TYPE] = type_id
            offsets = offsets_to_gc_pointers(TYPE)
            info["ofstoptrs"] = self.offsets2table(offsets, TYPE)
            info["finalyzer"] = self.finalizer_funcptr_for_type(TYPE)
            if not TYPE._is_varsize():
                info["isvarsize"] = False
                info["fixedsize"] = llmemory.sizeof(TYPE)
                info["ofstolength"] = -1
            else:
                info["isvarsize"] = True
                info["fixedsize"] = llmemory.sizeof(TYPE, 0)
                if isinstance(TYPE, lltype.Struct):
                    ARRAY = TYPE._flds[TYPE._arrayfld]
                    ofs1 = llmemory.offsetof(TYPE, TYPE._arrayfld)
                    info["ofstolength"] = ofs1 + llmemory.ArrayLengthOffset(ARRAY)
                    if ARRAY.OF != lltype.Void:
                        info["ofstovar"] = ofs1 + llmemory.itemoffsetof(ARRAY, 0)
                    else:
                        info["fixedsize"] = ofs1 + llmemory.sizeof(lltype.Signed)
                    if ARRAY._hints.get('isrpystring'):
                        info["fixedsize"] = llmemory.sizeof(TYPE, 1)
                else:
                    ARRAY = TYPE
                    info["ofstolength"] = llmemory.ArrayLengthOffset(ARRAY)
                    if ARRAY.OF != lltype.Void:
                        info["ofstovar"] = llmemory.itemoffsetof(TYPE, 0)
                    else:
                        info["fixedsize"] = llmemory.ArrayLengthOffset(ARRAY) + llmemory.sizeof(lltype.Signed)
                assert isinstance(ARRAY, lltype.Array)
                if ARRAY.OF != lltype.Void:
                    offsets = offsets_to_gc_pointers(ARRAY.OF)
                    info["varofstoptrs"] = self.offsets2table(offsets, ARRAY.OF)
                    info["varitemsize"] = llmemory.sizeof(ARRAY.OF)
                else:
                    info["varofstoptrs"] = self.offsets2table((), lltype.Void)
                    info["varitemsize"] = llmemory.sizeof(ARRAY.OF)
            return type_id

    def finalizer_funcptr_for_type(self, TYPE):
        if TYPE in self.finalizer_funcptrs:
            return self.finalizer_funcptrs[TYPE]

        rtti = get_rtti(TYPE)
        if rtti is not None and hasattr(rtti._obj, 'destructor_funcptr'):
            destrptr = rtti._obj.destructor_funcptr
            DESTR_ARG = lltype.typeOf(destrptr).TO.ARGS[0]
        else:
            destrptr = None
            DESTR_ARG = None

        assert not type_contains_pyobjs(TYPE), "not implemented"
        if destrptr:
            def ll_finalizer(addr):
                v = llmemory.cast_adr_to_ptr(addr, DESTR_ARG)
                ll_call_destructor(destrptr, v)
            fptr = self.annotate_helper(ll_finalizer, [llmemory.Address], lltype.Void)
        else:
            fptr = lltype.nullptr(ADDRESS_VOID_FUNC)

        self.finalizer_funcptrs[TYPE] = fptr
        return fptr

    def consider_constant(self, TYPE, value):
        if value is not lltype.top_container(value):
            return
        if id(value) in self.seen_roots:
            return
        self.seen_roots[id(value)] = True

        if isinstance(TYPE, (lltype.GcStruct, lltype.GcArray)):
            typeid = self.get_type_id(TYPE)
            hdrbuilder = self.gcdata.gc.gcheaderbuilder
            hdr = hdrbuilder.new_header(value)
            adr = llmemory.cast_ptr_to_adr(hdr)
            self.gcdata.gc.init_gc_object(adr, typeid)

        if find_gc_ptrs_in_type(TYPE):
            adr = llmemory.cast_ptr_to_adr(value._as_ptr())
            if isinstance(TYPE, (lltype.GcStruct, lltype.GcArray)):
                self.static_gc_roots.append(adr)
            else: 
                for a in gc_pointers_inside(value, adr):
                    self.addresses_of_static_ptrs_in_nongc.append(a)

    def gc_fields(self):
        return self._gc_fields

    def gc_field_values_for(self, obj):
        hdr = self.gcdata.gc.gcheaderbuilder.header_of_object(obj)
        HDR = self._gc_HDR
        return [getattr(hdr, fldname) for fldname in HDR._names]

    def offsets2table(self, offsets, TYPE):
        try:
            return self.offsettable_cache[TYPE]
        except KeyError:
            cachedarray = lltype.malloc(self.gcdata.OFFSETS_TO_GC_PTR,
                                        len(offsets), immortal=True)
            for i, value in enumerate(offsets):
                cachedarray[i] = value
            self.offsettable_cache[TYPE] = cachedarray
            return cachedarray

    def finish_tables(self):
        self.finished_tables = True
        table = lltype.malloc(self.gcdata.TYPE_INFO_TABLE,
                              len(self.type_info_list), immortal=True)
        for tableentry, newcontent in zip(table, self.type_info_list):
            for key, value in newcontent.items():
                setattr(tableentry, key, value)
        self.offsettable_cache = None

        # replace the type_info_table pointer in gcdata -- at this point,
        # the database is in principle complete, so it has already seen
        # the old (empty) array.  We need to force it to consider the new
        # array now.  It's a bit hackish as the old empty array will also
        # be generated in the C source, but that's a rather minor problem.

        # XXX because we call inputconst already in replace_malloc, we can't
        # modify the instance, we have to modify the 'rtyped instance'
        # instead.  horrors.  is there a better way?

        s_gcdata = self.translator.annotator.bookkeeper.immutablevalue(
            self.gcdata)
        r_gcdata = self.translator.rtyper.getrepr(s_gcdata)
        ll_instance = rmodel.inputconst(r_gcdata, self.gcdata).value
        ll_instance.inst_type_info_table = table
        #self.gcdata.type_info_table = table

        ll_static_roots = lltype.malloc(lltype.Array(llmemory.Address),
                                        len(self.static_gc_roots) +
                                            self.extra_static_slots,
                                        immortal=True)
        for i in range(len(self.static_gc_roots)):
            adr = self.static_gc_roots[i]
            ll_static_roots[i] = adr
        ll_instance.inst_static_roots = ll_static_roots

        ll_static_roots_inside = lltype.malloc(lltype.Array(llmemory.Address),
                                               len(self.addresses_of_static_ptrs_in_nongc),
                                               immortal=True)
        for i in range(len(self.addresses_of_static_ptrs_in_nongc)):
            ll_static_roots_inside[i] = self.addresses_of_static_ptrs_in_nongc[i]
        ll_instance.inst_static_root_start = llmemory.cast_ptr_to_adr(ll_static_roots_inside) + llmemory.ArrayItemsOffset(lltype.Array(llmemory.Address))
        ll_instance.inst_static_root_end = ll_instance.inst_static_root_start + llmemory.sizeof(llmemory.Address) * len(ll_static_roots_inside)

        newgcdependencies = []
        newgcdependencies.append(table)
        newgcdependencies.append(ll_static_roots)
        newgcdependencies.append(ll_static_roots_inside)
        return newgcdependencies

    def protect_roots(self, op, livevars, block, index=-1):
        livevars = [var for var in livevars if not var_ispyobj(var)]
        newops = list(self.push_roots(livevars))
        index = len(newops)
        newops.append(op)
        newops.extend(self.pop_roots(livevars))
        return newops, index

    def replace_direct_call(self, op, livevars, block):
        if self.collect_analyzer.analyze(op):
            return self.protect_roots(op, livevars, block)
        else:
            return [op], 0
    
    replace_indirect_call  = replace_direct_call

    def replace_malloc(self, op, livevars, block):
        if op.opname.startswith('flavored_'):
            flavor = op.args[0].value
            TYPE = op.args[1].value
        else:
            flavor = 'gc'
            TYPE = op.args[0].value

        if not flavor.startswith('gc'):
            return [op], 0
        c_can_collect = rmodel.inputconst(lltype.Bool,
                                          flavor != 'gc_nocollect')
        PTRTYPE = op.result.concretetype
        assert PTRTYPE.TO == TYPE
        type_id = self.get_type_id(TYPE)

        c_type_id = rmodel.inputconst(lltype.Signed, type_id)
        info = self.type_info_list[type_id]
        c_size = rmodel.inputconst(lltype.Signed, info["fixedsize"])
        if not op.opname.endswith('_varsize'):
            args = [self.malloc_fixedsize_ptr, self.c_const_gc, c_type_id,
                    c_size, c_can_collect]
        else:
            v_length = op.args[-1]
            c_ofstolength = rmodel.inputconst(lltype.Signed, info['ofstolength'])
            c_varitemsize = rmodel.inputconst(lltype.Signed, info['varitemsize'])
            args = [self.malloc_varsize_ptr, self.c_const_gc, c_type_id,
                    v_length, c_size, c_varitemsize, c_ofstolength,
                    c_can_collect]
        c_has_finalizer = rmodel.inputconst(
            lltype.Bool, bool(self.finalizer_funcptr_for_type(TYPE)))
        args.append(c_has_finalizer)
        v = varoftype(llmemory.GCREF)
        newop = SpaceOperation("direct_call", args, v)
        ops, index = self.protect_roots(newop, livevars, block,
                                        block.operations.index(op))
        ops.append(SpaceOperation("cast_opaque_ptr", [v], op.result))
        return ops

    replace_malloc_varsize = replace_malloc
    replace_flavored_malloc = replace_malloc
    replace_flavored_malloc_varsize = replace_malloc

    def replace_gc__collect(self, op, livevars, block):
        newop = SpaceOperation(
                    "direct_call",
                    [self.collect_ptr, self.c_const_gc],
                    op.result)
        ops, index = self.protect_roots(newop, livevars, block,
                                        block.operations.index(op))
        return ops

    def replace_gc_x_swap_pool(self, op, livevars, block):
        [v_malloced] = op.args
        newop = SpaceOperation("direct_call",
                               [self.x_swap_pool_ptr, self.c_const_gc,
                                                      v_malloced],
                               op.result)
        return [newop]

    def replace_gc_x_clone(self, op, livevars, block):
        [v_clonedata] = op.args
        newop = SpaceOperation("direct_call",
                               [self.x_clone_ptr, self.c_const_gc,
                                                  v_clonedata],
                               op.result)
        return [newop]

    def replace_gc_x_size_header(self, op, livevars, block):
        c_result = Constant(self.gcdata.gc.size_gc_header(), lltype.Signed)
        newop = SpaceOperation("same_as",
                               [c_result],
                               op.result)
        return [newop]

    def replace_gc_x_become(self, op, livevars, block):
        [v_target, v_source] = op.args
        newop = SpaceOperation("direct_call",
                               [self.x_become_ptr, self.c_const_gc,
                                v_target, v_source],
                               op.result)
        ops, index = self.protect_roots(newop, livevars, block,
                                        block.operations.index(op))
        return ops

    def push_alive_nopyobj(self, var):
        return []

    def pop_alive_nopyobj(self, var):
        return []

    def push_roots(self, vars):
        if self.push_root_ptr is None:
            return
        for var in vars:
            v = varoftype(llmemory.Address)
            yield SpaceOperation("cast_ptr_to_adr", [var], v)
            yield SpaceOperation("direct_call", [self.push_root_ptr, v],
                                 varoftype(lltype.Void))

    def pop_roots(self, vars):
        if self.pop_root_ptr is None:
            return
        for var in vars[::-1]:
            v = varoftype(lltype.Void)
            # XXX specific to non-moving collectors
            yield SpaceOperation("direct_call", [self.pop_root_ptr],
                                 v)
            #yield SpaceOperation("gc_reload_possibly_moved", [v, var],
            #                     varoftype(lltype.Void))

# XXX copied and modified from lltypelayout.py
def offsets_to_gc_pointers(TYPE):
    offsets = []
    if isinstance(TYPE, lltype.Struct):
        for name in TYPE._names:
            FIELD = getattr(TYPE, name)
            if isinstance(FIELD, lltype.Array):
                continue    # skip inlined array
            baseofs = llmemory.offsetof(TYPE, name)
            suboffsets = offsets_to_gc_pointers(FIELD)
            for s in suboffsets:
                try:
                    knownzero = s == 0
                except TypeError:
                    knownzero = False
                if knownzero:
                    offsets.append(baseofs)
                else:
                    offsets.append(baseofs + s)
        # sanity check
        #ex = lltype.Ptr(TYPE)._example()
        #adr = llmemory.cast_ptr_to_adr(ex)
        #for off in offsets:
        #    (adr + off)
    elif isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
        offsets.append(0)
    return offsets

# ____________________________________________________________


class StacklessFrameworkMinimalGCTransformer(MinimalGCTransformer):
    def replace_flavored_malloc(self, op, livevars, block):
        flavor = op.args[0].value
        if flavor == 'gc_nocollect':
            return self.parenttransformer.replace_flavored_malloc(op,
                                                                  livevars,
                                                                  block)
        else:
            return [op], 0
    replace_flavored_malloc_varsize = replace_flavored_malloc


class StacklessFrameworkGCTransformer(FrameworkGCTransformer):
    use_stackless = True
    extra_static_slots = 1     # for the stack_capture()'d frame
    MinimalGCTransformer = StacklessFrameworkMinimalGCTransformer

    def __init__(self, translator):
        FrameworkGCTransformer.__init__(self, translator)
        # and now, fun fun fun, we need to inline malloc_fixedsize
        # manually into all 'malloc' operation users, because inlining
        # it after it has been stackless transformed is both a Very
        # Bad Idea and forbidden by the fact that stackless transform
        # makes it self-recursive!  Argh.
        self.replace_and_inline_malloc_already_now()
        # nothing left to inline during code generation
        self.inline = False

    def replace_and_inline_malloc_already_now(self):
        for graph in self.translator.graphs:
            any_malloc = False
            for block in graph.iterblocks():
                if block.operations:
                    newops = []
                    for op in block.operations:
                        if op.opname.startswith('malloc'):
                            any_malloc = True
                            ops = self.replace_malloc(op, [], block)
                            if isinstance(ops, tuple):
                                ops = ops[0]
                            newops.extend(ops)
                        else:
                            newops.append(op)
                    block.operations = newops
            if any_malloc:
                self.inline_helpers(graph)

    def build_stack_root_iterator(self):
        from pypy.rpython.rstack import stack_capture
        sizeofaddr = llmemory.sizeof(llmemory.Address)
        gcdata = self.gcdata

        class StackRootIterator:
            _alloc_flavor_ = 'raw'

            def setup_root_stack():
                pass
            setup_root_stack = staticmethod(setup_root_stack)

            push_root = None
            pop_root = None

            def __init__(self):
                frame = llmemory.cast_ptr_to_adr(stack_capture())
                self.static_current = gcdata.static_root_start
                index = len(gcdata.static_roots)
                self.static_roots_index = index
                gcdata.static_roots[index-1] = frame

            def pop(self):
                while self.static_current != gcdata.static_root_end:
                    result = self.static_current
                    self.static_current += sizeofaddr
                    if result.address[0].address[0] != llmemory.NULL:
                        return result.address[0]
                i = self.static_roots_index
                if i > 0:
                    i -= 1
                    self.static_roots_index = i
                    p = lltype.direct_arrayitems(gcdata.static_roots)
                    p = lltype.direct_ptradd(p, i)
                    return llmemory.cast_ptr_to_adr(p)
                return llmemory.NULL

        return StackRootIterator

# ___________________________________________________________________
# calculate some statistics about the number of variables that need
# to be cared for across a call

relevant_ops = ["direct_call", "indirect_call", "malloc", "malloc_varsize"]

def filter_for_ptr(arg):
    return isinstance(arg.concretetype, lltype.Ptr)

def filter_for_nongcptr(arg):
    return isinstance(arg.concretetype, lltype.Ptr) and not arg.concretetype._needsgc()

def relevant_gcvars_block(block, filter=filter_for_ptr):
    import sets
    result = []
    def filter_ptr(args):
        return [arg for arg in args if filter(arg)]
    def live_vars_before(index):
        if index == 0:
            return sets.Set(filter_ptr(block.inputargs))
        op = block.operations[index - 1]
        result = live_vars_before(index - 1).union(filter_ptr(op.args + [op.result]))
        return result
    def live_vars_after(index):
        if index == len(block.operations) - 1:
            result = sets.Set()
            for exit in block.exits:
                result = result.union(filter_ptr(exit.args))
            return result
        op = block.operations[index + 1]
        result = live_vars_after(index + 1).union(filter_ptr(op.args + [op.result]))
        
        return result
    for i, op in enumerate(block.operations):
        if op.opname not in relevant_ops:
            continue
        live_before = live_vars_before(i)
        live_after = live_vars_after(i)
        result.append(len(live_before.intersection(live_after)))
    return result

def relevant_gcvars_graph(graph, filter=filter_for_ptr):
    result = []
    for block in graph.iterblocks():
        result += relevant_gcvars_block(block, filter)
    return result

def relevant_gcvars(t, filter=filter_for_ptr):
    result = []
    for graph in t.graphs:
        result.extend(relevant_gcvars_graph(graph, filter))
    return result

