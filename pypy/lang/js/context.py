
class ExecutionContext(object):
    
    def __init__(self, parent = None):
        self.parent = parent
        self.locals = {}
        if parent is None:
            self.globals = {}
        else:
            self.globals = parent.globals
        #self.locals = {}

    def assign(self, name, value):
        self.locals[name] = value
        #self.globals[name] = value

    def access(self, name):
        if name in self.locals:
            return self.locals[name]
        elif name in self.globals:
            return self.globals[name]
        raise NameError("%s is not declared" % name)
