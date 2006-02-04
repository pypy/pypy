N = int(2**19 - 1)

def test_loop():
    x = 0
    n = N
    while x < n:
        x = x + 1

#
def test_count_in_slot():
    class X(object):
        __slots__ = 'x'
    x = X()
    c = 0
    x.x = 0
    n = N
    while c < n:
        x.x = x.x + 1
        c += 1
    
#
def plus1(x):
    return x + 1

def test_call_function():
    x = 0
    n = N
    while x < n:
        x = plus1(x) 

#
def test_call_nested_function():
    def plus2(x):
        return x + 1

    x = 0
    n = N
    while x < n:
        x = plus2(x) 

def test_call_nested_function_other_count():
    def plus2(x):
        return x + 1.0

    x = 0.0
    c = 0
    n = N
    while c < n:
        x = plus2(x) 
        c += 1
        
def test_call_nested_function_many_args():
    def plus2(x, y1, y2, y3, y4):
        return x + 1

    x = 0
    n = N
    while x < n:
        x = plus2(x, 2, 3, 4, 5) 

#
class MyOldStyleClass:
    def my_method(self, x):
        return x + 1

class MyNewStyleClass(object):
    def my_method(self, x):
        return x + 1

def test_call_method_of_old_style_class():
    c = MyOldStyleClass()
    x = 0
    n = N
    while x < n:
        x = c.my_method(x) 

def test_call_method_of_new_style_class():
    c = MyNewStyleClass()
    x = 0
    n = N
    while x < n:
        x = c.my_method(x) 

#
