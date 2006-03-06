import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant, \
     c_last_exception, FunctionGraph, Block, Link, checkgraph
from pypy.translator.unsimplify import insert_empty_block
from pypy.translator.translator import graphof
from pypy.annotation import model as annmodel
from pypy.rpython import rmodel, rptr, annlowlevel
from pypy.rpython.memory import gc, lladdress
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
import sets, os

EXCEPTION_RAISING_OPS = ['direct_call', 'indirect_call']

def var_needsgc(var):
    if hasattr(var, 'concretetype'):
        vartype = var.concretetype
        return isinstance(vartype, lltype.Ptr) and vartype._needsgc()
    else:
        # assume PyObjPtr
        return True

def var_ispyobj(var):
    if hasattr(var, 'concretetype'):
        if isinstance(var.concretetype, lltype.Ptr):
            return var.concretetype.TO is lltype.PyObject
        else:
            return False
    else:
        # assume PyObjPtr
        return True
    

class GCTransformer(object):
    finished = False

    def __init__(self, translator):
        self.translator = translator
        self.seen_graphs = {}
        if translator:
            self.mixlevelannotator = MixLevelHelperAnnotator(translator.rtyper)
        else:
            self.mixlevelannotator = None

    def get_lltype_of_exception_value(self):
        if self.translator is not None and self.translator.rtyper is not None:
            exceptiondata = self.translator.rtyper.getexceptiondata()
            return exceptiondata.lltype_of_exception_value
        else:
            return lltype.Ptr(lltype.PyObject)

    def transform(self, graphs):
        for graph in graphs:
            self.transform_graph(graph)

    def transform_graph(self, graph):
        if graph in self.seen_graphs:
            return
        self.seen_graphs[graph] = True
        self.links_to_split = {} # link -> vars to pop_alive across the link
        
        for block in graph.iterblocks():
            self.transform_block(block)
        for link, livecounts in self.links_to_split.iteritems():
            newops = []
            for var, livecount in livecounts.iteritems():
                for i in range(livecount):
                    newops.extend(self.pop_alive(var))
                for i in range(-livecount):
                    newops.extend(self.push_alive(var))
            if newops:
                if len(link.prevblock.exits) == 1:
                    link.prevblock.operations.extend(newops)
                else:
                    insert_empty_block(None, link, newops)

        v = Variable('vanishing_exc_value')
        v.concretetype = self.get_lltype_of_exception_value()
        graph.exc_cleanup = (v, self.pop_alive(v))

    def transform_block(self, block):
        newops = []
        livevars = [var for var in block.inputargs if var_needsgc(var)]
        livevars2cleanup = {}
        newops = []
        if block.isstartblock:
            for var in block.inputargs:
                if var_needsgc(var):
                    newops.extend(self.push_alive(var))
        # XXX this is getting obscure.  Maybe we should use the basic
        # graph-transforming capabilities of the RTyper instead, as we
        # seem to run into all the same problems as the ones we already
        # had to solve there.
        num_ops_after_exc_raising = 0
        for op in block.operations:
            num_ops_after_exc_raising = 0
            res = self.replacement_operations(op, livevars)
            try:
                ops, cleanup_before_exception = res
            except ValueError:
                ops, cleanup_before_exception, num_ops_after_exc_raising = res
            newops.extend(ops)
            op = ops[-1-num_ops_after_exc_raising]
            # XXX for now we assume that everything can raise
            if 1 or op.opname in EXCEPTION_RAISING_OPS:
                if tuple(livevars) in livevars2cleanup:
                    cleanup_on_exception = livevars2cleanup[tuple(livevars)]
                else:
                    cleanup_on_exception = []
                    for var in livevars:
                        cleanup_on_exception.extend(self.pop_alive(var))
                    cleanup_on_exception = tuple(cleanup_on_exception)
                    livevars2cleanup[tuple(livevars)] = cleanup_on_exception
                op.cleanup = tuple(cleanup_before_exception), cleanup_on_exception
            op = ops[-1]
            if var_needsgc(op.result):
                if op.opname not in ('direct_call', 'indirect_call') and not var_ispyobj(op.result):
                    lst = list(self.push_alive(op.result))
                    newops.extend(lst)
                    num_ops_after_exc_raising += len(lst)
                livevars.append(op.result)
        if len(block.exits) == 0:
            # everything is fine already for returnblocks and exceptblocks
            pass
        else:
            if block.exitswitch is c_last_exception:
                # if we're in a try block, the last operation must
                # remain the last operation, so don't add a pop_alive
                # to the block, even if the variable dies in all
                # linked blocks.
                deadinallexits = sets.Set([])
                if num_ops_after_exc_raising > 0:
                    # No place to put the remaining pending operations!
                    # Need a new block along the non-exceptional link.
                    # XXX test this.
                    tail = newops[-num_ops_after_exc_raising:]
                    del newops[-num_ops_after_exc_raising:]
                    link = block.exits[0]
                    assert link.exitcase is None
                    insert_empty_block(self.translator, link, tail)
            else:
                deadinallexits = sets.Set(livevars)
                for link in block.exits:
                    deadinallexits.difference_update(sets.Set(link.args))
            for var in deadinallexits:
                newops.extend(self.pop_alive(var))
            for link in block.exits:
                livecounts = dict.fromkeys(sets.Set(livevars) - deadinallexits, 1)
                if (block.exitswitch is c_last_exception and
                    link.exitcase is not None):
                    if livevars and livevars[-1] is block.operations[-1].result:
                        # if the last operation in the block raised an
                        # exception, it can't have returned anything that
                        # might need pop_aliving.
                        del livecounts[livevars[-1]]
                    for v in link.last_exception, link.last_exc_value:
                        if var_needsgc(v):
                            livecounts[v] = 1
                for v in link.args:
                    if v in livecounts:
                        livecounts[v] -= 1
                    elif var_needsgc(v):
                        assert isinstance(v, Constant)
                        livecounts[v] = -1
                self.links_to_split[link] = livecounts
        if newops:
            block.operations = newops

    def replacement_operations(self, op, livevars):
        m = getattr(self, 'replace_' + op.opname, None)
        if m:
            return m(op, livevars)
        else:
            return [op], []


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
        return [SpaceOperation("gc_push_alive_pyobj", [var], result)]

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
        return [SpaceOperation("gc_pop_alive_pyobj", [var], result)]

    def annotate_helper(self, ll_helper, ll_args, ll_result):
        assert not self.finished
        args_s = map(annmodel.lltype_to_annotation, ll_args)
        s_result = annmodel.lltype_to_annotation(ll_result)
        g = self.mixlevelannotator.getgraph(ll_helper, args_s, s_result)
        FUNC = lltype.FuncType(ll_args, ll_result)
        ptr = rmodel.inputconst(
            lltype.Ptr(FUNC),
            lltype.functionptr(FUNC, g.name, graph=g, isgchelper=True))
        return g, ptr.value

    def inittime_helper(self, ll_helper, ll_args, ll_result):
        graph, ptr = self.annotate_helper(ll_helper, ll_args, ll_result)
        self.seen_graphs[graph] = True
        return Constant(ptr, lltype.Ptr(lltype.FuncType(ll_args, ll_result)))

    def finish(self):
        self.finished = True
        if self.translator and self.translator.rtyper:
            self.mixlevelannotator.finish()
    
