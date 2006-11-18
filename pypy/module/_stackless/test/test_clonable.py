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
        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
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
''' in mod.__dict__
        finally:
            del sys.modules['mod']
