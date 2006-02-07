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

##     def test_basic_producer_consummer_sream(self):
##         # this one is quite silly
##         sp = space.ComputationSpace(dummy_problem)

##         def generate(thread, var, n, limit):
##             s = var.get()
##             while n<limit:
##                 print n
##                 s.put(n)
##                 n += 1
##             s.put(None)
        
##         def reduc(thread, var, fun):
##             stream = var.get()
##             val = stream.get()
##             while (val != None):
##                 print val
##                 thread.result = fun(thread.result, val)
##                 val = stream.get()

##         s = sp.var('s')
##         s.bind(v.Stream())
        
##         generator = FunThread(generate, s, 1, 5)
##         reductor = FunThread(reduc, s, operator.mul)
##         reductor.result = 2

##         generator.start()
##         reductor.start()
##         generator.join()
##         reductor.join()

##         print  reductor.result
##         assert 0

    def test_daisychain_stream(self):
        # chained stupidity
        sp = space.ComputationSpace(dummy_problem)

        s1 = sp.var('s1')
        s2 = sp.var('s2')

        stream1 = v.Stream(stuff=[1, 2, 3, s2])
        stream2 = v.Stream(stuff=[4, 5, 6, None])

        s1.bind(stream1)
        s2.bind(stream2)

        def woman_in_chains(thread, stream_variable):
            stream = stream_variable.get()
            val = stream.get()
            while val != None:
                thread.result = val
                val = stream.get()
                if isinstance(val, v.Var):
                    stream = val.get()
                    val = stream.get()

        woman = FunThread(woman_in_chains, s1)
        woman.start()
        woman.join()

        assert woman.result == 6
                
    def test_cyclicproducer_consummer_sream(self):
        # infinite sillyness
        sp = space.ComputationSpace(dummy_problem)

        circular = sp.var('circular')
        s = v.Stream(stuff=[0, 1, 2, circular])
        circular.bind(s)

        def touch10(thread, stream_variable):
            stream = stream_variable.get()
            val = None
            for i in range(10):
                val = stream.get()
                if isinstance(val, v.Var):
                    # at stream tail is a var
                    stream = val.get()
                    val = stream.get()
                assert i % 3 == val 
            thread.result = val

        toucher = FunThread(touch10, circular)
        toucher.start()
        toucher.join()

        assert toucher.result == 0
