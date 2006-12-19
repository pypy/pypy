# encoding: utf-8

class Reference(object):
    """Reference Type"""
    def __init__(self, propertyname, baseobject=None):
        self.baseobject = baseobject
        self.propertyname = propertyname
        
    def GetValue(self):
        if self.baseobject is None:
            raise ReferenceError
        return self.baseobject.Get(self.propertyname)

    def PutValue(self, w, ctx):
        base = self.baseobject
        if self.baseobject is None:
            base = ctx.scope[-1]
        base.Put(self.propertyname, w)