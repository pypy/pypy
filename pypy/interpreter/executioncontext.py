import sys

class ExecutionContext:

    def __init__(self, space):
        self.space = space
        self.framestack = []

    def eval_frame(self, frame):
        __executioncontext__ = self
        self.framestack.append(frame)
        try:
            result = frame.eval(self)
        finally:
            self.framestack.pop()
        return result

    def get_w_builtins(self):
        if self.framestack:
            return self.framestack[-1].w_builtins
        else:
            return self.space.w_builtins

    def make_standard_w_globals(self):
        "Create a new empty 'globals' dictionary."
        w_key = self.space.wrap("__builtins__")
        w_value = self.get_w_builtins()
        w_globals = self.space.newdict([(w_key, w_value)])
        return w_globals

    def exception_trace(self, operationerr):
        "Trace function called upon OperationError."
        operationerr.nicetraceback(self.space)
