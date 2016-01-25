from rpython.rtyper.lltypesystem import lltype, opimpl
from rpython.rtyper.llinterp import LLFrame
from rpython.rtyper.test.test_llinterp import get_interpreter, clear_tcache
from rpython.translator.stm.transform import STMTransformer
from rpython.conftest import option


class _stmptr(lltype._ptr):
    """Like lltype._ptr, but also keeps a current category level"""

    __slots__ = ['_category', '_original_ptr']

    def __init__(self, ptr, category):
        lltype._ptr.__init__(self, ptr._TYPE, ptr._obj0, ptr._solid)
        _stmptr._category.__set__(self, category)
        _stmptr._original_ptr.__set__(self, ptr)

    def __eq__(self, other):
        return self._original_ptr == other


class BaseTestTransform(object):
    do_read_barrier = False
    do_turn_inevitable = False
    do_jit_driver = False
    do_gc_transform = False

    def build_state(self):
        self.read_barriers = []

    def get_category_or_null(self, p):
        if isinstance(p, _stmptr):
            return p._category
        if not p:
            return None
        if p._solid:
            return 'I'     # allocated with immortal=True
        raise AssertionError("unknown category on %r" % (p,))

    def interpret(self, fn, args, run=True):
        self.build_state()
        clear_tcache()
        interp, self.graph = get_interpreter(fn, args, view=False,
                                             viewbefore=False)
        interp.tester = self
        interp.frame_class = LLSTMFrame
        #
        self.translator = interp.typer.annotator.translator
        self.translator.config.translation.gc = "stmgc"
        self.translator.config.translation.stm = True
        self.stmtransformer = STMTransformer(self.translator)
        if self.do_jit_driver:
            self.stmtransformer.transform_jit_driver()
        if self.do_turn_inevitable:
            self.stmtransformer.transform_turn_inevitable()
        if self.do_gc_transform:
            pass
            # from rpython.translator.c.gc import StmFrameworkGcPolicy
            # from rpython.translator.c.database import LowLevelDatabase
            # from rpython.translator.backendopt.all import backend_optimizations
            # from rpython.rtyper.lltypesystem.lltype import getfunctionptr
            # self.translator.config.translation.backendopt.inline=True
            # self.translator.config.translation.backendopt.inline_threshold=10000
            # self.translator.config.translation.backendopt.mallocs=True
            # # backend_optimizations(self.translator,
            # #                       inline_graph_from_anywhere=True,
            # #                       secondary=True, inline=True, inline_threshold=0,
            # #                       mallocs=True, print_statistics=True,
            # #                       clever_malloc_removal=True)
            # db = LowLevelDatabase(self.translator, gcpolicyclass=StmFrameworkGcPolicy)
            # self.stmtransformer.transform_after_gc()
            # list(db.gcpolicy.gc_startup_code())
            # db.get(getfunctionptr(self.graph))
            # db.complete()
        if self.do_read_barrier:
            self.stmtransformer.transform_read_barrier()
        if option.view:
            self.translator.view()
        #
        if self.do_jit_driver:
            import py
            py.test.skip("XXX how to test?")
        if run:
            result = interp.eval_graph(self.graph, args)
            return result


class LLSTMFrame(LLFrame):
    stm_ignored = False

    def eval(self):
        result = LLFrame.eval(self)
        return result

    def all_stm_ptrs(self):
        for frame in self.llinterpreter.frame_stack:
            for value in frame.bindings.values():
                if isinstance(value, _stmptr):
                    yield value

    def op_stm_read(self, obj):
        self.llinterpreter.tester.read_barriers.append(obj)

    def op_stm_ignored_start(self):
        assert self.stm_ignored == False
        self.stm_ignored = True

    def op_stm_ignored_stop(self):
        assert self.stm_ignored == True
        self.stm_ignored = False

    def op_getfield(self, obj, field):
        return LLFrame.op_getfield(self, obj, field)

    def op_setfield(self, obj, fieldname, fieldvalue):
        return LLFrame.op_setfield(self, obj, fieldname, fieldvalue)

    def op_cast_pointer(self, RESTYPE, obj):
        if obj._TYPE.TO._gckind == 'gc':
            p = opimpl.op_cast_pointer(RESTYPE, obj)
            return p
        return lltype.cast_pointer(RESTYPE, obj)
    op_cast_pointer.need_result_type = True

    def op_cast_opaque_ptr(self, RESTYPE, obj):
        if obj._TYPE.TO._gckind == 'gc':
            p = lltype.cast_opaque_ptr(RESTYPE, obj)
            return p
        return LLFrame.op_cast_opaque_ptr(self, RESTYPE, obj)
    op_cast_opaque_ptr.need_result_type = True

    def op_malloc(self, obj, flags):
        assert flags['flavor'] == 'gc'
        p = LLFrame.op_malloc(self, obj, flags)
        ptr2 = p
        return ptr2

    def transaction_break(self):
        pass

    def op_stm_commit_transaction(self):
        self.transaction_break()

    def op_stm_transaction_break(self):
        self.transaction_break()

    def op_stm_leave_transactional_zone(self):
        self.transaction_break()

    def op_stm_enter_transactional_zone(self):
        self.transaction_break()

    def op_stm_enter_callback_call(self):
        self.transaction_break()

    def op_stm_leave_callback_call(self):
        self.transaction_break()

    def op_stm_begin_inevitable_transaction(self):
        self.transaction_break()

    def op_stm_partial_commit_and_resume_other_threads(self):
        self.transaction_break()

    def op_jit_assembler_call(self):
        self.transaction_break() # dummy for test_writebarrier.py

    def op_stm_perform_transaction(self):
        self.transaction_break() # dummy for test_writebarrier.py

    def op_gc_writebarrier(self, p):
        raise Exception("should have been removed")

    def op_gc_writebarrier_before_copy(self, p):
        raise Exception("should not be produced at all")
