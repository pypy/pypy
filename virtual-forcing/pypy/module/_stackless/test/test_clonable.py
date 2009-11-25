import py; py.test.skip("clonable coroutines not really maintained any more")

from pypy.conftest import gettestobjspace, option
import py, sys

# app-level testing of coroutine cloning

class AppTestClonable:

    def setup_class(cls):
        if not option.runappdirect:
            py.test.skip('pure appdirect test (run with -A)')
        cls.space = space = gettestobjspace(usemodules=('_stackless',))
        if not space.is_true(space.appexec([], """():
            import _stackless
            return hasattr(_stackless, 'clonable')
        """)):
            py.test.skip('no _stackless.clonable')


    def test_solver(self):
        import _stackless

        class Fail(Exception):
            pass

        class Success(Exception):
            pass

        def first_solution(func):
            global next_answer
            co = _stackless.clonable()
            co.bind(func)
            pending = [(co, None)]
            while pending:
                co, next_answer = pending.pop()
                try:
                    co.switch()
                except Fail:
                    pass
                except Success, e:
                    return e.args[0]
                else:
                    # zero_or_one() called, clone the coroutine
                    co2 = co.clone()
                    pending.append((co2, 1))
                    pending.append((co, 0))
            raise Fail("no solution")

        pending = []
        main = _stackless.clonable.getcurrent()

        def zero_or_one():
            main.switch()
            return next_answer

        # ____________________________________________________________

        invalid_prefixes = {
            (0, 0): True,
            (0, 1, 0): True,
            (0, 1, 1): True,
            (1, 0): True,
            (1, 1, 0, 0): True,
            }

        def example():
            test = []
            for n in range(5):
                test.append(zero_or_one())
                if tuple(test) in invalid_prefixes:
                    raise Fail
            raise Success(test)

        res = first_solution(example)
        assert res == [1, 1, 0, 1, 0]


    def test_myself_may_not_be_me_any_more(self):
        import gc
        from _stackless import clonable

        counter = [0]

        def runner():
            while 1:
                assert clonable.getcurrent() is coro
                counter[0] += 1
                main.switch()

        main = clonable.getcurrent()
        coro = clonable()
        coro.bind(runner)

        coro.switch()
        assert counter == [1]

        assert clonable.getcurrent() is main
        coro1 = coro.clone()
        assert counter == [1]
        assert clonable.getcurrent() is main
        coro.switch()
        assert counter == [2]
        coro.switch()
        assert counter == [3]
        assert clonable.getcurrent() is main
        del coro1
        gc.collect()
        #print "collected!"
        assert clonable.getcurrent() is main
        assert counter == [3]
        coro.switch()
        assert clonable.getcurrent() is main
        assert counter == [4]


    def test_fork(self):
        import _stackless

        class Fail(Exception):
            pass

        class Success(Exception):
            pass

        def first_solution(func):
            global next_answer
            co = _stackless.clonable()
            co.bind(func)
            try:
                co.switch()
            except Success, e:
                return e.args[0]

        def zero_or_one():
            sub = _stackless.fork()
            if sub is not None:
                # in the parent: run the child first
                try:
                    sub.switch()
                except Fail:
                    pass
                # then proceed with answer '1'
                return 1
            else:
                # in the child: answer '0'
                return 0

        # ____________________________________________________________

        invalid_prefixes = {
            (0, 0): True,
            (0, 1, 0): True,
            (0, 1, 1): True,
            (1, 0): True,
            (1, 1, 0, 0): True,
            }

        def example():
            test = []
            for n in range(5):
                test.append(zero_or_one())
                if tuple(test) in invalid_prefixes:
                    raise Fail
            raise Success(test)

        res = first_solution(example)
        assert res == [1, 1, 0, 1, 0]

    def test_clone_before_start(self):
        """Tests that a clonable coroutine can be
        cloned before it is started
        (this used to fail with a segmentation fault)
        """
        import _stackless

        counter = [0]
        def simple_coro():
            print "hello"
            counter[0] += 1

        s = _stackless.clonable()
        s.bind(simple_coro)
        t = s.clone()
        s.switch()
        t.switch()
        assert counter[0] == 2
