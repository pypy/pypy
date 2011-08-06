from pypy.rlib import rstacklet, rrandom
from pypy.rlib.rarithmetic import intmask
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.c.test.test_standalone import StandaloneTests



class Runner:
    STATUSMAX = 5000
    config = None

    def init(self, seed):
        self.thrd = rstacklet.newthread()
        self.random = rrandom.Random(seed)

    def done(self):
        rstacklet.deletethread(self.thrd)

    TESTS = []
    def here_is_a_test(fn, TESTS=TESTS):
        TESTS.append((fn.__name__, fn))
        return fn

    @here_is_a_test
    def test_new(self):
        print 'start'
        h = rstacklet.new(self.config, self.thrd, empty_callback,
                          rffi.cast(rffi.VOIDP, 123))
        print 'end', h
        assert rstacklet.is_empty_handle(h)

    def nextstatus(self, nextvalue):
        print 'expected nextvalue to be %d, got %d' % (nextvalue,
                                                       self.status + 1)
        assert self.status + 1 == nextvalue
        self.status = nextvalue

    @here_is_a_test
    def test_simple_switch(self):
        self.status = 0
        h = rstacklet.new(self.config, self.thrd, switchbackonce_callback,
                          rffi.cast(rffi.VOIDP, 321))
        assert not rstacklet.is_empty_handle(h)
        self.nextstatus(2)
        h = rstacklet.switch(self.config, runner.thrd, h)
        self.nextstatus(4)
        print 'end', h
        assert rstacklet.is_empty_handle(h)

    @here_is_a_test
    def test_various_depths(self):
        self.tasks = [Task(i) for i in range(10)]
        self.nextstep = -1
        self.comefrom = -1
        self.status = 0
        while self.status < self.STATUSMAX or self.any_alive():
            self.tasks[0].withdepth(self.random.genrand32() % 50)

    def any_alive(self):
        for task in self.tasks:
            if task.h:
                return True
        return False


class Task:
    def __init__(self, n):
        self.n = n
        self.h = lltype.nullptr(rstacklet.handle.TO)

    def withdepth(self, d):
        if d > 0:
            res = self.withdepth(d-1)
        else:
            res = 0
            n = intmask(runner.random.genrand32() % 10)
            if n == self.n or (runner.status >= runner.STATUSMAX and
                               not runner.tasks[n].h):
                return 1

            print "status == %d, self.n = %d" % (runner.status, self.n)
            assert not self.h
            assert runner.nextstep == -1
            runner.status += 1
            runner.nextstep = runner.status
            runner.comefrom = self.n
            runner.gointo = n
            task = runner.tasks[n]
            if not task.h:
                # start a new stacklet
                print "NEW", n
                h = rstacklet.new(runner.config, runner.thrd,
                                  variousstackdepths_callback,
                                  rffi.cast(rffi.VOIDP, n))
            else:
                # switch to this stacklet
                print "switch to", n
                h = task.h
                task.h = lltype.nullptr(rstacklet.handle.TO)
                h = rstacklet.switch(runner.config, runner.thrd, h)

            print "back in self.n = %d, coming from %d" % (self.n,
                                                           runner.comefrom)
            assert runner.nextstep == runner.status
            runner.nextstep = -1
            assert runner.gointo == self.n
            assert runner.comefrom != self.n
            assert not self.h
            if runner.comefrom != -42:
                assert 0 <= runner.comefrom < 10
                task = runner.tasks[runner.comefrom]
                assert not task.h
                task.h = h
            else:
                assert rstacklet.is_empty_handle(h)
            runner.comefrom = -1
            runner.gointo = -1
        assert (res & (res-1)) == 0   # to prevent a tail-call to withdepth()
        return res


runner = Runner()


def empty_callback(h, arg):
    print 'in empty_callback:', h, arg
    assert rffi.cast(lltype.Signed, arg) == 123
    return h

def switchbackonce_callback(h, arg):
    print 'in switchbackonce_callback:', h, arg
    assert rffi.cast(lltype.Signed, arg) == 321
    runner.nextstatus(1)
    assert not rstacklet.is_empty_handle(h)
    h = rstacklet.switch(runner.config, runner.thrd, h)
    runner.nextstatus(3)
    assert not rstacklet.is_empty_handle(h)
    return h

def variousstackdepths_callback(h, arg):
    assert runner.nextstep == runner.status
    runner.nextstep = -1
    arg = rffi.cast(lltype.Signed, arg)
    assert arg == runner.gointo
    self = runner.tasks[arg]
    assert self.n == runner.gointo
    assert not self.h
    assert 0 <= runner.comefrom < 10
    task = runner.tasks[runner.comefrom]
    assert not task.h
    assert bool(h) and not rstacklet.is_empty_handle(h)
    task.h = h
    runner.comefrom = -1
    runner.gointo = -1

    while self.withdepth(runner.random.genrand32() % 20) == 0:
        pass

    assert not self.h
    while 1:
        n = intmask(runner.random.genrand32() % 10)
        h = runner.tasks[n].h
        if h:
            break

    assert not rstacklet.is_empty_handle(h)
    runner.tasks[n].h = lltype.nullptr(rstacklet.handle.TO)
    runner.comefrom = -42
    runner.gointo = n
    assert runner.nextstep == -1
    runner.status += 1
    runner.nextstep = runner.status
    print "LEAVING %d to go to %d" % (self.n, n)
    return h


def entry_point(argv):
    seed = 0
    if len(argv) > 1:
        seed = int(argv[1])
    runner.init(seed)
    for name, meth in runner.TESTS:
        print '-----', name, '-----'
        meth(runner)
    print '----- all done -----'
    runner.done()
    return 0


class BaseTestStacklet(StandaloneTests):

    def setup_class(cls):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.gc = cls.gc
        if cls.gcrootfinder is not None:
            config.translation.stacklet = True
            config.translation.gcrootfinder = cls.gcrootfinder
            GCROOTFINDER = cls.gcrootfinder
        cls.config = config
        cls.old_values = Runner.config, Runner.STATUSMAX
        Runner.config = config
        Runner.STATUSMAX = 25000

    def teardown_class(cls):
        Runner.config, Runner.STATUSMAX = cls.old_values

    def test_demo1(self):
        t, cbuilder = self.compile(entry_point)

        expected_data = "----- all done -----\n"
        for i in range(20, 3):
            print 'running %s/%s with argument %d' % (
                self.gc, self.gcrootfinder, i)
            data = cbuilder.cmdexec('%d' % i, env={})
            assert data.endswith(expected_data)
            #data = cbuilder.cmdexec('%d' % i, env={'PYPY_GC_NURSERY': '10k'})
            #assert data.endswith(expected_data)


class TestStackletBoehm(BaseTestStacklet):
    gc = 'boehm'
    gcrootfinder = None

class TestStackletAsmGcc(BaseTestStacklet):
    gc = 'minimark'
    gcrootfinder = 'asmgcc'


def target(*args):
    return entry_point, None

if __name__ == '__main__':
    import sys
    sys.exit(entry_point(sys.argv))
