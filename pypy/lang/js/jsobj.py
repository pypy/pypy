# encoding: utf-8

from pypy.lang.js.reference import Reference

class SeePage(NotImplementedError):
    pass

INFDEF = 1e300 * 1e300
NaN    = INFDEF/INFDEF

class Property(object):
    def __init__(self, name, value, DontDelete=False, 
                 ReadOnly=False, DontEnum=False, Internal=False):
        self.name = name
        self.value = value
        self.DontDelete = DontDelete
        self.ReadOnly = ReadOnly
        self.DontEnum = DontEnum
        self.Internal = Internal

def internal_property(name, value):
    """return a internal property with the right attributes"""
    return Property(name, value, True, True, True, True)

class W_Root(object):
    def GetValue(self):
        return self

    def ToBoolean(self):
        return False

    def ToPrimitive(self, hint=""):
        return self

    def ToString(self):
        return ''
    
    def ToObject(self):
        return self

    def ToNumber(self):
        return NaN
    
    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, self.ToString())

class W_Primitive(W_Root):
    """unifying parent for primitives"""
    def ToPrimitive(self, PreferredType):
        return self

class W_Object(W_Root):
    def __init__(self):
        self.propdict = {}
        self.propdict['toString'] = Property('toString', 
                                             W_Builtin(self.__str__))
        self.propdict['prototype'] = Property('prototype', w_Undefined,
                                              DontDelete=True)
        self.Prototype = None
        self.Class = "Object"
        self.scope = []
    
    def Call(self, ctx, args=[], this = None):
        return W_Object()
    
    def Get(self, P):
        if P in self.propdict: return self.propdict[P].value
        if self.Prototype is None: return w_Undefined
        return self.Prototype.Get(P) # go down the prototype chain
    
    def CanPut(self, P):
        if P in self.propdict:
            if self.propdict[P].ReadOnly: return False
            return True
        if self.Prototype is None: return True
        return self.Prototype.CanPut(P)
    
    def Put(self, P, V):
        if not self.CanPut(P): return
        if P in self.propdict:
            self.propdict[P].value = V
        else:
            self.propdict[P] = Property(P, V)
    
    def HasProperty(self, P):
        if P in self.propdict: return True
        if self.Prototype is None: return False
        return self.Prototype.HasProperty(P) 
    
    def Delete(P):
        if P in self.propdict:
            if self.propdict[P].DontDelete: return False
            self.propdict.pop(P)
            return True
        return True
    
    def DefaultValue(self, hint):
        def internal_def_value(tryone, trytwo):
            t1 = self.Get(tryone)
            if isinstance(t1, W_Object):
                val = t1.Call(this=self)
                if isinstance(val, W_Primitive):
                    return val
            t2 = self.Get(trytwo)
            if isinstance(t2, W_Object):
                val = t2.Call(this=self)
                if isinstance(val, W_Primitive):
                    return val
            raise jsTypeError
        
        if hint == "String":
            internal_def_value("toString", "valueOf")
        else: #suppose hint is "Number" dunno what to do otherwise
            internal_def_value("valueOf", "toString")
    
    ToPrimitive = DefaultValue

    def ToString(self):
        return "[object %s]"%(self.Class,)
    
class W_Arguments(W_Object):
    def __init__(self, callee, args):
        W_Object.__init__(self)
        self.Put('callee', callee)
        self.Put('length', len(args))
        for i, arg in enumerate(args):
            self.Put(str(i), arg)

class ActivationObject(W_Object):
    """The object used on function calls to hold arguments and this"""
    def __init__(self):
        W_Object.__init__(self)
        self.propdict.pop("toString")
        self.propdict.pop("prototype")

