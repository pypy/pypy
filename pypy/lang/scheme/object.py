import autopath

class ExecutionContext(object):
    """Execution context implemented as a dict.

    { "IDENTIFIER": W_Root }
    """
    def __init__(self, scope):
        assert scope is not None
        self.scope = scope

    def __get__(self, name):
        # shouldn't neme be instance of sth like W_Identifier
        return self.scope.get(name, None)

    def __put__(self, name, obj):
        self.scope[name] = obj

class W_Root(object):
    def to_string(self):
        return ''

    def to_boolean(self):
        return False

    def __str__(self):
        return self.to_string() + "W"

    def __repr__(self):
        return "<W_Root " + self.to_string + " >"

class W_Symbol(W_Root):
    def __init__(self, val):
        self.name = val

    def to_string(self):
        return self.name

    def __repr__(self):
        return "<W_Symbol " + self.name + ">"

class W_Boolean(W_Root):
    def __init__(self, val):
        self.boolval = bool(val)

    def to_string(self):
        if self.boolval:
            return "#t"
        return "#f"

    def to_boolean(self):
        return self.boolval

    def __repr__(self):
        return "<W_Boolean " + str(self.boolval) + " >"

class W_String(W_Root):
    def __init__(self, val):
        self.strval = val

    def to_string(self):
        return self.strval

    def __repr__(self):
        return "<W_String " + self.strval + " >"

class W_Fixnum(W_Root):
    def __init__(self, val):
        self.fixnumval = int(val)

    def to_string(self):
        return str(self.fixnumval)

    def to_number(self):
        return self.to_fixnum()

    def to_fixnum(self):
        return self.fixnumval

    def to_float(self):
        return float(self.fixnumval)

class W_Float(W_Root):
    def __init__(self, val):
        self.floatval = float(val)

    def to_string(self):
        return str(self.floatval)

    def to_number(self):
        return self.to_float()

    def to_fixnum(self):
        return int(self.floatval)

    def to_float(self):
        return self.floatval

class W_Pair(W_Root):
    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def to_string(self):
        return "(" + self.car.to_string() + " . " + self.cdr.to_string() + ")"

class W_Nil(W_Root):
    def to_string(self):
        return "()"

