from pypy.jit.tl.spli import interpreter, objects, pycode


def run_from_cpython_code(co, args=[], locs=None, globs=None):
    space = objects.DumbObjSpace()
    pyco = pycode.Code._from_code(space, co)
    return run(pyco, [space.wrap(arg) for arg in args], locs, globs)

def run(pyco, args, locs=None, globs=None):
    frame = interpreter.SPLIFrame(pyco, locs, globs)
    frame.set_args(args)
    return get_ec().execute_frame(frame)


def get_ec():
    ec = state.get()
    if ec is None:
        ec = ExecutionContext()
        state.set(ec)
    return ec


class State(object):

    def __init__(self):
        self.value = None

    def get(self):
        return self.value

    def set(self, new):
        self.value = new

state = State()


class ExecutionContext(object):

    def __init__(self):
        self.framestack = []

    def execute_frame(self, frame):
        self.framestack.append(frame)
        try:
            return frame.run()
        finally:
            self.framestack.pop()
