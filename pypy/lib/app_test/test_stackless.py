"""
These tests are supposed to run on the following platforms:
1. CStackless
2. CPython (with the stackless_new module in the path
3. pypy-c
"""
from py.test import skip
try:
    import stackless
    if 'coroutine' in dir(stackless):
        raise ImportError("We are running pypy-c")
    withinit = False
except ImportError:
    try:
        from pypy.lib import stackless_new as stackless
    except ImportError, e:
        skip('cannot import stackless: %s' % (e,))
    #from pypy.lib import stackless
    withinit = True

class Test_Stackless:

    def setup_method(self, method):
        # there is still a bug in stackless_new
        # that requires to reinitialize the module
        # for every test
        if withinit:
            stackless._init()

    def test_simple(self):
        rlist = []

        def f():
            rlist.append('f')

        def g():
            rlist.append('g')
            stackless.schedule()

        def main():
            rlist.append('m')
            cg = stackless.tasklet(g)()
            cf = stackless.tasklet(f)()
            stackless.run()
            rlist.append('m')

        main()

        assert stackless.getcurrent() is stackless.getmain()
        assert rlist == 'm g f m'.split()

    def test_with_channel(self):
        rlist = []
        def f(outchan):
            for i in range(10):
                rlist.append('s%s' % i)
                outchan.send(i)
            outchan.send(-1)

        def g(inchan):
            while 1:
                val = inchan.receive()
                if val == -1:
                    break
                rlist.append('r%s' % val)

        ch = stackless.channel()
        t1 = stackless.tasklet(f)(ch)
        t2 = stackless.tasklet(g)(ch)

        stackless.run()

        assert len(rlist) == 20
        for i in range(10):
            (s,r), rlist = rlist[:2], rlist[2:]
            assert s == 's%s' % i
            assert r == 'r%s' % i

    def test_counter(self):
        import random

        numbers = range(20)
        random.shuffle(numbers)

        def counter(n, ch):
            for i in xrange(n):
                stackless.schedule()
            ch.send(n)

        ch = stackless.channel()
        for each in numbers:
            stackless.tasklet(counter)(each, ch)

        stackless.run()

        rlist = []
        while ch.balance:
            rlist.append(ch.receive())

        numbers.sort()
        assert rlist == numbers

    def test_scheduling_cleanup(self):
        rlist = []
        def f():
            rlist.append('fb')
            stackless.schedule()
            rlist.append('fa')

        def g():
            rlist.append('gb')
            stackless.schedule()
            rlist.append('ga')

        def h():
            rlist.append('hb')
            stackless.schedule()
            rlist.append('ha')

        tf = stackless.tasklet(f)()
        tg = stackless.tasklet(g)()
        th = stackless.tasklet(h)()

        rlist.append('mb')
        stackless.run()
        rlist.append('ma')

        assert rlist == 'mb fb gb hb fa ga ha ma'.split()

    def test_except(self):
        rlist = []
        def f():
            rlist.append('f')
            return 1/0

        def g():
            rlist.append('bg')
            stackless.schedule()
            rlist.append('ag')

        def h():
            rlist.append('bh')
            stackless.schedule()
            rlist.append('ah')

        tg = stackless.tasklet(g)()
        tf = stackless.tasklet(f)()
        th = stackless.tasklet(h)()

        try:
            stackless.run()
        # cheating, can't test for ZeroDivisionError
        except Exception, e:
            rlist.append('E')
        stackless.schedule()
        stackless.schedule()

        assert rlist == "bg f E bh ag ah".split()

    def test_except_full(self):
        rlist = []
        def f():
            rlist.append('f')
            return 1/0

        def g():
            rlist.append('bg')
            stackless.schedule()
            rlist.append('ag')

        def h():
            rlist.append('bh')
            stackless.schedule()
            rlist.append('ah')

        tg = stackless.tasklet(g)()
        tf = stackless.tasklet(f)()
        th = stackless.tasklet(h)()

        try:
            stackless.run()
        except ZeroDivisionError:
            rlist.append('E')
        stackless.schedule()
        stackless.schedule()

        assert rlist == "bg f E bh ag ah".split()

    def test_kill(self):
        def f():pass
        t =  stackless.tasklet(f)()
        t.kill()
        assert not t.alive

    # tests inspired from simple stackless.com examples

    def test_construction(self):
        output = []
        def print_(*args):
            output.append(args)

        def aCallable(value):
            print_("aCallable:", value)

        task = stackless.tasklet(aCallable)
        task.setup('Inline using setup')

        stackless.run()
        assert output == [("aCallable:", 'Inline using setup')]


        del output[:]
        task = stackless.tasklet(aCallable)
        task('Inline using ()')

        stackless.run()
        assert output == [("aCallable:", 'Inline using ()')]
        
        del output[:]
        task = stackless.tasklet()
        task.bind(aCallable)
        task('Bind using ()')

        stackless.run()
        assert output == [("aCallable:", 'Bind using ()')]

    def test_simple_channel(self):
        output = []
        #skip('')
        def print_(*args):
            output.append(args)
            
        def Sending(channel):
            print_("sending")
            channel.send("foo")

        def Receiving(channel):
            print_("receiving")
            print_(channel.receive())

        ch=stackless.channel()

        task=stackless.tasklet(Sending)(ch)

        # Note: the argument, schedule is taking is the value,
        # schedule returns, not the task that runs next

        #stackless.schedule(task)
        stackless.schedule()
        task2=stackless.tasklet(Receiving)(ch)
        #stackless.schedule(task2)
        stackless.schedule()

        stackless.run()

        assert output == [('sending',), ('receiving',), ('foo',)]

    def test_balance_zero(self):
        ch=stackless.channel()
        assert ch.balance == 0
        
    def test_balance_send(self):
        def Sending(channel):
            channel.send("foo")

        ch=stackless.channel()

        task=stackless.tasklet(Sending)(ch)
        stackless.run()

        assert ch.balance == 1

    def test_balance_recv(self):
        def Receiving(channel):
            channel.receive()

        ch=stackless.channel()

        task=stackless.tasklet(Receiving)(ch)
        stackless.run()

        assert ch.balance == -1

    def test_run(self):
        output = []
        def print_(*args):
            output.append(args)

        def f(i):
            print_(i)

        stackless.tasklet(f)(1)
        stackless.tasklet(f)(2)
        stackless.run()

        assert output == [(1,), (2,)]

    def test_schedule(self):
        output = []
        def print_(*args):
            output.append(args)

        def f(i):
            print_(i)

        stackless.tasklet(f)(1)
        stackless.tasklet(f)(2)
        stackless.schedule()

        assert output == [(1,), (2,)]


    def test_cooperative(self):
        output = []
        def print_(*args):
            output.append(args)

        def Loop(i):
            for x in range(3):
                stackless.schedule()
                print_("schedule", i)

        stackless.tasklet(Loop)(1)
        stackless.tasklet(Loop)(2)
        stackless.run()

        assert output == [('schedule', 1), ('schedule', 2),
                          ('schedule', 1), ('schedule', 2),
                          ('schedule', 1), ('schedule', 2),]

