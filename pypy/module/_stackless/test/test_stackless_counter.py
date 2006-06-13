from pypy.conftest import gettestobjspace

class AppTest_Stackless:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space

    def test_this(self):
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
