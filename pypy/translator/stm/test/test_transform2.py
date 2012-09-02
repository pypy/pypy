from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.llinterp import LLFrame
from pypy.rpython.test.test_llinterp import get_interpreter, clear_tcache
from pypy.objspace.flow.model import Constant
from pypy.translator.stm.transform2 import STMTransformer
from pypy.translator.stm.transform2 import MORE_PRECISE_CATEGORIES
from pypy.conftest import option


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

    def build_state(self):
        self.writemode = set()
        self.barriers = []

    def get_category(self, p):
        if isinstance(p, _stmptr):
            return p._category
        if not p:
            return 'N'
        if p._solid:
            return 'G'     # allocated with immortal=True
        raise AssertionError("unknown category on %r" % (p,))

    def interpret(self, fn, args):
        self.build_state()
        clear_tcache()
        interp, self.graph = get_interpreter(fn, args, view=False)
        interp.tester = self
        interp.frame_class = LLSTMFrame
        #
        self.translator = interp.typer.annotator.translator
        self.stmtransformer = STMTransformer(self.translator)
        self.stmtransformer.transform()
        if option.view:
            self.translator.view()
        #
        result = interp.eval_graph(self.graph, args)
        return result


class LLSTMFrame(LLFrame):

    def all_stm_ptrs(self):
        for frame in self.llinterpreter.frame_stack:
            for value in frame.bindings.values():
                if isinstance(value, _stmptr):
                    yield value

    def get_category(self, p):
        return self.llinterpreter.tester.get_category(p)

    def check_category(self, p, expected):
        cat = self.get_category(p)
        assert cat in MORE_PRECISE_CATEGORIES[expected]
        return cat

    def op_stm_barrier(self, kind, obj):
        frm, middledigit, to = kind
        assert middledigit == '2'
        cat = self.check_category(obj, frm)
        if cat in MORE_PRECISE_CATEGORIES[to]:
            # a barrier, but with no effect
            self.llinterpreter.tester.barriers.append(kind.lower())
            return obj
        else:
            # a barrier, calling a helper
            ptr2 = _stmptr(obj, to)
            if to == 'W':
                self.llinterpreter.tester.writemode.add(ptr2._obj)
            self.llinterpreter.tester.barriers.append(kind)
            return ptr2

    def op_stm_ptr_eq(self, obj1, obj2):
        self.check_category(obj1, 'P')
        self.check_category(obj2, 'P')
        self.llinterpreter.tester.barriers.append('=')
        return obj1 == obj2

    def op_getfield(self, obj, field):
        self.check_category(obj, 'R')
        return LLFrame.op_getfield(self, obj, field)

    def op_setfield(self, obj, fieldname, fieldvalue):
        self.check_category(obj, 'W')
        # convert R -> O all other pointers to the same object we can find
        for p in self.all_stm_ptrs():
            if p._category == 'R' and p._T == obj._T and p == obj:
                _stmptr._category.__set__(p, 'O')
        return LLFrame.op_setfield(self, obj, fieldname, fieldvalue)

    def op_malloc(self, obj, flags):
        p = LLFrame.op_malloc(self, obj, flags)
        ptr2 = _stmptr(p, 'W')
        self.llinterpreter.tester.writemode.add(ptr2._obj)
        return ptr2


