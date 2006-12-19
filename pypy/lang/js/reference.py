# encoding: utf-8

class Reference(object):
    """Reference Type"""
    def __init__(self, propertyname, baseobject=None):
        self.baseobject = baseobject
        self.propertyname = propertyname
        
def get_value(v):
    if not type(v, Reference):
        return v
    if v.baseobject is None:
        raise ReferenceError
    return v.baseobject.get(v.propertyname)

def put_value(v, w, context):
    if not type(v, Reference):
        raise ReferenceError
    base = v.baseobject
    if v.baseobject is None:
        base = context.scope[-1]
    base.put(v.propertyname, w)