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
from pypy.rpython.memory import gc, lladdress
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.rbuiltin import gen_cast
from pypy.rlib.rarithmetic import ovfcheck
import sets, os, sys

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

class GcHighLevelOp(object):
    def __init__(self, gctransformer, op, llops):
        self.gctransformer = gctransformer
        self.spaceop = op
        self.llops = llops

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
                                 'cast_pointer', 'getsubstruct'):
                    # XXX more operations?
                    gct.push_alive(v_result)
            elif opname not in ('direct_call', 'indirect_call'):
                gct.push_alive(v_result)

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
        self.llops = LowLevelOpList()
        #self.curr_block = block
        self.livevars = [var for var in block.inputargs
                    if var_needsgc(var) and not is_borrowed(var)]
        for op in block.operations:
            hop = GcHighLevelOp(self, op, self.llops)
            hop.dispatch()

        if len(block.exits) != 0: # i.e not the return block
            assert block.exitswitch is not c_last_exception

            deadinallexits = sets.Set(self.livevars)
            for link in block.exits:
                deadinallexits.difference_update(sets.Set(link.args))

            for var in deadinallexits:
                self.pop_alive(var)

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

            block.operations[:] = self.llops
        self.llops = None
        self.livevars = None

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
        return self.mixlevelannotator.graph2delayed(graph)

    def inittime_helper(self, ll_helper, ll_args, ll_result, inline=True):
        ptr = self.annotate_helper(ll_helper, ll_args, ll_result, inline=inline)
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

    def transform_generic_set(self, hop):
        opname = hop.spaceop.opname
        v_new = hop.spaceop.args[-1]
        v_old = hop.genop('g' + opname[1:],
                          hop.inputargs()[:-1],
                          resulttype=v_new.concretetype)
        self.push_alive(v_new)
        hop.rename('bare_' + opname)
        self.pop_alive(v_old)


    def push_alive(self, var, llops=None):
        if llops is None:
            llops = self.llops
        if var_ispyobj(var):
            self.push_alive_pyobj(var, llops)
        else:
            self.push_alive_nopyobj(var, llops)

    def pop_alive(self, var, llops=None):
        if llops is None:
            llops = self.llops
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

    #def gct_safe_call(self, hop):
    #    hop.rename("direct_call")

    def gct_zero_gc_pointers_inside(self, hop):
        pass

class MinimalGCTransformer(GCTransformer):
    def __init__(self, parenttransformer):
        GCTransformer.__init__(self, parenttransformer.translator)
        self.parenttransformer = parenttransformer

    def push_alive(self, var, llops=None):
        pass

    def pop_alive(self, var, llops=None):
        pass

GCTransformer.MinimalGCTransformer = MinimalGCTransformer
MinimalGCTransformer.MinimalGCTransformer = None
