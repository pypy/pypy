from threading import Thread

from py.test import raises

import computationspace as u
import variable as v
from problems import *

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

    def setup_method(self, meth):
        u._store = u.ComputationSpace(dummy_problem)

    def test_no_same_name(self):
        x = u.var('x')
        raises(u.AlreadyInStore, u.var, 'x')

    def test_get_by_name(self):
        x = u.var('x')
        assert x == u._store.get_var_by_name('x')
        raises(u.NotInStore, u._store.get_var_by_name, 'y')

    def test_one_thread_reading_one_var(self):
        cons = Consumer()
        x = u.var('x')
        cons.give_var(x)
        cons.start()
        u.bind(x, 42)
        cons.join()
        assert cons.var.val == 42

    def test_many_threads_reading_one_var(self):
        conss = [Consumer() for i in range(10)]
        x = u.var('x')
        for cons in conss:
            cons.give_var(x)
            cons.start()
        u.bind(x, 42)
        for cons in conss:
            cons.join()
        assert cons.var.val == 42

    def test_many_thread_reading_many_var(self):
        conss = [NConsumer() for i in range(10)]
        vars_ = [u.var(str(i)) for i in range(10)]
        for cons in conss:
            cons.give_vars(vars_)
            cons.start()
        for var in vars_:
            u.bind(var, var.name)
        for cons in conss:
            cons.join()
        for i in range(10):
            assert vars_[i].val == str(i)
