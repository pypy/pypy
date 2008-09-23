import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant, \
     c_last_exception, checkgraph
from pypy.translator.unsimplify import insert_empty_block
from pypy.translator.unsimplify import insert_empty_startblock
from pypy.translator.unsimplify import starts_with_empty_block
from pypy.translator.backendopt.support import var_needsgc
from pypy.translator.backendopt import inline
from pypy.translator.backendopt import graphanalyze
from pypy.translator.backendopt.canraise import RaiseAnalyzer
from pypy.translator.backendopt.ssa import DataFlowFamilyBuilder
from pypy.annotation import model as annmodel
from pypy.rpython import rmodel, annlowlevel
from pypy.rpython.memory import gc
from pypy.rpython.memory.gctransform.support import var_ispyobj
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.rbuiltin import gen_cast
from pypy.rlib.rarithmetic import ovfcheck
import sets, os, sys
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.translator.simplify import join_blocks, cleanup_graph

PyObjPtr = lltype.Ptr(lltype.PyObject)

class GcHighLevelOp(object):
    def __init__(self, gct, op, index, llops):
        self.gctransformer = gct
        self.spaceop = op
        self.index = index
        self.llops = llops

    def livevars_after_op(self):
        gct = self.gctransformer
        return [
            var for var in gct.livevars
                if gct.var_last_needed_in[var] > self.index]

    def current_op_keeps_alive(self):
        gct = self.gctransformer
        return [
            var for var in self.spaceop.args
                if gct.var_last_needed_in.get(var) == self.index]

    def dispatch(self):
        gct = self.gctransformer
        opname = self.spaceop.opname
        v_result = self.spaceop.result

        meth = getattr(gct, 'gct_' + opname, gct.default)
        meth(self)

        if var_needsgc(v_result):
            gct.livevars.append(v_result)
            if var_ispyobj(v_result):
                if opname in ('getfield', 'getarrayitem', 'same_as',
                                 'cast_pointer', 'getsubstruct',
                                 'getinteriorfield'):
                    # XXX more operations?
                    gct.push_alive(v_result, self.llops)
            elif opname not in ('direct_call', 'indirect_call'):
                gct.push_alive(v_result, self.llops)
        


    def rename(self, newopname):
        self.llops.append(
            SpaceOperation(newopname, self.spaceop.args, self.spaceop.result))

    def inputargs(self):
        return self.spaceop.args

    def genop(self, opname, args, resulttype=None, resultvar=None):
        assert resulttype is None or resultvar is None
        if resultvar is None:
            return self.llops.genop(opname, args,
                                    resulttype=resulttype)
        else:
            newop = SpaceOperation(opname, args, resultvar)
            self.llops.append(newop)
            return resultvar

    def cast_result(self, var):
        v_result = self.spaceop.result
        resulttype = getattr(v_result, 'concretetype', PyObjPtr)
        curtype = getattr(var, 'concretetype', PyObjPtr)
        if curtype == resulttype:
            self.genop('same_as', [var], resultvar=v_result)
        else:
            v_new = gen_cast(self.llops, resulttype, var)
            assert v_new != var
            self.llops[-1].result = v_result

# ________________________________________________________________

