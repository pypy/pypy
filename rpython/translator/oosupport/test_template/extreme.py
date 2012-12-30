import sys, py

class BaseTestExtreme:

    def test_memoryerror_due_to_oom(self):
        def relentless_memory_consumption_machine():
            lst = []
            while True: lst.append([])
            
        def fn():
            try:
                relentless_memory_consumption_machine()
            except MemoryError:
                return "OK"
            return "How much memory do you HAVE??"
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

