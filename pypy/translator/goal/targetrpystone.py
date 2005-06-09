import buildcache2
from pypy.objspace.std.objspace import StdObjSpace
from pypy.translator.test import rpystone

# __________  Entry point  __________

LOOPS = 150000

# rpystone.setslow(False)

def entry_point():
    rpystone.entrypoint(LOOPS)
    
# _____ Define and setup target _____
def target():
    global space, mmentrypoints
    space = StdObjSpace()

    # ------------------------------------------------------------

    return entry_point, []

# _____ Run translated _____

def run(c_entry_point):
    res_w = c_entry_point()
    print res_w
    print "CPython:"
    rpystone.entrypoint(50000)

if __name__ == "__main__":
    # just run it without translation
    LOOPS = 50000
    target()
    run(entry_point)
    