
class ExecutionContext(object):
    def __init__(self, parent = None):
        self.parent = parent
        if parent is None:
            self.globals = {}
        else:
            self.globals = parent.globals
        #self.locals = {}

    def assign(self, name, value):
        #if name in self.locals:
        #    self.locals[name] = value
        #else:
        #    if self.parent:
        #        self.parent.assign(name, value)
        #    else:
        self.globals[name] = value

    def access(self, name):
        #if name in self.locals:
        #    return self.locals[name]
        #else:
        #    if self.parent:
        #        return self.parent.access(name)
        #    else:
        if name in self.globals:
            return self.globals[name]
        raise NameError("%s is not declared" % name)
