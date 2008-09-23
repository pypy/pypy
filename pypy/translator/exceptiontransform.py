from pypy.translator.simplify import join_blocks, cleanup_graph
from pypy.translator.unsimplify import copyvar, varoftype
from pypy.translator.unsimplify import insert_empty_block, split_block
from pypy.translator.backendopt import canraise, inline, support, removenoops
from pypy.objspace.flow.model import Block, Constant, Variable, Link, \
    c_last_exception, SpaceOperation, checkgraph, FunctionGraph
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lloperation
from pypy.rpython.lltypesystem.llmemory import NULL
from pypy.rpython import rtyper
from pypy.rpython import rclass
from pypy.rpython.rmodel import inputconst
from pypy.rlib.rarithmetic import r_uint, r_longlong, r_ulonglong
from pypy.rlib.rarithmetic import r_singlefloat
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator

PrimitiveErrorValue = {lltype.Signed: -1,
                       lltype.Unsigned: r_uint(-1),
                       lltype.SignedLongLong: r_longlong(-1),
                       lltype.UnsignedLongLong: r_ulonglong(-1),
                       lltype.Float: -1.0,
                       lltype.SingleFloat: r_singlefloat(-1.0),
                       lltype.Char: chr(255),
                       lltype.UniChar: unichr(0xFFFF), # XXX is this always right?
                       lltype.Bool: True,
                       llmemory.Address: NULL,
                       lltype.Void: None}

for TYPE in rffi.NUMBER_TYPES:
    PrimitiveErrorValue[TYPE] = lltype.cast_primitive(TYPE, -1)
del TYPE

def error_value(T):
    if isinstance(T, lltype.Primitive):
        return PrimitiveErrorValue[T]
    elif isinstance(T, lltype.Ptr):
        return lltype.nullptr(T.TO)
    elif isinstance(T, ootype.OOType):
        return ootype.null(T)
    assert 0, "not implemented yet"

def error_constant(T):
    return Constant(error_value(T), T)

