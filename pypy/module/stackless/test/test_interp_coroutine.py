"""
testing coroutines at interprepter level
"""

import os
from pypy.module.stackless.interp_coroutine import main_coroutine_getter, Coroutine, AbstractThunk
from pypy.translator.c.test.test_stackless import StacklessTest
from pypy.translator.c import gc

def output(stuff):
    os.write(2, stuff + '\n')

class TestCoroutine(StacklessTest):
    backendopt = True
    stacklessmode = True
    gcpolicy = gc.BoehmGcPolicy
    Coroutine = Coroutine

    def setup_method(self, method):
        main_coroutine_getter.costate = None
        main_coroutine_getter.costate = None

    def _freeze_(self):    # for 'self.Coroutine'
        return True

    def test_coroutine(self):

        def g(lst, coros):
            coro_f, coro_g, coro_h = coros
            lst.append(2)
            output('g appended 2')
            coro_h.switch()
            lst.append(5)
            output('g appended 5')

        def h(lst, coros):
            coro_f, coro_g, coro_h = coros
            lst.append(3)
            output('h appended 3')
            coro_f.switch()
            lst.append(7)
            output('h appended 7')

        class T(AbstractThunk):
            def __init__(self, func, arg1, arg2):
                self.func = func
                self.arg1 = arg1
                self.arg2 = arg2
            def call(self):
                self.func(self.arg1, self.arg2)

        def f():
            lst = [1]
            coro_f = Coroutine.getcurrent()
            coro_g = self.Coroutine()
            coro_h = self.Coroutine()
            coros = [coro_f, coro_g, coro_h]
            thunk_g = T(g, lst, coros)
            output('binding g after f set 1')
            coro_g.bind(thunk_g)
            thunk_h = T(h, lst, coros)
            output('binding h after f set 1')
            coro_h.bind(thunk_h)
            output('switching to g')
            coro_g.switch()
            lst.append(4)
            output('f appended 4')
            coro_g.switch()
            lst.append(6)
            output('f appended 6')
            coro_h.switch()
            lst.append(8)
            output('f appended 8')
            n = 0
            for i in lst:
                n = n*10 + i
            return n

        data = self.wrap_stackless_function(f)
        assert data == 12345678

    def test_coroutine2(self):

        class TBase(AbstractThunk):
            def call(self):
                pass

        class T(TBase):
            def __init__(self, func, arg1, arg2):
                self.func = func
                self.arg1 = arg1
                self.arg2 = arg2
            def call(self):
                self.res = self.func(self.arg1, self.arg2)

        class T1(TBase):
            def __init__(self, func, arg1):
                self.func = func
                self.arg1 = arg1
            def call(self):
                self.res = self.func(self.arg1)

        def g(lst, coros):
            coro_f1, coro_g, coro_h = coros
            lst.append(2)
            output('g appended 2')
            coro_h.switch()
            lst.append(5)
            output('g appended 5')
            output('exiting g')

        def h(lst, coros):
            coro_f1, coro_g, coro_h = coros
            lst.append(3)
            output('h appended 3')
            coro_f1.switch()
            lst.append(7)
            output('h appended 7')
            output('exiting h')

        def f1(coro_f1):
            lst = [1]
            coro_g = self.Coroutine()
            coro_h = self.Coroutine()
            coros = [coro_f1, coro_g, coro_h]
            thunk_g = T(g, lst, coros)
            output('binding g after f1 set 1')
            coro_g.bind(thunk_g)
            thunk_h = T(h, lst, coros)
            output('binding h after f1 set 1')
            coro_h.bind(thunk_h)
            output('switching to g')
            coro_g.switch()
            lst.append(4)
            output('f1 appended 4')
            coro_g.switch()
            lst.append(6)
            output('f1 appended 6')
            coro_h.switch()
            lst.append(8)
            output('f1 appended 8')
            n = 0
            for i in lst:
                n = n*10 + i
            output('exiting f1')
            return n     

        def f():
            coro_f = Coroutine.getcurrent()
            coro_f1 = self.Coroutine()
            thunk_f1 = T1(f1, coro_f1)
            output('binding f1 after f set 1')
            coro_f1.bind(thunk_f1)
            coro_f1.switch()        
            output('return to main :-(')
            return thunk_f1.res

        data = self.wrap_stackless_function(f)
        assert data == 12345678

    def test_kill_raise_del_coro(self):
        py.test.skip("does not work :-(")
        class T(AbstractThunk):
            def __init__(self, func, arg):
                self.func = func
                self.arg = arg
            def call(self):
                self.func(self.arg, self)

        def g(nrec, t, count=0):
            t.count = count
            if nrec < 0:
                raise ValueError
            if nrec:
                g(nrec-1, t, count+1)
            Coroutine.getmain().switch()

        def f():
            assert Coroutine.getmain().frame is None
            coro_g = self.Coroutine()
            thunk_g = T(g, 42)
            coro_g.bind(thunk_g)
            coro_g.switch()
            res = thunk_g.count
            res *= 10
            res |= coro_g.frame is not None
            # testing kill
            coro_g.kill()
            res *= 10
            res |= coro_g.frame is None
            coro_g = self.Coroutine()
            thunk_g = T(g, -42)
            coro_g.bind(thunk_g)
            try:
                coro_g.switch()
            except ValueError:
                res += 500
            return res

        data = self.wrap_stackless_function(f)
        assert data == 4711

    def test_tree_compare(self):
        class Node:
            def __init__(self, value, left=None, right=None):
                self.value = value
                self.left = left
                self.right = right
            def __repr__(self):
                return 'Node(%r, %r, %r)'%(self.value, self.left, self.right)

        tree1 = Node(1, Node(2, Node(3)))
        tree2 = Node(1, Node(3, Node(2)))
        tree3 = Node(1, Node(2), Node(3))

        class Producer(AbstractThunk):
            def __init__(self, tree, objects, consumer):
                self.tree = tree
                self.objects = objects
                self.consumer = consumer
            def produce(self, t):
                if t is None:
                    return
                self.objects.append(t.value)
                self.consumer.switch()
                self.produce(t.left)
                self.produce(t.right)
            def call(self):
                self.produce(self.tree)
                while 1:
                    self.consumer.switch()
        class Consumer(AbstractThunk):
            def __init__(self, tree, objects, producer):
                self.tree = tree
                self.objects = objects
                self.producer = producer
            def consume(self, t):
                if t is None:
                    return True
                self.producer.switch()
                if not self.objects:
                    return False
                if self.objects.pop(0) != t.value:
                    return False
                if not self.consume(t.left):
                    return False
                return self.consume(t.right)

            def call(self):
                self.result = self.consume(self.tree)
                Coroutine.getmain().switch()

        def pre_order_eq(t1, t2):
            objects = []
            producer = self.Coroutine()
            consumer = self.Coroutine()

            producer.bind(Producer(t1, objects, consumer))
            cons = Consumer(t2, objects, producer)
            consumer.bind(cons)

            consumer.switch()

            return cons.result

        def ep():
            return int("%d%d%d%d"%(pre_order_eq(tree1, tree2),
                                   pre_order_eq(tree1, tree1),
                                   pre_order_eq(tree1, tree3),
                                   pre_order_eq(tree2, tree1),
                                   ))

        output = self.wrap_stackless_function(ep)
        assert output == int('0110')

class TestCoroutineOnCPython(TestCoroutine):
    def wrap_stackless_function(self, func):
        return func()

