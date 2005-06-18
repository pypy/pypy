from pypy.objspace.std.objspace import StdObjSpace
from pypy.translator.test import rpystone

# __________  Entry point  __________

LOOPS = 150000

# rpystone.setslow(False)

def entry_point():
    return rpystone.pystones(LOOPS)
    
# _____ Define and setup target _____
def target():
    return entry_point, []

# _____ Run translated _____

def run(c_entry_point):
    res = c_entry_point()
    benchtime, stones = res
    print "translated rpystone.pystones time for %d passes = %g" % \
        (LOOPS, benchtime)
    print "This machine benchmarks at %g translated rpystone pystones/second" % stones
    print "CPython:"
    benchtime, stones = rpystone.pystones(50000)
    print "rpystone.pystones time for %d passes = %g" % \
        (50000, benchtime)
    print "This machine benchmarks at %g rpystone pystones/second" % stones


#if __name__ == "__main__":
#    # just run it without translation
#    LOOPS = 50000
#    target()
#    run(entry_point)
    