class BaseExceptionTransformer(object):

    def __init__(self, translator):
        self.translator = translator
        self.raise_analyzer = canraise.RaiseAnalyzer(translator)
        edata = translator.rtyper.getexceptiondata()
        self.lltype_of_exception_value = edata.lltype_of_exception_value
        self.lltype_of_exception_type = edata.lltype_of_exception_type
        self.mixlevelannotator = MixLevelHelperAnnotator(translator.rtyper)
        exc_data, null_type, null_value = self.setup_excdata()

        rclass = translator.rtyper.type_system.rclass
        runtime_error_def = translator.annotator.bookkeeper.getuniqueclassdef(RuntimeError)
        runtime_error_ll_exc = edata.get_standard_ll_exc_instance(translator.rtyper, runtime_error_def)
        runtime_error_ll_exc_type = rclass.ll_inst_type(runtime_error_ll_exc)

        def rpyexc_occured():
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

        def rpyexc_fetch_exception():
            evalue = rpyexc_fetch_value()
            rpyexc_clear()
            return evalue
        
        def rpyexc_restore_exception(evalue):
            if evalue:
                rpyexc_raise(rclass.ll_inst_type(evalue), evalue)

        def rpyexc_raise_runtime_error():
            rpyexc_raise(runtime_error_ll_exc_type, runtime_error_ll_exc)

        self.rpyexc_occured_ptr = self.build_func(
            "RPyExceptionOccurred",
            rpyexc_occured,
            [], lltype.Bool)

        self.rpyexc_fetch_type_ptr = self.build_func(
            "RPyFetchExceptionType",
            rpyexc_fetch_type,
            [], self.lltype_of_exception_type)

        self.rpyexc_fetch_value_ptr = self.build_func(
            "RPyFetchExceptionValue",
            rpyexc_fetch_value,
            [], self.lltype_of_exception_value)

        self.rpyexc_clear_ptr = self.build_func(
            "RPyClearException",
            rpyexc_clear,
            [], lltype.Void)

        self.rpyexc_raise_ptr = self.build_func(
            "RPyRaiseException",
            rpyexc_raise,
            [self.lltype_of_exception_type, self.lltype_of_exception_value],
            lltype.Void,
            jitcallkind='rpyexc_raise') # for the JIT

        self.rpyexc_raise_runtime_error_ptr = self.build_func(
            "RPyRaiseRuntimeError",
            rpyexc_raise_runtime_error,
            [], lltype.Void)

        self.rpyexc_fetch_exception_ptr = self.build_func(
            "RPyFetchException",
            rpyexc_fetch_exception,
            [], self.lltype_of_exception_value)

        self.rpyexc_restore_exception_ptr = self.build_func(
            "RPyRestoreException",
            rpyexc_restore_exception,
            [self.lltype_of_exception_value], lltype.Void)

        self.mixlevelannotator.finish()
        self.lltype_to_classdef = translator.rtyper.lltype_to_classdef_mapping()

    def build_func(self, name, fn, inputtypes, rettype, **kwds):
        l2a = annmodel.lltype_to_annotation
        graph = self.mixlevelannotator.getgraph(fn, map(l2a, inputtypes), l2a(rettype))
        return self.constant_func(name, inputtypes, rettype, graph, 
                                  exception_policy="exc_helper", **kwds)

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
            assert self.same_obj(self.exc_data_ptr, graph.exceptiontransformed)
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
            self.replace_stack_unwind(block)
            self.replace_fetch_restore_operations(block)
            need_exc_matching, gen_exc_checks = self.transform_block(graph, block)
            n_need_exc_matching_blocks += need_exc_matching
            n_gen_exc_checks           += gen_exc_checks
        self.transform_except_block(graph, graph.exceptblock)
        cleanup_graph(graph)
        removenoops.remove_superfluous_keep_alive(graph)
        return n_need_exc_matching_blocks, n_gen_exc_checks

    def replace_stack_unwind(self, block):
        for i in range(len(block.operations)):
            if block.operations[i].opname == 'stack_unwind':
                # if there are stack_unwind ops left,
                # the graph was not stackless-transformed
                # so we need to raise a RuntimeError in any
                # case
                block.operations[i].opname = "direct_call"
                block.operations[i].args = [self.rpyexc_raise_runtime_error_ptr]

    def replace_fetch_restore_operations(self, block):
        # the gctransformer will create these operations.  It looks as if the
        # order of transformations is important - but the gctransformer will
        # put them in a new graph, so all transformations will run again.
        for i in range(len(block.operations)):
            if block.operations[i].opname == 'gc_fetch_exception':
                block.operations[i].opname = "direct_call"
                block.operations[i].args = [self.rpyexc_fetch_exception_ptr]

            if block.operations[i].opname == 'gc_restore_exception':
                block.operations[i].opname = "direct_call"
                block.operations[i].args.insert(0, self.rpyexc_restore_exception_ptr)

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

            splitlink = split_block(None, block, i+1)
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
        fptr = self.constant_func("dummy_exc1", ARGTYPES, op.result.concretetype, newgraph)
        return newgraph, SpaceOperation("direct_call", [fptr] + callargs, op.result) 

    def gen_exc_check(self, block, returnblock, normalafterblock=None):
        #var_exc_occured = Variable()
        #var_exc_occured.concretetype = lltype.Bool
        #block.operations.append(SpaceOperation("safe_call", [self.rpyexc_occured_ptr], var_exc_occured))

        llops = rtyper.LowLevelOpList(None)

        spaceop = block.operations[-1]
        alloc_shortcut = self.check_for_alloc_shortcut(spaceop)

        # XXX: does alloc_shortcut make sense also for ootype?
        if alloc_shortcut:
            T = spaceop.result.concretetype
            var_no_exc = self.gen_nonnull(spaceop.result, llops)
        else:
            v_exc_type = self.gen_getfield('exc_type', llops)
            var_no_exc = self.gen_isnull(v_exc_type, llops)

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
        # XXX this is not right. it also inserts zero_gc_pointers_inside
        # XXX on a path that malloc_nonmovable returns null, but does not raise
        # XXX which might end up with a segfault. But we don't have such gc now
        if spaceop.opname == 'malloc' or spaceop.opname == 'malloc_nonmovable':
            flavor = spaceop.args[1].value['flavor']
            if flavor == 'gc':
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

