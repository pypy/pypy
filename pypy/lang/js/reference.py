#!/usr/bin/env python
# encoding: utf-8
"""
reference.py

Created by Leonardo Santagada on 2006-12-16.
"""

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

def put_value(v, w):
    if not type(v, Reference):
        raise ReferenceError
    base = v.baseobject
    if v.baseobject is None:
        base = get_global() #gets the global object of js
    base.put(v.propertyname, w)