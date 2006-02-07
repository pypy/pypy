import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant, \
     c_last_exception, FunctionGraph, Block, Link, checkgraph
from pypy.translator.unsimplify import insert_empty_block
from pypy.translator.translator import graphof
from pypy.annotation import model as annmodel
from pypy.rpython import rmodel, objectmodel, rptr
from pypy.rpython.memory import gc
import sets

"""
thought experiments

'setfield' obj field value ->
  a1 <- 'cast_ptr_to_adr' obj
  a2 <- 'cast_ptr_to_adr' value
  'direct_call' write_barrier a1, offset(TYPE(obj), field), a2

operations that need hooks:

setfield, setarrayitem, direct_call, indirect_call, malloc, getfield,
getarrayitem, getsubstruct?

push_alive, pop_alive,

"""

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
    def __init__(self, translator):
        self.translator = translator
        self.seen_graphs = {}

    def transform(self, graphs):
        for graph in graphs:
            self.transform_graph(graph)

    def transform_graph(self, graph):
        if graph in self.seen_graphs:
            return
        self.seen_graphs[graph] = True
        self.links_to_split = {} # link -> vars to pop_alive across the link

        newops = []
        for var in graph.startblock.inputargs:
            if var_needsgc(var):
                newops.extend(self.push_alive(var))
        graph.startblock.operations[0:0] = newops
        
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
        if self.translator.rtyper is not None:
            self.translator.rtyper.specialize_more_blocks()

    def transform_block(self, block):
        newops = []
        livevars = [var for var in block.inputargs if var_needsgc(var)]
        for op in block.operations:
            newops.extend(self.replacement_operations(op))
            # XXX for now we assume that everything can raise
            if 1 or op.opname in EXCEPTION_RAISING_OPS:
                cleanup_on_exception = []
                for var in livevars:
                    cleanup_on_exception.extend(self.pop_alive(var))
                op.cleanup = cleanup_on_exception
            if var_needsgc(op.result):
                if op.opname not in ('direct_call', 'indirect_call') and not var_ispyobj(op.result):
                    newops.extend(self.push_alive(op.result))
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

    def replacement_operations(self, op):
        m = getattr(self, 'replace_' + op.opname, None)
        if m:
            return m(op)
        else:
            return [op]


    def push_alive(self, var):
        if var_ispyobj(var):
            return self.push_alive_pyobj(var)
        else:
            return self.push_alive_nopyobj(var)

    def push_alive_nopyobj(self, var):
        result = Variable()
        result.concretetype = lltype.Void
        return [SpaceOperation("gc_push_alive", [var], result)]

    def push_alive_pyobj(self, var):
        result = Variable()
        result.concretetype = lltype.Void
        return [SpaceOperation("gc_push_alive_pyobj", [var], result)]

    def pop_alive(self, var):
        if var_ispyobj(var):
            return self.pop_alive_pyobj(var)
        else:
            return self.pop_alive_nopyobj(var)

    def pop_alive_nopyobj(self, var):
        result = Variable()
        result.concretetype = lltype.Void
        return [SpaceOperation("gc_pop_alive", [var], result)]

    def pop_alive_pyobj(self, var):
        result = Variable()
        result.concretetype = lltype.Void
        return [SpaceOperation("gc_pop_alive_pyobj", [var], result)]

    def free(self, var):
        result = Variable()
        result.concretetype = lltype.Void
        return [SpaceOperation("gc_free", [var], result)]        
    

    # ----------------------------------------------------------------


