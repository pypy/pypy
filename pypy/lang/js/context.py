
class ExecutionContext(object):
    globals = {}
    
    def __init__(self, parent=None):
        pass
    
##    def __init__(self, parent = None):
##        self.parent = parent
##        if parent is None:
##            self.globals = {}
##        else:
##            self.globals = parent.globals
##        #self.locals = {}

    def assign(self, name, value):
        self.globals[name] = value

    def access(self, name):
        if name in self.globals:
            return self.globals[name]
        raise NameError("%s is not declared" % name)
