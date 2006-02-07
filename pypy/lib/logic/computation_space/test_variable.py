from threading import Thread

from py.test import raises

import computationspace as space
import variable as v
from problems import dummy_problem

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

    def test_producer_consummer_sreams(self):
        sp = space.ComputationSpace(dummy_problem)

        def generate(var, n, limit):
            if n<limit:
                var.get().put(n)
            else:
                var.get().put(None)
        
        def reduc(var, fun, a):
            val = var.get()
            while val != None:
                pass
