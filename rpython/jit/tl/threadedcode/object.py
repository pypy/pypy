class OperationError(Exception):
    pass

class W_Object:

    def getrepr(self):
        """
        Return an RPython string which represent the object
        """
        raise NotImplementedError

    def is_true(self):
        raise NotImplementedError

    def add(self, w_other):
        raise NotImplementedError



class W_IntObject(W_Object):

    def __init__(self, intvalue):
        self.intvalue = intvalue

    def __repr__(self):
        return self.getrepr()

    def getrepr(self):
        return str(self.intvalue)

    def is_true(self):
        return self.intvalue != 0

    def add(self, w_other):
        if isinstance(w_other, W_IntObject):
            sum = self.intvalue + w_other.intvalue
            return W_IntObject(sum)
        else:
            raise OperationError

    def sub(self, w_other):
        if isinstance(w_other, W_IntObject):
            sum = self.intvalue - w_other.intvalue
            return W_IntObject(sum)
        else:
            raise OperationError

    def mul(self, w_other):
        if isinstance(w_other, W_IntObject):
            sum = self.intvalue * w_other.intvalue
            return W_IntObject(sum)
        else:
            raise OperationError

    def div(self, w_other):
        if isinstance(w_other, W_IntObject):
            sum = self.intvalue / w_other.intvalue
            return W_IntObject(sum)
        else:
            raise OperationError

    def mod(self, w_other):
        if isinstance(w_other, W_IntObject):
            sum = self.intvalue % w_other.intvalue
            return W_IntObject(sum)
        else:
            raise OperationError

    def eq(self, w_other):
        if isinstance(w_other, W_IntObject):
            if self.intvalue == w_other.intvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

    def lt(self, w_other):
        if isinstance(w_other, W_IntObject):
            if self.intvalue < w_other.intvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

    def gt(self, w_other):
        if isinstance(w_other, W_IntObject):
            if self.intvalue > w_other.intvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

    def le(self, w_other):
        if isinstance(w_other, W_IntObject):
            if self.intvalue <= w_other.intvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

class W_FloatObject(W_Object):

    def __init__(self, floatvalue):
        self.floatvalue = floatvalue

    def __repr__(self):
        return self.getrepr()

    def getrepr(self):
        return str(self.floatvalue)

    def is_true(self):
        return self.floatvalue != 0.0

    def add(self, w_other):
        if isinstance(w_other, W_FloatObject):
            sum = self.floatvalue + w_other.floatvalue
            return W_FloatObject(sum)
        else:
            raise OperationError

    def sub(self, w_other):
        if isinstance(w_other, W_FloatObject):
            sum = self.floatvalue - w_other.floatvalue
            return W_FloatObject(sum)
        else:
            raise OperationError

    def mul(self, w_other):
        if isinstance(w_other, W_FloatObject):
            sum = self.floatvalue * w_other.floatvalue
            return W_FloatObject(sum)
        else:
            raise OperationError

    def div(self, w_other):
        if isinstance(w_other, W_FloatObject):
            sum = self.floatvalue / w_other.floatvalue
            return W_FloatObject(sum)
        else:
            raise OperationError

    def mod(self, w_other):
        if isinstance(w_other, W_FloatObject):
            sum = self.floatvalue % w_other.floatvalue
            return W_FloatObject(sum)
        else:
            raise OperationError

    def eq(self, w_other):
        if isinstance(w_other, W_FloatObject):
            if self.floatvalue == w_other.floatvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

    def lt(self, w_other):
        if isinstance(w_other, W_FloatObject):
            if self.floatvalue < w_other.floatvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

    def gt(self, w_other):
        if isinstance(w_other, W_FloatObject):
            if self.floatvalue > w_other.floatvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

    def le(self, w_other):
        if isinstance(w_other, W_FloatObject):
            if self.floatvalue <= w_other.floatvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

class W_StringObject(W_Object):

    def __init__(self, strvalue):
        self.strvalue = strvalue

    def getrepr(self):
        return self.strvalue

    def is_true(self):
        return len(self.strvalue) != 0
