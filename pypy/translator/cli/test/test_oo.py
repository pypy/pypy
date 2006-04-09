from pypy.translator.cli.test.runtest import check

def test_oo():
    for name, func in globals().iteritems():
        if not name.startswith('oo_'):
            continue

        yield check, func, [int, int], (42, 13)


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

##    def class_meth(cls, x, y):
##        return x*y + cls.INCREMENT
##    class_meth = classmethod(class_meth)

    def class_attribute(self):
        return self.x + self.INCREMENT

class MyDerivedClass(MyClass):
    INCREMENT = 2

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

def oo_class_attribute(x, y):
    base = MyClass(x, y)
    derived = MyDerivedClass(x, y)
    return base.class_attribute() + derived.class_attribute()

##def oo_class_meth(x, y):
##    return MyClass.class_meth(x, y) + MyDerivedClass.class_meth(x, y)

if __name__ == '__main__':
    from pypy.translator.cli import conftest
    conftest.option.wd = True    
    check(oo_liskov, [int, int], (42, 13))
