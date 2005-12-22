N = int(2**19 - 1)

def test_loop():
    x = 0
    n = N
    while x < n:
        x = x + 1

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
