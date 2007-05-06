# encoding: utf-8
from pypy.rlib.rarithmetic import r_uint, intmask


class SeePage(NotImplementedError):
    pass

class JsBaseExcept(Exception): pass

class ExecutionReturned(JsBaseExcept):
    def __init__(self, type='normal', value=None, identifier=None):
        self.type = type
        self.value = value
        self.identifier = identifier

class ThrowException(JsBaseExcept):
    def __init__(self, exception):
        self.exception = exception
        self.args = [exception]

class JsTypeError(JsBaseExcept):
    pass

class RangeError(JsBaseExcept): pass

Infinity = 1e300 * 1e300
NaN = Infinity/Infinity

class Property(object):
    def __init__(self, name, value, dd=False, 
                 ro=False, de=False, it=False):
        self.name = name
        self.value = value
        self.dd = dd
        self.ro = ro
        self.de = de
        self.it = it
    
    def __repr__(self):
        return "|%s %d%d%d|"%(self.value, self.dd,
                              self.ro, self.de)

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
    
    def ToInt32(self):
        return 0
    
    def ToUInt32(self):
        return r_uint(0)
    
    def Get(self, P):
        raise NotImplementedError
    
    def Put(self, P, V, dd=False,
            ro=False, de=False, it=False):
        raise NotImplementedError
    
    def PutValue(self, w, ctx):
        pass
    
    def Call(self, ctx, args=[], this=None):
        raise NotImplementedError

    def __str__(self):
        return self.ToString()
    
    def type(self):
        raise NotImplementedError
    
    def delete(self):
        raise NotImplementedError

class W_Undefined(W_Root):
    def __str__(self):
        return "w_undefined"
    
    def ToNumber(self):
        return NaN

    def ToBoolean(self):
        return False
    
    def ToString(self):
        return "undefined"
    
    def type(self):
        return 'undefined'

class W_Null(W_Root):
    def __str__(self):
        return "null"

    def ToBoolean(self):
        return False

    def type(self):
        return 'null'

w_Undefined = W_Undefined()
w_Null = W_Null()


class W_Primitive(W_Root):
    """unifying parent for primitives"""
    def ToPrimitive(self, ctx, hint=""):
        return self

class W_PrimitiveObject(W_Root):
    def __init__(self, ctx=None, Prototype=None, Class='Object',
                 Value=w_Undefined, callfunc=None):
        self.propdict = {}
        self.propdict['prototype'] = Property('prototype', w_Undefined,
                                              dd=True, de=True)
        self.Prototype = Prototype
        self.Class = Class
        self.callfunc = callfunc
        if callfunc is not None:
            self.Scope = ctx.scope[:] 
        else:
            self.Scope = None
        self.Value = Value

    def Call(self, ctx, args=[], this=None):
        act = ActivationObject()
        for i in range(len(self.callfunc.params)):
            arg = self.callfunc.params[i]
            try:
                value = args[i]
            except IndexError:
                value = w_Undefined
            act.Put(self.callfunc.params[i], value)
        act.Put('this', this)
        w_Arguments = W_Arguments(self, args)
        act.Put('arguments', w_Arguments)
        newctx = function_context(self.Scope, act, this)
        val = self.callfunc.body.execute(ctx=newctx)
        return val
    
    def Construct(self, ctx, args=[]):
        obj = W_Object(Class='Object')
        prot = self.Get('prototype')
        if isinstance(prot, W_PrimitiveObject):
            obj.Prototype = prot
        else:
            obj.Prototype = ctx.get_global().Get('Object')

        try: #this is a hack to be compatible to spidermonkey
            self.Call(ctx, args, this=obj)
            return obj
        except ExecutionReturned, e:
            return e.value
        
        
    def Get(self, P):
        if P in self.propdict: return self.propdict[P].value
        if self.Prototype is None: return w_Undefined
        return self.Prototype.Get(P) # go down the prototype chain
    
    def CanPut(self, P):
        if P in self.propdict:
            if self.propdict[P].ro: return False
            return True
        if self.Prototype is None: return True
        return self.Prototype.CanPut(P)

    def Put(self, P, V, dd=False,
            ro=False, de=False, it=False):
        if not self.CanPut(P):
            return
        if P in self.propdict:
            self.propdict[P].value = V
        else:
            self.propdict[P] = Property(P, V,
            dd = dd, ro = ro, it = it)
    
    def HasProperty(self, P):
        if P in self.propdict: return True
        if self.Prototype is None: return False
        return self.Prototype.HasProperty(P) 
    
    def Delete(self, P):
        if P in self.propdict:
            if self.propdict[P].dd: return False
            del self.propdict[P]
            return True
        return True

    def internal_def_value(self, ctx, tryone, trytwo):
        t1 = self.Get(tryone)
        if isinstance(t1, W_PrimitiveObject):
            val = t1.Call(ctx, this=self)
            if isinstance(val, W_Primitive):
                return val
        t2 = self.Get(trytwo)
        if isinstance(t2, W_PrimitiveObject):
            val = t2.Call(ctx, this=self)
            if isinstance(val, W_Primitive):
                return val
        raise JsTypeError

    def DefaultValue(self, ctx, hint=""):
        if hint == "String":
            return self.internal_def_value(ctx, "toString", "valueOf")
        else: #suppose hint is "Number" dunno what to do otherwise
            return self.internal_def_value(ctx, "valueOf", "toString")
    
    ToPrimitive = DefaultValue

    def ToString(self):
        return "[object %s]"%(self.Class,)
    
    def __str__(self):
        return "<Object class: %s>" % self.Class

    def type(self):
        if self.callfunc is not None:
            return 'function'
        else:
            return 'object'
    
