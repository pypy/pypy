import py
import os

from pypy.rpython.lltypesystem.llmemory import NULL
from pypy.rlib.rstack import yield_current_frame_to_caller

# ____________________________________________________________
# For testing

from pypy.translator.tool import cbuild
from pypy.translator.c import gc
from pypy.translator.c.test import test_stackless

# count of loops in tests (set lower to speed up)
loops = 1
    
def debug(s):
    os.write(2, "%s\n" % s)

class Globals:
    def __init__(self):
        pass

globals = Globals()
globals.count = 0

# ____________________________________________________________

class ThreadLocals(object):
    pass
threadlocals = ThreadLocals()

class Resumable(object):
    def __init__(self):
        self.alive = False
        
    def start(self):
        self.resumable = self._start()

    def _start(self):
        threadlocals.cc = yield_current_frame_to_caller()
        self.fn()
        return threadlocals.cc

    def suspend(self):
        # we suspend ourself
        threadlocals.cc = threadlocals.cc.switch()
        
    def resume(self):
        # the caller resumes me
        self.resumable = self.resumable.switch()  
        self.alive = self.resumable is not None

    def fn(self):
        pass

class Tasklet(Resumable):

    def __init__(self):
        Resumable.__init__(self)
        self.blocked = 0
        
        # propogates round suspend-resume to tell scheduler in run()
        # XXX this should probably be done by setting a value in the
        #     scheduler??
        self.remove = False

    def start(self):
        Resumable.start(self)
        scheduler.add_tasklet(self)

    def run(self):
        Resumable.start(self)
        scheduler.run_immediately(self)

    def suspend_and_remove(self, remove):
        self.remove = remove
        self.suspend()

    def resume(self):
        assert not self.remove
        Resumable.resume(self)
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
            t.blocked = 0
            t.remove = False
            scheduler.run_immediately(t)
            scheduler.schedule()

            # resuming
            t = getcurrent()
            assert t.blocked == 0
            
        else:
            t = getcurrent()
            assert isinstance(t, Tasklet)
            t.data = value
            # let it wait for a receiver to come along
            self.queue.append(t)
            t.blocked = 1
            schedule_remove()

            # resuming
            assert t == getcurrent()
            assert t.blocked == 0
    
    def receive(self):
        self.balance -= 1
        # good to go
        if self.balance >= 0:
            t = self.queue.pop(0)
            t.blocked = 0
            t.remove = False
            data = t.data
            scheduler.add_tasklet(t)
            return data
        else:
            # queue ourself
            t = getcurrent()
            assert isinstance(t, Tasklet)
            self.queue.append(t)

            # block until send has reenabled me
            t.blocked = -1
            schedule_remove()

            # resuming
            assert t == getcurrent()
            assert t.blocked == 0

            return t.data
    
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
        
def schedule():
    scheduler.schedule()

def schedule_remove():
    scheduler.schedule(remove=True)

def run():
    scheduler.run()

def getcurrent():
    return scheduler.current_tasklet

# ____________________________________________________________

