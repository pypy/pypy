from pypy.translator.cli.test.runtest import CliTest

class MyClass:
    INCREMENT = 1

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

    def class_attribute(self):
        return self.x + self.INCREMENT

class MyDerivedClass(MyClass):
    INCREMENT = 2

    def __init__(self, x, y):
        MyClass.__init__(self, x+12, y+34)

    def compute(self):
        return self.x - self.y


# helper functions
def call_method(obj):
    return obj.compute()

def init_and_compute(cls, x, y):
    return cls(x, y).compute()

def nonnull_helper(lst):
    if lst is None:
        return 1
    else:
        return 2


class TestOO(CliTest):
    def test_indirect_call(self):
        def f():
            return 1
        def g():
            return 2
        def fn(flag):
            if flag:
                x = f
            else:
                x = g
            return x()
        assert self.interpret(fn, [True]) == 1
        assert self.interpret(fn, [False]) == 2

    def test_indirect_call_arguments(self):
        def f(x):
            return x+1
        def g(x):
            return x+2
        def fn(flag, n):
            if flag:
                x = f
            else:
                x = g
            return x(n)
        assert self.interpret(fn, [True, 42]) == 43


    def test_compute(self):
        def fn(x, y):
            obj = MyClass(x, y)
            return obj.compute()
        assert self.interpret(fn, [42, 13]) == fn(42, 13)

    def test_compute_multiply(self):
        def fn(x, y):
            obj = MyClass(x, y)
            return obj.compute_and_multiply(2)
        assert self.interpret(fn, [42, 13]) == fn(42, 13)
        
    def test_inheritance(self):
        def fn(x, y):
            obj = MyDerivedClass(x, y)
            return obj.compute_and_multiply(2)
        assert self.interpret(fn, [42, 13]) == fn(42, 13)

    def test_liskov(self):
        def fn(x, y):
            base = MyClass(x, y)
            derived = MyDerivedClass(x, y)
            return call_method(base) + call_method(derived)
        assert self.interpret(fn, [42, 13]) == fn(42, 13)

    def test_static_method(self):
        def fn(x, y):
            base = MyClass(x, y)
            derived = MyDerivedClass(x, y)
            return base.static_meth(x,y) + derived.static_meth(x, y)\
                   + MyClass.static_meth(x, y) + MyDerivedClass.static_meth(x, y)
        assert self.interpret(fn, [42, 13]) == fn(42, 13)

    def test_class_attribute(self):
        def fn(x, y):
            base = MyClass(x, y)
            derived = MyDerivedClass(x, y)
            return base.class_attribute() + derived.class_attribute()
        assert self.interpret(fn, [42, 13]) == fn(42, 13)

    def test_runtimenew(self):
        def fn(x, y):
            return init_and_compute(MyClass, x, y) + init_and_compute(MyDerivedClass, x, y)
        assert self.interpret(fn, [42, 13]) == fn(42, 13)

    def test_nonnull(self):
        def fn(x, y):
            return nonnull_helper([]) + nonnull_helper(None)
        assert self.interpret(fn, [42, 13]) == fn(42, 13)

