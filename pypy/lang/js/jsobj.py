# encoding: utf-8
from pypy.rlib.rarithmetic import r_uint, intmask


class SeePage(NotImplementedError):
    pass

class JsBaseExcept(Exception):
    pass    

#XXX Just an idea for now
class JsRuntimeExcept(Exception):
    def __init__(self, pos, message, exception_object):
        self.pos = pos
        self.message = message
        self.exception_object = exception_object # JS Exception Object

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

    def ToString(self, ctx):
        return ''
    
    def ToObject(self, ctx):
        # XXX should raise not implemented
        return self

    def ToNumber(self):
        return NaN
    
    def ToInt32(self):
        return 0
    
    def ToUInt32(self):
        return r_uint(0)
    
    def Get(self, P):
        print P
        raise NotImplementedError
    
    def Put(self, P, V, dd=False,
            ro=False, de=False, it=False):
        raise NotImplementedError
    
    def PutValue(self, w, ctx):
        pass
    
    def Call(self, ctx, args=[], this=None):
        raise NotImplementedError

    def __str__(self):
        return self.ToString(ctx=None)
    
    def type(self):
        raise NotImplementedError
        
    def GetPropertyName(self):
        raise NotImplementedError

class W_Undefined(W_Root):
    def __str__(self):
        return "w_undefined"
    
    def ToNumber(self):
        return NaN

    def ToBoolean(self):
        return False
    
    def ToString(self, ctx = None):
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
        self.Prototype = Prototype
        if Prototype is None:
            Prototype = w_Undefined
        self.propdict['prototype'] = Property('prototype', Prototype,
                                              dd=True, de=True)
        self.Class = Class
        self.callfunc = callfunc
        if callfunc is not None:
            self.Scope = ctx.scope[:] 
        else:
            self.Scope = None
        self.Value = Value

    def Call(self, ctx, args=[], this=None):
        if self.callfunc is None: # XXX Not sure if I should raise it here
            raise JsTypeError('not a function')
        act = ActivationObject()
        paramn = len(self.callfunc.params)
        for i in range(paramn):
            paramname = self.callfunc.params[i]
            try:
                value = args[i]
            except IndexError:
                value = w_Undefined
            act.Put(paramname, value)
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
        else: # would love to test this
            #but I fail to find a case that falls into this
            obj.Prototype = ctx.get_global().Get('Object').Get('prototype')
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
        else: # hint can only be empty, String or Number
            return self.internal_def_value(ctx, "valueOf", "toString")
    
    ToPrimitive = DefaultValue

    def ToString(self, ctx):
        try:
            res = self.ToPrimitive(ctx, 'String')
        except JsTypeError:
            return "[object %s]"%(self.Class,)
        return res.ToString(ctx)
    
    def __str__(self):
        return "<Object class: %s>" % self.Class

    def type(self):
        if self.callfunc is not None:
            return 'function'
        else:
            return 'object'
    
def str_builtin(ctx, args, this):
    return W_String(this.ToString(ctx))

class W_Object(W_PrimitiveObject):
    def __init__(self, ctx=None, Prototype=None, Class='Object',
                 Value=w_Undefined, callfunc=None):
        W_PrimitiveObject.__init__(self, ctx, Prototype,
                                   Class, Value, callfunc)

class W_NewBuiltin(W_PrimitiveObject):
    def __init__(self, ctx, Prototype=None, Class='function',
                 Value=w_Undefined, callfunc=None):
        if Prototype is None:
            proto = ctx.get_global().Get('Function').Get('prototype')
            Prototype = proto

        W_PrimitiveObject.__init__(self, ctx, Prototype, Class, Value, callfunc)

    def Call(self, ctx, args=[], this = None):
        raise NotImplementedError

    def type(self):
        return 'builtin'

class W_Builtin(W_PrimitiveObject):
    def __init__(self, builtin=None, ctx=None, Prototype=None, Class='function',
                 Value=w_Undefined, callfunc=None):        
        W_PrimitiveObject.__init__(self, ctx, Prototype, Class, Value, callfunc)
        self.set_builtin_call(builtin)
    
    def set_builtin_call(self, callfuncbi):
        self.callfuncbi = callfuncbi

    def Call(self, ctx, args=[], this = None):
        return self.callfuncbi(ctx, args, this)

    def Construct(self, ctx, args=[]):
        return self.callfuncbi(ctx, args, None)
        
    def type(self):
        return 'builtin'

class W_ListObject(W_PrimitiveObject):
    def tolist(self):
        l = []
        for i in range(self.length):
            l.append(self.propdict[str(i)].value)
        return l
        
class W_Arguments(W_ListObject):
    def __init__(self, callee, args):
        W_PrimitiveObject.__init__(self, Class='Arguments')
        del self.propdict["prototype"]
        self.Put('callee', callee)
        self.Put('length', W_Number(len(args)))
        for i in range(len(args)):
            self.Put(str(i), args[i])
        self.length = len(args)

class ActivationObject(W_PrimitiveObject):
    """The object used on function calls to hold arguments and this"""
    def __init__(self):
        W_PrimitiveObject.__init__(self, Class='Activation')
        del self.propdict["prototype"]

    def __repr__(self):
        return str(self.propdict)
    
