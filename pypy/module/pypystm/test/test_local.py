from pypy.module.thread.test import test_local


class AppTestSTMLocal(test_local.AppTestLocal):
    spaceconfig = test_local.AppTestLocal.spaceconfig.copy()
    spaceconfig['usemodules'] += ('pypystm',)

    def setup_class(cls):
        test_local.AppTestLocal.setup_class.im_func(cls)
        cls.w__local = cls.space.appexec([], """():
            import pypystm
            return pypystm.local
        """)


def test_direct_call_to_become_inevitable():
    # this test directly checks if we call rstm.become_inevitable() in the
    # right places (before modifying the real threadlocal). Could possibly be
    # tested in a better way...
    from pypy.module.pypystm.threadlocals import STMThreadLocals
    from rpython.rlib import rstm
    from pypy.interpreter.executioncontext import ExecutionContext

    class FakeEC(ExecutionContext):
        def __init__(self): pass
    class FakeConfig:
        class translation:
            rweakref = False
    class FakeSpace:
        config = FakeConfig()
        def createexecutioncontext(self):
            return FakeEC()
    call_counter = [0]
    def fake_become_inevitable():
        call_counter[0] += 1
    rstm.become_inevitable = fake_become_inevitable

    space = FakeSpace()

    l = STMThreadLocals(space)
    assert call_counter[0] == 0
    l.try_enter_thread(space)
    assert call_counter[0] == 1
    l.enter_thread(space)
    assert call_counter[0] == 2
    l.leave_thread(space)
    assert call_counter[0] == 3
