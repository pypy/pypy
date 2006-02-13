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

    #-- concurrent streams and lists ----------------

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
                
    def test_multiple_readers_eager_list(self):
        """the generator controls the flow"""
        sp = space.ComputationSpace(dummy_problem)

        class EOL: pass
        
        def generate(thread, Xs, n, limit):
            """declare
            fun {Generate N Limit}
               if N<Limit then
                  N|{Generate N+1 Limit}
               else nil end
            end"""
            if n<limit:
                sp = space.ComputationSpace(dummy_problem)
                Xr = sp.var('Xr')
                Xs.bind(v.CList(n, Xr))
                generate(thread, Xr, n+1, limit)
            else:
                Xs.bind(EOL)
                
        def reduc(thread, Xs, a, fun):
            """declare
            fun {Sum Xs A}
                case Xs
                    of X|Xr then {Sum Xr A+X}
                    [] nil then A
                    else {Sum Xs A}
                end
            end"""
            X_Xr = Xs.get()
            if X_Xr == EOL:
                thread.result = a
                return
            Xr = X_Xr.rest()
            reduc(thread, Xr, fun(a, X_Xr.first()), fun)
            
        Xs = sp.var('L')

        r1 = FunThread(reduc, Xs, 0, operator.add)
        r2 = FunThread(reduc, Xs, 0, operator.add)
        r3 = FunThread(reduc, Xs, 0, operator.add)
        generator = FunThread(generate, Xs, 0, 42)

        r1.start()
        r2.start()
        r3.start()
        generator.start()

        generator.join()
        for r in (r1, r2, r3):
            r.join()
            assert r.result == 861

    def test_lazy_list(self):
        """the reader controls the flow"""
        sp = space.ComputationSpace(dummy_problem)

        def newspace():
            return space.ComputationSpace(dummy_problem)

        def dgenerate(thread, n, Xs):
            """declare
            proc {DGenerate N Xs}
                case Xs of X|Xr then
                   X=N
                   {DGenerate N+1 Xr}
                end
            end"""
            # new local space
            sp = newspace()
            # go ahead ...
            print "GENERATOR waits on Xs"
            X_Xr = Xs.get()      # destructure Xs
            if X_Xr == None: return
            X = X_Xr.first()     # ... into X
            X.bind(n)            # bind X to n
            print "GENERATOR binds X to", n
            Xr = X_Xr.rest()     # ... and Xr
            dgenerate(thread, n+1, Xr)

        def dsum(thread, Xs, a, limit):
            """declare
            fun {DSum ?Xs A Limit}
               if Limit>0 then
                  X|Xr=Xs
               in
                  {DSum Xr A+X Limit-1}
               else A end
            end"""
            if limit > 0:
                sp = newspace()
                # fill Xs with an empty pair
                X = sp.var('X')
                Xr = sp.var('Xr')
                print "CLIENT binds Xs to X|Xr"
                Xs.bind(v.Pair(X, Xr))
                x = X.get() # wait on the value of X
                print "CLIENT got", x
                dsum(thread, Xr, a+x, limit-1)
            else:
                print "CLIENT binds Xs to None and exits"
                Xs.bind(None)
                thread.result = a

        def run_test(t1, t2):
            """
            local Xs S in
              thread {DGenerate 0 Xs} end
              thread S={DSum Xs 0 15} end
              {Browse S}
            end"""
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        Xs = sp.var('Xs')
        generator = FunThread(dgenerate, 0, Xs)
        summer = FunThread(dsum, Xs, 0, 15)

        run_test(generator, summer)
        assert summer.result == 105
