
class Base(object):
    pass

class A(Base):
    a = 1
    b = 2
    c = 3

class B(Base):
    a = 1
    b = 2

class C(Base):
    b = 8
    c = 6

def f(n):
    if n > 3:
        x = A
    elif n > 1:
        x = B
    else:
        x = C
    if n > 0:
        return x.a
    return 8

# __________  Entry point  __________

def entry_point(argv):
    f(int(argv[0]))
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
