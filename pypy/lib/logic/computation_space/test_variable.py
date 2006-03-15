from threading import Thread
import operator

from py.test import raises

from variable import var, NoValue, AlreadyBound, \
     UnificationFailure, stream_repr, Eqset, unify

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

    def test_rebinding(self):
        x = var()
        assert x.val == NoValue
        x.bind(42)
        assert x.val == 42
        x.bind(42)
        raises(UnificationFailure, x.bind, 43)

    def test_reunifying(self):
        x = var()
        unify(x, 42)
        unify(x, 42)
        raises(UnificationFailure, x.bind, 43)
        raises(UnificationFailure, unify, x, 43)


    def test_bind_var_val(self):
        x, y, z = var(), var(), var()
        x.bind(z)
        assert x.aliases() == z.aliases() == Eqset([x, z])
        y.bind(42)
        z.bind(3.14)
        assert x.val == 3.14
        assert y.val == 42
        assert z.val == 3.14

    def test_bind_var_var(self):
        x, y, z = var(), var(), var()
        x.bind(z)
        assert x.aliases() == Eqset([x, z])
        assert y.aliases() == Eqset([y])
        assert z.aliases() == Eqset([x, z])
        assert x.val == y.val == z.val == NoValue
        z.bind(42)
        assert z.val == 42
        assert x.val == 42
        y.bind(42)
        assert y.val == 42
        y.bind(z)

    def test_unify_same(self):
        x,y,z,w = var(), var(), var(), var()
        x.bind([42, z])
        y.bind([z, 42])
        w.bind([z, 43])
        raises(UnificationFailure, unify, x, w)
        unify(x, y)
        assert z.val == 42

    def test_double_unification(self):
        x, y, z = var(), var(), var()
        x.bind(42)
        y.bind(z)
        unify(x, y)
        assert z.val == 42
        unify(x, y)
        assert (z.val == x.val == y.val)

    def test_unify_values(self):
        x, y = var(), var()
        x.bind([1, 2, 3])
        y.bind([1, 2, 3])
        unify(x, y)
        assert x.val == [1, 2, 3]
        assert y.val == [1, 2, 3]

    def test_unify_lists_success(self):
        x,y,z,w = var(), var(), var(), var()
        x.bind([42, z])
        y.bind([w, 44])
        unify(x, y)
        assert x.val == [42, z]
        assert y.val == [w, 44]
        assert z.val == 44
        assert w.val == 42

    def test_unify_dicts_success(self):
        x,y,z,w = var(), var(), var(), var()
        x.bind({1:42, 2:z})
        y.bind({1:w,  2:44})
        unify(x, y)
        assert x.val == {1:42, 2:z}
        assert y.val == {1:w,  2:44}
        assert z.val == 44
        assert w.val == 42

    def test_unify_failure(self):
        x, y, z = var(), var(), var()
        x.bind([42, z])
        y.bind([z, 44])
        raises(UnificationFailure, unify, x, y)
        # check state
        assert x.val == [42, z]
        assert y.val == [z, 44]
        assert z.aliases() == Eqset([z])

    def test_unify_failure2(self):
        x,y,z,w = var(), var(), var(), var()
        x.bind([42, z])
        y.bind([w, 44])
        z.bind(w)
        raises(UnificationFailure, unify, x, y)
        # check state
        assert x.val == [42, z]
        assert y.val == [w, 44]
        # note that z has been bound to 42 !
        assert z.val == 42
        assert w.val == 42

    def test_unify_circular(self):
        x, y, z, w, a, b = (var(), var(), var(),
                            var(), var(), var())
        x.bind([y])
        y.bind([x])
        raises(UnificationFailure, unify, x, y)
        z.bind([1, w])
        w.bind([z, 2])
        raises(UnificationFailure, unify, z, w)
        a.bind({1:42, 2:b})
        b.bind({1:a,  2:42})
        raises(UnificationFailure, unify, a, b)
        # check store consistency
        assert x.val == [y]
        assert y.val == [x]
        assert z.val == [1, w]
        assert w.val == [z, 2]
        assert a.val == {1:42, 2:b}
        assert b.val == {1:a,  2:42}
        

    def notest_threads_binding_vars(self):
        # WTF ?
        #E       x = var()
        #>       UnboundLocalError: local variable 'var' referenced before assignment
        x = var() #
        vars_ = []

        def do_stuff(thread, var, val):
            thread.raised = False
            try:
                var.bind(val)
            except Exception, e:
                print e
                thread.raised = True
                assert isinstance(e, UnificationFailure)
            
        for nvar in range(100):
            v = var()
            x.bind(v)
            vars_.append(v)
            
        for var in vars_:
            assert var.val == x.val

        t1, t2 = (FunThread(do_stuff, x, 42),
                  FunThread(do_stuff, x, 43))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        #check that every var is really bound to 42 or 43
        for var in vars_:
            assert var in sp.vars
            assert var.val == x.val
        assert (t2.raised and not t1.raised) or \
               (t1.raised and not t2.raised)
    

    def test_threads_waiting_for_unbound_var(self):
        import time
        
        def near(v1, v2, err):
            return abs(v1 - v2) < err
        
        start_time = time.time()

        def wait_on_unbound(thread, var, start_time):
            thread.val = var.wait()
            thread.waited = time.time() - start_time

        x = var()
        t1, t2 = (FunThread(wait_on_unbound, x, start_time),
                  FunThread(wait_on_unbound, x, start_time))
        t1.start()
        t2.start()
        time.sleep(1)
        x.bind(42)
        t1.join()
        t2.join()
        assert t1.val == 42
        assert t2.val == 42
        assert near(t1.waited, 1, .1)
        assert near(t2.waited, 1, .1)

    def test_repr_stream(self):
        var._vcount = 0 #ensure consistent numbering
        x = var()
        it = x
        for i in range(3):
            it.bind((var(), var()))
            it = it.wait()[1]
        assert stream_repr(x) == '<?1>|<?3>|<?5>|<?6>'
        it.bind(None)
        assert stream_repr(x) == '<?1>|<?3>|<?5>|None'
        it = x
        for i in range(3):
            it.wait()[0].bind(i)
            it = it.wait()[1]
        assert stream_repr(x) == '0|1|2|None'


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
    print "generator waits on %s " % Xs
    X_Xr = Xs.wait()      # destructure Xs
    if X_Xr == None: return
    print "generator got X_Xr = ", X_Xr
    X = X_Xr[0]          # ... into X
    print "generator binds %s to %s" % (X, n)
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
        Xs.bind((X, Xr))
        print "client binds %s, waits on %s" % (Xs, X)
        x = X.wait() # wait on the value of X
        dsum(thread, Xr, a+x, limit-1)
    else:
        print "client binds Xs to None and exits"
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

        for r in (r1, r2, r3):
            r.start()

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
        def bounded_buffer(thread, n, Xs, Ys):

            def startup(n, Xs):
                """
                fun {Startup N ?Xs}
                    if N==0 then Xs 
                    else Xr in Xs=_|Xr {Startup N-1 Xr} end
                end
                """
                if n==0: return Xs
                Xr = var()
                Xs.bind((var(), Xr))
                print "startup n = ", n, Xs
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
                Y_Yr = Ys.wait()   # destructure Ys
                if Y_Yr != None: 
                    Y, Yr = Y_Yr
                    X, Xr = Xs.wait()
                    Y.bind(X.wait())
                    End2 = var()
                    print "Ask_loop Ys Xs End", Ys, Xs, End
                    End.bind((var(), End2))
                    ask_loop(Yr, Xr, End2)
                else:
                    End.bind(None)

            End = startup(n, Xs)
            print "buffer starts", Ys, Xs, End
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
