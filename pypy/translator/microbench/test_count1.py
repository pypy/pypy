N = int(2**19 - 1)

def test_loop():
    x = 0
    n = N
    while x < n:
        x = x + 1

#
def test_loop_other_count():
    x = 0.0
    n = N
    c = 0
    while c < n:
        x = x + 1.0
        c += 1

#
def test_loop_unrolled():
    '''32x the following bytecodes
    28 LOAD_FAST                0 (x)
    31 LOAD_CONST               2 (1)
    34 BINARY_ADD
    35 STORE_FAST               0 (x)'''
    x = 0
    n = N
    while x < n:
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
        x = x + 1
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

def test_count_in_dict():
    d = {'a': 0, 'b': 0}
    c = 0
    d['x'] = 0
    n = N
    while c < n:
        d['x'] = d['x'] + 1
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


def func_with_arg_in_cellvars(x, y, z):
    return 
    def nested():
        return x, y, z

def func_without_arg_in_cellvars(x, y, z):
    return 
    i = None
    def nested():
        return i
    
def test_call_function_with_arguments_in_cellvars():
    n = N
    c = 0
    while c < n:
        func_with_arg_in_cellvars(c, n, test_call_function_with_arguments_in_cellvars)
        c = c + 1

def test_call_function_without_arguments_in_cellvars():
    n = N
    c = 0
    while c < n:
        func_without_arg_in_cellvars(c, n, test_call_function_without_arguments_in_cellvars)
        c = c + 1

#

def test_count_in_attr():
    class X(object):
        pass
    x = X()
    c = 0
    x.x = 0
    n = N
    while c < n:
        x.x = x.x + 1
        c += 1

x = 0
def test_count_in_global():
    global x
    c = 0
    x = 0
    n = N
    while c < n:
        x = x + 1
        c += 1

def test_count_increment_in_global():
    global inc
    c = 0
    x = 0
    inc = 1
    n = N
    while c < n:
        x = x + inc
        c += inc

def test_count_in_global2():
    global y
    c = 0
    y = 0
    n = N
    while c < n:
        y = y + 1
        c += 1
    
def test_count_with_True():
    x = 0
    n = N
    while x < n:
        x = x + True

increment = 1
def test_count_with_global_increment():
    x = 0
    n = N
    while x < n:
        x = x + increment
