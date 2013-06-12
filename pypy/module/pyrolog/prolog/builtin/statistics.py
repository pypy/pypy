import prolog
import py
import time
from prolog.interpreter import helper, term, error
from prolog.builtin.register import expose_builtin

class Clocks(object):
    def __init__(self):
        pass

    def startup(self):
        self.startup_wall = time.time()
        self.last_wall = 0
        self.startup_cpu = time.clock()
        self.last_cpu = 0

    def get_walltime(self):
        t = time.time() - self.startup_wall
        t = int(t * 1000)
        res = [t, t - self.last_wall]
        self.last_wall = t
        return res

    def get_cputime(self):
        t = time.clock() - self.startup_cpu
        t = int(t * 1000)
        res = [t, t - self.last_cpu]
        self.last_cpu = t
        return res

# TODO: make this continuation based and return all statistics
# RPYTHON??
@expose_builtin("statistics", unwrap_spec=["atom", "obj"])
def impl_statistics(engine, heap, stat_name, value):
    t = []
    if stat_name == 'runtime':
        t = engine.clocks.get_cputime()
    if stat_name == 'walltime':
        t = engine.clocks.get_walltime()
    l = [term.Number(x) for x in t]
    helper.wrap_list(l).unify(value, heap)
