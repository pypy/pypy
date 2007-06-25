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
        return "<W_Root " + self.to_string() + ">"

    def eval(self, ctx):
        return self

class W_Symbol(W_Root):
    def __init__(self, val):
        self.name = val

    def to_string(self):
        return self.name

    def __repr__(self):
        return "<W_Symbol " + self.name + ">"

    def eval(self, ctx):
        try:
            return OPERATION_MAP[self.name]
        except KeyError:
            raise NotImplementedError

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

    def eval(self, ctx):
        oper = self.car.eval(ctx)
        return oper(ctx, self.cdr)

class W_Nil(W_Root):
    def to_string(self):
        return "()"

############################
# operations
#not sure though any operations should exist here
#it its very similar to operation.add
#############################
def add_lst(ctx, lst):
    return apply_lst(ctx, lambda x, y: x + y, lst)

def mul_lst(ctx, lst):
    return apply_lst(ctx, lambda x, y: x * y, lst)

def apply_lst(ctx, fun, lst):
    acc = None

    if not isinstance(lst, W_Pair):
        #raise argument error
        raise

    arg = lst
    while not isinstance(arg, W_Nil):
        if acc is None:
            acc = arg.car.eval(ctx).to_number()
        else:
            acc = fun(acc, arg.car.eval(ctx).to_number())
        arg = arg.cdr

    if isinstance(acc, int):
        return W_Fixnum(acc)
    else:
        return W_Float(acc)

######################################
# dict mapping operations to callables
# callables must have 2 arguments
# - ctx = execution context
# - lst = list of arguments
#######################################
OPERATION_MAP = \
    {
        '+': add_lst,
        '*': mul_lst,
    }

