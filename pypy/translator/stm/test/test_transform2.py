from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLFrame
from pypy.rpython.test.test_llinterp import get_interpreter, clear_tcache
from pypy.objspace.flow.model import Constant
from pypy.translator.stm.transform2 import STMTransformer
from pypy.translator.stm.transform2 import MORE_PRECISE_CATEGORIES
from pypy.conftest import option


class _stmptr(lltype._ptr):
    """Like lltype._ptr, but also keeps a current category level"""

    __slots__ = ['_category']

    def __init__(self, ptr, category):
        lltype._ptr.__init__(self, ptr._TYPE, ptr._obj0, ptr._solid)
        _stmptr._category.__set__(self, category)


class BaseTestTransform(object):
    prebuilt = ()

    def build_state(self):
        self.writemode = set()
        self.barriers = []

    def get_category(self, p):
        if isinstance(p, _stmptr):
            return p._category
        if not p:
            return 'N'
        if p in self.prebuilt:
            return 'G'
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

    def get_category(self, p):
        return self.llinterpreter.tester.get_category(p)

    def check_category(self, p, expected):
        cat = self.get_category(p)
        assert cat in MORE_PRECISE_CATEGORIES[expected]

    def op_stm_barrier(self, kind, obj):
        frm, middledigit, to = kind
        assert middledigit == '2'
        self.check_category(obj, frm)
        ptr2 = _stmptr(obj, to)
        if to == 'W':
            self.llinterpreter.tester.writemode.add(ptr2._obj)
        self.llinterpreter.tester.barriers.append(kind)
        return ptr2

    def op_getfield(self, obj, field):
        self.check_category(obj, 'R')
        return LLFrame.op_getfield(self, obj, field)

    def op_setfield(self, obj, fieldname, fieldvalue):
        self.check_category(obj, 'W')
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
        self.prebuilt = [x1, x2]

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
        self.prebuilt = [x1]

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
        self.prebuilt = [x1, x2]

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