def str_builtin(ctx, args, this):
    return W_String(this.ToString())

class W_Object(W_PrimitiveObject):
    def __init__(self, ctx=None, Prototype=None, Class='Object',
                 Value=w_Undefined, callfunc=None):
        W_PrimitiveObject.__init__(self, ctx, Prototype,
                                   Class, Value, callfunc)
        self.propdict['toString'] = Property('toString', W_Builtin(str_builtin), de=True)


class W_Builtin(W_PrimitiveObject):
    def __init__(self, builtin=None, ctx=None, Prototype=None, Class='function',
                 Value=w_Undefined, callfunc=None):
        W_PrimitiveObject.__init__(self, ctx, Prototype,
                                   Class, Value, callfunc)
        self.set_builtin_call(builtin)
        
    def set_builtin_call(self, callfuncbi):
        self.callfuncbi = callfuncbi

    def Call(self, ctx, args=[], this = None):
        return self.callfuncbi(ctx, args, this)
        
    def type(self):
        return 'builtin'
    
class W_Arguments(W_PrimitiveObject):
    def __init__(self, callee, args):
        W_PrimitiveObject.__init__(self, Class='Arguments')
        del self.propdict["prototype"]
        self.Put('callee', callee)
        self.Put('length', W_Number(len(args)))
        for i in range(len(args)):
            self.Put(str(i), args[i])

class ActivationObject(W_PrimitiveObject):
    """The object used on function calls to hold arguments and this"""
    def __init__(self):
        W_PrimitiveObject.__init__(self, Class='Activation')
        del self.propdict["prototype"]

    def __repr__(self):
        return str(self.propdict)
        
def arraycallbi(ctx, args, this):
    return W_Array()
    
