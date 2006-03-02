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

def newspace():
    return space.ComputationSpace(dummy_problem)


#-- meat ----------------------------

class TestSimpleVariable:

    def test_basics(self):
        x = v.SimpleVar()
        assert x.val == v.NoValue
        x.bind(42)
        assert x.val == 42
        x.bind(42)
        raises(v.AlreadyBound, x.bind, 43)

    def test_dataflow(self):
        def fun(thread, var):
            thread.state = 1
            v = var.get()
            thread.state = v

        x = v.SimpleVar()
        t = FunThread(fun, x)
        import time
        t.start()
        time.sleep(.5)
        assert t.state == 1
        x.bind(42)
        t.join()
        assert t.state == 42
            

class TestCsVariable:

    def test_no_same_name(self):
        sp = newspace()
        x = sp.var('x')
        raises(space.AlreadyInStore, sp.var, 'x')

    def test_get_by_name(self):
        sp = newspace()
        x = sp.var('x')
        assert x == sp.get_var_by_name('x')
        raises(space.NotInStore, sp.get_var_by_name, 'y')

    def test_one_thread_reading_one_var(self):
        sp = newspace()
        cons = Consumer()
        x = sp.var('x')
        cons.give_var(x)
        cons.start()
        sp.bind(x, 42)
        cons.join()
        assert cons.var.val == 42

    def test_many_threads_reading_one_var(self):
        sp = newspace()
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
        sp = newspace()
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

#-- concurrent streams and lists ----------------

#-- utilities -----------------------------------

class EOL: pass

def generate(thread, Xs, n, limit):
    """(eager generation of a stream 0|1|2|...)
    declare
    fun {Generate N Limit}
       if N<Limit then
          N|{Generate N+1 Limit}
       else nil end
    end"""
    if n<limit:
        sp = newspace()
        Xr = sp.var('Xr')
        Xs.bind((n, Xr))
        generate(thread, Xr, n+1, limit)
    else:
        Xs.bind(EOL)    

def dgenerate(thread, n, Xs):
    """(demand-driven generation of 0|1|2|...)
    declare
    proc {DGenerate N Xs}
        case Xs of X|Xr then
           X=N
           {DGenerate N+1 Xr}
        end
    end"""
    sp = newspace()
    print "GENERATOR waits on Xs"
    X_Xr = Xs.get()      # destructure Xs
    if X_Xr == None: return
    X = X_Xr[0]          # ... into X
    X.bind(n)            # bind X to n
    print "GENERATOR binds X to", n
    Xr = X_Xr[1]         # ... and Xr
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
        Xs.bind((X, Xr))
        x = X.get() # wait on the value of X
        print "CLIENT got", x
        dsum(thread, Xr, a+x, limit-1)
    else:
        print "CLIENT binds Xs to None and exits"
        Xs.bind(None)
        thread.result = a

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
    Xr = X_Xr[1]
    reduc(thread, Xr, fun(a, X_Xr[0]), fun)

#-- meat ----------------------------------------

class TestStream:
                
    def test_multiple_readers_eager_list(self):
        """the generator controls the flow"""
        sp = newspace()
            
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
        sp = newspace()

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


    def test_bounded_buffer_transducer(self):
        """reader controls the flow but a
           buffer between generator/consummer
           avoids inefficient step-wise progression
        """
        sp = newspace()

        def bounded_buffer(thread, n, Xs, Ys):

            sp = newspace()

            def startup(n, Xs):
                """
                fun {Startup N ?Xs}
                    if N==0 then Xs 
                    else Xr in Xs=_|Xr {Startup N-1 Xr} end
                end
                """
                if n==0: return Xs
                sp = newspace()
                X_ = sp.var('X_')
                Xr = sp.var('Xr')
                Xs.bind((X_, Xr))
                return startup(n-1, Xr)

            def ask_loop(Ys, Xs, End):
                """
                proc {AskLoop Ys ?Xs ?End}
                    case Ys of Y|Yr then Xr End2 in
                        Xs=Y|Xr
                        End=_|End2
                        {AskLoop Yr Xr End2}
                    end
                end
                """
                sp = newspace()
                Y_Yr = Ys.get()   # destructure Ys
                if Y_Yr != None: 
                    Y, Yr = Y_Yr
                    X, Xr = Xs.get()
                    Y.bind(X.get())
                    End2 = sp.var('End2')
                    X_ = sp.var('X_')
                    End.bind((X_, End2))
                    ask_loop(Yr, Xr, End2)
                else:
                    End.bind(None)

            End = sp.var('End')
            End.bind(startup(n, Xs))
            print "BUFFER starts"
            ask_loop(Ys, Xs, End)

        Xs = sp.var('Xs')
        Ys = sp.var('Ys')

        generator = FunThread(dgenerate, 0, Xs)
        bbuffer = FunThread(bounded_buffer, 8, Xs, Ys)
        summer = FunThread(dsum, Ys, 0, 50)

        generator.start()
        summer.start()
        bbuffer.start()

        generator.join()
        summer.join()
        bbuffer.join()

        assert summer.result == 1225
