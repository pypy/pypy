from pypy.translator.simplify import join_blocks, cleanup_graph
from pypy.translator.unsimplify import copyvar, varoftype
from pypy.translator.unsimplify import insert_empty_block, split_block
from pypy.translator.backendopt import canraise, inline, support, removenoops
from pypy.objspace.flow.model import Block, Constant, Variable, Link, \
    c_last_exception, SpaceOperation, checkgraph, FunctionGraph, mkentrymap
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lloperation
from pypy.rpython import rtyper
from pypy.rpython import rclass
from pypy.rpython.rmodel import inputconst
from pypy.rlib.rarithmetic import r_uint, r_longlong, r_ulonglong
from pypy.rlib.rarithmetic import r_singlefloat
from pypy.rlib.debug import ll_assert
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.tool.sourcetools import func_with_new_name

PrimitiveErrorValue = {lltype.Signed: -1,
                       lltype.Unsigned: r_uint(-1),
                       lltype.SignedLongLong: r_longlong(-1),
                       lltype.UnsignedLongLong: r_ulonglong(-1),
                       lltype.Float: -1.0,
                       lltype.SingleFloat: r_singlefloat(-1.0),
                       lltype.Char: chr(255),
                       lltype.UniChar: unichr(0xFFFF), # XXX is this always right?
                       lltype.Bool: True,
                       llmemory.Address: llmemory.NULL,
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

def constant_value(llvalue):
    return Constant(llvalue, lltype.typeOf(llvalue))

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
        (assertion_error_ll_exc_type,
         assertion_error_ll_exc) = self.get_builtin_exception(AssertionError)
        (n_i_error_ll_exc_type,
         n_i_error_ll_exc) = self.get_builtin_exception(NotImplementedError)

        self.c_assertion_error_ll_exc_type = constant_value(
            assertion_error_ll_exc_type)
        self.c_n_i_error_ll_exc_type = constant_value(n_i_error_ll_exc_type)

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
            # When compiling in debug mode, the following ll_asserts will
            # crash the program as soon as it raises AssertionError or
            # NotImplementedError.  Useful when you are in a debugger.
            # When compiling in release mode, AssertionErrors and
            # NotImplementedErrors are raised normally, and only later
            # caught by debug_catch_exception and printed, which allows
            # us to see at least part of the traceback for them.
            ll_assert(etype != assertion_error_ll_exc_type, "AssertionError")
            ll_assert(etype != n_i_error_ll_exc_type, "NotImplementedError")
            exc_data.exc_type = etype
            exc_data.exc_value = evalue
            lloperation.llop.debug_start_traceback(lltype.Void, etype)

        def rpyexc_reraise(etype, evalue):
            exc_data.exc_type = etype
            exc_data.exc_value = evalue
            lloperation.llop.debug_reraise_traceback(lltype.Void, etype)

        def rpyexc_fetch_exception():
            evalue = rpyexc_fetch_value()
            rpyexc_clear()
            return evalue
        
        def rpyexc_restore_exception(evalue):
            if evalue:
                exc_data.exc_type = rclass.ll_inst_type(evalue)
                exc_data.exc_value = evalue

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
            self.noinline(rpyexc_raise),
            [self.lltype_of_exception_type, self.lltype_of_exception_value],
            lltype.Void,
            jitcallkind='rpyexc_raise') # for the JIT

        self.rpyexc_reraise_ptr = self.build_func(
            "RPyReRaiseException",
            rpyexc_reraise,
            [self.lltype_of_exception_type, self.lltype_of_exception_value],
            lltype.Void,
            jitcallkind='rpyexc_raise') # for the JIT

        self.rpyexc_fetch_exception_ptr = self.build_func(
            "RPyFetchException",
            rpyexc_fetch_exception,
            [], self.lltype_of_exception_value)

        self.rpyexc_restore_exception_ptr = self.build_func(
            "RPyRestoreException",
            self.noinline(rpyexc_restore_exception),
            [self.lltype_of_exception_value], lltype.Void)

        self.build_extra_funcs()

        self.mixlevelannotator.finish()
        self.lltype_to_classdef = translator.rtyper.lltype_to_classdef_mapping()

    def noinline(self, fn):
        fn = func_with_new_name(fn, fn.__name__)
        fn._dont_inline_ = True
        return fn

    def build_func(self, name, fn, inputtypes, rettype, **kwds):
        l2a = annmodel.lltype_to_annotation
        graph = self.mixlevelannotator.getgraph(fn, map(l2a, inputtypes), l2a(rettype))
        return self.constant_func(name, inputtypes, rettype, graph, 
                                  exception_policy="exc_helper", **kwds)

    def get_builtin_exception(self, Class):
        edata = self.translator.rtyper.getexceptiondata()
        rclass = self.translator.rtyper.type_system.rclass
        bk = self.translator.annotator.bookkeeper
        error_def = bk.getuniqueclassdef(Class)
        error_ll_exc = edata.get_standard_ll_exc_instance(
            self.translator.rtyper, error_def)
        error_ll_exc_type = rclass.ll_inst_type(error_ll_exc)
        return error_ll_exc_type, error_ll_exc

    def transform_completely(self):
        for graph in self.translator.graphs:
            self.create_exception_handling(graph)

    def create_exception_handling(self, graph):
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

        join_blocks(graph)
        # collect the blocks before changing them
        n_need_exc_matching_blocks = 0
        n_gen_exc_checks           = 0
        #
        entrymap = mkentrymap(graph)
        if graph.exceptblock in entrymap:
            for link in entrymap[graph.exceptblock]:
                self.transform_jump_to_except_block(graph, entrymap, link)
        #
        for block in list(graph.iterblocks()):
            self.replace_fetch_restore_operations(block)
            need_exc_matching, gen_exc_checks = self.transform_block(graph, block)
            n_need_exc_matching_blocks += need_exc_matching
            n_gen_exc_checks           += gen_exc_checks
        cleanup_graph(graph)
        return n_need_exc_matching_blocks, n_gen_exc_checks

    def replace_fetch_restore_operations(self, block):
        # the gctransformer will create these operations.  It looks as if the
        # order of transformations is important - but the gctransformer will
        # put them in a new graph, so all transformations will run again.
        for i in range(len(block.operations)):
            opname = block.operations[i].opname
            if opname == 'gc_fetch_exception':
                block.operations[i].opname = "direct_call"
                block.operations[i].args = [self.rpyexc_fetch_exception_ptr]

            elif opname == 'gc_restore_exception':
                block.operations[i].opname = "direct_call"
                block.operations[i].args.insert(0, self.rpyexc_restore_exception_ptr)
            elif opname == 'get_exception_addr':    # only for lltype
                block.operations[i].opname = "direct_call"
                block.operations[i].args.insert(0, self.rpyexc_get_exception_addr_ptr)
            elif opname == 'get_exc_value_addr':    # only for lltype
                block.operations[i].opname = "direct_call"
                block.operations[i].args.insert(0, self.rpyexc_get_exc_value_addr_ptr)

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
               block.exits[0].args[0] is block.operations[-1].result) and
              block.operations[-1].opname not in ('malloc',     # special cases
                                                  'malloc_nonmovable')):
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

    def comes_from_last_exception(self, entrymap, link):
        seen = {}
        pending = [(link, link.args[1])]
        while pending:
            link, v = pending.pop()
            if (link, v) in seen:
                continue
            seen[link, v] = True
            if link.last_exc_value is not None and v is link.last_exc_value:
                return True
            block = link.prevblock
            if block is None:
                continue
            for op in block.operations[::-1]:
                if v is op.result:
                    if op.opname == 'cast_pointer':
                        v = op.args[0]
                    else:
                        break
            for link in entrymap.get(block, ()):
                for v1, v2 in zip(link.args, block.inputargs):
                    if v2 is v:
                        pending.append((link, v1))
        return False

    def transform_jump_to_except_block(self, graph, entrymap, link):
        reraise = self.comes_from_last_exception(entrymap, link)
        result = Variable()
        result.concretetype = lltype.Void
        block = Block([copyvar(None, v)
                       for v in graph.exceptblock.inputargs])
        if reraise:
            block.operations = [
                SpaceOperation("direct_call",
                               [self.rpyexc_reraise_ptr] + block.inputargs,
                               result),
                ]
        else:
            block.operations = [
                SpaceOperation("direct_call",
                               [self.rpyexc_raise_ptr] + block.inputargs,
                               result),
                SpaceOperation('debug_record_traceback', [],
                               varoftype(lltype.Void)),
                ]
        link.target = block
        RETTYPE = graph.returnblock.inputargs[0].concretetype
        l = Link([error_constant(RETTYPE)], graph.returnblock)
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
        #
        c_check1 = self.c_assertion_error_ll_exc_type
        c_check2 = self.c_n_i_error_ll_exc_type
        llops.genop('debug_catch_exception', [var_type, c_check1, c_check2])
        #
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
        b = Block([])
        b.operations = [SpaceOperation('debug_record_traceback', [],
                                       varoftype(lltype.Void))]
        l = Link([error_constant(returnblock.inputargs[0].concretetype)], returnblock)
        b.closeblock(l)
        l = Link([], b)
        l.exitcase = l.llexitcase = False

        #non-exception case
        l0 = block.exits[0]
        l0.exitcase = l0.llexitcase = True

        block.recloseblock(l0, l)

        insert_zeroing_op = False
        if spaceop.opname == 'malloc':
            flavor = spaceop.args[1].value['flavor']
            if flavor == 'gc':
                insert_zeroing_op = True
        elif spaceop.opname == 'malloc_nonmovable':
            # xxx we cannot insert zero_gc_pointers_inside after
            # malloc_nonmovable, because it can return null.  For now
            # we simply always force the zero=True flag on
            # malloc_nonmovable.
            c_flags = spaceop.args[1]
            c_flags.value = c_flags.value.copy()
            spaceop.args[1].value['zero'] = True
        # NB. when inserting more special-cases here, keep in mind that
        # you also need to list the opnames in transform_block()
        # (see "special cases")

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

    def build_extra_funcs(self):
        EXCDATA = self.EXCDATA
        exc_data = self.exc_data_ptr

        def rpyexc_get_exception_addr():
            return (llmemory.cast_ptr_to_adr(exc_data) +
                    llmemory.offsetof(EXCDATA, 'exc_type'))

        def rpyexc_get_exc_value_addr():
            return (llmemory.cast_ptr_to_adr(exc_data) +
                    llmemory.offsetof(EXCDATA, 'exc_value'))

        self.rpyexc_get_exception_addr_ptr = self.build_func(
            "RPyGetExceptionAddr",
            rpyexc_get_exception_addr,
            [], llmemory.Address)

        self.rpyexc_get_exc_value_addr_ptr = self.build_func(
            "RPyGetExcValueAddr",
            rpyexc_get_exc_value_addr,
            [], llmemory.Address)


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

    def build_extra_funcs(self):
        pass

def ExceptionTransformer(translator):
    type_system = translator.rtyper.type_system.name
    if type_system == 'lltypesystem':
        return LLTypeExceptionTransformer(translator)
    else:
        assert type_system == 'ootypesystem'
        return OOTypeExceptionTransformer(translator)
