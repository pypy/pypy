import py

class GenericTestThread:

    def setup_class(cls):
        space = cls.space
        if "thread" not in space.options.usemodules:
            py.test.skip("--usemodules=thread option not provided")

        cls.w_waitfor = space.appexec([], """():
            import time
            def waitfor(expr, timeout=10.0):
                limit = time.time() + timeout
                while time.time() <= limit:
                    time.sleep(0.005)
                    if expr():
                        return
                print '*** timed out ***'
            return waitfor
        """)
        cls.w_busywait = space.appexec([], """():
            import time
            def busywait(t):
                limit = time.time() + t
                while time.time() <= limit:
                    time.sleep(0.005)
            return busywait
        """)
