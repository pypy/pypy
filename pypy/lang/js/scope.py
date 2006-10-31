
class Scope(object):
    def __init__(self, parent=None):
        # string --> W_Root
        self.dict_w = {}
        self.parent = parent
    
    def set(self, name, w_obj):
        self.dict_w[name] = w_obj
    
    def get(self, name):
        return self.dict_w[name]

    def has(self, name):
        return name in self.dict_w

class ScopeManager(object):
    def __init__(self):
        self.current_scope = Scope(None)
    
    def enter_scope(self):
        self.current_scope = Scope(self.current_scope)
        return self.current_scope
    
    def leave_scope(self):
        self.current_scope = self.current_scope.parent
    
    def get_variable(self, name, scope=None):
        if scope is None:
            scope = self.current_scope
        while 1:
            try:
                return scope.get(name)
            except KeyError:
                scope = scope.parent
                if scope is None:
                    raise NameError("Name %s not defined" % name)
    
    def set_variable(self, name, w_value, scope=None):
        if scope is None:
            scope = self.current_scope
        while 1:
            if scope.has(name):
                scope.set(name, w_value)
                return
            if scope.parent is None:
                scope.set(name, w_value)
                return
            scope = scope.parent

    def add_variable(self, name, w_value, scope=None):
        if scope is None:
            scope = self.current_scope
        scope.set(name, w_value)

scope_manager = ScopeManager()
