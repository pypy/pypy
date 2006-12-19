# encoding: utf-8

from copy import copy
from pypy.lang.js.jsobj import w_Undefined, Property
from pypy.lang.js.reference import Reference


class ExecutionContext(object):
    def __init__(self):
        self.scope = []
        self.this = None
        self.variable = None
        self.property = Property('',w_Undefined) #Attribute flags for new vars
    
    def push_object(self, obj):
        """push object into scope stack"""
        self.scope.insert(0, obj)
    
    def pop_object(self):
        """docstring for pop_object"""
        return self.scope.pop(0)
        
    def resolve_identifier(self, identifier):
        for obj in self.scope:
            if obj.HasProperty(identifier):
                return Reference(property_name, obj)
        
        return Reference(property_name)
    

def global_context(global):
    ctx = ExecutionContext()
    ctx.push_object(global)
    ctx.this = global
    ctx.variable = global
    ctx.property = Property('', w_Undefined, DontDelete=True)
    return ctx

def eval_context(calling_context):
    ctx = ExecutionContext()
    ctx.scope = copy(calling_context.scope)
    ctx.this = calling_context.this
    ctx.variable = calling_context.variable
    ctx.property = Property('', w_Undefined)
    return ctx