class W_Array(W_ListObject):
    def __init__(self, ctx=None, Prototype=None, Class='Array',
                 Value=w_Undefined, callfunc=None):
        W_PrimitiveObject.__init__(self, ctx, Prototype, Class, Value, callfunc)
        self.Put('length', W_Number(0))
        self.length = r_uint(0)

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


class W_Boolean(W_Primitive):
    def __init__(self, boolval):
        self.boolval = bool(boolval)
    
    def ToObject(self, ctx):
        return create_object(ctx, 'Boolean', Value=self)

    def ToString(self, ctx=None):
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

    def ToObject(self, ctx):
        return create_object(ctx, 'String', Value=self)

    def ToString(self, ctx=None):
        return self.strval
    
    def ToBoolean(self):
        return bool(self.strval)

    def type(self):
        return 'string'

    def GetPropertyName(self):
        return self.ToString()

class W_Number(W_Primitive):
    def __init__(self, floatval):
        try:
            self.floatval = float(floatval)
        except OverflowError: 
            # XXX this should not be happening, there is an error somewhere else
            #an ecma test to stress this is GlobalObject/15.1.2.2-2.js
            self.floatval = Infinity

    def __str__(self):
        return str(self.floatval)+"W"

    def ToObject(self, ctx):
        return create_object(ctx, 'Number', Value=self)
        
    def ToString(self, ctx = None):
        floatstr = str(self.floatval)
        if floatstr == str(NaN):
            return 'NaN'
        if floatstr == str(Infinity):
            return 'Infinity'
        if floatstr == str(-Infinity):
            return '-Infinity'
        try:
            if float(int(self.floatval)) == self.floatval:
                return str(int(self.floatval))
        except OverflowError, e:
            pass
        return floatstr
    
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
    
    def GetPropertyName(self):
        return self.ToString()
        
class W_List(W_Root):
    def __init__(self, list_w):
        self.list_w = list_w

    def ToString(self, ctx = None):
        raise SeePage(42)

    def ToBoolean(self):
        return bool(self.list_w)
    
    def get_args(self):
        return self.list_w
    
    def __str__(self):
        return str(self.list_w)

class ExecutionContext(object):
    def __init__(self, scope, this=None, variable=None, 
                    debug=False, jsproperty=None):
        assert scope is not None
        self.scope = scope
        if this is None:
            self.this = scope[-1]
        else:
            self.this = this
        
        if variable is None:
            self.variable = self.scope[0]
        else:
            self.variable = variable
        self.debug = debug
        if jsproperty is None:
            #Attribute flags for new vars
            self.property = Property('',w_Undefined)
        else:
            self.property = jsproperty
    
    def __str__(self):
        return "<ExCtx %s, var: %s>"%(self.scope, self.variable)
        
    def assign(self, name, value):
        pass
    
    def get_global(self):
        return self.scope[-1]
            
    def push_object(self, obj):
        """push object into scope stack"""
        assert isinstance(obj, W_PrimitiveObject)
        self.scope.insert(0, obj)
        self.variable = obj
    
    def pop_object(self):
        """remove the last pushed object"""
        return self.scope.pop(0)
        
    def resolve_identifier(self, identifier):
        for obj in self.scope:
            assert isinstance(obj, W_PrimitiveObject)
            if obj.HasProperty(identifier):
                return W_Reference(identifier, obj)
        
        return W_Reference(identifier)
    

def global_context(w_global):
    assert isinstance(w_global, W_PrimitiveObject)
    ctx = ExecutionContext([w_global],
                            this = w_global,
                            variable = w_global,
                            jsproperty = Property('', w_Undefined, dd=True))
    return ctx

def function_context(scope, activation, this=None):
    newscope = scope[:]
    ctx = ExecutionContext(newscope,
                            this = this, 
                            jsproperty = Property('', w_Undefined, dd=True))
    ctx.push_object(activation)
    return ctx
    
def eval_context(calling_context):
    ctx = ExecutionContext(calling_context.scope[:],
                            this = calling_context.this,
                            variable = calling_context.variable,
                            jsproperty = Property('', w_Undefined))
    return ctx

def empty_context():
    obj = W_Object()
    ctx = ExecutionContext([obj],
                            this = obj,
                            variable = obj,
                            jsproperty = Property('', w_Undefined))
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
        if base is None:
            base = ctx.scope[-1]
        base.Put(self.property_name, w)
        return w

    def GetBase(self):
        return self.base

    def GetPropertyName(self):
        return self.property_name

    def __str__(self):
        return "<" + str(self.base) + " -> " + str(self.property_name) + ">"
    
def create_object(ctx, prototypename, callfunc=None, Value=w_Undefined):
    proto = ctx.get_global().Get(prototypename).Get('prototype')
    obj = W_Object(ctx, callfunc = callfunc,Prototype=proto,
                    Class = proto.Class, Value = Value)
    return obj

def isnull_or_undefined(obj):
    if isinstance(obj, W_Undefined) or isinstance(obj, W_Null):
        return True
    else:
        return False
