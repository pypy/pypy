import buildcache2
from pypy.objspace.std.objspace import StdObjSpace
from pypy.translator.test import rpystone

# __________  Entry point  __________

LOOPS = 150000

def entry_point():
    rpystone.entrypoint(LOOPS)
    
# _____ Define and setup target _____
def target():
    global space, mmentrypoints
    # disable translation of the whole of classobjinterp.py
    #StdObjSpace.setup_old_style_classes = lambda self: None
    space = StdObjSpace()
    # call cache filling code
    #buildcache2.buildcache(space)

    # ------------------------------------------------------------

    return entry_point, []

# _____ Run translated _____

def run(c_entry_point):
    res_w = c_entry_point()
    print res_w

if __name__ == "__main__":
    # just run it without translation
    target()
    run(entry_point)
    