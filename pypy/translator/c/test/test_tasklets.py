import os

from pypy.rpython.memory.lladdress import NULL
from pypy.rpython.rstack import yield_current_frame_to_caller

# ____________________________________________________________
# For testing

from pypy.translator.c.gc import BoehmGcPolicy
gcpolicy = BoehmGcPolicy 
debug_flag = True

# count of loops in tests (set lower to speed up)
loops = 10
    
def debug(s):
    if debug_flag:
        os.write(2, "%s\n" % s)

class Globals:
    def __init__(self):
        pass

globals = Globals()
globals.count = 0

def wrap_stackless_function(fn):
    from pypy.translator.translator import TranslationContext
    from pypy.translator.c.genc import CStandaloneBuilder
    from pypy.annotation.model import SomeList, SomeString
    from pypy.annotation.listdef import ListDef
    from pypy.translator.backendopt.all import backend_optimizations

    def entry_point(argv):
        os.write(1, str(fn()))
        return 0

    s_list_of_strings = SomeList(ListDef(None, SomeString()))
    s_list_of_strings.listdef.resize()
    t = TranslationContext()
    t.buildannotator().build_types(entry_point, [s_list_of_strings])
    t.buildrtyper().specialize()
    backend_optimizations(t)
    cbuilder = CStandaloneBuilder(t, entry_point, gcpolicy=gcpolicy)
    cbuilder.stackless = True
    cbuilder.generate_source()
    cbuilder.compile()
    return cbuilder.cmdexec('')

# ____________________________________________________________

class Resumable(object):
    def __init__(self, fn):
        self.fn = fn
        self.alive = False
        
    def start(self):
        self.caller = yield_current_frame_to_caller()
        self.fn(self.name)
        return self.caller

    def set_resumable(self, resumable):
        self.resumable = resumable

    def suspend(self):
        self.caller = self.caller.switch()  
        
    def resume(self):
        self.resumable = self.resumable.switch()  
        self.alive = self.resumable is not None
    
class Tasklet(Resumable):
    def __init__(self, name, fn):
        Resumable.__init__(self, fn)
        self.name = name
        self.blocked = 0
        self.data = -1
        
        # propogates round suspend-resume to tell scheduler in run()
        # XXX too late to think this thru
        self.remove = False

    def suspend_and_remove(self, remove):
        self.remove = remove
        self.suspend()

    def resume(self):
        assert not self.remove
        Resumable.resume(self)
        
        # not sure what to do with alive yetXXX        

        #XXX arggh - why NOT??
        #if not alive:
        #    self.caller = # None / NULL
        return self.alive and not self.remove         

class Channel:
    def __init__(self):
        self.queue = []
        self.balance = 0

    def send(self, value):
        self.balance += 1
        if self.balance <= 0:
            t = self.queue.pop(0)
            t.data = value
            ##!!t.blocked = 0
            scheduler.run_immediately(tasklet)
            scheduler.schedule()
            
        else:
            t = getcurrent()
            assert isinstance(t, Tasklet)
            # let it wait for a receiver to come along
            self.queue.append(t)
            ##!!t.blocked = 1
            schedule_remove()
    
    def receive(self):
        self.balance -= 1
        # good to go
        if self.balance >= 0:
            t = self.queue.pop(0)
            ##!!t.blocked = 0
            scheduler.add_tasklet(t)

        else:
            # block until ready
            t = getcurrent()
            self.queue.append(t)
            ##!!t.blocked = -1
            schedule_remove()
    
