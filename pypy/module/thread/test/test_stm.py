from pypy.module.thread.test import test_local


class AppTestSTMLocal(test_local.AppTestLocal):

    def setup_class(cls):
        test_local.AppTestLocal.setup_class.im_func(cls)
        cls.w__local = cls.space.appexec([], """():
            import thread
            return thread._untranslated_stmlocal
        """)
