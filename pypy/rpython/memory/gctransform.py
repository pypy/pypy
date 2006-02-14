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

        v = Variable('vanishing_exc_value')
        v.concretetype = self.get_lltype_of_exception_value()
        graph.exc_cleanup = (v, self.pop_alive(v))
                    
        self.specialize_more_blocks()

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

    def specialize_more_blocks(self):
        if self.translator is not None and self.translator.rtyper is not None:
            self.translator.rtyper.specialize_more_blocks()

    annotate_helper_count = 0
    def annotate_helper(self, ll_helper, args):
##         import sys, time
##         self.annotate_helper_count += 1
##         f = sys._getframe(1)
##         TYPE = f.f_locals.get('TYPE')
##         print "ahc", self.annotate_helper_count, f.f_code.co_name, 
##         if TYPE:
##             print repr(TYPE),
##         T = time.time()
        r = self.translator.rtyper.annotate_helper(ll_helper, args)
##         print time.time() - T
        return r
    

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
    elif isinstance(TYPE, lltype.Ptr):
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
        # create incref graph
        def incref(adr):
            if adr:
                gcheader = adr - RefcountingGCTransformer.gc_header_offset
                gcheader.signed[0] = gcheader.signed[0] + 1
        def decref(adr, dealloc):
            if adr:
                gcheader = adr - RefcountingGCTransformer.gc_header_offset
                refcount = gcheader.signed[0] - 1
                gcheader.signed[0] = refcount
                if refcount == 0:
                    dealloc(adr)
        def no_pointer_dealloc(adr):
            objectmodel.llop.gc_free(lltype.Void, adr)
        if self.translator is not None and self.translator.rtyper is not None:
            increfgraph = self.annotate_helper(
                incref, [annmodel.SomeAddress()])
            self.translator.rtyper.specialize_more_blocks()
            self.increfptr = const_funcptr_fromgraph(increfgraph)
            self.seen_graphs[increfgraph] = True
            
            decref_graph = self.annotate_helper(
                decref, [annmodel.SomeAddress(), lltype.Ptr(ADDRESS_VOID_FUNC)])
            self.translator.rtyper.specialize_more_blocks()
            self.decref_ptr = const_funcptr_fromgraph(decref_graph)
            self.seen_graphs[decref_graph] = True

            no_pointer_dealloc_graph = self.annotate_helper(
                no_pointer_dealloc, [annmodel.SomeAddress()])
            self.translator.rtyper.specialize_more_blocks()
            self.no_pointer_dealloc_ptr = lltype.functionptr(
                ADDRESS_VOID_FUNC, no_pointer_dealloc_graph.name,
                graph=no_pointer_dealloc_graph)
            self.seen_graphs[no_pointer_dealloc_graph] = True
        self.deallocator_graphs_needing_transforming = []
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
        cdealloc_fptr = rmodel.inputconst(
            lltype.Ptr(ADDRESS_VOID_FUNC), dealloc_fptr)
             
        result.append(SpaceOperation("direct_call",
                                     [self.decref_ptr, adr1, cdealloc_fptr],
                                     varoftype(lltype.Void)))
        return result

    def replace_setfield(self, op):
        if not var_needsgc(op.args[2]):
            return [op]
        oldval = Variable()
        oldval.concretetype = op.args[2].concretetype
        getoldvalop = SpaceOperation("getfield",
                                     [op.args[0], op.args[1]], oldval)
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
        if isinstance(TYPE, lltype.GcStruct):
            try:
                return lltype.getRuntimeTypeInfo(TYPE)
            except ValueError:
                pass
        return None

    def static_deallocation_funcptr_for_type(self, TYPE):
        if TYPE in self.static_deallocator_funcptrs:
            return self.static_deallocator_funcptrs[TYPE]
        fptr = self._static_deallocation_funcptr_for_type(TYPE)
        self.specialize_more_blocks()
        for g in self.deallocator_graphs_needing_transforming:
            MinimalGCTransformer(self.translator).transform_graph(g)
        self.deallocator_graphs_needing_transforming = []
        return fptr

    def _static_deallocation_funcptr_for_type(self, TYPE):
        if TYPE in self.static_deallocator_funcptrs:
            return self.static_deallocator_funcptrs[TYPE]
        #print_call_chain(self)
        def compute_pop_alive_ll_ops(hop):
            hop.llops.extend(self.pop_alive(hop.args_v[1]))
            return hop.inputconst(hop.r_result.lowleveltype, hop.s_result.const)
        def pop_alive(var):
            pass
        pop_alive.compute_ll_ops = compute_pop_alive_ll_ops
        pop_alive.llresult = lltype.Void

        rtti = self.get_rtti(TYPE) 
        if rtti is not None and hasattr(rtti._obj, 'destructor_funcptr'):
            destrptr = rtti._obj.destructor_funcptr
            DESTR_ARG = lltype.typeOf(destrptr).TO.ARGS[0]
        else:
            destrptr = None
            DESTR_ARG = None

        if destrptr is None and not find_gc_ptrs_in_type(TYPE):
            #print repr(TYPE)[:80], 'is dealloc easy'
            p = self.no_pointer_dealloc_ptr
            self.static_deallocator_funcptrs[TYPE] = p
            return p

        if destrptr is not None:
            body = '\n'.join(_static_deallocator_body_for_type('v', TYPE, 2))
            src = """
def deallocator(addr):
    v = cast_adr_to_ptr(addr, PTR_TYPE)
    gcheader = addr - gc_header_offset
    # refcount is at zero, temporarily bump it to 1:
    gcheader.signed[0] = 1
    destr_v = cast_pointer(DESTR_ARG, v)
    try:
        destrptr(destr_v)
    except Exception:
        os.write(2, "a destructor raised an exception, ignoring it\\n")
    refcount = gcheader.signed[0] - 1
    gcheader.signed[0] = refcount
    if refcount == 0:
%s
        objectmodel.llop.gc_free(lltype.Void, addr)
""" % (body, )
        else:
            call_del = None
            body = '\n'.join(_static_deallocator_body_for_type('v', TYPE))
            src = ('def deallocator(addr):\n    v = cast_adr_to_ptr(addr, PTR_TYPE)\n' +
                   body + '\n    objectmodel.llop.gc_free(lltype.Void, addr)\n')
        d = {'pop_alive': pop_alive,
             'objectmodel': objectmodel,
             'lltype': lltype,
             'destrptr': destrptr,
             'gc_header_offset': RefcountingGCTransformer.gc_header_offset,
             'cast_adr_to_ptr': objectmodel.cast_adr_to_ptr,
             'cast_pointer': lltype.cast_pointer,
             'PTR_TYPE': lltype.Ptr(TYPE),
             'DESTR_ARG': DESTR_ARG,
             'os': py.std.os}
        exec src in d
        this = d['deallocator']
        g = self.annotate_helper(this, [llmemory.Address])
        # the produced deallocator graph does not need to be transformed
        self.seen_graphs[g] = True
        if destrptr:
            # however, the direct_call to the destructor needs to get
            # .cleanup attached
            self.deallocator_graphs_needing_transforming.append(g)

        fptr = lltype.functionptr(ADDRESS_VOID_FUNC, g.name, graph=g)
             
        self.static_deallocator_funcptrs[TYPE] = fptr
        return fptr

    def dynamic_deallocation_funcptr_for_type(self, TYPE):
        if TYPE in self.dynamic_deallocator_funcptrs:
            return self.dynamic_deallocator_funcptrs[TYPE]
        #print_call_chain(self)

        rtti = self.get_rtti(TYPE)
        if rtti is None:
            p = self._static_deallocation_funcptr_for_type(TYPE)
            self.dynamic_deallocator_funcptrs[TYPE] = p
            return p
            
        queryptr = rtti._obj.query_funcptr
        if queryptr._obj in self.queryptr2dynamic_deallocator_funcptr:
            return self.queryptr2dynamic_deallocator_funcptr[queryptr._obj]
        
        RTTI_PTR = lltype.Ptr(lltype.RuntimeTypeInfo)
        QUERY_ARG_TYPE = lltype.typeOf(queryptr).TO.ARGS[0]
        def dealloc(addr):
            # bump refcount to 1
            gcheader = addr - RefcountingGCTransformer.gc_header_offset
            gcheader.signed[0] = 1
            v = objectmodel.cast_adr_to_ptr(addr, QUERY_ARG_TYPE)
            rtti = queryptr(v)
            gcheader.signed[0] = 0
            objectmodel.llop.gc_call_rtti_destructor(lltype.Void, rtti, addr)
        g = self.annotate_helper(dealloc, [llmemory.Address])
        self.seen_graphs[g] = True
        
        fptr = lltype.functionptr(ADDRESS_VOID_FUNC, g.name, graph=g)
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

    def finalizer_funcptr_for_type(self, TYPE):
        if TYPE in self.finalizer_funcptrs:
            return self.finalizer_funcptrs[TYPE]
        
        def compute_pop_alive_ll_ops(hop):
            hop.llops.extend(self.pop_alive(hop.args_v[1]))
            return hop.inputconst(hop.r_result.lowleveltype, hop.s_result.const)
        def pop_alive(var):
            pass
        pop_alive.compute_ll_ops = compute_pop_alive_ll_ops
        pop_alive.llresult = lltype.Void
        
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
            d = {'pop_alive':pop_alive,
                 'PTR_TYPE':lltype.Ptr(TYPE),
                 'cast_adr_to_ptr':objectmodel.cast_adr_to_ptr}
            src = ("def finalizer(addr):\n"
                   "    v = cast_adr_to_ptr(addr, PTR_TYPE)\n"
                   "%s\n")%(static_body,)
            exec src in d
            g = self.annotate_helper(d['finalizer'], [llmemory.Address])
        elif destrptr:
            d = {'PTR_TYPE':DESTR_ARG,
                 'cast_adr_to_ptr':objectmodel.cast_adr_to_ptr,
                 'destrptr':destrptr}
            src = ("def finalizer(addr):\n"
                   "    v = cast_adr_to_ptr(addr, PTR_TYPE)\n"
                   "    destrptr(v)\n")
            exec src in d
            g = self.annotate_helper(d['finalizer'], [llmemory.Address])
        else:
            g = None

        if g:
            self.seen_graphs[g] = True

            fptr = lltype.functionptr(ADDRESS_VOID_FUNC, g.name, graph=g)
            self.finalizer_funcptrs[TYPE] = fptr
            return fptr
        else:
            self.finalizer_funcptrs[TYPE] = None
            return None
        
# ___________________________________________________________________
# calculate some statistics about the number of variables that need
# to be cared for across a call

relevant_ops = ["direct_call", "indirect_call", "malloc"]

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