class RefcountingGCTransformer(GCTransformer):

    gc_header_offset = gc.GCHeaderOffset(lltype.Struct("header", ("refcount", lltype.Signed)))

    def __init__(self, translator):
        super(RefcountingGCTransformer, self).__init__(translator)
        # create incref graph
        def incref(adr):
            if adr:
                gcheader = adr - RefcountingGCTransformer.gc_header_offset
                gcheader.signed[0] = gcheader.signed[0] + 1
        self.increfgraph = self.translator.rtyper.annotate_helper(
            incref, [annmodel.SomeAddress()])
        self.translator.rtyper.specialize_more_blocks()
        self.increfptr = const_funcptr_fromgraph(self.increfgraph)
        self.seen_graphs[self.increfgraph] = True
        # cache graphs:
        self.decref_graphs = {}
        self.static_deallocator_graphs = {}
        self.dynamic_deallocator_graphs = {}

    def push_alive_nopyobj(self, var):
        adr1 = varoftype(llmemory.Address)
        result = [SpaceOperation("cast_ptr_to_adr", [var], adr1)]
        result.append(SpaceOperation("direct_call", [self.increfptr, adr1],
                                     varoftype(lltype.Void)))
        return result

    def pop_alive_nopyobj(self, var):
        PTRTYPE = var.concretetype
        decref_graph = self.decref_graph_for_type(PTRTYPE.TO)
        FUNC = lltype.FuncType([PTRTYPE], lltype.Void)
        const_fptr = rmodel.inputconst(
             lltype.Ptr(FUNC), lltype.functionptr(FUNC, decref_graph.name, graph=decref_graph))
        return [SpaceOperation("direct_call", [const_fptr, var], varoftype(lltype.Void))]

    def replace_setfield(self, op):
        if not var_needsgc(op.args[2]):
            return [op]
        oldval = Variable()
        oldval.concretetype = op.args[2].concretetype
        getoldvalop = SpaceOperation("getfield", [op.args[0], op.args[1]], oldval)
        result = [getoldvalop]
        result.extend(self.pop_alive(oldval))
        result.extend(self.push_alive(op.args[2]))
        result.append(op)
        return result

    def replace_setarrayitem(self, op):
        if not var_needsgc(op.args[2]):
            return [op]
        oldval = Variable()
        oldval.concretetype = op.args[2].concretetype
        getoldvalop = SpaceOperation("getarrayitem",
                                     [op.args[0], op.args[1]], oldval)
        result = [getoldvalop]
        result.extend(self.pop_alive(oldval))
        result.extend(self.push_alive(op.args[2]))
        result.append(op)
        return result

    def get_rtti(self, TYPE):
        if isinstance(TYPE, lltype.Struct):
            try:
                return lltype.getRuntimeTypeInfo(TYPE)
            except ValueError:
                pass
        return None

    def _static_deallocator_body_for_type(self, v, TYPE, depth=1):
        if isinstance(TYPE, lltype.Array):
            
            inner = list(self._static_deallocator_body_for_type('v_%i'%depth, TYPE.OF, depth+1))
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
                inner = list(self._static_deallocator_body_for_type(
                    v + '_' + name, TYPE._flds[name], depth))
                if inner:
                    yield '    '*depth + v + '_' + name + ' = ' + v + '.' + name
                    for line in inner:
                        yield line
        elif isinstance(TYPE, lltype.Ptr):
            yield '    '*depth + 'pop_alive(%s)'%v

    def static_deallocation_graph_for_type(self, TYPE):
        if TYPE in self.static_deallocator_graphs:
            return self.static_deallocator_graphs[TYPE]
        PTRS = find_gc_ptrs_in_type(TYPE)
        def compute_pop_alive_ll_ops(hop):
            hop.llops.extend(self.pop_alive(hop.args_v[1]))
            return hop.inputconst(hop.r_result.lowleveltype, hop.s_result.const)
        def pop_alive(var):
            pass
        pop_alive.compute_ll_ops = compute_pop_alive_ll_ops
        pop_alive.llresult = lltype.Void
        def compute_destroy_ll_ops(hop):
            hop.llops.extend(self.free(hop.args_v[1]))
            return hop.inputconst(hop.r_result.lowleveltype, hop.s_result.const)
        def destroy(var):
            pass
        destroy.compute_ll_ops = compute_destroy_ll_ops
        destroy.llresult = lltype.Void

        rtti = self.get_rtti(TYPE) 
        if rtti is not None and hasattr(rtti._obj, 'destructor_funcptr'):
            destrptr = rtti._obj.destructor_funcptr
        else:
            destrptr = None

        if destrptr is not None:
            body = '\n'.join(self._static_deallocator_body_for_type('v', TYPE, 2))
            src = """
def deallocator(addr):
    v = cast_adr_to_ptr(addr, PTR_TYPE)
    gcheader = addr - gc_header_offset
    # refcount is at zero, temporarily bump it to 1:
    gcheader.signed[0] = 1
    try:
        destrptr(v)
    except Exception:
        os.write(0, "a destructor raised an exception, ignoring it")
    refcount = gcheader.signed[0] - 1
    gcheader.signed[0] = refcount
    if refcount == 0:
%s
        destroy(v)
""" % (body, )
        else:
            call_del = None
            body = '\n'.join(self._static_deallocator_body_for_type('v', TYPE))
            src = ('def deallocator(addr):\n    v = cast_adr_to_ptr(addr, PTR_TYPE)\n' +
                   body + '\n    destroy(v)\n')
        d = {'pop_alive': pop_alive,
             'destroy': destroy,
             'destrptr': destrptr,
             'gc_header_offset': RefcountingGCTransformer.gc_header_offset,
             'cast_adr_to_ptr': objectmodel.cast_adr_to_ptr,
             'PTR_TYPE': lltype.Ptr(TYPE),
             'os': py.std.os}
        print
        print src
        print
        exec src in d
        this = d['deallocator']
        g = self.translator.rtyper.annotate_helper(this, [llmemory.Address])
        # the produced deallocator graph does not need to be transformed
        self.seen_graphs[g] = True
        opcount = 0
        for block in g.iterblocks():
            opcount += len(block.operations)
        if opcount == 0:
            result = None
        else:
            result = g
        self.static_deallocator_graphs[TYPE] = result
        for PTR in PTRS:
            # as a side effect the graphs are cached
            self.static_deallocation_graph_for_type(PTR.TO)
        return result

    def dynamic_deallocation_graph_for_type(self, TYPE):
        if TYPE in self.dynamic_deallocator_graphs:
            return self.dynamic_deallocator_graphs[TYPE]

        rtti = self.get_rtti(TYPE)
        assert rtti is not None
        queryptr = rtti._obj.query_funcptr
        RTTI_PTR = lltype.Ptr(lltype.RuntimeTypeInfo)
        QUERY_ARG_TYPE = lltype.typeOf(queryptr).TO.ARGS[0]
        def call_destructor_for_rtti(v, rtti):
            pass
        def call_destructor_for_rtti_compute_ops(hop):
            _, v_addr, v_rtti = hop.inputargs(lltype.Void, llmemory.Address, hop.args_r[2])
            return hop.genop("gc_call_rtti_destructor", [v_rtti, v_addr],
                             resulttype = lltype.Void) 
        call_destructor_for_rtti.llresult = lltype.Void
        call_destructor_for_rtti.compute_ll_ops = call_destructor_for_rtti_compute_ops
        def dealloc(addr):
            # bump refcount to 1
            gcheader = addr - RefcountingGCTransformer.gc_header_offset
            gcheader.signed[0] = 1
            v = objectmodel.cast_adr_to_ptr(addr, QUERY_ARG_TYPE)
            rtti = queryptr(v)
            gcheader.signed[0] = 0
            call_destructor_for_rtti(addr, rtti)
        g = self.translator.rtyper.annotate_helper(dealloc, [llmemory.Address])
        self.dynamic_deallocator_graphs[TYPE] = g
        self.seen_graphs[g] = True
        return g

    def decref_graph_for_type(self, TYPE):
        if TYPE in self.decref_graphs:
            return self.decref_graphs[TYPE]
        need_dynamic_destructor = False
        rtti = self.get_rtti(TYPE)
        if rtti is None:
            need_dynamic_destructor = False
        else:
            need_dynamic_destructor = True
        if not need_dynamic_destructor:
            graph = self.static_deallocation_graph_for_type(TYPE)
        else:
            graph = self.dynamic_deallocation_graph_for_type(TYPE)
        FUNC = lltype.FuncType([llmemory.Address], lltype.Void)
        const_funcptr = rmodel.inputconst(lltype.Ptr(FUNC),
                                 lltype.functionptr(FUNC, graph.name, graph=graph))
        def compute_destructor_ll_ops(hop):
            assert hop.args_v[1].concretetype.TO == TYPE
            addr = hop.genop("cast_ptr_to_adr", [hop.args_v[1]], resulttype=llmemory.Address)
            return hop.genop("direct_call", [const_funcptr, addr],
                             resulttype=lltype.Void)
        def destructor(var):
            pass
        destructor.compute_ll_ops = compute_destructor_ll_ops
        destructor.llresult = lltype.Void
        def decref(obj):
            if not obj:
                return
            objadr = objectmodel.cast_ptr_to_adr(obj)
            gcheader = objadr - RefcountingGCTransformer.gc_header_offset
            refcount = gcheader.signed[0] - 1
            gcheader.signed[0] = refcount
            if refcount == 0:
                destructor(obj)
        g = self.translator.rtyper.annotate_helper(decref, [lltype.Ptr(TYPE)])
        # the produced deallocator graph does not need to be transformed
        self.seen_graphs[g] = True
        self.decref_graphs[TYPE] = g
        return g

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
