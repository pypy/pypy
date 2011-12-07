from pypy.objspace.fake.objspace import FakeObjSpace, W_Root, is_root
from pypy.interpreter import gateway


class ModuleChecker(object):

    def __init__(self):
        self.space = FakeObjSpace()

    def load_module(self, modname):
        space = self.space
        mod = __import__('pypy.module.%s' % modname, None, None, ['__doc__'])
        # force computation and record what we wrap
        del space.seen_wrap[:]
        module = mod.Module(space, W_Root())
        for name in module.loaders:
            module._load_lazily(space, name)
        self.seen = space.seen_wrap[:]

    def collect_entry_points(self):
        self.entry_points = []
        for value in self.seen:
            if isinstance(value, gateway.interp2app):
                self.collect_interp2app(value)

    def collect_interp2app(self, interp2app):
        space = self.space
        activation = interp2app._code.activation
        scopelen = interp2app._code.sig.scope_length()
        scope_w = [W_Root()] * scopelen
        #
        def check():
            w_result = activation._run(space, scope_w)
            is_root(w_result)
        #
        self.entry_points.append(check)

    def check_translates(self):
        def entry_point():
            for fn in entry_points:
                fn()
        entry_points = self.entry_points
        self.space.translates(entry_point)


def checkmodule(modname):
    checker = ModuleChecker()
    checker.load_module(modname)
    checker.collect_entry_points()
    checker.check_translates()