class TestTasklets(test_stackless.StacklessTest):
    backendopt = True

    def test_simplex(self):

        class Tasklet1(Tasklet):
            def fn(self):
                for ii in range(5):
                    globals.count += 1
                    schedule()

        def f():
            for ii in range(loops):
                Tasklet1().start()
            run()
            return globals.count == loops * 5

        res = self.wrap_stackless_function(f)
        print res
        assert res == 1

    def test_multiple_simple(self):

        class Tasklet1(Tasklet):
            def fn(self):
                for ii in range(5):
                    globals.count += 1
                    schedule()

        class Tasklet2(Tasklet):
            def fn(self):
                for ii in range(5):
                    globals.count += 1
                    schedule()
                    globals.count += 1

        class Tasklet3(Tasklet):
            def fn(self):
                schedule()
                for ii in range(10):
                    globals.count += 1
                    if ii % 2:
                        schedule()
                schedule()

        def f():
            for ii in range(loops):
                Tasklet1().start()
                Tasklet2().start()
                Tasklet3().start()
            run()
            return globals.count == loops * 25

        res = self.wrap_stackless_function(f)
        assert res == 1

    def test_schedule_remove(self):

        class Tasklet1(Tasklet):
            def fn(self):
                for ii in range(20):
                    if ii < 10:
                        schedule()
                    else:
                        schedule_remove()
                    globals.count += 1

        def f():
            for ii in range(loops):
                Tasklet1().start()
            run()
            for ii in range(loops):
                Tasklet1().start()
            run()
            return globals.count == loops * 10 * 2

        res = self.wrap_stackless_function(f)
        assert res == 1

    def test_run_immediately(self):
        globals.intermediate = 0
        class Tasklet1(Tasklet):
            def fn(self):
                for ii in range(20):
                    globals.count += 1
                    schedule()

        class RunImmediate(Tasklet):
            def fn(self):
                globals.intermediate = globals.count
                schedule()

        class Tasklet2(Tasklet):
            def fn(self):
                for ii in range(20):
                    globals.count += 1
                    if ii == 10:
                        RunImmediate().run()
                    schedule()

        def f():
            Tasklet2().start()
            for ii in range(loops):
                Tasklet1().start()
            run()
            total_expected = (loops + 1) * 20
            return (globals.intermediate == total_expected / 2 + 1 and
                    globals.count == total_expected)

        res = self.wrap_stackless_function(f)
        assert res == 1

    def test_channel1(self):
        ch = Channel()

        class Tasklet1(Tasklet):
            def fn(self):
                for ii in range(5):
                    ch.send(ii)

        class Tasklet2(Tasklet):
            def fn(self):
                #while True: XXX Doesnt annotate
                for ii in range(6):
                    globals.count += ch.receive()

        def f():
            Tasklet2().start()
            Tasklet1().start()
            run()
            return (globals.count == 10)

        res = self.wrap_stackless_function(f)
        assert res == 1

    def test_channel2(self):

        class Tasklet1(Tasklet):
            def __init__(self, ch):
                self.ch = ch
            def fn(self):
                for ii in range(5):
                    self.ch.send(ii)

        class Tasklet2(Tasklet):
            def __init__(self, ch):
                self.ch = ch            
            def fn(self):
                #while True:XXX Doesnt annotate
                for ii in range(6):
                    res = self.ch.receive()
                    globals.count += res

        def f():
            ch = Channel()
            Tasklet1(ch).start()
            Tasklet2(ch).start()
            run()
            return globals.count == 10

        res = self.wrap_stackless_function(f)
        assert res == 1

    def test_channel3(self):

        class Tasklet1(Tasklet):
            def __init__(self, ch):
                self.ch = ch
            def fn(self):
                for ii in range(5):
                    self.ch.send(ii)

        class Tasklet2(Tasklet):
            def __init__(self, ch):
                self.ch = ch
            def fn(self):
                #while True: XXX Doesnt annotate
                for ii in range(16):
                    res = self.ch.receive()
                    globals.count += res

        def f():
            ch = Channel()
            Tasklet1(ch).start()
            Tasklet1(ch).start()
            Tasklet1(ch).start()
            Tasklet2(ch).start()
            run()
            return globals.count == 30

        res = self.wrap_stackless_function(f)
        assert res == 1

    def test_flexible_channels(self):
        """ test with something other than int """

        class A(object):
            def __init__(self, num):
                self.num = num
            def getvalue(self):
                res = self.num
                self.num *= 2
                return res

        class Data(object):
            pass

        class IntData(Data):
            def __init__(self, i):
                self.int = i

        class StringData(Data):
            def __init__(self, s):
                self.str = s

        class InstanceData(Data):
            def __init__(self, i):
                self.instance = i


        class Tasklet1(Tasklet):
            def __init__(self, ch):
                self.ch = ch
            def fn(self):
                for ii in range(5):
                    self.ch.send(IntData(ii))

        class Tasklet2(Tasklet):
            def __init__(self, ch, strdata):
                self.ch = ch
                self.strdata = strdata
            def fn(self):
                for ii in range(5):
                    self.ch.send(StringData(self.strdata))

        class Tasklet3(Tasklet):
            def __init__(self, ch, instance):
                self.ch = ch
                self.instance = instance
            def fn(self):
                for ii in range(5):
                    self.ch.send(InstanceData(self.instance))

        class Server(Tasklet):
            def __init__(self, ch):
                self.ch = ch
                self.loop = True

            def stop(self):
                self.loop = False

            def fn(self):
                while self.loop:
                    data = self.ch.receive()
                    if isinstance(data, IntData):
                        globals.count += data.int
                    elif isinstance(data, StringData):
                        globals.count += len(data.str)
                    elif isinstance(data, InstanceData):
                        globals.count += data.instance.getvalue()

        ch = Channel()
        server = Server(ch)

        def f():
            Tasklet1(ch).start()
            Tasklet2(ch, "abcd").start()
            Tasklet2(ch, "xxx").start()
            Tasklet3(ch, A(1)).start()
            server.start()
            run()
            return globals.count == (0+1+2+3+4) + (5*4) + (5*3) + (1+2+4+8+16)

        res = self.wrap_stackless_function(f)
        assert res == 1

    def test_original_api(self):

        class TaskletAsFunction(Tasklet):
            def __init__(self, fn):
                self.redirect_fn = fn
            def fn(self):
                self.redirect_fn()

        def tasklet(fn):
            return TaskletAsFunction(fn)

        def simple():
            for ii in range(5):
                globals.count += 1
                schedule()

        def f():
            for ii in range(loops):
                tasklet(simple).start()
            run()
            run()
            return globals.count == loops * 5

        res = self.wrap_stackless_function(f)
        assert res == 1
