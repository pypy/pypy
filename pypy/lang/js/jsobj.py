
class SeePage(NotImplementedError):
    pass

class W_Root(object):
    def GetValue(self):
        return self

    def ToPrimitive(self):
        return self

    def ToNumber(self):
        raise SeePage(37)

    def ToString(self):
        return str(self)

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, str(self))

class W_Undefined(W_Root):
    def __str__(self):
        return "undefined"

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

class W_String(W_Root):
    def __init__(self, strval):
        # XXX: Should be unicode object
        self.strval = strval

#    def ToString(self):
#        return self.strval

    def __str__(self):
        return self.strval

class W_Number(W_Root):
    def __init__(self, floatval):
        self.floatval = floatval

    def __str__(self):
        # XXX: more attention
        if float(int(self.floatval)) == self.floatval:
            return str(int(self.floatval))
        return str(self.floatval)

    def ToNumber(self):
        return self.floatval

class W_Reference(W_Root):
    def GetValue(self):
        raise NotImplementedError("W_Reference.GetValue")

class W_Object(W_Root):
    def __init__(self, dict_w):
        # string --> W_Root
        self.dict_w = dict_w

    def ToPrimitive(self):
        raise SeePage(37)

    def ToString(self):
        raise SeePage(42)

class W_List(W_Root):
    def __init__(self, list_w):
        self.list_w = list_w

    def ToString(self):
        raise SeePage(42)

w_Undefined = W_Undefined()
w_Null = W_Null()
