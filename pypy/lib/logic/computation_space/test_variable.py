from threading import Thread
import operator

from py.test import raises

from variable import var, NoValue, AlreadyBound

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
        val = self.var.wait()

class NConsumer(Thread):

    def give_vars(self, vars_):
        self.vars = vars_

    def run(self):
        val = [var.wait() for var in self.vars]

#-- meat ----------------------------

class TestSimpleVariable:

    def test_basics(self):
        x = var()
        assert x.val == NoValue
        x.bind(42)
        assert x.val == 42
        x.bind(42)
        raises(AlreadyBound, x.bind, 43)

    def test_dataflow(self):
        def fun(thread, var):
            thread.state = 1
            v = var.wait()
            thread.state = v

        x = var()
        t = FunThread(fun, x)
        import time
        t.start()
        time.sleep(.5)
        assert t.state == 1
        x.bind(42)
        t.join()
        assert t.state == 42
            
    def test_stream(self):
        def consummer(thread, S):
            v = S.wait()
            if v:
                thread.res += v[0]
                consummer(thread, v[1])

        S = var()
        t = FunThread(consummer, S)
        t.res = 0
        t.start()
        for i in range(10):
            tail = var()
            S.bind((i, tail))
            S = tail
        S.bind(None)
        t.join()
        assert t.res == 45

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
        Xr = var()
        Xs.bind((n, Xr))
        generate(thread, Xr, n+1, limit)
    else:
        Xs.bind(None)    

def dgenerate(thread, n, Xs):
    """(demand-driven generation of 0|1|2|...)
    declare
    proc {DGenerate N Xs}
        case Xs of X|Xr then
           X=N
           {DGenerate N+1 Xr}
        end
    end"""
    print "GENERATOR in %s waits on Xs" % thread.getName()
    X_Xr = Xs.wait()      # destructure Xs
    if X_Xr == None: return
    X = X_Xr[0]          # ... into X
    print "GENERATOR in %s binds X to %s" % (thread.getName(), n)
    X.bind(n)            # bind X to n
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
        # fill Xs with an empty pair
        X = var()
        Xr = var()
        print "CLIENT binds Xs to X|Xr"
        Xs.bind((X, Xr))
        x = X.wait() # wait on the value of X
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
    X_Xr = Xs.wait()
    if X_Xr == None:
        thread.result = a
        return
    Xr = X_Xr[1]
    reduc(thread, Xr, fun(a, X_Xr[0]), fun)

def run_test(t1, t2):
    t1.start()
    t2.start()
    t1.join()
    t2.join()


#-- meat ----------------------------------------

class TestStream:
                
    def test_multiple_readers_eager_list(self):
        """the generator controls the flow"""
        Xs = var()

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
        """the reader controls the flow
        local Xs S in
          thread {DGenerate 0 Xs} end
          thread S={DSum Xs 0 15} end
          {Browse S}
        end"""
        Xs = var()
        generator = FunThread(dgenerate, 0, Xs)
        summer = FunThread(dsum, Xs, 0, 15)

        run_test(generator, summer)
        assert summer.result == 105

    def test_wait_needed(self):
        """lazyness by wait_needed"""
        Xs = var()

        def lgenerate(thread, n, Xs):
            """wait-needed version of dgenerate"""
            print "GENERATOR waits on Xs"
            Xs.wait_needed()
            Xr = var()
            Xs.bind((n, Xr))  
            print "GENERATOR binds Xs to", n
            dgenerate(thread, n+1, Xr)

        def sum(thread, Xs, a, limit):
            """much shorter than dsum"""
            if limit > 0:
                x = Xs.wait()
                print "CLIENT got", x
                dsum(thread, x[1], a+x[0], limit-1)
            else:
                thread.result = a
        
        generator = FunThread(lgenerate, 0, Xs)
        summer = FunThread(sum, Xs, 0, 15)

        run_test(generator, summer)
        assert summer.result == 105
        

    def test_bounded_buffer_transducer(self):
        """reader controls the flow but a
           buffer between generator/consummer
           avoids inefficient step-wise progression
        """
        def print_stream(S):
            while S.is_bound():
                v = S.wait()
                if isinstance(v, tuple):
                    v0 = v[0]
                    if v0.is_bound(): print v0, '|',
                    else: print '?' ; break
                    S = v[1]
                else:
                    print v
                    break

        def bounded_buffer(thread, n, Xs, Ys):

            def startup(n, Xs):
                """
                fun {Startup N ?Xs}
                    if N==0 then Xs 
                    else Xr in Xs=_|Xr {Startup N-1 Xr} end
                end
                """
                if n==0: return Xs
                print "startup n = ", n,
                print_stream(Xs)
                Xr = var()
                Xs.bind((var(), Xr))
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
                print "Ask_loop ..."
                print_stream(Xs)
                print_stream(Ys)
                Y_Yr = Ys.wait()   # destructure Ys
                if Y_Yr != None: 
                    Y, Yr = Y_Yr
                    print "Ask_loop in thread %s got %s %s " % \
                          (thread.getName(), Y, Yr)
                    X, Xr = Xs.wait()
                    Y.bind(X.wait())
                    End2 = var()
                    End.bind((var(), End2))
                    ask_loop(Yr, Xr, End2)
                else:
                    End.bind(None)

            End = var()
            End.bind(startup(n, Xs))
            print "BUFFER starts"
            ask_loop(Ys, Xs, End)

        Xs = var()
        Ys = var()

        generator = FunThread(dgenerate, 0, Xs)
        bbuffer = FunThread(bounded_buffer, 4, Xs, Ys)
        summer = FunThread(dsum, Ys, 0, 50)

        generator.start()
        summer.start()
        bbuffer.start()

        generator.join()
        summer.join()
        bbuffer.join()

        assert summer.result == 1225