class TestTransform(BaseTestTransform):

    def test_simple_read(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42
        x2 = lltype.malloc(X, immortal=True)
        x2.foo = 81

        def f1(n):
            if n > 1:
                return x2.foo
            else:
                return x1.foo

        res = self.interpret(f1, [4])
        assert res == 81
        assert len(self.writemode) == 0
        res = self.interpret(f1, [-5])
        assert res == 42
        assert len(self.writemode) == 0
        assert self.barriers == ['G2R']

    def test_simple_write(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1(n):
            x1.foo = n

        self.interpret(f1, [4])
        assert x1.foo == 4
        assert len(self.writemode) == 1
        assert self.barriers == ['G2W']

    def test_multiple_reads(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed),
                                 ('bar', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 6
        x1.bar = 7
        x2 = lltype.malloc(X, immortal=True)
        x2.foo = 81
        x2.bar = -1

        def f1(n):
            if n > 1:
                return x2.foo * x2.bar
            else:
                return x1.foo * x1.bar

        res = self.interpret(f1, [4])
        assert res == -81
        assert len(self.writemode) == 0
        assert self.barriers == ['G2R']

    def test_malloc(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(n):
            p = lltype.malloc(X)
            p.foo = n

        self.interpret(f1, [4])
        assert len(self.writemode) == 1
        assert self.barriers == []

    def test_write_may_alias(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(p, q):
            x1 = p.foo
            q.foo = 7
            x2 = p.foo
            return x1 * x2

        x = lltype.malloc(X, immortal=True); x.foo = 6
        y = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 36
        assert self.barriers == ['P2R', 'P2W', 'o2r']
        res = self.interpret(f1, [x, x])
        assert res == 42
        assert self.barriers == ['P2R', 'P2W', 'O2R']

    def test_write_cannot_alias(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        Y = lltype.GcStruct('Y', ('foo', lltype.Signed))
        def f1(p, q):
            x1 = p.foo
            q.foo = 7
            x2 = p.foo
            return x1 * x2

        x = lltype.malloc(X, immortal=True); x.foo = 6
        y = lltype.malloc(Y, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 36
        assert self.barriers == ['P2R', 'P2W']

    def test_call_external_random_effects(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        external_stuff = rffi.llexternal('external_stuff', [], lltype.Void,
                                         _callable=lambda: None,
                                         random_effects_on_gcobjs=True,
                                         threadsafe=False)
        def f1(p):
            x1 = p.foo
            external_stuff()
            x2 = p.foo
            return x1 * x2

        x = lltype.malloc(X, immortal=True); x.foo = 6
        res = self.interpret(f1, [x])
        assert res == 36
        assert self.barriers == ['P2R', 'p2r']

    def test_call_external_no_random_effects(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        external_stuff = rffi.llexternal('external_stuff2', [], lltype.Void,
                                         _callable=lambda: None,
                                         random_effects_on_gcobjs=False,
                                         threadsafe=False)
        def f1(p):
            x1 = p.foo
            external_stuff()
            x2 = p.foo
            return x1 * x2

        x = lltype.malloc(X, immortal=True); x.foo = 6
        res = self.interpret(f1, [x])
        assert res == 36
        assert self.barriers == ['P2R']

    def test_pointer_compare_0(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x):
            return x != lltype.nullptr(X)
        x = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x])
        assert res == 1
        assert self.barriers == []

    def test_pointer_compare_1(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x, y):
            return x != y
        x = lltype.malloc(X, immortal=True)
        y = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 1
        assert self.barriers == ['=']
        res = self.interpret(f1, [x, x])
        assert res == 0
        assert self.barriers == ['=']

    def test_pointer_compare_2(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x, y):
            x.foo = 41
            return x == y
        x = lltype.malloc(X, immortal=True)
        y = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 0
        assert self.barriers == ['P2W', '=']
        res = self.interpret(f1, [x, x])
        assert res == 1
        assert self.barriers == ['P2W', '=']

    def test_pointer_compare_3(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x, y):
            y.foo = 41
            return x != y
        x = lltype.malloc(X, immortal=True)
        y = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 1
        assert self.barriers == ['P2W', '=']
        res = self.interpret(f1, [x, x])
        assert res == 0
        assert self.barriers == ['P2W', '=']

    def test_pointer_compare_4(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x, y):
            x.foo = 40
            y.foo = 41
            return x != y
        x = lltype.malloc(X, immortal=True)
        y = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 1
        assert self.barriers == ['P2W', 'P2W']
        res = self.interpret(f1, [x, x])
        assert res == 0
        assert self.barriers == ['P2W', 'P2W']

    def test_simple_loop(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x, i):
            while i > 0:
                x.foo = i
                i -= 1
            return i
        x = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, 5])
        assert res == 0
        # for now we get this.  Later, we could probably optimize it
        assert self.barriers == ['P2W', 'p2w', 'p2w', 'p2w', 'p2w']
