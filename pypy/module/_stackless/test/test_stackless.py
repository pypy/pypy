from pypy.conftest import gettestobjspace, skip_on_missing_buildoption
from py.test import skip


class AppTest_Stackless:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space

    def x_test_one(self):
        import stackless

        print stackless.__file__
        t = stackless.tasklet()
        t.demo()
        class A(stackless.tasklet):
            def __init__(self, name):
                self.name = name
            def __new__(subtype, *args):
                return stackless.tasklet.__new__(subtype)
        x = A("heinz")
        x.demo()
        print x.name

    def test_simple(self):
        import stackless

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
        import stackless

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
        import stackless

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
        import stackless
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
        import stackless
        
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
        import stackless
        
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
        skip('kill is not really working')
        import stackless
        def f():pass
        t =  stackless.tasklet(f)()
        t.kill()
        assert not t.alive

    # tests inspired from simple stackless.com examples

    def test_construction(self):
        output = []
        def print_(*args):
            output.append(args)

        import stackless
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
        def print_(*args):
            output.append(args)
            
        import stackless
        
        def Sending(channel):
            print_("sending")
            channel.send("foo")

        def Receiving(channel):
            print_("receiving")
            print_(channel.receive())

        ch=stackless.channel()

        task=stackless.tasklet(Sending)(ch)
        stackless.schedule(task)
        task2=stackless.tasklet(Receiving)(ch)
        stackless.schedule(task2)

        stackless.run()

        assert output == [('sending',), ('receiving',), ('foo',)]

    def test_balance_zero(self):
        import stackless

        ch=stackless.channel()
        assert ch.balance == 0
        
    def test_balance_send(self):
        import stackless

        def Sending(channel):
            channel.send("foo")

        ch=stackless.channel()

        task=stackless.tasklet(Sending)(ch)
        stackless.schedule(task)
        stackless.run()

        assert ch.balance == 1

    def test_balance_recv(self):
        import stackless

        def Receiving(channel):
            channel.receive()

        ch=stackless.channel()

        task=stackless.tasklet(Receiving)(ch)
        stackless.schedule(task)
        stackless.run()

        assert ch.balance == -1

    def test_run(self):
        output = []
        def print_(*args):
            output.append(args)

        import stackless
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

        import stackless
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

        import stackless
        
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

class Test_StacklessPickling:

    def setup_class(cls):
        skip_on_missing_buildoption(stackless=True)


    def test_basic_tasklet_pickling(self):
        import stackless
        from stackless import run, schedule, tasklet
        import pickle

        output = []

        import new

        mod = new.module('mod')
        mod.output = output

        exec """from stackless import schedule
        
def aCallable(name):
    output.append(('b', name))
    schedule()
    output.append(('a', name))
""" in mod.__dict__
        import sys
        sys.modules['mod'] = mod
        aCallable = mod.aCallable


        tasks = []
        for name in "ABCDE":
            tasks.append(tasklet(aCallable)(name))

        schedule()

        assert output == [('b', x) for x in "ABCDE"]
        del output[:]
        pickledTasks = pickle.dumps(tasks)

        schedule()
        assert output == [('a', x) for x in "ABCDE"]
        del output[:]
        
        unpickledTasks = pickle.loads(pickledTasks)
        for task in unpickledTasks:
            task.insert()

        schedule()
        assert output == [('a', x) for x in "ABCDE"]
