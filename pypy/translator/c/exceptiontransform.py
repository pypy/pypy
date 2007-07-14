from pypy.translator.simplify import join_blocks, cleanup_graph
from pypy.translator.unsimplify import copyvar, varoftype
from pypy.translator.unsimplify import insert_empty_block
from pypy.translator.backendopt import canraise, inline, support, removenoops
from pypy.objspace.flow.model import Block, Constant, Variable, Link, \
    c_last_exception, SpaceOperation, checkgraph, FunctionGraph
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem import lloperation
from pypy.rpython.memory.lladdress import NULL
from pypy.rpython import rtyper
from pypy.rpython import rclass
from pypy.rpython.rmodel import inputconst
from pypy.rlib.rarithmetic import r_uint, r_longlong, r_ulonglong
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator

PrimitiveErrorValue = {lltype.Signed: -1,
                       lltype.Unsigned: r_uint(-1),
                       lltype.SignedLongLong: r_longlong(-1),
                       lltype.UnsignedLongLong: r_ulonglong(-1),
                       lltype.Float: -1.0,
                       lltype.Char: chr(255),
                       lltype.UniChar: unichr(0xFFFF), # XXX is this always right?
                       lltype.Bool: True,
                       llmemory.Address: NULL,
                       llmemory.WeakGcAddress: llmemory.fakeweakaddress(None),
                       lltype.Void: None}

def error_value(T):
    if isinstance(T, lltype.Primitive):
        return PrimitiveErrorValue[T]
    elif isinstance(T, lltype.Ptr):
        return lltype.nullptr(T.TO)
    assert 0, "not implemented yet"

def error_constant(T):
    return Constant(error_value(T), T)

