LOOPS = 1 << 18

class OldStyleFoo:
    pass

class NewStyleFoo(object):
    pass

def test_simple_loop():
    i = 0
    while i < LOOPS:
        i += 1

def test_simple_loop_with_old_style_class_creation():
    i = 0
    while i < LOOPS:
        OldStyleFoo()
        i += 1

def test_simple_loop_with_new_style_class_creation():
    i = 0
    while i < LOOPS:
        NewStyleFoo()
        i += 1

def test_simple_loop_with_new_style_class_new():
    i = 0
    new = object.__new__
    while i < LOOPS:
        new(NewStyleFoo)
        i += 1