class BaseGCTransformer(object):
    finished_helpers = False

    def __init__(self, translator, inline=False):
        self.translator = translator
        self.seen_graphs = {}
        self.prepared = False
        self.minimal_transform = {}
        if translator:
            self.mixlevelannotator = MixLevelHelperAnnotator(translator.rtyper)
        else:
            self.mixlevelannotator = None
        self.inline = inline
        if translator and inline:
            self.lltype_to_classdef = translator.rtyper.lltype_to_classdef_mapping()
        self.graphs_to_inline = {}
        self.graph_dependencies = {}
        self.ll_finalizers_ptrs = []
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

    def prepare_inline_helpers(self, graphs):
        from pypy.translator.backendopt.inline import iter_callsites
        for graph in graphs:
            self.graph_dependencies[graph] = {}
            for called, block, i in iter_callsites(graph, None):
                if called in self.graphs_to_inline:
                    self.graph_dependencies[graph][called] = True
        self.prepared = True

    def inline_helpers(self, graph):
        if not self.prepared:
            raise Exception("Need to call prepare_inline_helpers first")
        if self.inline:
            raise_analyzer = RaiseAnalyzer(self.translator)
            to_enum = self.graph_dependencies.get(graph, self.graphs_to_inline)
            for inline_graph in to_enum:
                try:
                    inline.inline_function(self.translator, inline_graph, graph,
                                           self.lltype_to_classdef,
                                           raise_analyzer,
                                           cleanup=False)
                except inline.CannotInline, e:
                    print 'CANNOT INLINE:', e
                    print '\t%s into %s' % (inline_graph, graph)
            cleanup_graph(graph)

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

    def transform_block(self, block, is_borrowed):
        llops = LowLevelOpList()
        #self.curr_block = block
        self.livevars = [var for var in block.inputargs
                    if var_needsgc(var) and not is_borrowed(var)]
        allvars = [var for var in block.getvariables() if var_needsgc(var)]
        self.var_last_needed_in = dict.fromkeys(allvars, 0)
        for i, op in enumerate(block.operations):
            for var in op.args:
                if not var_needsgc(var):
                    continue
                self.var_last_needed_in[var] = i
        for link in block.exits:
            for var in link.args:
                if not var_needsgc(var):
                    continue
                self.var_last_needed_in[var] = len(block.operations) + 1

        for i, op in enumerate(block.operations):
            hop = GcHighLevelOp(self, op, i, llops)
            hop.dispatch()

        if len(block.exits) != 0: # i.e not the return block
            assert block.exitswitch is not c_last_exception

            deadinallexits = sets.Set(self.livevars)
            for link in block.exits:
                deadinallexits.difference_update(sets.Set(link.args))

            for var in deadinallexits:
                self.pop_alive(var, llops)

            for link in block.exits:
                livecounts = dict.fromkeys(sets.Set(self.livevars) - deadinallexits, 1)
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

            block.operations[:] = llops
        self.livevars = None
        self.var_last_needed_in = None

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
        inserted_empty_startblock = False
        if not starts_with_empty_block(graph):
            insert_empty_startblock(self.translator.annotator, graph)
            inserted_empty_startblock = True
        is_borrowed = self.compute_borrowed_vars(graph)

        for block in graph.iterblocks():
            self.transform_block(block, is_borrowed)

        for link, livecounts in self.links_to_split.iteritems():
            llops = LowLevelOpList()
            for var, livecount in livecounts.iteritems():
                for i in range(livecount):
                    self.pop_alive(var, llops)
                for i in range(-livecount):
                    self.push_alive(var, llops)
            if llops:
                if link.prevblock.exitswitch is None:
                    link.prevblock.operations.extend(llops)
                else:
                    insert_empty_block(self.translator.annotator, link, llops)

        # remove the empty block at the start of the graph, which should
        # still be empty (but let's check)
        if starts_with_empty_block(graph) and inserted_empty_startblock:
            old_startblock = graph.startblock
            graph.startblock.isstartblock = False
            graph.startblock = graph.startblock.exits[0].target
            graph.startblock.isstartblock = True

        checkgraph(graph)

        self.links_to_split = None
        v = Variable('vanishing_exc_value')
        v.concretetype = self.get_lltype_of_exception_value()
        llops = LowLevelOpList()
        self.pop_alive(v, llops)
        graph.exc_cleanup = (v, list(llops))
        return is_borrowed    # xxx for tests only

    def annotate_helper(self, ll_helper, ll_args, ll_result, inline=False):
        assert not self.finished_helpers
        args_s = map(annmodel.lltype_to_annotation, ll_args)
        s_result = annmodel.lltype_to_annotation(ll_result)
        graph = self.mixlevelannotator.getgraph(ll_helper, args_s, s_result)
        # the produced graphs does not need to be fully transformed
        self.need_minimal_transform(graph)
        if inline:
            self.graphs_to_inline[graph] = True
        FUNCTYPE = lltype.FuncType(ll_args, ll_result)
        return self.mixlevelannotator.graph2delayed(graph, FUNCTYPE=FUNCTYPE)

    def inittime_helper(self, ll_helper, ll_args, ll_result, inline=True):
        ptr = self.annotate_helper(ll_helper, ll_args, ll_result, inline=inline)
        return Constant(ptr, lltype.typeOf(ptr))

    def annotate_finalizer(self, ll_finalizer, ll_args, ll_result):
        fptr = self.annotate_helper(ll_finalizer, ll_args, ll_result)
        self.ll_finalizers_ptrs.append(fptr)
        return fptr

    def finish_helpers(self, backendopt=True):
        if self.translator is not None:
            self.mixlevelannotator.finish_annotate()
        self.finished_helpers = True
        if self.translator is not None:
            self.mixlevelannotator.finish_rtype()
            if backendopt:
                self.mixlevelannotator.backend_optimize()
        # Make sure that the database also sees all finalizers now.
        # XXX we need to think more about the interaction with stackless...
        # It is likely that the finalizers need special support there
        newgcdependencies = self.ll_finalizers_ptrs
        return newgcdependencies

    def finish_tables(self):
        pass

    def finish(self, backendopt=True):
        self.finish_helpers(backendopt=backendopt)
        self.finish_tables()

    def transform_generic_set(self, hop):
        opname = hop.spaceop.opname
        v_new = hop.spaceop.args[-1]
        v_old = hop.genop('g' + opname[1:],
                          hop.inputargs()[:-1],
                          resulttype=v_new.concretetype)
        self.push_alive(v_new, hop.llops)
        hop.rename('bare_' + opname)
        self.pop_alive(v_old, hop.llops)


    def push_alive(self, var, llops):
        if var_ispyobj(var):
            self.push_alive_pyobj(var, llops)
        else:
            self.push_alive_nopyobj(var, llops)

    def pop_alive(self, var, llops):
        if var_ispyobj(var):
            self.pop_alive_pyobj(var, llops)
        else:
            self.pop_alive_nopyobj(var, llops)

    def push_alive_pyobj(self, var, llops):
        if hasattr(var, 'concretetype') and var.concretetype != PyObjPtr:
            var = gen_cast(llops, PyObjPtr, var)
        llops.genop("gc_push_alive_pyobj", [var])

    def pop_alive_pyobj(self, var, llops):
        if hasattr(var, 'concretetype') and var.concretetype != PyObjPtr:
            var = gen_cast(llops, PyObjPtr, var)
        llops.genop("gc_pop_alive_pyobj", [var])

    def push_alive_nopyobj(self, var, llops):
        pass

    def pop_alive_nopyobj(self, var, llops):
        pass

    def var_needs_set_transform(self, var):
        return var_ispyobj(var)

    def default(self, hop):
        hop.llops.append(hop.spaceop)

    def gct_setfield(self, hop):
        if self.var_needs_set_transform(hop.spaceop.args[-1]):
            self.transform_generic_set(hop)
        else:
            hop.rename('bare_' + hop.spaceop.opname)
    gct_setarrayitem = gct_setfield
    gct_setinteriorfield = gct_setfield

    def gct_zero_gc_pointers_inside(self, hop):
        pass

    def gct_gc_id(self, hop):
        # this assumes a non-moving GC.  Moving GCs need to override this
        hop.rename('cast_ptr_to_int')


