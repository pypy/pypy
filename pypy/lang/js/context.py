
class ExecutionContext(object):
    def __init__(self):
        self.scope = []
        self.this = None
        self.variable = None
        self.property = Property('',w_Undefined) #Attribute flags for new vars

    def get_identifier(self, identifier):
        """docstring for get_identifier"""
        pass




class GlobalContext(ExecutionContext):
    """docstring for GlobalContext"""
    def __init__(self, global):
        ExecutionContext.__init__()
        self.scope.append(global)
        self.this = global
        self.variable = global
        


