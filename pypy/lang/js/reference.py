# encoding: utf-8

class Reference(object):
    """Reference Type"""
    def __init__(self, property_name, base=None):
        self.base = base
        self.property_name = property_name
        
    def GetValue(self):
        if self.base is None:
            raise ReferenceError
        return self.base.Get(self.property_name)

    def PutValue(self, w, ctx):
        base = self.base
        if self.base is None:
            base = ctx.scope[-1]
        base.Put(self.property_name, w)
    
    def GetBase(self):
        return self.base
    
    def GetPropertyName(self):
        return self.property_name
        
    def __str__(self):
        return "< " + str(self.base) + " -> " + str(self.property_name) + " >"