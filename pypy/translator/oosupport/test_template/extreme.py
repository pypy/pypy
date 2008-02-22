import sys, py

class BaseTestExtreme:

    def test_memoryerror_due_to_oom(self):
        py.test.skip("can't get MemoryError except block to show up")
        def fn():
            try:
                lst = []
                for i in range(sys.maxint): lst.append(i)
            except MemoryError:
                return "OK"
        assert self.interpret(fn, []) == "OK"
        
    def test_runtimeerror_due_to_stack_overflow(self):
        def loop():
            loop()
        def fn():
            try:
                loop()
            except RuntimeError, e:
                return "OK"
        assert self.interpret(fn, []) == "OK"

