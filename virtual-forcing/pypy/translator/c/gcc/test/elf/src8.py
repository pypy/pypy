# ../../../../goal/translate.py --gcrootfinder=asmgcc --gc=semispace src8

class A:
    pass

def foo(rec, a1, a2, a3, a4, a5, a6):
    if rec > 0:
        b = A()
        foo(rec-1, b, b, b, b, b, b)
        foo(rec-1, b, b, b, b, b, b)
        foo(rec-1, a6, a5, a4, a3, a2, a1)

# __________  Entry point  __________

def entry_point(argv):
    foo(5, A(), A(), A(), A(), A(), A())
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