class MinimalGCTransformer(BaseGCTransformer):
    def __init__(self, parenttransformer):
        BaseGCTransformer.__init__(self, parenttransformer.translator)
        self.parenttransformer = parenttransformer

    def push_alive(self, var, llops):
        pass

    def pop_alive(self, var, llops):
        pass

    def gct_malloc(self, hop):
        flags = hop.spaceop.args[1].value
        flavor = flags['flavor']
        assert flavor == 'raw'
        assert not flags.get('zero')
        return self.parenttransformer.gct_malloc(hop)

    def gct_malloc_varsize(self, hop):
        flags = hop.spaceop.args[1].value
        flavor = flags['flavor']
        assert flavor == 'raw'
        assert not flags.get('zero')
        return self.parenttransformer.gct_malloc_varsize(hop)
    
    def gct_free(self, hop):
        flavor = hop.spaceop.args[1].value
        assert flavor == 'raw'
        return self.parenttransformer.gct_free(hop)

BaseGCTransformer.MinimalGCTransformer = MinimalGCTransformer
MinimalGCTransformer.MinimalGCTransformer = None

# ________________________________________________________________

def mallocHelpers():
    class _MallocHelpers(object):
        def _freeze_(self):
            return True
    mh = _MallocHelpers()

    def _ll_malloc_fixedsize(size):
        result = mh.allocate(size)
        if not result:
            raise MemoryError()
        return result
    mh._ll_malloc_fixedsize = _ll_malloc_fixedsize

    def _ll_compute_size(length, size, itemsize):
        try:
            varsize = ovfcheck(itemsize * length)
            tot_size = ovfcheck(size + varsize)
        except OverflowError:
            raise MemoryError()
        return tot_size
    _ll_compute_size._always_inline_ = True

    def _ll_malloc_varsize_no_length(length, size, itemsize):
        tot_size = _ll_compute_size(length, size, itemsize)
        result = mh.allocate(tot_size)
        if not result:
            raise MemoryError()
        return result
    mh._ll_malloc_varsize_no_length = _ll_malloc_varsize_no_length
    mh.ll_malloc_varsize_no_length = _ll_malloc_varsize_no_length

    def ll_malloc_varsize(length, size, itemsize, lengthoffset):
        result = mh.ll_malloc_varsize_no_length(length, size, itemsize)
        (result + lengthoffset).signed[0] = length
        return result
    mh.ll_malloc_varsize = ll_malloc_varsize

    def _ll_malloc_varsize_no_length_zero(length, size, itemsize):
        tot_size = _ll_compute_size(length, size, itemsize)
        result = mh.allocate(tot_size)
        if not result:
            raise MemoryError()
        llmemory.raw_memclear(result, tot_size)
        return result
    mh.ll_malloc_varsize_no_length_zero = _ll_malloc_varsize_no_length_zero

    def ll_realloc(ptr, length, constsize, itemsize, lengthoffset):
        size = constsize + length * itemsize
        result = mh.realloc(ptr, size)
        if not result:
            raise MemoryError()
        (result + lengthoffset).signed[0] = length
        return result
    mh.ll_realloc = ll_realloc

    return mh

