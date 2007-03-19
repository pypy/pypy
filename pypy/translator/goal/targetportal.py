from pypy.rlib.objectmodel import hint

def compute(x, y):
    hint(x, concrete=True)
    r = x + y
    return r

# __________  Entry point  __________

def entry_point(argv):
    if len(argv) <3:
        return -2
    r = compute(int(argv[1]), int(argv[2]))
    print r
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

def portal(drv):
    return compute, None
