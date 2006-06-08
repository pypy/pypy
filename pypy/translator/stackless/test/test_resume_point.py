from pypy.translator.stackless.transform import StacklessTransformer
from pypy.translator.stackless.test.test_transform import llinterp_stackless_function, rtype_stackless_function, one, run_stackless_function
from pypy import conftest
import py
from pypy.rpython import rstack

def transform_stackless_function(fn, do_inline=False):
    def wrapper(argv):
        return fn()
    t = rtype_stackless_function(wrapper)
    if do_inline:
        from pypy.translator.backendopt import inline, removenoops
        callgraph = inline.inlinable_static_callers(t.graphs)
        inline.auto_inlining(t, 1, callgraph=callgraph)
        for graph in t.graphs:
            removenoops.remove_superfluous_keep_alive(graph)
            removenoops.remove_duplicate_casts(graph, t)
    if conftest.option.view:
        t.view()
    st = StacklessTransformer(t, wrapper, False)
    st.transform_all()

def test_no_call():
    def f(x, y):
        x = x-1
        rstack.resume_point("rp0", x, y) 
        r = x+y
        rstack.stack_unwind()
        return r
    def example():
        v1 = f(one(),one()+one())
        state = rstack.resume_state_create(None, "rp0", one(), one()+one()+one())
        v2 = rstack.resume_state_invoke(int, state)
        return v1*10 + v2
##     transform_stackless_function(example)
    res = llinterp_stackless_function(example, assert_unwind=False)
    assert res == 24

def test_bogus_restart_state_create():
    def f(x, y):
        x = x-1
        rstack.resume_point("rp0", x, y) 
        return x+y
    def example():
        v1 = f(one(),one()+one())
        state = rstack.resume_state_create(None, "rp0", one())
        return v1
    info = py.test.raises(AssertionError, "transform_stackless_function(example)")
    assert 'rp0' in str(info.value)
    

def test_call():
    def g(x,y):
        return x*y
    def f(x, y):
        z = g(x,y)
        rstack.resume_point("rp1", y, returns=z) 
        return z+y
    def example():
        v1 = f(one(),one()+one())
        s = rstack.resume_state_create(None, "rp1", 5*one())
        v2 = rstack.resume_state_invoke(int, s, returning=one()*7)
        return v1*100 + v2
    res = llinterp_stackless_function(example)
    assert res == 412
    res = run_stackless_function(example)
    assert res == 412

def test_returns_with_instance():
    class C:
        def __init__(self, x):
            self.x = x
    def g(x):
        return C(x+1)
    def f(x, y):
        r = g(x)
        rstack.resume_point("rp1", y, returns=r)
        return r.x + y
    def example():
        v1 = f(one(),one()+one())
        s = rstack.resume_state_create(None, "rp1", 5*one())
        v2 = rstack.resume_state_invoke(int, s, returning=C(one()*3))
        return v1*100 + v2
    res = llinterp_stackless_function(example, assert_unwind=False)
    assert res == 408
    res = run_stackless_function(example)
    assert res == 408

def test_call_uncovered():
    def g(x,y):
        return x*y
    def f(x, y):
        z = g(x,y)
        rstack.resume_point("rp1", y, returns=z)
        return z+y+x
    def example():
        f(one(),one()+one())
        return 0
    e = py.test.raises(Exception, transform_stackless_function, example)
    assert e.value.args == ('not covered needed value at resume_point',)

def test_chained_states():
    def g(x, y):
        x += 1
        rstack.resume_point("rp1", x, y)
        return x + y
    def f(x, y, z):
        y += 1
        r = g(x, y)
        rstack.resume_point("rp2", z, returns=r)
        return r + z
    def example():
        v1 = f(one(), 2*one(), 3*one())
        s2 = rstack.resume_state_create(None, "rp2", 2*one())
        s1 = rstack.resume_state_create(s2, "rp1", 4*one(), 5*one())
        return 100*v1 + rstack.resume_state_invoke(int, s1)
    res = llinterp_stackless_function(example)
    assert res == 811
    res = run_stackless_function(example)
    assert res == 811

def test_return_instance():
    class C:
        pass
    def g(x):
        c = C()
        c.x = x + 1
        rstack.resume_point("rp1", c)
        return c
    def f(x, y):
        r = g(x)
        rstack.resume_point("rp2", y, returns=r)
        return r.x + y
    def example():
        v1 = f(one(), 2*one())
        s2 = rstack.resume_state_create(None, "rp2", 2*one())
        c = C()
        c.x = 4*one()
        s1 = rstack.resume_state_create(s2, "rp1", c)
        return v1*100 + rstack.resume_state_invoke(int, s1)
    res = llinterp_stackless_function(example)
    assert res == 406
    res = run_stackless_function(example)
    assert res == 406

