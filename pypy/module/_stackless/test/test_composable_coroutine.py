""" a faith is the connection between past and future that divides the
    application into switch-compatible chunks.
    -- stakkars
"""
from pypy.conftest import gettestobjspace
from py.test import skip

class AppTest_ComposableCoroutine:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space

        cls.w_generator_ = space.appexec([], """():
            import _stackless

            generators_costate = _stackless.usercostate()
            main = generators_costate.getcurrent()

            class generator_iterator(_stackless.coroutine):

                def __iter__(self):
                    return self

                def next(self):
                    if self.gi_answer is not None:
                        raise ValueError('stackless-generator'
                                         ' already executing')
                    self.gi_answer = []
                    self.gi_caller = generators_costate.getcurrent()
                    self.switch()
                    answer = self.gi_answer
                    self.gi_answer = None
                    if answer:
                        return answer[0]
                    else:
                        raise StopIteration

            def generator(f):
                def myfunc(*args, **kwds):
                    g = generators_costate.spawn(generator_iterator)
                    g.gi_answer = None
                    g.bind(f, *args, **kwds)
                    return g
                return myfunc

            def Yield(value):
                g = generators_costate.getcurrent()
                if g is main:
                    raise ValueError('Yield() outside any stackless-generator')
                assert isinstance(g, generator_iterator)
                assert g.gi_answer == []
                g.gi_answer.append(value)
                g.gi_caller.switch()

            generator.Yield = Yield
            generator._costate = generators_costate
            return (generator,)
        """)

    def test_simple_costate(self):
        import _stackless
        costate = _stackless.usercostate()
        main = costate.getcurrent()

        result = []
        def f():
            result.append(costate.getcurrent())
        co = costate.spawn()
        co.bind(f)
        co.switch()
        assert result == [co]

    def test_generator(self):
        generator, = self.generator_

        def squares(n):
            for i in range(n):
                generator.Yield(i*i)
        squares = generator(squares)

        lst1 = [i*i for i in range(10)]
        for got in squares(10):
            expected = lst1.pop(0)
            assert got == expected
        assert lst1 == []

    def test_multiple_costates(self):
        """Test that two independent costates mix transparently:

        - compute_costate, used for a coroutine that fills a list with
                           some more items each time it is switched to

        - generators_costate, used interally by self.generator (see above)
        """

        import _stackless
        generator, = self.generator_

        # you can see how it fails if we don't have two different costates
        # by setting compute_costate to generator._costate instead
        compute_costate = _stackless.usercostate()
        compute_main = compute_costate.getcurrent()
        lst = []

        def filler():     # -> 0, 1, 2, 100, 101, 102, 200, 201, 202, 300 ...
            for k in range(5):
                for j in range(3):
                    lst.append(100 * k + j)
                compute_main.switch()

        filler_co = compute_costate.spawn()
        filler_co.bind(filler)

        def grab_next_value():
            while not lst:
                #print 'filling more...'
                filler_co.switch()
                #print 'now lst =', lst
            #print 'grabbing', lst[0]
            return lst.pop(0)

        def squares(n):
            for i in range(n):
                #print 'square:', i
                generator.Yield(i*grab_next_value())
        squares = generator(squares)

        lst1 = [0, 1, 4,  300, 404, 510,  1200, 1407, 1616,  2700]
        for got in squares(10):
            expected = lst1.pop(0)
            assert got == expected
        assert lst1 == []
