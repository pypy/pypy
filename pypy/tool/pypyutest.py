from std.__impl__.magic import exprinfo
from pypy.objspace.std import StdObjSpace

class AppRunnerFrame:

    def __init__(self, space, w_globals, w_locals):
        self.space = space
        self.w_globals = w_globals
        self.w_locals = w_locals

    def eval(self, code, **vars):
        space = self.space
        for key, w_value in vars.items():
            space.setitem(self.w_locals, space.wrap(key), w_value)
        return space.eval(code, self.w_globals, self.w_locals)

    def exec_(self, code, **vars):
        space = self.space
        for key, w_value in vars.items():
            space.setitem(self.w_locals, space.wrap(key), w_value)
        space.exec_(code, self.w_globals, self.w_locals)

    def repr(self, w_value):
        return self.space.unwrap(self.space.repr(w_value))

    def is_true(self, w_value):
        return self.space.is_true(w_value)


def test():
    space = StdObjSpace()
    w_glob = space.newdict([])
    w_loc = space.newdict([])
    runner = AppRunnerFrame(space, w_glob, w_loc)
    exprinfo.run("f = lambda x: x+1", runner)
    exprinfo.check("isinstance(f(2), float)", runner)

if __name__ == '__main__':
    test()
