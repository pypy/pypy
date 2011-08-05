from pypy.rlib import rstacklet, rrandom
from pypy.rlib.rarithmetic import intmask
from pypy.translator.c.test.test_standalone import StandaloneTests


STATUSMAX = 5000


class Runner:

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
        h = rstacklet.new(self.thrd, empty_callback, 123)
        print 'end', h
        assert h == -1

    def nextstatus(self, nextvalue):
        print 'expected nextvalue to be %d, got %d' % (nextvalue,
                                                       self.status + 1)
        assert self.status + 1 == nextvalue
        self.status = nextvalue

    @here_is_a_test
    def test_simple_switch(self):
        self.status = 0
        h = rstacklet.new(self.thrd, switchbackonce_callback, 321)
        assert h != rstacklet.EMPTY_STACK_HANDLE
        self.nextstatus(2)
        h = rstacklet.switch(runner.thrd, h)
        self.nextstatus(4)
        print 'end', h
        assert h == rstacklet.EMPTY_STACK_HANDLE

    @here_is_a_test
    def test_various_depths(self):
        self.tasks = [Task(i) for i in range(10)]
        self.nextstep = -1
        self.comefrom = -1
        self.status = 0
        while self.status < STATUSMAX or self.any_alive():
            self.tasks[0].withdepth(self.random.genrand32() % 50)

    def any_alive(self):
        for task in self.tasks:
            if task.h != 0:
                return True
        return False


class Task:
    def __init__(self, n):
        self.n = n
        self.h = 0

    def withdepth(self, d):
        if d > 0:
            res = self.withdepth(d-1)
        else:
            res = 0
            n = intmask(runner.random.genrand32() % 10)
            if n == self.n or (runner.status >= STATUSMAX and
                               runner.tasks[n].h == 0):
                return 1

            print "status == %d, self.n = %d" % (runner.status, self.n)
            assert self.h == 0
            assert runner.nextstep == -1
            runner.status += 1
            runner.nextstep = runner.status
            runner.comefrom = self.n
            runner.gointo = n
            task = runner.tasks[n]
            if task.h == 0:
                # start a new stacklet
                print "NEW", n
                h = rstacklet.new(runner.thrd, variousstackdepths_callback, n)
            else:
                # switch to this stacklet
                print "switch to", n
                h = task.h
                task.h = 0
                h = rstacklet.switch(runner.thrd, h)

            print "back in self.n = %d, coming from %d" % (self.n,
                                                           runner.comefrom)
            assert runner.nextstep == runner.status
            runner.nextstep = -1
            assert runner.gointo == self.n
            assert runner.comefrom != self.n
            assert self.h == 0
            if runner.comefrom != -42:
                assert 0 <= runner.comefrom < 10
                task = runner.tasks[runner.comefrom]
                assert task.h == 0
                task.h = h
            else:
                assert h == rstacklet.EMPTY_STACK_HANDLE
            runner.comefrom = -1
            runner.gointo = -1
        assert (res & (res-1)) == 0   # to prevent a tail-call to withdepth()
        return res


runner = Runner()


def empty_callback(h, arg):
    print 'in empty_callback:', h, arg
    assert arg == 123
    return h

def switchbackonce_callback(h, arg):
    print 'in switchbackonce_callback:', h, arg
    assert arg == 321
    runner.nextstatus(1)
    assert h != rstacklet.EMPTY_STACK_HANDLE
    h = rstacklet.switch(runner.thrd, h)
    runner.nextstatus(3)
    assert h != rstacklet.EMPTY_STACK_HANDLE
    return h

def variousstackdepths_callback(h, arg):
    assert runner.nextstep == runner.status
    runner.nextstep = -1
    assert arg == runner.gointo
    self = runner.tasks[arg]
    assert self.n == runner.gointo
    assert self.h == 0
    assert 0 <= runner.comefrom < 10
    task = runner.tasks[runner.comefrom]
    assert task.h == 0
    assert h != 0 and h != rstacklet.EMPTY_STACK_HANDLE
    task.h = h
    runner.comefrom = -1
    runner.gointo = -1

    while self.withdepth(runner.random.genrand32() % 20) == 0:
        pass

    assert self.h == 0
    while 1:
        n = intmask(runner.random.genrand32() % 10)
        h = runner.tasks[n].h
        if h != 0:
            break

    assert h != rstacklet.EMPTY_STACK_HANDLE
    runner.tasks[n].h = 0
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
            config.translation.gcrootfinder = cls.gcrootfinder
        #try:
        #    config.translation.tealet = True
        #except ConflictConfigError, e:
        #    py.test.skip(str(e))
        cls.config = config

    def test_demo1(self):
        t, cbuilder = self.compile(entry_point)

        expected_data = "----- all done -----\n"
        for i in range(20):
            data = cbuilder.cmdexec('%d' % i, env={})
            assert data.endswith(expected_data)
            #data = cbuilder.cmdexec('%d' % i, env={'PYPY_GC_NURSERY': '10k'})
            #assert data.endswith(expected_data)


class TestStackletBoehm(BaseTestStacklet):
    gc = 'boehm'
    gcrootfinder = None


def target(*args):
    return entry_point, None

if __name__ == '__main__':
    import sys
    sys.exit(entry_point(sys.argv))