class GCTransformer(BaseGCTransformer):

    def __init__(self, translator, inline=False):
        super(GCTransformer, self).__init__(translator, inline=inline)

        mh = mallocHelpers()
        mh.allocate = llmemory.raw_malloc
        ll_raw_malloc_fixedsize = mh._ll_malloc_fixedsize
        ll_raw_malloc_varsize_no_length = mh.ll_malloc_varsize_no_length
        ll_raw_malloc_varsize = mh.ll_malloc_varsize
        ll_raw_malloc_varsize_no_length_zero  = mh.ll_malloc_varsize_no_length_zero

        stack_mh = mallocHelpers()
        stack_mh.allocate = lambda size: llop.stack_malloc(llmemory.Address, size)
        ll_stack_malloc_fixedsize = stack_mh._ll_malloc_fixedsize
        
        if self.translator:
            self.raw_malloc_fixedsize_ptr = self.inittime_helper(
                ll_raw_malloc_fixedsize, [lltype.Signed], llmemory.Address)
            self.raw_malloc_varsize_no_length_ptr = self.inittime_helper(
                ll_raw_malloc_varsize_no_length, [lltype.Signed]*3, llmemory.Address, inline=False)
            self.raw_malloc_varsize_ptr = self.inittime_helper(
                ll_raw_malloc_varsize, [lltype.Signed]*4, llmemory.Address, inline=False)
            self.raw_malloc_varsize_no_length_zero_ptr = self.inittime_helper(
                ll_raw_malloc_varsize_no_length_zero, [lltype.Signed]*3, llmemory.Address, inline=False)

            self.stack_malloc_fixedsize_ptr = self.inittime_helper(
                ll_stack_malloc_fixedsize, [lltype.Signed], llmemory.Address)

    def gct_malloc(self, hop, add_flags=None):
        TYPE = hop.spaceop.result.concretetype.TO
        assert not TYPE._is_varsize()
        flags = hop.spaceop.args[1].value
        flavor = flags['flavor']
        meth = getattr(self, 'gct_fv_%s_malloc' % flavor, None)
        assert meth, "%s has no support for malloc with flavor %r" % (self, flavor) 
        c_size = rmodel.inputconst(lltype.Signed, llmemory.sizeof(TYPE))
        v_raw = meth(hop, flags, TYPE, c_size)
        hop.cast_result(v_raw)
 
    def gct_fv_raw_malloc(self, hop, flags, TYPE, c_size):
        v_raw = hop.genop("direct_call", [self.raw_malloc_fixedsize_ptr, c_size],
                          resulttype=llmemory.Address)
        if flags.get('zero'):
            hop.genop("raw_memclear", [v_raw, c_size])
        return v_raw

    def gct_fv_stack_malloc(self, hop, flags, TYPE, c_size):
        v_raw = hop.genop("direct_call", [self.stack_malloc_fixedsize_ptr, c_size],
                          resulttype=llmemory.Address)
        if flags.get('zero'):
            hop.genop("raw_memclear", [v_raw, c_size])
        return v_raw        

    def gct_malloc_varsize(self, hop, add_flags=None):
        flags = hop.spaceop.args[1].value
        if add_flags:
            flags.update(add_flags)
        flavor = flags['flavor']
        assert flavor != 'cpy', "cannot malloc CPython objects directly"
        meth = getattr(self, 'gct_fv_%s_malloc_varsize' % flavor, None)
        assert meth, "%s has no support for malloc_varsize with flavor %r" % (self, flavor) 
        return self.varsize_malloc_helper(hop, flags, meth, [])

    def gct_malloc_nonmovable(self, *args, **kwds):
        return self.gct_malloc(*args, **kwds)

    def gct_malloc_nonmovable_varsize(self, *args, **kwds):
        return self.gct_malloc_varsize(*args, **kwds)

    def gct_malloc_resizable_buffer(self, hop):
        flags = hop.spaceop.args[1].value
        flags['varsize'] = True
        flags['nonmovable'] = True
        flags['resizable'] = True
        flavor = flags['flavor']
        assert flavor != 'cpy', "cannot malloc CPython objects directly"
        meth = getattr(self, 'gct_fv_%s_malloc_varsize' % flavor, None)
        assert meth, "%s has no support for malloc_varsize with flavor %r" % (self, flavor) 
        return self.varsize_malloc_helper(hop, flags, meth, [])

    def gct_resize_buffer(self, hop):
        op = hop.spaceop
        if self._can_realloc():
            self._gct_resize_buffer_realloc(hop, op.args[2], True)
        else:
            self._gct_resize_buffer_no_realloc(hop, op.args[1])

    def _can_realloc(self):
        return False

    def _gct_resize_buffer_realloc(self, hop, v_newsize, grow=True):
        def intconst(c): return rmodel.inputconst(lltype.Signed, c)
        op = hop.spaceop
        flags = {'flavor':'gc', 'varsize': True}
        TYPE = op.args[0].concretetype.TO
        ARRAY = TYPE._flds[TYPE._arrayfld]
        offset_to_length = llmemory.FieldOffset(TYPE, TYPE._arrayfld) + \
                           llmemory.ArrayLengthOffset(ARRAY)
        c_const_size = intconst(llmemory.sizeof(TYPE, 0))
        c_item_size = intconst(llmemory.sizeof(ARRAY.OF))

        c_lengthofs = intconst(offset_to_length)
        v_ptr = op.args[0]
        v_ptr = gen_cast(hop.llops, llmemory.GCREF, v_ptr)
        c_grow = rmodel.inputconst(lltype.Bool, grow)
        v_raw = self.perform_realloc(hop, v_ptr, v_newsize, c_const_size,
                                     c_item_size, c_lengthofs, c_grow)
        hop.cast_result(v_raw)

    def _gct_resize_buffer_no_realloc(self, hop, v_lgt):
        op = hop.spaceop
        meth = self.gct_fv_gc_malloc_varsize
        flags = {'flavor':'gc', 'varsize': True, 'keep_current_args': True}
        self.varsize_malloc_helper(hop, flags, meth, [])
        # fish resvar
        v_newbuf = hop.llops[-1].result
        v_src = op.args[0]
        TYPE = v_src.concretetype.TO
        c_fldname = rmodel.inputconst(lltype.Void, TYPE._arrayfld)
        v_adrsrc = hop.genop('cast_ptr_to_adr', [v_src],
                             resulttype=llmemory.Address)
        v_adrnewbuf = hop.genop('cast_ptr_to_adr', [v_newbuf],
                                resulttype=llmemory.Address)
        ofs = (llmemory.offsetof(TYPE, TYPE._arrayfld) +
               llmemory.itemoffsetof(getattr(TYPE, TYPE._arrayfld), 0))
        v_ofs = rmodel.inputconst(lltype.Signed, ofs)
        v_adrsrc = hop.genop('adr_add', [v_adrsrc, v_ofs],
                             resulttype=llmemory.Address)
        v_adrnewbuf = hop.genop('adr_add', [v_adrnewbuf, v_ofs],
                                resulttype=llmemory.Address)
        size = llmemory.sizeof(getattr(TYPE, TYPE._arrayfld).OF)
        c_size = rmodel.inputconst(lltype.Signed, size)
        v_lgtsym = hop.genop('int_mul', [c_size, v_lgt],
                             resulttype=lltype.Signed) 
        vlist = [v_adrsrc, v_adrnewbuf, v_lgtsym]
        hop.genop('raw_memcopy', vlist)

    def gct_finish_building_buffer(self, hop):
        op = hop.spaceop
        if self._can_realloc():
            return self._gct_resize_buffer_realloc(hop, op.args[1], False)
        else:
            return self._gct_resize_buffer_no_realloc(hop, op.args[1])

    def varsize_malloc_helper(self, hop, flags, meth, extraargs):
        def intconst(c): return rmodel.inputconst(lltype.Signed, c)
        op = hop.spaceop
        TYPE = op.result.concretetype.TO
        assert TYPE._is_varsize()
        if isinstance(TYPE, lltype.Struct):
            ARRAY = TYPE._flds[TYPE._arrayfld]
        else:
            ARRAY = TYPE
        assert isinstance(ARRAY, lltype.Array)
        c_const_size = intconst(llmemory.sizeof(TYPE, 0))
        c_item_size = intconst(llmemory.sizeof(ARRAY.OF))

        if ARRAY._hints.get("nolength", False):
            c_offset_to_length = None
        else:
            if isinstance(TYPE, lltype.Struct):
                offset_to_length = llmemory.FieldOffset(TYPE, TYPE._arrayfld) + \
                                   llmemory.ArrayLengthOffset(ARRAY)
            else:
                offset_to_length = llmemory.ArrayLengthOffset(ARRAY)
            c_offset_to_length = intconst(offset_to_length)

        args = [hop] + extraargs + [flags, TYPE,
                op.args[-1], c_const_size, c_item_size, c_offset_to_length]
        v_raw = meth(*args)
        hop.cast_result(v_raw)

    def gct_fv_raw_malloc_varsize(self, hop, flags, TYPE, v_length, c_const_size, c_item_size,
                                                                    c_offset_to_length):
        if c_offset_to_length is None:
            if flags.get('zero'):
                fnptr = self.raw_malloc_varsize_no_length_zero_ptr
            else:
                fnptr = self.raw_malloc_varsize_no_length_ptr
            v_raw = hop.genop("direct_call",
                               [fnptr, v_length, c_const_size, c_item_size],
                               resulttype=llmemory.Address)
        else:
            if flags.get('zero'):
                raise NotImplementedError("raw zero varsize malloc with length field")
            v_raw = hop.genop("direct_call",
                               [self.raw_malloc_varsize_ptr, v_length,
                                c_const_size, c_item_size, c_offset_to_length],
                               resulttype=llmemory.Address)
        return v_raw

    def gct_free(self, hop):
        op = hop.spaceop
        flavor = op.args[1].value
        v = op.args[0]
        assert flavor != 'cpy', "cannot free CPython objects directly"
        if flavor == 'raw':
            v = hop.genop("cast_ptr_to_adr", [v], resulttype=llmemory.Address)
            hop.genop('raw_free', [v])
        else:
            assert False, "%s has no support for free with flavor %r" % (self, flavor)           

    def gct_gc_can_move(self, hop):
        return hop.cast_result(rmodel.inputconst(lltype.Bool, False))
