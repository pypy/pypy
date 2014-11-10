from pypy.module.thread.test import test_local


class AppTestSTMLocal(test_local.AppTestLocal):
    spaceconfig = test_local.AppTestLocal.spaceconfig.copy()
    spaceconfig['usemodules'] += ('_stm',)

    def setup_class(cls):
        test_local.AppTestLocal.setup_class.im_func(cls)
        cls.w__local = cls.space.appexec([], """():
            import _stm
            return _stm.local
        """)
