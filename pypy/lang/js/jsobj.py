
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
        return bool(self)

    def ToPrimitive(self, hint=""):
        return self

    #def ToNumber(self):
    #    return int(self.ToPrimitive(hint="number"))

    def ToString(self):
        return str(self)
    
    def ToObject(self):
        return self

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, str(self))

class W_Primitive(W_Root):
    """unifying parent for primitives"""
    pass    

class W_Object(W_Root):
    def __init__(self, function=None):
        self.propdict = {}
        self.propdict['toString'] = Property('toString', 
                                             W_Builtin(self.__str__)) # FIXME: Not working
        self.propdict['prototype'] = Property('prototype', w_Undefined,
                                              DontDelete=True)
        self.Prototype = None
        self.Class = "Object"
        self.function = function
        self.scope = []
    
    def Call(self, context, args=[], this = None): # FIXME: Context-ng
        if self.function is not none:
            return self.function.body.call(context=context, args=args,
                                           params=self.function.params,
                                           this=this)
        else:
            print "returning common object"
            return W_Object()
    
    def Get(self, P):
        if P in self.propdict: return self.propdict[P].value
        if self.prototype is None: return w_Undefined
        return self.prototype.Get(P) # go down the prototype chain
    
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
    
    def __str__(self):
        return "[object %s]"%(self.Class,)
    
class W_Arguments(W_Object):
    pass

class ActivationObject(W_Object):
    """The object used on function calls to hold arguments and this"""
    def __init__(self):
        W_Object.__init__()
        self.propdict.pop(P)


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

class W_Boolean(W_Root):
    def __init__(self, boolval):
        self.boolval = bool(boolval)

    def __str__(self):
        if self.boolval:
            return "true"
        return "false"
    
    def ToNumber(self):
        if self.boolval:
            return 1
        return 0

    def ToBoolean(self):
        return self.boolval

    
class W_String(W_Root):
    def __init__(self, strval):
        self.strval = strval

#    def ToString(self):
#        return self.strval

    def __str__(self):
        return self.strval

    def ToBoolean(self):
        return bool(self.strval)


class W_Number(W_Root):
    def __init__(self, floatval):
        self.floatval = floatval

    def __str__(self):
        # XXX: more attention
        # cough, cough
        if str(self.floatval) == str(NaN):
            return 'NaN'
        if float(int(self.floatval)) == self.floatval:
            return str(int(self.floatval))
        return str(self.floatval)
    
    def ToBoolean(self):
        return bool(self.floatval)

    def Get(self, name):
        return w_Undefined

    def ToNumber(self):
        return self.floatval

class W_Reference(W_Root):
    def GetValue(self):
        raise NotImplementedError("W_Reference.GetValue")

class W_Builtin(W_Object):
    def __init__(self, builtinfunction):
        W_Object.__init__()
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

def to_primitive(Value, PreferredType):
    assert isinstance(Value, W_Root)
    if isinstance(Value, W_Object):
        return Value.DefaultValue(PreferredType)
    return Value


        