def exception_clean(graph):
    c = 0
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname in ('direct_call', 'indirect_call'):
                op.cleanup = None
                c += 1
    return c

class MinimalGCTransformer(GCTransformer):
    def push_alive_nopyobj(self, var):
        return []

    def pop_alive_nopyobj(self, var):
        return []


    # ----------------------------------------------------------------

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

class RefcountingGCTransformer(GCTransformer):

    gc_header_offset = gc.GCHeaderOffset(lltype.Struct("header", ("refcount", lltype.Signed)))

    def __init__(self, translator):
        super(RefcountingGCTransformer, self).__init__(translator)
        self.deallocator_graphs_needing_transforming = []
        self.graphs_needing_exception_cleaning = {}
        # create incref graph
        def ll_incref(adr):
            if adr:
                gcheader = adr - RefcountingGCTransformer.gc_header_offset
                gcheader.signed[0] = gcheader.signed[0] + 1
        def ll_decref(adr, dealloc):
            if adr:
                gcheader = adr - RefcountingGCTransformer.gc_header_offset
                refcount = gcheader.signed[0] - 1
                gcheader.signed[0] = refcount
                if refcount == 0:
                    dealloc(adr)
        def ll_no_pointer_dealloc(adr):
            llop.gc_free(lltype.Void, adr)
        if self.translator is not None and self.translator.rtyper is not None:
            self.increfptr = self.inittime_helper(
                ll_incref, [llmemory.Address], lltype.Void)
            self.decref_ptr = self.inittime_helper(
                ll_decref, [llmemory.Address, lltype.Ptr(ADDRESS_VOID_FUNC)],
                lltype.Void)
            self.graphs_needing_exception_cleaning[self.decref_ptr.value._obj.graph] = 1
            self.no_pointer_dealloc_ptr = self.inittime_helper(
                ll_no_pointer_dealloc, [llmemory.Address], lltype.Void)
        # cache graphs:
        self.decref_funcptrs = {}
        self.static_deallocator_funcptrs = {}
        self.dynamic_deallocator_funcptrs = {}
        self.queryptr2dynamic_deallocator_funcptr = {}
        

    def push_alive_nopyobj(self, var):
        adr1 = varoftype(llmemory.Address)
        result = [SpaceOperation("cast_ptr_to_adr", [var], adr1)]
        result.append(SpaceOperation("direct_call", [self.increfptr, adr1],
                                     varoftype(lltype.Void), cleanup=None))
        return result

    def pop_alive_nopyobj(self, var):
        PTRTYPE = var.concretetype
        adr1 = varoftype(llmemory.Address)
        result = [SpaceOperation("cast_ptr_to_adr", [var], adr1)]

        dealloc_fptr = self.dynamic_deallocation_funcptr_for_type(PTRTYPE.TO)
        cdealloc_fptr = rmodel.inputconst(
            lltype.Ptr(ADDRESS_VOID_FUNC), dealloc_fptr)
             
        result.append(SpaceOperation("direct_call",
                                     [self.decref_ptr, adr1, cdealloc_fptr],
                                     varoftype(lltype.Void), cleanup=None))
        return result

    def replace_setfield(self, op, livevars):
        if not var_needsgc(op.args[2]):
            return [op], []
        oldval = varoftype(op.args[2].concretetype)
        getoldvalop = SpaceOperation("getfield",
                                     [op.args[0], op.args[1]], oldval)
        result = [getoldvalop]
        result.extend(self.push_alive(op.args[2]))
        result.append(op)
        return result, self.pop_alive(oldval)

    def replace_setarrayitem(self, op, livevars):
        if not var_needsgc(op.args[2]):
            return [op], []
        oldval = varoftype(op.args[2].concretetype)
        getoldvalop = SpaceOperation("getarrayitem",
                                     [op.args[0], op.args[1]], oldval)
        result = [getoldvalop]
        result.extend(self.push_alive(op.args[2]))
        result.append(op)
        return result, self.pop_alive(oldval)

    def get_rtti(self, TYPE):
        if isinstance(TYPE, lltype.GcStruct):
            try:
                return lltype.getRuntimeTypeInfo(TYPE)
            except ValueError:
                pass
        return None

    def finish(self):
        super(RefcountingGCTransformer, self).finish()
        if self.translator and self.translator.rtyper:
            for g in self.deallocator_graphs_needing_transforming:
                MinimalGCTransformer(self.translator).transform_graph(g)
            for g, nsafecalls in self.graphs_needing_exception_cleaning.iteritems():
                n = exception_clean(g)
                assert n == nsafecalls

    def static_deallocation_funcptr_for_type(self, TYPE):
        if TYPE in self.static_deallocator_funcptrs:
            return self.static_deallocator_funcptrs[TYPE]
        #print_call_chain(self)
        def compute_pop_alive_ll_ops(hop):
            hop.llops.extend(self.pop_alive(hop.args_v[1]))
            hop.exception_cannot_occur()
            return hop.inputconst(hop.r_result.lowleveltype, hop.s_result.const)
        def ll_pop_alive(var):
            pass
        ll_pop_alive.compute_ll_ops = compute_pop_alive_ll_ops
        ll_pop_alive.llresult = lltype.Void

        rtti = self.get_rtti(TYPE) 
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
        try:
            destrptr(destr_v)
        except:
            try:
                os.write(2, "a destructor raised an exception, ignoring it\\n")
            except:
                pass
        refcount = gcheader.signed[0] - 1
        gcheader.signed[0] = refcount
        if refcount == 0:
