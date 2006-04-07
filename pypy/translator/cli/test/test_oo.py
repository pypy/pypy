from pypy.translator.cli.test.runtest import check

def test_oo():
    for name, func in globals().iteritems():
        if not name.startswith('oo_'):
            continue

        yield check, func, [int, int], (42, 13)


class MyClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def compute(self):
        return self.x + self.y

    def compute_and_multiply(self, factor):
        return self.compute() * factor

    def static_meth(x, y):
        return x*y
    static_meth = staticmethod(static_meth)

class MyDerivedClass(MyClass):
    def __init__(self, x, y):
        MyClass.__init__(self, x, y)

    def compute(self):
        return self.x - self.y

def oo_compute(x, y):
    obj = MyClass(x, y)
    return obj.compute()

def oo_compute_multiply(x, y):
    obj = MyClass(x, y)
    return obj.compute_and_multiply(2)

def oo_inheritance(x, y):
    obj = MyDerivedClass(x, y)
    return obj.compute_and_multiply(2)

def helper(obj):
    return obj.compute()

def oo_liskov(x, y):
    base = MyClass(x, y)
    derived = MyDerivedClass(x, y)
    return helper(base) + helper(derived)

def oo_static_method(x, y):
    base = MyClass(x, y)
    derived = MyDerivedClass(x, y)
    return base.static_meth(x,y) + derived.static_meth(x, y)\
           + MyClass.static_meth(x, y) + MyDerivedClass.static_meth(x, y)

