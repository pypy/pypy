from threading import Thread
import operator

from py.test import raises

import computationspace as space
import variable as v
from problems import dummy_problem

#-- utilities ---------------------

class FunThread(Thread):

    def __init__(self, fun, *args):
        Thread.__init__(self)
        self.fun = fun
        self.args = args

    def run(self):
        self.fun(self, *self.args)

class Consumer(Thread):

    def give_var(self, var):
        self.var = var

    def run(self):
        val = self.var.get()

class NConsumer(Thread):

    def give_vars(self, vars_):
        self.vars = vars_

    def run(self):
        val = [var.get() for var in self.vars]

#-- meat ----------------------------

class TestVariable:

    def test_no_same_name(self):
        sp = space.ComputationSpace(dummy_problem)
        x = sp.var('x')
        raises(space.AlreadyInStore, sp.var, 'x')

    def test_get_by_name(self):
        sp = space.ComputationSpace(dummy_problem)
        x = sp.var('x')
        assert x == sp.get_var_by_name('x')
        raises(space.NotInStore, sp.get_var_by_name, 'y')

    def test_one_thread_reading_one_var(self):
        sp = space.ComputationSpace(dummy_problem)
        cons = Consumer()
        x = sp.var('x')
        cons.give_var(x)
        cons.start()
        sp.bind(x, 42)
        cons.join()
        assert cons.var.val == 42

    def test_many_threads_reading_one_var(self):
        sp = space.ComputationSpace(dummy_problem)
        conss = [Consumer() for i in range(10)]
        x = sp.var('x')
        for cons in conss:
            cons.give_var(x)
            cons.start()
        sp.bind(x, 42)
        for cons in conss:
            cons.join()
        assert cons.var.val == 42

    def test_many_thread_reading_many_var(self):
        sp = space.ComputationSpace(dummy_problem)
        conss = [NConsumer() for i in range(10)]
        vars_ = [sp.var(str(i)) for i in range(10)]
        for cons in conss:
            cons.give_vars(vars_)
            cons.start()
        for var in vars_:
            sp.bind(var, var.name)
        for cons in conss:
            cons.join()
        for i in range(10):
            assert vars_[i].val == str(i)

    def test_basic_list(self):
        s = v.make_list([1, 2, 3])
        assert s.__str__() == '1|2|3'
        assert s.length() == 3
        s.rest().rest().set_rest(s)
        assert s.length() == 4
        assert s.__str__() == '1|2|3|...'
        s. set_rest(s)
        assert s.__str__() == '1|...'
        assert s.length() == 2

    def test_producer_consummer_stream(self):
        sp = space.ComputationSpace(dummy_problem)
        import time

        def generate(thread, var, n, limit):
            s = var.get()
            while n<limit:
                s.put(limit-n)
                n += 1
            s.put(v.NoValue)
        
        def reduc(thread, var, fun):
            stream = var.get()
            val = stream.get()
            while (val != v.NoValue):
                thread.result = fun(thread.result, val)
                val = stream.get()

        s = sp.var('s')
        s.bind(v.Stream())
        
        generator = FunThread(generate, s, 1, 10)
        reductor = FunThread(reduc, s, operator.mul)
        reductor.result = 2

        generator.start()
        reductor.start()
        generator.join()
        reductor.join()
        
        assert reductor.result == 725760

    def test_daisychain_stream(self):
        sp = space.ComputationSpace(dummy_problem)

        def woman_in_chains(thread, S):
            stream = S.get()
            assert isinstance(stream, v.Stream)
            val = stream.get()
            while val != v.NoValue:
                print val
                thread.result = val
                val = stream.get()
                if isinstance(val, v.Var):
                    stream = val.get()
                    val = stream.get()

        s1 = sp.var('s1')
        s2 = sp.var('s2')
        stream1 = v.Stream(v.make_list([1, 2, 3, s2]))
        stream2 = v.Stream(v.make_list([4, 5, 6, v.NoValue]))
        assert str(stream1) == '1|2|3|s2'
        assert str(stream2) == '4|5|6|variable.NoValue'
        
        woman = FunThread(woman_in_chains, s1)
        woman.start()

        s1.bind(stream1)
        s2.bind(stream2)

        woman.join()

        assert woman.result == 6
                
    def test_multiple_readers_list(self):
        sp = space.ComputationSpace(dummy_problem)
        
        def generate(thread, L, N):
            n=N.get()
            assert 0 < n < 32768
            l = v.Pair(0, None)
            L.bind(l)
            for i in range(1,n):
                l.set_rest(v.Pair(i, None))
                l = l.rest()
            l.set_rest(v.NoValue)

        def reduc(thread, L, fun):
            l=L.get()
            thread.result = 0
            while l != v.NoValue:
                val = l.first()
                thread.result = fun(thread.result, val)
                l = l.rest()
            
        L = sp.var('L')
        N = sp.var('N')

        r1 = FunThread(reduc, L, operator.add)
        r2 = FunThread(reduc, L, operator.add)
        r3 = FunThread(reduc, L, operator.add)
        generator = FunThread(generate, L, N)

        r1.start()
        r2.start()
        r3.start()
        generator.start()

        N.bind(42)

        generator.join()
        for r in (r1, r2, r3):
            r.join()
            assert r.result == 861
