
class W_Object:
    def __init__(self, w_class):
        self.w_class = w_class

class W_Class(W_Object):
    def __init__(self, w_class, w_superclass):
        W_Object.__init__(self, w_class)
        self.w_superclass = w_superclass
        self.methoddict = {}

    def new(self):
        return W_Object(self)