class ExceptionTransformer(object):
    def __init__(self, translator):
        self.translator = translator
        self.raise_analyzer = canraise.RaiseAnalyzer(translator)
        edata = translator.rtyper.getexceptiondata()
        self.lltype_of_exception_value = edata.lltype_of_exception_value
        self.lltype_of_exception_type = edata.lltype_of_exception_type
        mixlevelannotator = MixLevelHelperAnnotator(translator.rtyper)
        l2a = annmodel.lltype_to_annotation

        EXCDATA = lltype.Struct('ExcData',
            ('exc_type',  self.lltype_of_exception_type),
            ('exc_value', self.lltype_of_exception_value))
        self.EXCDATA = EXCDATA

        exc_data = lltype.malloc(EXCDATA, immortal=True)
        null_type = lltype.nullptr(self.lltype_of_exception_type.TO)
        null_value = lltype.nullptr(self.lltype_of_exception_value.TO)
        
        def rpyexc_occured():
            exc_type = exc_data.exc_type
            return bool(exc_type)

        # XXX tmp HACK for genllvm
        # llvm is strongly typed between bools and ints, which means we have no way of
        # calling rpyexc_occured() from c code with lltype.Bool
        def _rpyexc_occured():
            exc_type = exc_data.exc_type
            return bool(exc_type)

        def rpyexc_fetch_type():
            return exc_data.exc_type

        def rpyexc_fetch_value():
            return exc_data.exc_value

        def rpyexc_clear():
            exc_data.exc_type = null_type
            exc_data.exc_value = null_value

        def rpyexc_raise(etype, evalue):
            # assert(!RPyExceptionOccurred());
            exc_data.exc_type = etype
            exc_data.exc_value = evalue
        
        RPYEXC_OCCURED_TYPE = lltype.FuncType([], lltype.Bool)
        rpyexc_occured_graph = mixlevelannotator.getgraph(
            rpyexc_occured, [], l2a(lltype.Bool))
        self.rpyexc_occured_ptr = Constant(lltype.functionptr(
            RPYEXC_OCCURED_TYPE, "RPyExceptionOccurred",
            graph=rpyexc_occured_graph,
            exception_policy="exc_helper"),
            lltype.Ptr(RPYEXC_OCCURED_TYPE))

        # XXX tmp HACK for genllvm
        _RPYEXC_OCCURED_TYPE = lltype.FuncType([], lltype.Signed)
        _rpyexc_occured_graph = mixlevelannotator.getgraph(
            _rpyexc_occured, [], l2a(lltype.Signed))
        self._rpyexc_occured_ptr = Constant(lltype.functionptr(
            _RPYEXC_OCCURED_TYPE, "_RPyExceptionOccurred",
            graph=_rpyexc_occured_graph,
            exception_policy="exc_helper"),
            lltype.Ptr(_RPYEXC_OCCURED_TYPE))
        
        RPYEXC_FETCH_TYPE_TYPE = lltype.FuncType([], self.lltype_of_exception_type)
        rpyexc_fetch_type_graph = mixlevelannotator.getgraph(
            rpyexc_fetch_type, [],
            l2a(self.lltype_of_exception_type))
        self.rpyexc_fetch_type_ptr = Constant(lltype.functionptr(
            RPYEXC_FETCH_TYPE_TYPE, "RPyFetchExceptionType",
            graph=rpyexc_fetch_type_graph,
            exception_policy="exc_helper"),
            lltype.Ptr(RPYEXC_FETCH_TYPE_TYPE))
        
        RPYEXC_FETCH_VALUE_TYPE = lltype.FuncType([], self.lltype_of_exception_value)
        rpyexc_fetch_value_graph = mixlevelannotator.getgraph(
            rpyexc_fetch_value, [],
            l2a(self.lltype_of_exception_value))
        self.rpyexc_fetch_value_ptr = Constant(lltype.functionptr(
            RPYEXC_FETCH_VALUE_TYPE, "RPyFetchExceptionValue",
            graph=rpyexc_fetch_value_graph,
            exception_policy="exc_helper"),
            lltype.Ptr(RPYEXC_FETCH_VALUE_TYPE))

        RPYEXC_CLEAR = lltype.FuncType([], lltype.Void)
        rpyexc_clear_graph = mixlevelannotator.getgraph(
            rpyexc_clear, [], l2a(lltype.Void))
        self.rpyexc_clear_ptr = Constant(lltype.functionptr(
            RPYEXC_CLEAR, "RPyClearException",
            graph=rpyexc_clear_graph,
            exception_policy="exc_helper"),
            lltype.Ptr(RPYEXC_CLEAR))

        RPYEXC_RAISE = lltype.FuncType([self.lltype_of_exception_type,
                                        self.lltype_of_exception_value],
                                        lltype.Void)
        rpyexc_raise_graph = mixlevelannotator.getgraph(
            rpyexc_raise, [l2a(self.lltype_of_exception_type),
                           l2a(self.lltype_of_exception_value)],
            l2a(lltype.Void))
        self.rpyexc_raise_ptr = Constant(lltype.functionptr(
            RPYEXC_RAISE, "RPyRaiseException",
            graph=rpyexc_raise_graph,
            exception_policy="exc_helper",
            jitcallkind='rpyexc_raise',   # for the JIT
            ),
            lltype.Ptr(RPYEXC_RAISE))

        mixlevelannotator.finish()

        self.exc_data_ptr = exc_data
        self.cexcdata = Constant(exc_data, lltype.Ptr(EXCDATA))
        
        self.lltype_to_classdef = translator.rtyper.lltype_to_classdef_mapping()
        p = lltype.nullptr(self.lltype_of_exception_type.TO)
        self.c_null_etype = Constant(p, self.lltype_of_exception_type)
        p = lltype.nullptr(self.lltype_of_exception_value.TO)
        self.c_null_evalue = Constant(p, self.lltype_of_exception_value)

    def gen_getfield(self, name, llops):
        c_name = inputconst(lltype.Void, name)
        return llops.genop('getfield', [self.cexcdata, c_name],
                           resulttype = getattr(self.EXCDATA, name))

    def gen_setfield(self, name, v_value, llops):
        c_name = inputconst(lltype.Void, name)
        llops.genop('setfield', [self.cexcdata, c_name, v_value])

    def transform_completely(self):
        for graph in self.translator.graphs:
            self.create_exception_handling(graph)

    def create_exception_handling(self, graph, always_exc_clear=False):
        """After an exception in a direct_call (or indirect_call), that is not caught
        by an explicit
        except statement, we need to reraise the exception. So after this
        direct_call we need to test if an exception had occurred. If so, we return
        from the current graph with a special value (False/-1/-1.0/null).
        Because of the added exitswitch we need an additional block.
        """
        if hasattr(graph, 'exceptiontransformed'):
            assert self.exc_data_ptr._same_obj(graph.exceptiontransformed)
            return
        else:
            self.raise_analyzer.analyze_direct_call(graph)
            graph.exceptiontransformed = self.exc_data_ptr

        self.always_exc_clear = always_exc_clear
        join_blocks(graph)
        # collect the blocks before changing them
        n_need_exc_matching_blocks = 0
        n_gen_exc_checks           = 0
        for block in list(graph.iterblocks()):
            need_exc_matching, gen_exc_checks = self.transform_block(graph, block)
            n_need_exc_matching_blocks += need_exc_matching
            n_gen_exc_checks           += gen_exc_checks
        self.transform_except_block(graph, graph.exceptblock)
        cleanup_graph(graph)
        removenoops.remove_superfluous_keep_alive(graph)
        return n_need_exc_matching_blocks, n_gen_exc_checks

    def transform_block(self, graph, block):
        need_exc_matching = False
        n_gen_exc_checks = 0
        if block is graph.exceptblock:
            return need_exc_matching, n_gen_exc_checks
        elif block is graph.returnblock:
            return need_exc_matching, n_gen_exc_checks
        last_operation = len(block.operations) - 1
        if block.exitswitch == c_last_exception:
            need_exc_matching = True
            last_operation -= 1
        elif (len(block.exits) == 1 and 
              block.exits[0].target is graph.returnblock and
              len(block.operations) and
              (block.exits[0].args[0].concretetype is lltype.Void or
               block.exits[0].args[0] is block.operations[-1].result)):
            last_operation -= 1
        lastblock = block
        for i in range(last_operation, -1, -1):
            op = block.operations[i]
            if not self.raise_analyzer.can_raise(op):
                continue

            splitlink = support.split_block_with_keepalive(block, i+1, False)
            afterblock = splitlink.target
            if lastblock is block:
                lastblock = afterblock

            self.gen_exc_check(block, graph.returnblock, afterblock)
            n_gen_exc_checks += 1
        if need_exc_matching:
            assert lastblock.exitswitch == c_last_exception
            if not self.raise_analyzer.can_raise(lastblock.operations[-1]):
                #print ("operation %s cannot raise, but has exception"
                #       " guarding in graph %s" % (lastblock.operations[-1],
                #                                  graph))
                lastblock.exitswitch = None
                lastblock.recloseblock(lastblock.exits[0])
                lastblock.exits[0].exitcase = None
            else:
                self.insert_matching(lastblock, graph)
        return need_exc_matching, n_gen_exc_checks

    def transform_except_block(self, graph, block):
        # attach an except block -- let's hope that nobody uses it
        graph.exceptblock = Block([Variable('etype'),   # exception class
                                   Variable('evalue')])  # exception value
        graph.exceptblock.operations = ()
        graph.exceptblock.closeblock()
        
        result = Variable()
        result.concretetype = lltype.Void
        block.operations = [SpaceOperation(
           "direct_call", [self.rpyexc_raise_ptr] + block.inputargs, result)]
        l = Link([error_constant(graph.returnblock.inputargs[0].concretetype)], graph.returnblock)
        block.recloseblock(l)

    def insert_matching(self, block, graph):
        proxygraph, op = self.create_proxy_graph(block.operations[-1])
        block.operations[-1] = op
        #non-exception case
        block.exits[0].exitcase = block.exits[0].llexitcase = None
        # use the dangerous second True flag :-)
        inliner = inline.OneShotInliner(
            self.translator, graph, self.lltype_to_classdef,
            inline_guarded_calls=True, inline_guarded_calls_no_matter_what=True,
            raise_analyzer=self.raise_analyzer)
        inliner.inline_once(block, len(block.operations)-1)
        #block.exits[0].exitcase = block.exits[0].llexitcase = False

    def create_proxy_graph(self, op):
        """ creates a graph which calls the original function, checks for
        raised exceptions, fetches and then raises them again. If this graph is
        inlined, the correct exception matching blocks are produced."""
        # XXX slightly annoying: construct a graph by hand
        # but better than the alternative
        result = copyvar(None, op.result)
        opargs = []
        inputargs = []
        callargs = []
        ARGTYPES = []
        for var in op.args:
            if isinstance(var, Variable):
                v = Variable()
                v.concretetype = var.concretetype
                inputargs.append(v)
                opargs.append(v)
                callargs.append(var)
                ARGTYPES.append(var.concretetype)
            else:
                opargs.append(var)
        newop = SpaceOperation(op.opname, opargs, result)
        startblock = Block(inputargs)
        startblock.operations.append(newop) 
        newgraph = FunctionGraph("dummy_exc1", startblock)
        startblock.closeblock(Link([result], newgraph.returnblock))
        newgraph.returnblock.inputargs[0].concretetype = op.result.concretetype
        self.gen_exc_check(startblock, newgraph.returnblock)
        excblock = Block([])

        llops = rtyper.LowLevelOpList(None)
        var_value = self.gen_getfield('exc_value', llops)
        var_type  = self.gen_getfield('exc_type' , llops)
        self.gen_setfield('exc_value', self.c_null_evalue, llops)
        self.gen_setfield('exc_type',  self.c_null_etype,  llops)
        excblock.operations[:] = llops
        newgraph.exceptblock.inputargs[0].concretetype = self.lltype_of_exception_type
        newgraph.exceptblock.inputargs[1].concretetype = self.lltype_of_exception_value
        excblock.closeblock(Link([var_type, var_value], newgraph.exceptblock))
        startblock.exits[True].target = excblock
        startblock.exits[True].args = []
        FUNCTYPE = lltype.FuncType(ARGTYPES, op.result.concretetype)
        fptr = Constant(lltype.functionptr(FUNCTYPE, "dummy_exc1", graph=newgraph),
                        lltype.Ptr(FUNCTYPE))
        return newgraph, SpaceOperation("direct_call", [fptr] + callargs, op.result) 

    def gen_exc_check(self, block, returnblock, normalafterblock=None):
        #var_exc_occured = Variable()
        #var_exc_occured.concretetype = lltype.Bool
        #block.operations.append(SpaceOperation("safe_call", [self.rpyexc_occured_ptr], var_exc_occured))

        llops = rtyper.LowLevelOpList(None)
        alloc_shortcut = False

        spaceop = block.operations[-1]
        if spaceop.opname in ('malloc', 'malloc_varsize'):
            alloc_shortcut = True
        elif spaceop.opname == 'direct_call':
            fnobj = spaceop.args[0].value._obj
            if hasattr(fnobj, '_callable'):
                oopspec = getattr(fnobj._callable, 'oopspec', None)
                if oopspec and oopspec == 'newlist(length)':
                    alloc_shortcut = True
                    
        if alloc_shortcut:
            T = spaceop.result.concretetype
            var_no_exc = llops.genop('ptr_nonzero', [spaceop.result],
                                     lltype.Bool)            
        else:
            v_exc_type = self.gen_getfield('exc_type', llops)
            var_no_exc = llops.genop('ptr_iszero', [v_exc_type],
                                     lltype.Bool)

        block.operations.extend(llops)
        
        block.exitswitch = var_no_exc
        #exception occurred case
        l = Link([error_constant(returnblock.inputargs[0].concretetype)], returnblock)
        l.exitcase = l.llexitcase = False

        #non-exception case
        l0 = block.exits[0]
        l0.exitcase = l0.llexitcase = True

        block.recloseblock(l0, l)

        insert_zeroing_op = False
        if spaceop.opname == 'malloc':
            insert_zeroing_op = True
        elif spaceop.opname == 'flavored_malloc':
            flavor = spaceop.args[0].value
            if flavor.startswith('gc'):
                insert_zeroing_op = True

        if insert_zeroing_op:
            if normalafterblock is None:
                normalafterblock = insert_empty_block(None, l0)
            v_result = spaceop.result
            if v_result in l0.args:
                result_i = l0.args.index(v_result)
                v_result_after = normalafterblock.inputargs[result_i]
            else:
                v_result_after = copyvar(None, v_result)
                l0.args.append(v_result)
                normalafterblock.inputargs.append(v_result_after)
            normalafterblock.operations.insert(
                0, SpaceOperation('zero_gc_pointers_inside',
                                  [v_result_after],
                                  varoftype(lltype.Void)))

        if self.always_exc_clear:
            # insert code that clears the exception even in the non-exceptional
            # case...  this is a hint for the JIT, but pointless otherwise
            if normalafterblock is None:
                normalafterblock = insert_empty_block(None, l0)
            llops = rtyper.LowLevelOpList(None)
            self.gen_setfield('exc_value', self.c_null_evalue, llops)
            self.gen_setfield('exc_type',  self.c_null_etype,  llops)
            normalafterblock.operations[:0] = llops
