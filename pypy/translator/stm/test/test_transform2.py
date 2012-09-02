from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLFrame
from pypy.rpython.test.test_llinterp import get_interpreter, clear_tcache
from pypy.translator.stm.transform2 import STMTransformer
from pypy.conftest import option


class BaseTestTransform(object):
    prebuilt = ()

    def interpret(self, fn, args):
        clear_tcache()
        self.stmstate = STMState(self.prebuilt)
        interp, self.graph = get_interpreter(fn, args, view=False)
        interp.stmstate = self.stmstate
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


class STMState(object):
    def __init__(self, prebuilt=()):
        self.categories = {None: 'N'}   # Null
        for p in prebuilt:
            self.categories[self._getkey(p)] = 'G'   # Global
        self.writemode = set()

    def _getkey(self, p):
        assert lltype.typeOf(p).TO._gckind == 'gc'
        p = lltype.normalizeptr(p)
        if p:
            return p._obj0
        else:
            return None

    def get_category(self, p):
        key = self._getkey(p)
        return self.categories[key]

    def set_category(self, p, ncat):
        key = self._getkey(p)
        assert key is not None and ncat != 'N'
        self.categories[key] = ncat
        if ncat == 'W':
            self.writemode.add(key)


class LLSTMFrame(LLFrame):
    _MORE_PRECISE_CATEGORIES = {
        'P': 'PGORLWN',
        'G': 'GN',
        'O': 'ORLWN',
        'R': 'RLWN',
        'L': 'LWN',
        'W': 'WN',
        'N': 'N'}

    def get_category(self, p):
        return self.llinterpreter.stmstate.get_category(p)

    def set_category(self, p, ncat):
        self.llinterpreter.stmstate.set_category(p, ncat)

    def check_category(self, p, expected):
        cat = self.get_category(p)
        assert cat in self._MORE_PRECISE_CATEGORIES[expected]

    def op_stm_barrier(self, kind, obj):
        frm, digittwo, to = kind
        assert digittwo == '2'
        self.check_category(obj, frm)
        self.set_category(obj, to)
        return obj

    def op_getfield(self, obj, field):
        self.check_category(obj, 'R')
        return LLFrame.op_getfield(self, obj, field)

    def op_setfield(self, obj, fieldname, fieldvalue):
        self.check_category(obj, 'W')
        return LLFrame.op_setfield(self, obj, fieldname, fieldvalue)


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
        assert len(self.stmstate.writemode) == 0
        res = self.interpret(f1, [-5])
        assert res == 42
        assert len(self.stmstate.writemode) == 0

    def test_simple_write(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42
        self.prebuilt = [x1]

        def f1(n):
            x1.foo = n

        self.interpret(f1, [4])
        assert x1.foo == 4
        assert len(self.stmstate.writemode) == 1