class Scheduler(object):
    def __init__(self):
        self.runnables = []
        self.current_tasklet = None
        self.immediately_schedule = None

    def add_tasklet(self, tasklet):
        self.runnables.append(tasklet)

    def run_immediately(self, tasklet):
        self.immediately_schedule = tasklet

    def run(self):            
        while self.runnables:
            runnables = self.runnables
            self.runnables = []
            count = 0
            for t in runnables:
                assert self.current_tasklet is None
                self.current_tasklet = t
                if t.resume():
                    self.runnables.append(self.current_tasklet)
                self.current_tasklet = None
                count += 1

                if self.immediately_schedule:
                    self.runnables = [self.immediately_schedule] \
                                     + runnables[count:] + self.runnables
                    self.immediately_schedule = None
                    break
                
    def schedule(self, remove=False):
        assert self.current_tasklet is not None
        self.current_tasklet.suspend_and_remove(remove)
        
# ____________________________________________________________

scheduler = Scheduler()
def start_tasklet(tasklet):
    res = tasklet.start()
    tasklet.set_resumable(res)
    scheduler.add_tasklet(tasklet)

def start_tasklet_now(tasklet):
    res = tasklet.start()
    tasklet.set_resumable(res)
    scheduler.run_immediately(tasklet)
        
def schedule():
    scheduler.schedule()

def schedule_remove():
    scheduler.schedule(remove=True)

def run():
    scheduler.run()

def getcurrent():
    return scheduler.current_tasklet

# ____________________________________________________________

def test_simple():
    
    def simple(name):
        for ii in range(5):
            globals.count += 1
            schedule()

    def f():
        for ii in range(loops):
            start_tasklet(Tasklet("T%s" % ii, simple))
        run()
        return globals.count == loops * 5

    res = wrap_stackless_function(f)
    assert res == '1'

def test_multiple_simple():
    
    def simple(name):
        for ii in range(5):
            globals.count += 1
            schedule()

    def simple2(name):
        for ii in range(5):
            globals.count += 1
            schedule()
            globals.count += 1

    def simple3(name):
        schedule()
        for ii in range(10):
            globals.count += 1
            if ii % 2:
                schedule()
        schedule()

    def f():
        for ii in range(loops):
            start_tasklet(Tasklet("T1%s" % ii, simple))
            start_tasklet(Tasklet("T2%s" % ii, simple2))
            start_tasklet(Tasklet("T3%s" % ii, simple3))
        run()
        return globals.count == loops * 25
    
    res = wrap_stackless_function(f)
    assert res == '1'

def test_schedule_remove():
    
    def simple(name):
        for ii in range(20):
            if ii < 10:
                schedule()
            else:
                schedule_remove()
            globals.count += 1

    def f():
        for ii in range(loops):
            start_tasklet(Tasklet("T%s" % ii, simple))
        run()
        for ii in range(loops):
            start_tasklet(Tasklet("T%s" % ii, simple))
        run()
        return globals.count == loops * 10 * 2

    res = wrap_stackless_function(f)
    assert res == '1'

def test_run_immediately():
    globals.intermediate = 0
    globals.count = 0
    def simple(name):
        for ii in range(20):
            globals.count += 1
            schedule()

    def run_immediately(name):
        globals.intermediate = globals.count
        schedule()
    
    def simple2(name):
        for ii in range(20):
            globals.count += 1
            if ii == 10:
                start_tasklet_now(Tasklet("intermediate", run_immediately))
            schedule()

    def f():
        start_tasklet(Tasklet("simple2", simple2))
        for ii in range(loops):
            start_tasklet(Tasklet("T%s" % ii, simple))        
        run()
        total_expected = (loops + 1) * 20
        return (globals.intermediate == total_expected / 2 + 1 and
                globals.count == total_expected)

    res = wrap_stackless_function(f)
    assert res == '1'

def test_channels():
    ch = Channel()
        
    def f1(name):
        for ii in range(5):
            ch.send(ii)
        debug("done sending")
            
    def f2(name):
        while True:
            ch.receive()
            debug("received")

    def f():
        start_tasklet(Tasklet("f2", f2))
        start_tasklet(Tasklet("f1", f1))
        run()

        return 0
    
    res = wrap_stackless_function(f)
    assert res == '1'
