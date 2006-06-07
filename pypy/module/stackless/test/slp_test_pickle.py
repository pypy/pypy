# app-level testing of coroutine pickling
import stackless

class TestPickle:

    def test_simple_ish(self):

        output = []
        def f(coro, n, x):
            if n == 0:
                coro.switch()
                return
            f(coro, n-1, 2*x)
            output.append(x)

        def example():
            main_coro = stackless.coroutine.getcurrent()
            sub_coro = stackless.coroutine()
            sub_coro.bind(f, main_coro, 5, 1)
            sub_coro.switch()

            import pickle
            pckl = pickle.dumps(sub_coro)
            new_coro = pickle.loads(pckl)

            new_coro.switch()

        example()
        assert output == [16, 8, 4, 2, 1]