class W_FunctionObject(W_Object):
    def __init__(self, function, ctx):
        # TODO: See page 80
        W_Object.__init__(self)
        self.function = function
        self.Class = "Function"
        self.Prototype = None # TODO: See page 95 section 15.3.3.1
        self.scope = ctx.scope[:]
    
    def Call(self, ctx, args=[], this=None):
        print args
        act = ActivationObject()
        for i, arg in enumerate(args):
            try:
                value = args[i]
            except IndexError:
                value = w_Undefined
            act.Put(self.function.params[i], value)
        act.Put('this', this)
        print act.propdict
        w_Arguments = W_Arguments(self, args)
        act.Put('arguments', w_Arguments)
        newctx = function_context(self.scope, act, this)
        val = self.function.body.call(ctx=newctx)
        return val

class W_Undefined(W_Root):
    def __str__(self):
        return ""
    
    def ToNumber(self):
        # XXX make NaN
        return NaN

    def ToBoolean(self):
        return False

class W_Null(W_Root):
    def __str__(self):
        return "null"

    def ToBoolean(self):
        return False

class W_Boolean(W_Primitive):
    def __init__(self, boolval):
        self.boolval = bool(boolval)

    def ToString(self):
        if self.boolval:
            return "true"
        return "false"
    
    def ToNumber(self):
        if self.boolval:
            return 1.0
        return 0.0
    
class W_String(W_Primitive):
    def __init__(self, strval):
        self.strval = strval

    def __str__(self):
        return self.strval

    def ToString(self):
        return self.strval
    
    def ToBoolean(self):
        return bool(self.strval)


class W_Number(W_Primitive):
    def __init__(self, floatval):
        print "novo numero"
        self.floatval = floatval

    def ToString(self):
        if str(self.floatval) == str(NaN):
            return 'NaN'
        if float(int(self.floatval)) == self.floatval:
            return str(int(self.floatval))
        return str(self.floatval)
    
    def ToBoolean(self):
        return W_Boolean(bool(self.floatval))

    def ToNumber(self):
        return self.floatval
    
    def Get(self, name):
        return w_Undefined


class W_Reference(W_Root):
    def GetValue(self):
        raise NotImplementedError("W_Reference.GetValue")

class W_Builtin(W_Root):
    def __init__(self, builtinfunction):
        #W_Object.__init__(self)
        self.builtinfunction = builtinfunction
    
    def Call(self, context, args=[], this = None):
        return self.builtinfunction(*args)

class W_List(W_Root):
    def __init__(self, list_w):
        self.list_w = list_w

    def ToString(self):
        raise SeePage(42)

    def ToBoolean(self):
        return bool(self.list_w)

w_Undefined = W_Undefined()
w_Null = W_Null()

class ExecutionContext(object):
    def __init__(self):
        self.scope = []
        self.this = None
        self.variable = None
        self.property = Property('',w_Undefined) #Attribute flags for new vars
    
    def assign(self, name, value):
        """
        assign to property name, creating it if it doesn't exist
        """
        pass
        #ref = self.resolve_identifier(name)
        #if ref.
    
    def get_global(self):
        return self.scope[-1]
            
    def push_object(self, obj):
        """push object into scope stack"""
        self.scope.insert(0, obj)
        self.variable = obj
    
    def pop_object(self):
        """docstring for pop_object"""
        return self.scope.pop(0)
        
    def resolve_identifier(self, identifier):
        for obj in self.scope:
            if obj.HasProperty(identifier):
                return Reference(identifier, obj)
        
        return Reference(identifier)
    

def global_context(w_global):
    ctx = ExecutionContext()
    ctx.push_object(w_global)
    ctx.this = w_global
    ctx.property = Property('', w_Undefined, DontDelete=True)
    return ctx

def function_context(scope, activation, this=None):
    ctx = ExecutionContext()
    ctx.scope = scope
    ctx.push_object(activation)
    if this is None:
        ctx.this = ctx.get_global()
    else:
        ctx.this = this
    
    ctx.property = Property('', w_Undefined, DontDelete=True)
    return ctx
    
def eval_context(calling_context):
    ctx = ExecutionContext()
    ctx.scope = calling_context.scope[:]
    ctx.this = calling_context.this
    ctx.variable = calling_context.variable
    ctx.property = Property('', w_Undefined)
    return ctx

        