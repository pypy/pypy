# encoding: utf-8


class SeePage(NotImplementedError):
    pass

class ExecutionReturned(Exception):
    def __init__(self, value):
        self.value = value

class ThrowException(Exception):
    def __init__(self, exception):
        self.exception = exception
        self.args = self.exception

class JsTypeError(Exception):
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
    
    def __repr__(self):
        return "|%s %d%d%d|"%(self.value, self.DontDelete, self.ReadOnly, self.DontEnum)

def internal_property(name, value):
    """return a internal property with the right attributes"""
    return Property(name, value, True, True, True, True)

class W_Root(object):
    def GetValue(self):
        return self

    def ToBoolean(self):
        return False

    def ToPrimitive(self, ctx, hint=""):
        return self

    def ToString(self):
        return ''
    
    def ToObject(self):
        return self

    def ToNumber(self):
        return NaN
    
    def Get(self, P):
        raise NotImplementedError
    
    def Put(self, P, V, DontDelete=False, ReadOnly=False, DontEnum=False, Internal=False):
        raise NotImplementedError
    
    def PutValue(self, w, ctx):
        raise NotImplementedError
    
    def Call(self, ctx, args=[], this=None):
        raise NotImplementedError

    def __str__(self):
        return self.ToString()
        
    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, self.ToString())

class W_Primitive(W_Root):
    """unifying parent for primitives"""
    def ToPrimitive(self, ctx, PreferredType):
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
        if not self.CanPut(P):
            return
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
            del self.propdict[P]
            return True
        return True

    def internal_def_value(self, ctx, tryone, trytwo):
        t1 = self.Get(tryone)
        if isinstance(t1, W_Object):
            val = t1.Call(ctx, this=self)
            if isinstance(val, W_Primitive):
                return val
        t2 = self.Get(trytwo)
        if isinstance(t2, W_Object):
            val = t2.Call(ctx, this=self)
            if isinstance(val, W_Primitive):
                return val
        raise JsTypeError

    def DefaultValue(self, ctx, hint):
        if hint == "String":
            return self.internal_def_value(ctx, "toString", "valueOf")
        else: #suppose hint is "Number" dunno what to do otherwise
            return self.internal_def_value(ctx, "valueOf", "toString")
    
    ToPrimitive = DefaultValue

    def ToString(self):
        return "[object %s]"%(self.Class,)
    
    def __str__(self):
        return "<Object class: %s>" % self.Class

    
class W_Arguments(W_Object):
    def __init__(self, callee, args):
        W_Object.__init__(self)
        self.Class = "arguments"
        del self.propdict["toString"]
        del self.propdict["prototype"]
        self.Put('callee', callee)
        self.Put('length', W_Number(len(args)))
##        for i, arg in enumerate(args):
##            self.Put(str(i), arg)
        for i in range(len(args)):
            self.Put(str(i), args[i])

class ActivationObject(W_Object):
    """The object used on function calls to hold arguments and this"""
    def __init__(self):
        W_Object.__init__(self)
        self.Class = "Activation"
        del self.propdict["toString"]
        del self.propdict["prototype"]

class W_FunctionObject(W_Object):
    def __init__(self, function, ctx):
        # TODO: See page 80
        W_Object.__init__(self)
        self.function = function
        self.Class = "Function"
        self.Prototype = None # TODO: See page 95 section 15.3.3.1
        self.scope = ctx.scope[:]
    
    def Call(self, ctx, args=[], this=None):
        #print "* start of function call"
        #print " args = ", args
        act = ActivationObject()
        #for i, arg in enumerate(self.function.params):
        for i in range(len(self.function.params)):
            arg = self.function.params[i]
            try:
                value = args[i]
            except IndexError:
                value = w_Undefined
            act.Put(self.function.params[i], value)
        act.Put('this', this)
        #print " act.propdict = ", act.propdict
        w_Arguments = W_Arguments(self, args)
        act.Put('arguments', w_Arguments)
        newctx = function_context(self.scope, act, this)
        val = self.function.body.execute(ctx=newctx)
        #print "* end of function call return = ", val
        return val

class W_Array(W_Object):
    def __init__(self, items):
        W_Object.__init__(self)
        self.Put('length', W_Number(0))
    
    def Put(self, P, V):
        if not self.CanPut(P): return
        if P in self.propdict:
            self.propdict[P].value = V
        else:
            try:
                x = int(P)
            except ValueError:
                x = -1
            # FIXME: Get this working
            # if x > self.Get('length'):
            #     self.propdict['length'].value = W_Number(x)
            self.propdict[P] = Property(P, V)
    
class W_Undefined(W_Root):
    def __str__(self):
        return "w_undefined"
    
    def ToNumber(self):
        return NaN

    def ToBoolean(self):
        return False
    
    def ToString(self):
        return "undefined"

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
    
    def ToBoolean(self):
        return self.boolval
    
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
        #print "w_number = ", floatval
        self.floatval = floatval

    def ToString(self):
        if str(self.floatval) == str(NaN):
            return 'NaN'
        if float(int(self.floatval)) == self.floatval:
            return str(int(self.floatval))
        return str(self.floatval)
    
    def ToBoolean(self):
        if self.floatval == 0.0 or self.floatval == NaN:
            return False
        return bool(self.floatval)

    def ToNumber(self):
        return self.floatval
    
    def Get(self, name):
        return w_Undefined


class W_Builtin(W_Root):
    def __init__(self, builtinfunction):
        #W_Object.__init__(self)
        self.builtinfunction = builtinfunction
    
    def Call(self, ctx, args=[], this = None):
        assert len(args) == 0
        return W_String(self.builtinfunction()) # ???

class W_List(W_Root):
    def __init__(self, list_w):
        self.list_w = list_w

    def ToString(self):
        raise SeePage(42)

    def ToBoolean(self):
        return bool(self.list_w)
    
    def __str__(self):
        return str(self.list_w)

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
                return W_Reference(identifier, obj)
        
        return W_Reference(identifier)
    

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

class W_Reference(W_Root):
    """Reference Type"""
    def __init__(self, property_name, base=None):
        self.base = base
        self.property_name = property_name

    def GetValue(self):
        if self.base is None:
            exception = "ReferenceError: %s is not defined"%(self.property_name,)
            raise ThrowException(W_String(exception))
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
    