def test_really_return_instance():
    class C:
        pass
    def g(x):
        c = C()
        c.x = x + 1
        rstack.resume_point("rp1", c)
        return c
    def example():
        v1 = g(one()).x
        c = C()
        c.x = 4*one()
        s1 = rstack.resume_state_create(None, "rp1", c)
        return v1*100 + rstack.resume_state_invoke(C, s1).x
    res = llinterp_stackless_function(example)
    assert res == 204
    res = run_stackless_function(example)
    assert res == 204

def test_resume_and_raise():
    def g(x):
        rstack.resume_point("rp0", x)
        if x == 0:
            raise KeyError
        return x + 1
    def example():
        v1 = g(one())
        s = rstack.resume_state_create(None, "rp0", one()-1)
        try:
            v2 = rstack.resume_state_invoke(int, s)
        except KeyError:
            v2 = 42
        return v1*100 + v2
    res = llinterp_stackless_function(example)
    assert res == 242
    res = run_stackless_function(example)
    assert res == 242
    
def test_resume_and_raise_and_catch():
    def g(x):
        rstack.resume_point("rp0", x)
        if x == 0:
            raise KeyError
        return x + 1
    def f(x):
        x = x - 1
        try:
            r = g(x)
            rstack.resume_point("rp1", returns=r)
        except KeyError:
            r = 42
        return r - 1
    def example():
        v1 = f(one()+one())
        s1 = rstack.resume_state_create(None, "rp1")
        s0 = rstack.resume_state_create(s1, "rp0", one()-1)
        v2 = rstack.resume_state_invoke(int, s0)
        return v1*100 + v2
    res = llinterp_stackless_function(example)
    assert res == 141
    res = run_stackless_function(example)
    assert res == 141

def test_invoke_raising():
    def g(x):
        rstack.resume_point("rp0", x)
        return x + 1
    def f(x):
        x = x - 1
        try:
            r = g(x)
            rstack.resume_point("rp1", returns=r)
        except KeyError:
            r = 42
        return r - 1
    def example():
        v1 = f(one()+one())
        s1 = rstack.resume_state_create(None, "rp1")
        s0 = rstack.resume_state_create(s1, "rp0", 0)
        v2 = rstack.resume_state_invoke(int, s0, raising=KeyError())
        return v1*100 + v2
    res = llinterp_stackless_function(example)
    assert res == 141
    res = run_stackless_function(example)
    assert res == 141
    

def test_finally():
    def f(x):
        rstack.resume_point("rp1", x)        
        return 1/x
    def in_finally(x): 
        rstack.resume_point("rp1.5", x)
        return 2/x
    def g(x):
        r = y = 0
        r += f(x)
        try:
            y = f(x)
            rstack.resume_point("rp0", x, r, returns=y)
        finally:
            r += in_finally(x)
        return r + y
    def example():
        return g(one())
    transform_stackless_function(example)

def test_except():
    py.test.skip("please don't write code like this")
    def f(x):
        rstack.resume_point("rp1", x)        
        return 1/x
    def g(x):
        r = y = 0
        r += f(x)
        try:
            y = f(x)
            rstack.resume_point("rp0", x, r, y, returns=y)
        except ZeroDivisionError:
            r += f(x)
        return r + y
    def example():
        return g(one())
    transform_stackless_function(example)

def test_using_pointers():
    from pypy.interpreter.miscutils import FixedStack
    class Arguments:
        def __init__(self, a, b, c, d, e):
            pass
    class W_Root:
        pass
    class FakeFrame:
        def __init__(self, space):
            self.space = space
            self.valuestack = FixedStack()
            self.valuestack.setup(10)
            self.valuestack.push(W_Root())
    class FakeSpace:
        def call_args(self, args, kw):
            return W_Root()
        def str_w(self, ob):
            return 'a string'
    def call_function(f, oparg, w_star=None, w_starstar=None):
        n_arguments = oparg & 0xff
        n_keywords = (oparg>>8) & 0xff
        keywords = None
        if n_keywords:
            keywords = {}
            for i in range(n_keywords):
                w_value = f.valuestack.pop()
                w_key   = f.valuestack.pop()
                key = f.space.str_w(w_key)
                keywords[key] = w_value
        arguments = [None] * n_arguments
        for i in range(n_arguments - 1, -1, -1):
            arguments[i] = f.valuestack.pop()
        args = Arguments(f.space, arguments, keywords, w_star, w_starstar)
        w_function  = f.valuestack.pop()
        w_result = f.space.call_args(w_function, args)
        rstack.resume_point("call_function", f, returns=w_result)
        f.valuestack.push(w_result)
    def example():
        s = FakeSpace()
        f = FakeFrame(s)
        call_function(f, 100, W_Root(), W_Root())
        return one()
    transform_stackless_function(example, do_inline=True)
