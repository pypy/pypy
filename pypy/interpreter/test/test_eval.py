
import autopath
from pypy.interpreter.eval import Frame, UNDEFINED
from pypy.interpreter.pycode import PyCode


class TestFrame: 
    def setup_method(self, method):
        def c(x, y, *args):
            pass
        code = PyCode(self.space)._from_code(c.func_code)

        class ConcreteFastscopeFrame(Frame):
            
            def __init__(self, space, code, numlocals):
                Frame.__init__(self, space, code, numlocals=numlocals)
                self.fastlocals_w = [UNDEFINED] * self.numlocals

            def setfastscope(self, scope_w):
                self.fastlocals_w = scope_w

            def getfastscope(self):
                return self.fastlocals_w
        
        self.f = ConcreteFastscopeFrame(self.space, code, numlocals=5)
        

    def test_fast2locals(self):
        space = self.space 
        w = space.wrap
        self.f.fast2locals()
        assert space.eq_w(self.f.w_locals, self.space.newdict([]))
        
        self.f.fastlocals_w[0] = w(5)
        self.f.fast2locals()
        assert space.eq_w(self.f.w_locals, self.space.newdict([
                                               (w('x'), w(5))]))

        self.f.fastlocals_w[2] = w(7)
        self.f.fast2locals()
        assert space.eq_w(self.f.w_locals, self.space.newdict([
            (w('x'), w(5)),
            (w('args'), w(7))]))

    def sameList(self, l1, l2):
        assert len(l1) == len(l2) 
        for w_1, w_2 in zip(l1, l2):
            assert (w_1 is UNDEFINED) == (w_2 is UNDEFINED)
            if w_1 is not UNDEFINED:
                assert self.space.eq_w(w_1, w_2) 

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
