LOOPS = 1 << 18

class Foo:
    pass

def test_simple_loop():
    i = 0
    while i < LOOPS:
        i += 1

def test_simple_loop_with_class_creation():
    i = 0
    while i < LOOPS:
        Foo()
        i += 1
