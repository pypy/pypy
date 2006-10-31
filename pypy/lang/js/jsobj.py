
class SeePage(NotImplementedError):
    pass

class W_Root(object):
    def GetValue(self):
        return self

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

class W_Undefined(W_Root):
    def __str__(self):
        return ""
    
    def ToNumber(self):
        # XXX make NaN
        return 0

class W_Null(W_Root):
    def __str__(self):
        return "null"

class W_Boolean(W_Root):
    def __init__(self, boolval):
        self.boolval = boolval

    def __str__(self):
        if self.boolval:
            return "true"
        return "false"
    
    def ToNumber(self):
        if self.boolval:
            return 1
        return 0
    
class W_String(W_Root):
    def __init__(self, strval):
        # XXX: Should be unicode object
        self.strval = strval

#    def ToString(self):
#        return self.strval

    def __str__(self):
        # INSANE - should be like 'str' or so
        return self.strval

class W_Number(W_Root):
    def __init__(self, floatval):
        self.floatval = floatval

    def __str__(self):
        # XXX: more attention
        if float(int(self.floatval)) == self.floatval:
            return str(int(self.floatval))
        return str(self.floatval)
    
    def Get(self, name):
        return w_Undefined

    def ToNumber(self):
        return self.floatval

class W_Reference(W_Root):
    def GetValue(self):
        raise NotImplementedError("W_Reference.GetValue")

class W_Object(W_Root):
    def __init__(self, dict_w, function=None):
        # string --> W_Root
        self.dict_w = dict_w
        # XXX: more stuff
        self.dict_w['toString'] = W_Builtin({}, self.w_string)
        # XXX A bit hairy here, we store here a Function, and Script
        #     is a self.function.body
        self.function = function
        #self.class_ = None

    def Call(self, this=None):
        if self.function:
            return self.function.body.call()
        else:
            raise SeePage(33)
    
    def w_string(self):
        return W_String(str(self))
    
    def DefaultValue(self, hint):
        #if hint == "string":
        tostring_meth = self.Get("toString")
        if isinstance(tostring_meth, W_Object):
            return tostring_meth.Call(this=self)
        valueof_meth = self.Get("valueOf")
        if isinstance(valueof_meth, W_Object):
            retval = valueof_meth.Call(this=self)
            # XXX: check primitiveness of retval
            return retval
##    else:
##            if isinstance(valueof_meth, W_Object):
##                retval = valueof_meth.Call(this=self)
##                # XXX: check primitiveness of retval
##                return retval
##            tostring_meth = self.Get("toString")
##            if isinstance(tostring_meth, W_Object):
##                return tostring_meth.Call(this=self)
        return w_Undefined
    
    def ToPrimitive(self, hint=""):
        return self.DefaultValue(hint)
    
    def ToNumber(self):
        return self.ToPrimitive("number").ToNumber(hint="number")
    
    def ToString(self):
        return str(self.DefaultValue(hint="string"))
    
    def Get(self, name):
        if name in self.dict_w:
            return self.dict_w[name]
        
        return w_Undefined

    #def ToPrimitive(self, hint=""):
    #    return DefaultValue(hint)

    #def ToString(self):
    #    raise SeePage(42)
    
    def CanPut(self, name):
        return True
    
    def Put(self, name, w_obj):
        # INSANE - raise some exceptions in case of read only and such
        if not self.CanPut(name):
            return # AAAAAAAAAAAAaaaaaaaaaaaa
        self.dict_w[name] = w_obj
    
    def __str__(self):
        # INSANE
        return "[object Object]"

class W_Builtin(W_Object):
    def __init__(self, dict_w, internalfunction):
        self.dict_w = {}
        self.internalfunction = internalfunction
    
    def Call(self, this=None):
        return self.internalfunction()

class W_List(W_Root):
    def __init__(self, list_w):
        self.list_w = list_w

    def ToString(self):
        raise SeePage(42)

w_Undefined = W_Undefined()
w_Null = W_Null()
