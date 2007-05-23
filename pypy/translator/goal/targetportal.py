from pypy.rlib.jit import hint, we_are_jitted

def jitted():
    print "jitted"

def compute(x, y):
    if we_are_jitted():
        jitted()
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
    from pypy.jit.hintannotator.annotator import HintAnnotatorPolicy
    class MyHintAnnotatorPolicy(HintAnnotatorPolicy):
        
        def __init__(self):
            HintAnnotatorPolicy.__init__(self, oopspec=True,
                                         novirtualcontainer=True)
            
        def look_inside_graph(self, graph):
            if graph.func is jitted:
                return False
            return True
        
    return compute, MyHintAnnotatorPolicy()
