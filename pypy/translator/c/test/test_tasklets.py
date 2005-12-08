from pypy.translator.translator import TranslationContext
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.annotation.model import SomeList, SomeString
from pypy.annotation.listdef import ListDef
from pypy.rpython.rstack import stack_unwind, stack_frames_depth, stack_too_big
from pypy.rpython.rstack import yield_current_frame_to_caller
import os

def wrap_stackless_function(fn):
    def entry_point(argv):
        os.write(1, str(fn()))
        return 0

    s_list_of_strings = SomeList(ListDef(None, SomeString()))
    s_list_of_strings.listdef.resize()
    t = TranslationContext()
    t.buildannotator().build_types(entry_point, [s_list_of_strings])
    t.buildrtyper().specialize()
    cbuilder = CStandaloneBuilder(t, entry_point)
    cbuilder.stackless = True
    cbuilder.generate_source()
    cbuilder.compile()
    return cbuilder.cmdexec('')

# ____________________________________________________________

def debug(s):
    #os.write(1, "%s\n" % s)
    pass

class Tasklet(object):

    def __init__(self, name, fn):
        self.fn = fn
        self.name = name
        self.alive = False

    def start(self):
        debug("starting %s" % self.name)
        self.caller = yield_current_frame_to_caller()

        debug("entering %s" % self.name)
        self.fn(self.name)
        debug("leaving %s" % self.name)
        return self.caller

    def setalive(self, resumable):
        self.alive = True
        self.resumable = resumable

    def schedule(self):
        debug("scheduling %s" % self.name)            
        self.caller = self.caller.switch()  

    def resume(self):
        debug("resuming %s" % self.name)            
        self.resumable = self.resumable.switch()  
        self.alive = self.resumable is not None


class Scheduler(object):
    def __init__(self):
        self.runnables = []
        self.current_tasklet = None

    def add_tasklet(self, tasklet):
        self.runnables.append(tasklet)

    def run(self):            
        debug("running: length of runnables %s" % len(self.runnables))
        while self.runnables:
            t = self.runnables.pop(0)
            debug("resuming %s(%s)" % (t.name, t.alive))
            self.current_tasklet = t
            t.resume()
            self.current_tasklet = None
            if t.alive:
                self.runnables.append(t)

        debug("ran")

scheduler = Scheduler()
def start_tasklet(tasklet):
    res = tasklet.start()
    tasklet.setalive(res)
    scheduler.add_tasklet(tasklet)

def run():
    scheduler.run()

def schedule():
    assert scheduler.current_tasklet
    scheduler.current_tasklet.schedule()

def test_simple():
    class Counter:
        def __init__(self):
            self.count = 0

        def increment(self):
            self.count += 1

        def get_count(self):
            return self.count

    c = Counter()
    
    def simple(name):
        for ii in range(5):
            debug("xxx %s %s" % (name, ii))
            c.increment()
            schedule()

    def f():
        for ii in range(5):
            start_tasklet(Tasklet("T%s" % ii, simple))
        run()
        return c.get_count() == 25
    
    res = wrap_stackless_function(f)
    assert res == '1'
