from pypy.module.transaction import interp_transaction


class FakeSpace:
    def new_exception_class(self, name):
        return "some error class"
    def call_args(self, w_callback, args):
        w_callback(*args)


def test_linear_list():
    space = FakeSpace()
    interp_transaction.state.startup(space)
    seen = []
    #
    def do(n):
        seen.append(n)
        if n < 200:
            interp_transaction.add(space, do, (n+1,))
    #
    interp_transaction.add(space, do, (0,))
    assert seen == []
    interp_transaction.run(space)
    assert seen == range(201)
