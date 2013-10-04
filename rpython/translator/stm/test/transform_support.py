from rpython.rtyper.lltypesystem import lltype, opimpl
from rpython.rtyper.llinterp import LLFrame
from rpython.rtyper.test.test_llinterp import get_interpreter, clear_tcache
from rpython.translator.stm.transform import STMTransformer
from rpython.translator.stm.writebarrier import needs_barrier
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
    do_write_barrier = False
    do_turn_inevitable = False
    do_jit_driver = False

    def build_state(self):
        self.writemode = set()
        self.barriers = []

    def get_category_or_null(self, p):
        if isinstance(p, _stmptr):
            return p._category
        if not p:
            return None
        if p._solid:
            return 'I'     # allocated with immortal=True
        raise AssertionError("unknown category on %r" % (p,))

    def interpret(self, fn, args, gcremovetypeptr=False, run=True):
        self.build_state()
        clear_tcache()
        interp, self.graph = get_interpreter(fn, args, view=False)
        interp.tester = self
        interp.frame_class = LLSTMFrame
        #
        self.translator = interp.typer.annotator.translator
        self.translator.config.translation.gcremovetypeptr = gcremovetypeptr
        self.stmtransformer = STMTransformer(self.translator)
        if self.do_jit_driver:
            self.stmtransformer.transform_jit_driver()
        if self.do_write_barrier:
            self.stmtransformer.transform_write_barrier()
        if self.do_turn_inevitable:
            self.stmtransformer.transform_turn_inevitable()
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

    def all_stm_ptrs(self):
        for frame in self.llinterpreter.frame_stack:
            for value in frame.bindings.values():
                if isinstance(value, _stmptr):
                    yield value

    def get_category_or_null(self, p):
        return self.llinterpreter.tester.get_category_or_null(p)

    def check_category(self, p, expected):
        cat = self.get_category_or_null(p)
        assert cat is None or cat in 'AIQRVW'
        if expected is not None:
            if self.stm_ignored:
                if expected >= 'W':
                    raise AssertionError("should not be seen in 'stm_ignored'")
                if expected > 'I':
                    expected = 'I'
            assert cat is not None and cat >= expected
        return cat

    def op_stm_barrier(self, kind, obj):
        frm, middledigit, to = kind
        assert middledigit == '2'
        cat = self.check_category(obj, frm)
        if not needs_barrier(cat, to):
            # a barrier, but with no effect
            self.llinterpreter.tester.barriers.append(kind.lower())
            return obj
        else:
            # a barrier, calling a helper
            ptr2 = _stmptr(obj, to)
            if to >= 'V':
                self.llinterpreter.tester.writemode.add(ptr2._obj)
            self.llinterpreter.tester.barriers.append(kind)
            return ptr2

    def op_stm_ignored_start(self):
        assert self.stm_ignored == False
        self.stm_ignored = True

    def op_stm_ignored_stop(self):
        assert self.stm_ignored == True
        self.stm_ignored = False

    def op_stm_ptr_eq(self, obj1, obj2):
        self.check_category(obj1, None)
        self.check_category(obj2, None)
        self.llinterpreter.tester.barriers.append('=')
        return obj1 == obj2

    def op_getfield(self, obj, field):
        if obj._TYPE.TO._gckind == 'gc':
            if obj._TYPE.TO._immutable_field(field):
                expected = 'I'
            else:
                expected = 'R'
            self.check_category(obj, expected)
        return LLFrame.op_getfield(self, obj, field)

    def op_setfield(self, obj, fieldname, fieldvalue):
        if obj._TYPE.TO._gckind == 'gc':
            T = lltype.typeOf(fieldvalue)
            if isinstance(T, lltype.Ptr) and T.TO._gckind == 'gc':
                self.check_category(obj, 'W')
            else:
                self.check_category(obj, 'V')
            # convert R -> Q all other pointers to the same object we can find
            for p in self.all_stm_ptrs():
                if p._category == 'R' and p._T == obj._T and p == obj:
                    _stmptr._category.__set__(p, 'Q')
        return LLFrame.op_setfield(self, obj, fieldname, fieldvalue)

    def op_cast_pointer(self, RESTYPE, obj):
        if obj._TYPE.TO._gckind == 'gc':
            cat = self.check_category(obj, None)
            p = opimpl.op_cast_pointer(RESTYPE, obj)
            return _stmptr(p, cat)
        return lltype.cast_pointer(RESTYPE, obj)
    op_cast_pointer.need_result_type = True

    def op_cast_opaque_ptr(self, RESTYPE, obj):
        if obj._TYPE.TO._gckind == 'gc':
            cat = self.check_category(obj, None)
            p = lltype.cast_opaque_ptr(RESTYPE, obj)
            return _stmptr(p, cat)
        return LLFrame.op_cast_opaque_ptr(self, RESTYPE, obj)
    op_cast_opaque_ptr.need_result_type = True

    def op_malloc(self, obj, flags):
        assert flags['flavor'] == 'gc'
        # convert all existing pointers W -> V
        for p in self.all_stm_ptrs():
            if p._category == 'W':
                _stmptr._category.__set__(p, 'V')
        p = LLFrame.op_malloc(self, obj, flags)
        ptr2 = _stmptr(p, 'W')
        self.llinterpreter.tester.writemode.add(ptr2._obj)
        return ptr2

    def transaction_break(self):
        # convert -> I all other pointers to the same object we can find
        for p in self.all_stm_ptrs():
            if p._category > 'I':
                _stmptr._category.__set__(p, 'I')

    def op_stm_commit_transaction(self):
        self.transaction_break()

    def op_stm_begin_inevitable_transaction(self):
        self.transaction_break()

    def op_gc_writebarrier(self, p):
        raise Exception("should have been removed")

    def op_gc_writebarrier_before_copy(self, p):
        raise Exception("should not be produced at all")
