
from pypy.interpreter.eval import Frame
from pypy.interpreter.pycode import PyCode


class TestFrame: 
    def setup_method(self, method):
        def c(x, y, *args):
            pass
        code = PyCode._from_code(self.space, c.func_code)

        class ConcreteFastscopeFrame(Frame):
            
            def __init__(self, space, code, numlocals):
                self.code = code
                Frame.__init__(self, space, numlocals=numlocals)
                self.fastlocals_w = [None] * self.numlocals

            def getcode(self):
                return self.code

            def setfastscope(self, scope_w):
                self.fastlocals_w = scope_w

            def getfastscope(self):
                return self.fastlocals_w
        
        self.f = ConcreteFastscopeFrame(self.space, code, numlocals=5)
        

    def test_fast2locals(self):
        space = self.space 
        w = space.wrap
        self.f.fast2locals()
        assert space.eq_w(self.f.w_locals, self.space.wrap({}))
        
        self.f.fastlocals_w[0] = w(5)
        self.f.fast2locals()
        assert space.eq_w(self.f.w_locals, self.space.wrap({'x': 5}))

        self.f.fastlocals_w[2] = w(7)
        self.f.fast2locals()
        assert space.eq_w(self.f.w_locals, self.space.wrap({'x': 5, 'args': 7}))

    def sameList(self, l1, l2):
        assert len(l1) == len(l2) 
        for w_1, w_2 in zip(l1, l2):
            assert (w_1 is None) == (w_2 is None)
            if w_1 is not None:
                assert self.space.eq_w(w_1, w_2) 

    def test_locals2fast(self):
        w = self.space.wrap
        self.f.w_locals = self.space.wrap({})
        self.f.locals2fast()
        self.sameList(self.f.fastlocals_w, [None]*5)

        self.f.w_locals = self.space.wrap({'x': 5})
        self.f.locals2fast()
        self.sameList(self.f.fastlocals_w, [w(5)] + [None]*4)

        self.f.w_locals = self.space.wrap({'x':5, 'args':7})
        self.f.locals2fast()
        self.sameList(self.f.fastlocals_w, [w(5), None, w(7),
                                            None, None])