class LLTypeExceptionTransformer(BaseExceptionTransformer):

    def setup_excdata(self):
        EXCDATA = lltype.Struct('ExcData',
            ('exc_type',  self.lltype_of_exception_type),
            ('exc_value', self.lltype_of_exception_value))
        self.EXCDATA = EXCDATA

        exc_data = lltype.malloc(EXCDATA, immortal=True)
        null_type = lltype.nullptr(self.lltype_of_exception_type.TO)
        null_value = lltype.nullptr(self.lltype_of_exception_value.TO)

        self.exc_data_ptr = exc_data
        self.cexcdata = Constant(exc_data, lltype.Ptr(self.EXCDATA))
        self.c_null_etype = Constant(null_type, self.lltype_of_exception_type)
        self.c_null_evalue = Constant(null_value, self.lltype_of_exception_value)

        return exc_data, null_type, null_value

    def constant_func(self, name, inputtypes, rettype, graph, **kwds):
        FUNC_TYPE = lltype.FuncType(inputtypes, rettype)
        fn_ptr = lltype.functionptr(FUNC_TYPE, name, graph=graph, **kwds)
        return Constant(fn_ptr, lltype.Ptr(FUNC_TYPE))

    def gen_getfield(self, name, llops):
        c_name = inputconst(lltype.Void, name)
        return llops.genop('getfield', [self.cexcdata, c_name],
                           resulttype = getattr(self.EXCDATA, name))

    def gen_setfield(self, name, v_value, llops):
        c_name = inputconst(lltype.Void, name)
        llops.genop('setfield', [self.cexcdata, c_name, v_value])

    def gen_isnull(self, v, llops):
        return llops.genop('ptr_iszero', [v], lltype.Bool)

    def gen_nonnull(self, v, llops):
        return llops.genop('ptr_nonzero', [v], lltype.Bool)

    def same_obj(self, ptr1, ptr2):
        return ptr1._same_obj(ptr2)

    def check_for_alloc_shortcut(self, spaceop):
        if spaceop.opname in ('malloc', 'malloc_varsize'):
            return True
        elif spaceop.opname == 'direct_call':
            fnobj = spaceop.args[0].value._obj
            if hasattr(fnobj, '_callable'):
                oopspec = getattr(fnobj._callable, 'oopspec', None)
                if oopspec and oopspec == 'newlist(length)':
                    return True
        return False

class OOTypeExceptionTransformer(BaseExceptionTransformer):

    def setup_excdata(self):
        EXCDATA = ootype.Record({'exc_type': self.lltype_of_exception_type,
                                 'exc_value': self.lltype_of_exception_value})
        self.EXCDATA = EXCDATA

        exc_data = ootype.new(EXCDATA)
        null_type = ootype.null(self.lltype_of_exception_type)
        null_value = ootype.null(self.lltype_of_exception_value)

        self.exc_data_ptr = exc_data
        self.cexcdata = Constant(exc_data, self.EXCDATA)

        self.c_null_etype = Constant(null_type, self.lltype_of_exception_type)
        self.c_null_evalue = Constant(null_value, self.lltype_of_exception_value)

        return exc_data, null_type, null_value

    def constant_func(self, name, inputtypes, rettype, graph, **kwds):
        FUNC_TYPE = ootype.StaticMethod(inputtypes, rettype)
        fn_ptr = ootype.static_meth(FUNC_TYPE, name, graph=graph, **kwds)
        return Constant(fn_ptr, FUNC_TYPE)

    def gen_getfield(self, name, llops):
        c_name = inputconst(lltype.Void, name)
        return llops.genop('oogetfield', [self.cexcdata, c_name],
                           resulttype = self.EXCDATA._field_type(name))

    def gen_setfield(self, name, v_value, llops):
        c_name = inputconst(lltype.Void, name)
        llops.genop('oosetfield', [self.cexcdata, c_name, v_value])

    def gen_isnull(self, v, llops):
        nonnull = self.gen_nonnull(v, llops)
        return llops.genop('bool_not', [nonnull], lltype.Bool)

    def gen_nonnull(self, v, llops):
        return llops.genop('oononnull', [v], lltype.Bool)

    def same_obj(self, obj1, obj2):
        return obj1 is obj2

    def check_for_alloc_shortcut(self, spaceop):
        return False

def ExceptionTransformer(translator):
    type_system = translator.rtyper.type_system.name
    if type_system == 'lltypesystem':
        return LLTypeExceptionTransformer(translator)
    else:
        assert type_system == 'ootypesystem'
        return OOTypeExceptionTransformer(translator)
