from pypy.translator.tool.raymond import (get_compiled_module, get_compiled,
                                          wrap, unwrap, __init__,
                                          ExtCompiler)

import sys, types

P = False  # debug printing


# track __del__ calls
class DelMonitor(object):
    def __init__(self):
        self.reset()
    def reset(self):
        self.deletions = 0
    def notify(self):
        self.deletions += 1
    def report(self):
        return self.deletions

delmonitor = DelMonitor()

class DemoBaseNotExposed(object):
    """this is the doc string"""
    def __init__(self, a, b):
        self.a = a
        self.b = b
        if P:print 'init'

    def demo(self):
        """this is the doc for demo"""
        if P:print 'demo'
        return self.a + self.b


# a trivial class to be exposed
class DemoClass(DemoBaseNotExposed):
    def demonotcalled(self):
        return self.demo() + 42

    def __del__(self):
        delmonitor.notify()
        if P:print 'del'

    def __add__(self, other):
        # XXX I would like to use type(), but its support is very limited
        #return type(self)(self.a + other.a, self.b + other.b)
        return DemoClass(self.a + other.a, self.b + other.b)

    def ab(self):
        return self.a + self.b
    ab = property(ab)

# see if we get things exported with subclassing
class DemoSubclass(DemoClass):
    def __init__(self, a, b, c):
        #super(DemoSubclass, self).__init__(a, b)
        DemoClass.__init__(self, b, a)
        self.c = c

    def demo(self, *other):
        #if other: print other
        return float(DemoClass.demo(self))
    
    def otherdemo(self):
        return 'this is the DemoSubclass', self.a, self.b

    def __del__(self):
        pass # this is intentionally another thing

# see how classes are handled that were not annotated
class DemoNotAnnotated(object):
    def __init__(self):
        self.hugo = 42
    def retrieve(self):
        return self.hugo

def democlass_helper_sub(a, b):
    # prevend inlining
    if a == -42:
        return democlass_helper_sub(a-1, b)
    inst = DemoClass(a, b)
    pyobj = wrap(inst)
    obj = unwrap(pyobj, DemoClass)
    ret = obj.demo()
    inst = DemoSubclass(a, b, 42)
    pyobj = wrap(inst)
    obj = unwrap(pyobj, DemoSubclass)
    ret = obj.demo()
    return ret

def democlass_helper(a=int, b=int):
    delmonitor.reset()
    ret = democlass_helper_sub(a, b)
    return delmonitor.report(), ret, long(42)

def democlass_helper2(a=int, b=int):
    self = DemoClass(a, b)
    self.demo()
    self2 = DemoSubclass(a, b, 42)
    return self

# creating an object, wrapping, unwrapping, call function, check whether __del__ is called
def test_wrap_call_dtor():
    f = get_compiled(democlass_helper, use_boehm=not True, exports=[DemoSubclass])
    ret = f(2, 3)
    if P: print ret
    assert ret[0] == 1

# exposing and using classes from a generasted extension module
def test_expose_classes():
    m = get_compiled_module(democlass_helper2, use_boehm=not True, exports=[
        DemoClass, DemoSubclass, __init__, DemoNotAnnotated])
    obj = m.DemoClass(2, 3)
    res = obj.demo()
    assert res == DemoClass(2, 3).demo()
    assert (obj + obj).demo() == 10

def extfunc(inst):
    return inst.demo()

def extfunc2(tup):
    inst1, inst2 = tup
    return inst1.__add__(inst2)

def t(a=int, b=int, c=DemoClass):
    x = DemoClass(a, b)
    x.demo()
    DemoSubclass(a, a, b).demo()
    DemoSubclass(a, a, b).demo(6)
    y = DemoSubclass(a, a, b).demo(6, 'hu')
    extfunc(x)
    extfunc2( (x, x) )
    if isinstance(c, DemoSubclass):
        print 42
    return x.__add__(x), DemoBaseNotExposed(17, 4) # see if it works without wrapper

# exposing and using classes from a generated extension module
def test_asd():
    m = get_compiled_module(t, use_boehm=not True, exports=[
        DemoClass, DemoSubclass, DemoNotAnnotated, extfunc, extfunc2])
    obj = m.DemoClass(2, 3)
    res = obj.demo()
    assert res == DemoClass(2, 3).demo()
    assert (obj + obj).demo() == 10

def test_extcompiler():
    compiler = ExtCompiler(t)
    compiler.export(DemoClass)
    compiler.export(DemoSubclass)
    compiler.export(DemoNotAnnotated)
    compiler.export(42, name='zweiundvierzig')
    m = compiler.build('testmodule')
    obj = m.DemoClass(2, 3)
    res = obj.demo()
    assert res == DemoClass(2, 3).demo()
    assert (obj + obj).demo() == 10
    assert hasattr(m, '__init__')
    
if __name__=='__main__':
    test_expose_classes()
    