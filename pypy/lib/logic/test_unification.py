import unification as u
import variable as v
from constraint import FiniteDomain
from py.test import raises, skip
from threading import Thread

class FunThread(Thread):

    def __init__(self, fun, *args):
        Thread.__init__(self)
        self.fun = fun
        self.args = args

    def run(self):
        self.fun(self, *self.args)

class TestUnification:
    
    def setup_method(self, meth):
        u._store = u.Store()

    def test_already_in_store(self):
        x = u.var('x')
        raises(v.AlreadyExists, u.var, 'x')

    def test_already_bound(self):
        x = u.var('x')
        u.bind(x, 42)
        raises(u.AlreadyBound, u.bind, x, 42)

    def test_bind_var_var(self):
        x = u.var('x')
        y = u.var('y')
        z = u.var('z')
        u.bind(x, z)
        assert x.val == u.EqSet([x, z])
        assert y.val == u.EqSet([y])
        assert z.val == u.EqSet([x, z])

    def test_bind_var_val(self):
        x, y, z = u.var('x'), u.var('y'), u.var('z')
        u.bind(x, z)
        u.bind(y, 42)
        u.bind(z, 3.14)
        assert x.val == 3.14
        assert y.val == 42
        assert z.val == 3.14

    def test_unify_same(self):
        x,y,z,w = (u.var('x'), u.var('y'),
                   u.var('z'), u.var('w'))
        u.bind(x, [42, z])
        u.bind(y, [z, 42])
        u.bind(w, [z, 43])
        raises(u.UnificationFailure, u.unify, x, w)
        u.unify(x, y)
        assert z.val == 42

    def test_double_unification(self):
        x, y, z = (u.var('x'), u.var('y'),
                   u.var('z'))
        u.bind(x, 42)
        u.bind(y, z)
        u.unify(x, y)
        assert z.val == 42
        #raises(u.UnificationFailure, u.unify, x, y)

    def test_unify_values(self):
        x, y = u.var('x'), u.var('y')
        u.bind(x, [1, 2, 3])
        u.bind(y, [1, 2, 3])
        u.unify(x, y)
        assert x.val == [1, 2, 3]
        assert y.val == [1, 2, 3]

    def test_unify_lists_success(self):
        x,y,z,w = (u.var('x'), u.var('y'),
                   u.var('z'), u.var('w'))
        u.bind(x, [42, z])
        u.bind(y, [w, 44])
        u.unify(x, y)
        assert x.val == [42, z]
        assert y.val == [w, 44]
        assert z.val == 44
        assert w.val == 42

    def test_unify_dicts_success(self):
        x,y,z,w = (u.var('x'), u.var('y'),
                   u.var('z'), u.var('w'))
        u.bind(x, {1:42, 2:z})
        u.bind(y, {1:w,  2:44})
        u.unify(x, y)
        assert x.val == {1:42, 2:z}
        assert y.val == {1:w,  2:44}
        assert z.val == 44
        assert w.val == 42

    def test_unify_failure(self):
        x,y,z = u.var('x'), u.var('y'), u.var('z')
        u.bind(x, [42, z])
        u.bind(y, [z, 44])
        raises(u.UnificationFailure, u.unify, x, y)
        # check store consistency
        assert x.val == [42, z]
        assert y.val == [z, 44]
        assert z.val == u.EqSet([z])

    def test_unify_failure2(self):
        x,y,z,w = (u.var('x'), u.var('y'),
                   u.var('z'), u.var('w'))
        u.bind(x, [42, z])
        u.bind(y, [w, 44])
        u.bind(z, w)
        assert u._store.in_transaction == False
        raises(u.UnificationFailure, u.unify, x, y)
        assert u._store.in_transaction == False
        # check store consistency
        assert x.val == [42, z]
        assert y.val == [w, 44]
        assert z.val == u.EqSet([z,w])
        assert w.val == u.EqSet([z,w])

    def test_unify_circular(self):
        x, y, z, w, a, b = (u.var('x'), u.var('y'),
                            u.var('z'), u.var('w'),
                            u.var('a'), u.var('b'))
        u.bind(x, [y])
        u.bind(y, [x])
        raises(u.UnificationFailure, u.unify, x, y)
        u.bind(z, [1, w])
        u.bind(w, [z, 2])
        raises(u.UnificationFailure, u.unify, z, w)
        u.bind(a, {1:42, 2:b})
        u.bind(b, {1:a,  2:42})
        raises(u.UnificationFailure, u.unify, a, b)
        # check store consistency
        assert x.val == [y]
        assert y.val == [x]
        assert z.val == [1, w]
        assert w.val == [z, 2]
        assert a.val == {1:42, 2:b}
        assert b.val == {1:a,  2:42}
        
        
    def test_threads_creating_vars(self):
        def create_var(thread, *args):
            x = u.var('x')

        def create_var2(thread, *args):
            raises(v.AlreadyExists, u.var, 'x')

        t1, t2 = (FunThread(create_var),
                  FunThread(create_var2))
        t1.start()
        t2.start()


    def test_threads_binding_vars(self):
        
        def do_stuff(thread, var, val):
            thread.raised = False
            try:
                u.bind(var, val)
            except u.AlreadyBound:
                thread.raised = True
            
        x = u.var('x')
        vars_ = []
        for nvar in range(1000):
            v = u.var('x-'+str(nvar))
            u.bind(x, v)
            vars_.append(v)

        for var in u._store.vars:
            assert var.val == x.val

        t1, t2 = (FunThread(do_stuff, x, 42),
                  FunThread(do_stuff, x, 43))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        #check that every var is really bound to 42 or 43
        for var in u._store.vars:
            assert var.val == x.val
        assert (t2.raised and not t1.raised) or \
               (t1.raised and not t2.raised)
    

    def test_threads_unifying_vars(self):
        x, y, z = u.var('x'), u.var('y'), u.var('z')
        l1 = range(999)
        l2 = range(999)
        l1[-1] = z
        l2[0] = z
        l2[-1] = 0
        u.bind(x, l1)
        u.bind(y, l2)

        def do_unify(thread, v1, v2):
            thread.raised = False
            print thread
            try:
                u.unify(v1, v2)
            except u.UnificationFailure:
                thread.raised = True
            print thread

        t1, t2 = (FunThread(do_unify, x, y),
                  FunThread(do_unify, x, y))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        print "Z", z
        assert (t2.raised and not t1.raised) or \
               (t1.raised and not t2.raised)
        assert z.val == 0
            

    def test_set_var_domain(self):
        x = u.var('x')
        u.set_domain(x, [1, 3, 5])
        assert x.dom == FiniteDomain([1, 3, 5])
        assert u._store.domains[x] == FiniteDomain([1, 3, 5])

    def test_bind_with_domain(self):
        x = u.var('x')
        u.set_domain(x, [1, 2, 3])
        raises(u.OutOfDomain, u.bind, x, 42)
        u.bind(x, 3)
        assert x.val == 3

    def test_bind_with_incompatible_domains(self):
        x, y = u.var('x'), u.var('y')
        u.set_domain(x, [1, 2])
        u.set_domain(y, [3, 4])
        raises(u.IncompatibleDomains, u.bind, x, y)
        u.set_domain(y, [2, 4])
        u.bind(x, y)
        # check x and y are in the same equiv. set
        assert x.val == y.val


    def test_unify_with_domains(self):
        x,y,z = u.var('x'), u.var('y'), u.var('z')
        u.bind(x, [42, z])
        u.bind(y, [z, 42])
        u.set_domain(z, [1, 2, 3])
        raises(u.UnificationFailure, u.unify, x, y)
        u.set_domain(z, [41, 42, 43])
        u.unify(x, y)
        assert z.val == 42
        assert z.dom == FiniteDomain([41, 42, 43])
