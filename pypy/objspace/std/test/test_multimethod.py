import unittest
import testsupport

from pypy.objspace.std.multimethod import *

W_ANY = object


class X:
    delegate_once = {}
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return '<X %r>' % self.value

def from_y_to_x(space, yinstance):
    return X(yinstance)

class Y:
    delegate_once = {X: from_y_to_x}
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return '<Y %r>' % self.value


def add_x_x(space, x1, x2):
    return "add_x_x", x1, x2

def add_x_y(space, x1, y2):
    if x1.value < 0:
        raise FailedToImplement(ValueError, 'not good')
    return "add_x_y", x1, y2

def add_y_y(space, y1, y2):
    return "add_y_y", y1, y2

def add_string_string(space, x, y):
    return "add_string_string", x, y

def add_int_string(space, x, y):
    return "add_int_string", x, y

def add_int_any(space, y1, o2):
    return "add_int_any", y1, o2

class FakeObjSpace:
    add = MultiMethod('+', 2, [])
    add.register(add_x_x,           X,   X)
    add.register(add_x_y,           X,   Y)
    add.register(add_y_y,           Y,   Y)
    add.register(add_string_string, str, str)
    add.register(add_int_string,    int, str)
    add.register(add_int_any,       int, W_ANY)
    
    def wrap(self, x):
        return '<wrapped %r>' % (x,)
    w_TypeError = 'w_TypeError'


class TestMultiMethod(unittest.TestCase):

    def test_base(self):
        space = FakeObjSpace()
        
        r = space.add(X(2), X(5))
        self.assertEquals(repr(r), "('add_x_x', <X 2>, <X 5>)")
        
        r = space.add(X(3), Y(4))
        self.assertEquals(repr(r), "('add_x_y', <X 3>, <Y 4>)")
        
        r = space.add(Y(-1), X(7))
        self.assertEquals(repr(r), "('add_x_x', <X <Y -1>>, <X 7>)")
        
        r = space.add(Y(1), X(7))
        self.assertEquals(repr(r), "('add_x_x', <X <Y 1>>, <X 7>)")
        
        r = space.add(Y(0), Y(20))
        self.assertEquals(repr(r), "('add_y_y', <Y 0>, <Y 20>)")
        
        r = space.add(X(-3), Y(20))
        self.assertEquals(repr(r), "('add_x_x', <X -3>, <X <Y 20>>)")
        
        r = space.add(-3, [7,6,5])
        self.assertEquals(repr(r), "('add_int_any', -3, [7, 6, 5])")

        r = space.add(5,"test")
        self.assertEquals(repr(r), "('add_int_string', 5, 'test')")
        
        r = space.add("x","y")
        self.assertEquals(repr(r), "('add_string_string', 'x', 'y')")
        
        self.assertRaises(OperationError, space.add, [3],4)
        
        self.assertRaises(OperationError, space.add, 3.0,'bla')


if __name__ == '__main__':
    unittest.main()