%s
            llop.gc_free(lltype.Void, addr)
    except:
        pass
    llop.gc_restore_exception(lltype.Void, exc_instance)
        
""" % (body, )
        else:
            call_del = None
            body = '\n'.join(_static_deallocator_body_for_type('v', TYPE))
            src = ('def ll_deallocator(addr):\n    v = cast_adr_to_ptr(addr, PTR_TYPE)\n' +
                   body + '\n    llop.gc_free(lltype.Void, addr)\n')
        d = {'pop_alive': ll_pop_alive,
             'llop': llop,
             'lltype': lltype,
             'destrptr': destrptr,
             'gc_header_offset': RefcountingGCTransformer.gc_header_offset,
             'cast_adr_to_ptr': llmemory.cast_adr_to_ptr,
             'cast_pointer': lltype.cast_pointer,
             'PTR_TYPE': lltype.Ptr(TYPE),
             'DESTR_ARG': DESTR_ARG,
             'EXC_INSTANCE_TYPE': self.translator.rtyper.exceptiondata.lltype_of_exception_value,
             'os': py.std.os}
        exec src in d
        this = d['ll_deallocator']
        g, fptr = self.annotate_helper(this, [llmemory.Address], lltype.Void)
        # the produced deallocator graph does not need to be transformed
        self.seen_graphs[g] = True
        if destrptr:
            # however, the direct_call to the destructor needs to get
            # .cleanup attached
            self.deallocator_graphs_needing_transforming.append(g)

        self.static_deallocator_funcptrs[TYPE] = fptr
        for p in find_gc_ptrs_in_type(TYPE):
            self.static_deallocation_funcptr_for_type(p.TO)
        return fptr

    def dynamic_deallocation_funcptr_for_type(self, TYPE):
        if TYPE in self.dynamic_deallocator_funcptrs:
            return self.dynamic_deallocator_funcptrs[TYPE]
        #print_call_chain(self)

        rtti = self.get_rtti(TYPE)
        if rtti is None:
            p = self.static_deallocation_funcptr_for_type(TYPE)
            self.dynamic_deallocator_funcptrs[TYPE] = p
            return p
            
        queryptr = rtti._obj.query_funcptr
        if queryptr._obj in self.queryptr2dynamic_deallocator_funcptr:
            return self.queryptr2dynamic_deallocator_funcptr[queryptr._obj]
        
        RTTI_PTR = lltype.Ptr(lltype.RuntimeTypeInfo)
        QUERY_ARG_TYPE = lltype.typeOf(queryptr).TO.ARGS[0]
        def ll_dealloc(addr):
            # bump refcount to 1
            gcheader = addr - RefcountingGCTransformer.gc_header_offset
            gcheader.signed[0] = 1
            v = llmemory.cast_adr_to_ptr(addr, QUERY_ARG_TYPE)
            rtti = queryptr(v)
            gcheader.signed[0] = 0
            llop.gc_call_rtti_destructor(lltype.Void, rtti, addr)
        g, fptr = self.annotate_helper(ll_dealloc, [llmemory.Address], lltype.Void)
        self.graphs_needing_exception_cleaning[g] = 1
        self.seen_graphs[g] = True
        
        self.dynamic_deallocator_funcptrs[TYPE] = fptr
        self.queryptr2dynamic_deallocator_funcptr[queryptr._obj] = fptr
        return fptr

def varoftype(concretetype):
    var = Variable()
    var.concretetype = concretetype
    return var

def const_funcptr_fromgraph(graph):
    FUNC = lltype.FuncType([v.concretetype for v in graph.startblock.inputargs],
                           graph.returnblock.inputargs[0].concretetype)
    return rmodel.inputconst(lltype.Ptr(FUNC),
                             lltype.functionptr(FUNC, graph.name, graph=graph))

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
    elif isinstance(TYPE, lltype.Ptr) and TYPE.TO == lltype.PyObject:
        return True
    else:
        return False


class BoehmGCTransformer(GCTransformer):
    gc_header_offset = gc.GCHeaderOffset(lltype.Void)

    def __init__(self, translator):
        super(BoehmGCTransformer, self).__init__(translator)
        self.finalizer_funcptrs = {}

    def push_alive_nopyobj(self, var):
        return []

    def pop_alive_nopyobj(self, var):
        return []

    def get_rtti(self, TYPE):
        if isinstance(TYPE, lltype.GcStruct):
            try:
                return lltype.getRuntimeTypeInfo(TYPE)
            except ValueError:
                pass
        return None

    def finish(self):
        self.mixlevelannotator.finish()
        for fptr in self.finalizer_funcptrs.itervalues():
            if fptr:
                g = fptr._obj.graph
                MinimalGCTransformer(self.translator).transform_graph(g)

    def finalizer_funcptr_for_type(self, TYPE):
        if TYPE in self.finalizer_funcptrs:
            return self.finalizer_funcptrs[TYPE]
        
        def compute_pop_alive_ll_ops(hop):
            hop.llops.extend(self.pop_alive(hop.args_v[1]))
            return hop.inputconst(hop.r_result.lowleveltype, hop.s_result.const)
        def ll_pop_alive(var):
            pass
        ll_pop_alive.compute_ll_ops = compute_pop_alive_ll_ops
        ll_pop_alive.llresult = lltype.Void
        
        rtti = self.get_rtti(TYPE)
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
            d = {'pop_alive':ll_pop_alive,
                 'PTR_TYPE':lltype.Ptr(TYPE),
                 'cast_adr_to_ptr': llmemory.cast_adr_to_ptr}
            src = ("def ll_finalizer(addr):\n"
                   "    v = cast_adr_to_ptr(addr, PTR_TYPE)\n"
                   "%s\n")%(static_body,)
            exec src in d
            g, fptr = self.annotate_helper(d['ll_finalizer'], [llmemory.Address], lltype.Void)
        elif destrptr:
            EXC_INSTANCE_TYPE = self.translator.rtyper.exceptiondata.lltype_of_exception_value
            def ll_finalizer(addr):
                exc_instance = llop.gc_fetch_exception(EXC_INSTANCE_TYPE)
                try:
                    v = llmemory.cast_adr_to_ptr(addr, DESTR_ARG)
                    destrptr(v)
                except:
                    try:
                        os.write(2, "a destructor raised an exception, ignoring it\n")
                    except:
                        pass
                llop.gc_restore_exception(lltype.Void, exc_instance)
            g, fptr = self.annotate_helper(ll_finalizer, [llmemory.Address], lltype.Void)
        else:
            g = fptr = None

        if g:
            self.seen_graphs[g] = True
        self.finalizer_funcptrs[TYPE] = fptr
        return fptr

class FrameworkGCTransformer(BoehmGCTransformer):

    def __init__(self, translator):
        super(FrameworkGCTransformer, self).__init__(translator)
        class GCData(object):
            from pypy.rpython.memory.gc import MarkSweepGC as GCClass
            startheapsize = 640*1024    # XXX adjust
            rootstacksize = 640*1024    # XXX adjust

            # types of the GC information tables
            OFFSETS_TO_GC_PTR = lltype.Array(lltype.Signed)
            TYPE_INFO = lltype.Struct("type_info",
                ("fixedsize",   lltype.Signed),
                ("ofstoptrs",   lltype.Ptr(OFFSETS_TO_GC_PTR)),
                ("varitemsize", lltype.Signed),
                ("ofstovar",    lltype.Signed),
                ("ofstolength", lltype.Signed),
                ("varofstoptrs",lltype.Ptr(OFFSETS_TO_GC_PTR)),
                )
            TYPE_INFO_TABLE = lltype.Array(TYPE_INFO)

        def q_is_varsize(typeid):
            return gcdata.type_info_table[typeid].varitemsize != 0

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
        self.gcdata = gcdata
        self.type_info_list = []
        self.id_of_type = {}      # {LLTYPE: type_id}
        self.offsettable_cache = {}
        self.malloc_fnptr_cache = {}

        sizeofaddr = llmemory.sizeof(llmemory.Address)
        from pypy.rpython.memory.lladdress import NULL

        class StackRootIterator:
            _alloc_flavor_ = 'raw'
            def __init__(self):
                self.current = gcdata.root_stack_top

            def pop(self):
                while self.current != gcdata.root_stack_base:
                    self.current -= sizeofaddr
                    if self.current.address[0] != NULL:
                        return self.current
                return NULL

        def frameworkgc_setup():
            # run-time initialization code
            stackbase = lladdress.raw_malloc(GCData.rootstacksize)
            gcdata.root_stack_top  = stackbase
            gcdata.root_stack_base = stackbase
            gcdata.gc = GCData.GCClass(GCData.startheapsize, StackRootIterator)
            gcdata.gc.set_query_functions(
                q_is_varsize,
                q_offsets_to_gc_pointers,
                q_fixed_size,
                q_varsize_item_sizes,
                q_varsize_offset_to_variable_part,
                q_varsize_offset_to_length,
                q_varsize_offsets_to_gcpointers_in_var_part)

        def push_root(addr):
            top = gcdata.root_stack_top
            top.address[0] = addr
            gcdata.root_stack_top = top + sizeofaddr

        def pop_root():
            top = gcdata.root_stack_top - sizeofaddr
            result = top.address[0]
            gcdata.root_stack_top = top
            return result

        bk = self.translator.annotator.bookkeeper

        # the point of this little dance is to not annotate
        # self.gcdata.type_info_table as a constant.
        data_classdef = bk.getuniqueclassdef(GCData)
        data_classdef.generalize_attr(
            'type_info_table',
            annmodel.SomePtr(lltype.Ptr(GCData.TYPE_INFO_TABLE)))
        
        annhelper = annlowlevel.MixLevelHelperAnnotator(self.translator.rtyper)
        frameworkgc_setup_graph = annhelper.getgraph(frameworkgc_setup, [],
                                                     annmodel.s_None)
        push_root_graph = annhelper.getgraph(push_root,
                                             [annmodel.SomeAddress()],
                                             annmodel.s_None)
        pop_root_graph = annhelper.getgraph(pop_root, [],
                                            annmodel.SomeAddress())

        classdef = bk.getuniqueclassdef(GCData.GCClass)
        s_gcdata = annmodel.SomeInstance(classdef)
        malloc_graph = annhelper.getgraph(GCData.GCClass.malloc.im_func,
                                          [s_gcdata,
                                           annmodel.SomeInteger(nonneg=True),
                                           annmodel.SomeInteger(nonneg=True)],
                                          annmodel.SomeAddress())
        annhelper.finish()   # at this point, annotate all mix-level helpers
        self.frameworkgc_setup_ptr = self.graph2funcptr(frameworkgc_setup_graph,
                                                        attach_empty_cleanup=True)
        self.push_root_ptr = self.graph2funcptr(push_root_graph)
        self.pop_root_ptr  = self.graph2funcptr(pop_root_graph)
        self.malloc_ptr    = self.graph2funcptr(malloc_graph, True)

    def graph2funcptr(self, graph, attach_empty_cleanup=False):
        self.seen_graphs[graph] = True
        if attach_empty_cleanup:
            MinimalGCTransformer(self.translator).transform_graph(graph)
        return const_funcptr_fromgraph(graph)

    def get_type_id(self, TYPE):
        try:
            return self.id_of_type[TYPE]
        except KeyError:
            assert not self.finished
            assert isinstance(TYPE, (lltype.GcStruct, lltype.GcArray))
            # Record the new type_id description as a small dict for now.
            # It will be turned into a Struct("type_info") in finish()
            type_id = len(self.type_info_list)
            info = {}
            self.type_info_list.append(info)
            self.id_of_type[TYPE] = type_id
            offsets = offsets_to_gc_pointers(TYPE)
            info["ofstoptrs"] = self.offsets2table(offsets)
            if not TYPE._is_varsize():
                info["fixedsize"] = llmemory.sizeof(TYPE)
            else:
                info["fixedsize"] = llmemory.sizeof(TYPE, 0)
                if isinstance(TYPE, lltype.Struct):
                    ARRAY = TYPE._flds[TYPE._arrayfld]
                    ofs1 = llmemory.offsetof(TYPE, TYPE._arrayfld)
                    info["ofstolength"] = ofs1
                    info["ofstovar"] = ofs1 + llmemory.itemoffsetof(ARRAY, 0)
                else:
                    ARRAY = TYPE
                    info["ofstolength"] = 0
                    info["ofstovar"] = llmemory.itemoffsetof(TYPE, 0)
                assert isinstance(ARRAY, lltype.Array)
                offsets = offsets_to_gc_pointers(ARRAY.OF)
                info["varofstoptrs"] = self.offsets2table(offsets)
                info["varitemsize"] = llmemory.sizeof(ARRAY.OF)
            return type_id

    def offsets2table(self, offsets):
        key = tuple(offsets)
        try:
            return self.offsettable_cache[key]
        except KeyError:
            cachedarray = lltype.malloc(self.gcdata.OFFSETS_TO_GC_PTR,
                                        len(offsets), immortal=True)
            for i, value in enumerate(offsets):
                cachedarray[i] = value
            self.offsettable_cache[key] = cachedarray
            return cachedarray

    def finish(self):
        newgcdependencies = super(FrameworkGCTransformer, self).finish()
        if self.type_info_list is not None:
            # XXX this is a kind of sledgehammer-wallnut approach to make sure
            # all types get an ID.
            for graph in self.translator.graphs:
                for block in graph.iterblocks():
                    for v in block.getvariables() + block.getconstants():
                        t = getattr(v, 'concretetype', None)
                        if t is None:
                            continue
                        if isinstance(t, lltype.Ptr) and t.TO != lltype.PyObject and \
                               t._needsgc():
                            self.get_type_id(v.concretetype.TO)

            table = lltype.malloc(self.gcdata.TYPE_INFO_TABLE,
                                  len(self.type_info_list), immortal=True)
            for tableentry, newcontent in zip(table, self.type_info_list):
                for key, value in newcontent.items():
                    setattr(tableentry, key, value)
            self.type_info_list = None
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
            
            newgcdependencies = newgcdependencies or []
            newgcdependencies.append(table)
        return newgcdependencies

    def protect_roots(self, op, livevars):
        livevars = [var for var in livevars if not var_ispyobj(var)]
        newops = list(self.push_roots(livevars))
        newops.append(op)
        return newops, tuple(self.pop_roots(livevars))

    replace_direct_call    = protect_roots
    replace_indirect_call  = protect_roots

    def replace_malloc(self, op, livevars):
        TYPE = op.args[0].value
        PTRTYPE = op.result.concretetype
        assert PTRTYPE.TO == TYPE
        type_id = self.get_type_id(TYPE)

        v = varoftype(llmemory.Address)
        c_type_id = rmodel.inputconst(lltype.Signed, type_id)
        if len(op.args) == 1:
            v_length = rmodel.inputconst(lltype.Signed, 0)
        else:
            v_length = op.args[1]

        # surely there's a better way of doing this?
        s_gcdata = self.translator.annotator.bookkeeper.immutablevalue(self.gcdata)
        r_gcdata = self.translator.rtyper.getrepr(s_gcdata)
        s_gc = self.translator.annotator.bookkeeper.valueoftype(self.gcdata.GCClass)
        r_gc = self.translator.rtyper.getrepr(s_gc)
        
        newop0 = SpaceOperation(
            "getfield",
            [rmodel.inputconst(r_gcdata, self.gcdata), Constant("inst_gc")],
            varoftype(r_gc.lowleveltype))
        newop = SpaceOperation("direct_call",
                               [self.malloc_ptr, newop0.result, c_type_id, v_length],
                               v)
        ops, finally_ops = self.protect_roots(newop, livevars)
        ops.insert(0, newop0)
        ops.append(SpaceOperation("cast_adr_to_ptr", [v], op.result))
        return ops, finally_ops, 1

    replace_malloc_varsize = replace_malloc

    def push_alive_nopyobj(self, var):
        return []

    def pop_alive_nopyobj(self, var):
        return []

    def push_roots(self, vars):
        for var in vars:
            v = varoftype(llmemory.Address)
            yield SpaceOperation("cast_ptr_to_adr", [var], v)
            yield SpaceOperation("direct_call", [self.push_root_ptr, v],
                                 varoftype(lltype.Void), cleanup=None)

    def pop_roots(self, vars):
        for var in vars[::-1]:
            v = varoftype(llmemory.Address)
            yield SpaceOperation("direct_call", [self.pop_root_ptr],
                                 v, cleanup=None)
            yield SpaceOperation("gc_reload_possibly_moved", [v, var],
                                 varoftype(lltype.Void))

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
                if s == 0:
                    offsets.append(baseofs)
                else:
                    offsets.append(baseofs + s)
    elif (isinstance(TYPE, lltype.Ptr) and TYPE._needsgc() and
          TYPE.TO is not lltype.PyObject):
        offsets.append(0)
    return offsets

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

