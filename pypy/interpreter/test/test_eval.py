
import autopath
from pypy.interpreter.eval import Frame, UNDEFINED
from pypy.interpreter.pycode import PyCode


class TestFrame: 
    def setup_method(self, method):
        def c(x, y, *args):
            pass
        code = PyCode()._from_code(c.func_code)
        self.f = Frame(self.space, code, numlocals=5)

    def test_fast2locals(self):
        w = self.space.wrap
        space = self.space 
        self.f.fast2locals()
        assert space._isequal(self.f.w_locals, self.space.newdict([]))
        
        self.f.fastlocals_w[0] = w(5)
        self.f.fast2locals()
        assert space._isequal(self.f.w_locals, self.space.newdict([
                                               (w('x'), w(5))]))

        self.f.fastlocals_w[2] = w(7)
        self.f.fast2locals()
        assert space._isequal(self.f.w_locals, self.space.newdict([
            (w('x'), w(5)),
            (w('args'), w(7))]))

    def sameList(self, l1, l2):
        assert len(l1) == len(l2) 
        for w_1, w_2 in zip(l1, l2):
            assert not ((w_1 is UNDEFINED) != (w_2 is UNDEFINED))
            if w_1 is not UNDEFINED:
                assert self.space._isequal(w_1, w_2) 

    def test_locals2fast(self):
        w = self.space.wrap
        self.f.w_locals = self.space.newdict([])
        self.f.locals2fast()
        self.sameList(self.f.fastlocals_w, [UNDEFINED]*5)

        self.f.w_locals = self.space.newdict([
            (w('x'), w(5))])
        self.f.locals2fast()
        self.sameList(self.f.fastlocals_w, [w(5)] + [UNDEFINED]*4)

        self.f.w_locals = self.space.newdict([
            (w('x'), w(5)),
            (w('args'), w(7))])
        self.f.locals2fast()
        self.sameList(self.f.fastlocals_w, [w(5), UNDEFINED, w(7),
                                            UNDEFINED, UNDEFINED])
