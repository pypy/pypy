from pypy.translator.cli.test.runtest import check

class MyClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def compute(self):
        return self.x + self.y

    def compute_and_multiply(self, factor):
        return self.compute() * factor

def oo_compute(x, y):
    obj = MyClass(x, y)
    return obj.compute()

def oo_compute_multiply(x, y):
    obj = MyClass(x, y)
    return obj.compute_and_multiply(2)

def test_oo():
    yield check, oo_compute, [int, int], (42, 13)
    yield check, oo_compute_multiply, [int, int], (42, 13)