class W_Array(W_Builtin):
    def __init__(self, ctx=None, Prototype=None, Class='Array',
                 Value=w_Undefined, callfunc=None):
        W_PrimitiveObject.__init__(self, ctx, Prototype, Class, Value, callfunc)
        toString = W_Builtin(array_str_builtin)
        self.Put('toString', toString, de=True)
        self.Put('length', W_Number(0))
        self.length = r_uint(0)
        self.set_builtin_call(arraycallbi)

    def Construct(self, ctx, args=[]):
        return self

    def Put(self, P, V, dd=False,
            ro=False, de=False, it=False):
        
        if not self.CanPut(P): return
        if P in self.propdict:
            if P == 'length':
                try:
                    res = V.ToUInt32()
                    if V.ToNumber() < 0:
                        raise RangeError()
                    self.propdict['length'].value = W_Number(res)
                    self.length = res
                    return
                except ValueError:
                    raise RangeError('invalid array length')
            else:
                self.propdict[P].value = V
        else:
            self.propdict[P] = Property(P, V,
            dd = dd, ro = ro, it = it)

        try:
            index = r_uint(float(P))
        except ValueError:
            return
        if index < self.length:
            return
        self.length = index+1
        self.propdict['length'].value = W_Number(index+1)
        return
    
    def ToString(self):
        return ','.join([self.Get(str(index)).ToString() for index in range(self.length)])

def array_str_builtin(ctx, args, this):
    return W_String(this.ToString())



class W_Boolean(W_Primitive):
    def __init__(self, boolval):
        self.boolval = bool(boolval)

    def ToString(self):
        if self.boolval == True:
            return "true"
        return "false"
    
    def ToNumber(self):
        if self.boolval:
            return 1.0
        return 0.0
    
    def ToBoolean(self):
        return self.boolval

    def type(self):
        return 'boolean'
        
    def __repr__(self):
        return "<W_Bool "+str(self.boolval)+" >"

class W_String(W_Primitive):
    def __init__(self, strval):
        self.strval = strval

    def __str__(self):
        return self.strval+"W"

    def ToString(self):
        return self.strval
    
    def ToBoolean(self):
        return bool(self.strval)

    def type(self):
        return 'string'


class W_Number(W_Primitive):
    def __init__(self, floatval):
        self.floatval = float(floatval)

    def __str__(self):
        return str(self.floatval)+"W"
        
    def ToString(self):
        if str(self.floatval) == str(NaN):
            return 'NaN'
        try:
            if float(int(self.floatval)) == self.floatval:
                return str(int(self.floatval))
        except OverflowError, e:
            pass
        return str(self.floatval)
    
    def ToBoolean(self):
        if self.floatval == 0.0 or str(self.floatval) == str(NaN):
            return False
        return bool(self.floatval)

    def ToNumber(self):
        return self.floatval
    
    def Get(self, name):
        return w_Undefined

    def type(self):
        return 'number'
    
    def ToInt32(self):
        strval = str(self.floatval)
        if strval == str(NaN) or \
           strval == str(Infinity) or \
           strval == str(-Infinity):
            return 0
           
        return int(self.floatval)
    
    def ToUInt32(self):
        strval = str(self.floatval)
        if strval == str(NaN) or \
           strval == str(Infinity) or \
           strval == str(-Infinity):
            return r_uint(0)
           
        return r_uint(self.floatval)
    
class W_List(W_Root):
    def __init__(self, list_w):
        self.list_w = list_w

    def ToString(self):
        raise SeePage(42)

    def ToBoolean(self):
        return bool(self.list_w)
    
    def get_args(self):
        return self.list_w
    
    def __str__(self):
        return str(self.list_w)

class ExecutionContext(object):
    def __init__(self):
        self.scope = []
        self.this = None
        self.variable = None
        self.debug = False
        self.property = Property('',w_Undefined) #Attribute flags for new vars
    
    def __str__(self):
        return "<ExCtx %s>"%(str(self.scope))
        
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
        """remove the last pushed object"""
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
    ctx.property = Property('', w_Undefined, dd=True)
    return ctx

def function_context(scope, activation, this=None):
    ctx = ExecutionContext()
    ctx.scope = scope[:]
    ctx.push_object(activation)
    if this is None:
        ctx.this = ctx.get_global()
    else:
        ctx.this = this
    ctx.property = Property('', w_Undefined, dd=True)
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
        return w

    def GetBase(self):
        return self.base

    def GetPropertyName(self):
        return self.property_name

    def __str__(self):
        return "<" + str(self.base) + " -> " + str(self.property_name) + ">"
    
