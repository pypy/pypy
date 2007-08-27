import py

class SchemeException(Exception):
    pass

class UnboundVariable(SchemeException):
    def __str__(self):
        return "Unbound variable %s" % (self.args[0], )

class NotCallable(SchemeException):
    def __str__(self):
        return "%s is not a callable" % (self.args[0].to_string(), )

class WrongArgsNumber(SchemeException):
    def __str__(self):
        return "Wrong number of args"

class WrongArgType(SchemeException):
    def __str__(self):
        return "Wrong argument type: %s is not %s" % \
                (self.args[0].to_string(), self.args[1])

class SchemeSyntaxError(SchemeException):
    def __str__(self):
        return "Syntax error"

class SchemeQuit(SchemeException):
    """raised on (quit) evaluation"""
    pass

class W_Root(object):
    __slots__ = []

    def to_string(self):
        return ''

    def to_boolean(self):
        return True

    def __repr__(self):
        return "<W_Root " + self.to_string() + ">"

    def eval_cf(self, ctx, caller, cont, elst=[], enum=0):
        return self.eval(ctx)

    def eval(self, ctx):
        w_expr = self
        while ctx is not None:
            (w_expr, ctx) = w_expr.eval_tr(ctx)

        assert isinstance(w_expr, W_Root)
        return w_expr

    def eval_tr(self, ctx):
        return (self, None)

    def eq(self, w_obj):
        return self is w_obj
    eqv = eq
    equal = eqv

class W_Undefined(W_Root):
    def to_string(self):
        return "#<undefined>"

w_undefined = W_Undefined()

class W_Symbol(W_Root):
    #class dictionary for symbol storage
    obarray = {}

    def __init__(self, val):
        self.name = val

    def to_string(self):
        return self.name

    def __repr__(self):
        return "<W_Symbol " + self.name + ">"

    def eval_tr(self, ctx):
        w_obj = ctx.get(self.name)
        return (w_obj, None)

w_ellipsis = W_Symbol("...")

def symbol(name):
    #use this to create new symbols, it stores all symbols
    #in W_Symbol.obarray dict
    #if already in obarray return it 
    name = name.lower()
    w_symb = W_Symbol.obarray.get(name, None)
    if w_symb is None:
        w_symb = W_Symbol(name)
        W_Symbol.obarray[name] = w_symb

    assert isinstance(w_symb, W_Symbol)
    return w_symb

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
        return "<W_Boolean " + str(self.boolval) + ">"

    def eqv(self, w_obj):
        if isinstance(w_obj, W_Boolean):
            return self.boolval is w_obj.boolval
        return False
    eq = eqv
    equal = eqv

class W_String(W_Root):
    def __init__(self, val):
        self.strval = val

    def to_string(self):
        return self.strval

    def __repr__(self):
        return "<W_String \"" + self.strval + "\">"

class W_Real(W_Root):
    def __init__(self, val):
        self.exact = False
        self.realval = val

    def to_string(self):
        return str(self.realval)

    def to_number(self):
        return self.to_float()

    def to_fixnum(self):
        return int(self.realval)

    def to_float(self):
        return self.realval

    def round(self):
        int_part = int(self.realval)
        if self.realval > 0:
            if self.realval >= (int_part + 0.5):
                return int_part + 1

            return int_part

        else:
            if self.realval <= (int_part - 0.5):
                return int_part - 1

            return int_part

    def is_integer(self):
        return self.realval == self.round()

    def eqv(self, w_obj):
        return isinstance(w_obj, W_Real) \
                and self.exact is w_obj.exact \
                and self.realval == w_obj.realval
    equal = eqv

W_Number = W_Real

class W_Integer(W_Real):
    def __init__(self, val):
        self.intval = val
        self.realval = val
        self.exact = True

    def to_string(self):
        return str(self.intval)

    def to_number(self):
        return self.to_fixnum()

    def to_fixnum(self):
        return self.intval

    def to_float(self):
        return float(self.intval)

class W_Eval(W_Root):
    #this class is for objects which does more than
    # evaluate to themselves
    def eval_cf(self, ctx, caller, cont, elst=[], enum=0):
        #eval with continuation frame!
        ctx.cont_stack.append(ContinuationFrame(caller, cont, elst, enum))
        result = self.eval(ctx)
        ctx.cont_stack.pop()
        return result

    def continue_tr(self, ctx, lst, elst, cnt=True):
        raise NotImplementedError

class W_List(W_Eval):
    pass

class W_Nil(W_List):
    def __repr__(self):
        return "<W_Nil ()>"

    def to_string(self):
        return "()"

    def eval_cf(self, ctx, caller, cont, elst=[], enum=0):
        raise SchemeSyntaxError

    def eval_tr(self, ctx):
        raise SchemeSyntaxError

w_nil = W_Nil()

class W_Pair(W_List):
    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def to_string(self):
        car = self.car.to_string()
        cdr = self.cdr
        if isinstance(cdr, W_Pair): #proper list
            return "(" + car + " " + cdr.to_lstring() + ")"
        elif cdr is w_nil: #one element proper list
            return "(" + car + ")"

        #dotted list/pair
        return "(" + car + " . " + cdr.to_string() + ")"

    def to_lstring(self):
        car = self.car.to_string()
        cdr = self.cdr
        if isinstance(cdr, W_Pair): #still proper list
            return car + " " + cdr.to_lstring()
        elif cdr is w_nil: #end of proper list
            return car

        #end proper list with dotted
        return car + " . " + cdr.to_string()

    def __repr__(self):
        return "<W_Pair " + self.to_string() + ">"

    def continue_tr(self, ctx, lst, elst, cnt=True):
        oper = elst[0]
        if not isinstance(oper, W_Callable):
            raise NotCallable(oper)

        cdr = lst
        if isinstance(cdr, W_List):
            result = oper.call_tr(ctx, cdr)
        else:
            raise SchemeSyntaxError

        if result[1] is None:
            result = result[0]
        else:
            result = result[0].eval(result[1])

        if len(ctx.cont_stack) == 0:
            raise ContinuationReturn(result)

        cont = ctx.cont_stack.pop()
        return cont.run(ctx, result)

    def eval_tr(self, ctx):
        oper = self.car.eval_cf(ctx, self, self.cdr)
        if not isinstance(oper, W_Callable):
            raise NotCallable(oper)

        #a proper (oper args ...) call
        # self.cdr has to be a proper list
        cdr = self.cdr
        if isinstance(cdr, W_List):
            return oper.call_tr(ctx, cdr)
        else:
            raise SchemeSyntaxError

    def get_car_as_pair(self):
        res = self.car
        if not isinstance(res, W_Pair):
            raise SchemeSyntaxError
        return res

    def get_cdr_as_pair(self):
        res = self.cdr
        if not isinstance(res, W_Pair):
            raise SchemeSyntaxError
        return res

    def equal(self, w_obj):
        return isinstance(w_obj, W_Pair) and \
                self.car.equal(w_obj.car) and \
                self.cdr.equal(w_obj.cdr)

class W_Callable(W_Eval):
    def call_tr(self, ctx, lst):
        #usually tail-recursive call is normal call
        # which returns tuple with no further ExecutionContext
        return (self.call(ctx, lst), None)

    def call(self, ctx, lst):
        raise NotImplementedError

class Body(W_Eval):
    def __init__(self, body):
        self.body = body

    def __repr__(self):
        return "<Body " + self.to_string() + ">"

    def to_string(self):
        return self.body.to_string()

    def eval_tr(self, ctx):
        return self.continue_tr(ctx, self.body, [], False)

    def continue_tr(self, ctx, body, elst, cnt=True):
        body_expression = body
        while isinstance(body_expression, W_Pair):
            if body_expression.cdr is w_nil:
                if cnt is False:
                    return (body_expression.car, ctx)

                if ctx is None:
                    result = body_expression.car
                else:
                    result = body_expression.car.eval(ctx)

                if len(ctx.cont_stack) == 0:
                    raise ContinuationReturn(result)

                cont = ctx.cont_stack.pop()
                return cont.run(ctx, result)

            else:
                body_expression.car.eval_cf(ctx, self, body_expression.cdr)

            body_expression = body_expression.cdr

        raise SchemeSyntaxError

class W_Procedure(W_Callable):
    def __init__(self, pname=""):
        self.pname = pname

    def to_string(self):
        return "#<primitive-procedure %s>" % (self.pname,)

    def call_tr(self, ctx, lst):
        return self.continue_tr(ctx, lst, [], False)

    def continue_tr(self, ctx, lst, elst, cnt=True):
        #evaluate all arguments into list
        arg_lst = elst
        arg_num = 0
        arg = lst
        while isinstance(arg, W_Pair):
            #this is non tail-call, it should create continuation frame
            # continuation frame consist:
            #  - plst of arleady evaluated arguments
            #  - arg (W_Pair) = arg.cdr as a pointer to not evaluated
            #    arguments
            #  - actual context
            w_obj = arg.car.eval_cf(ctx, self, arg.cdr, arg_lst, arg_num)

            arg_num += 1
            arg_lst.append(w_obj)
            arg = arg.cdr

        if arg is not w_nil:
            raise SchemeSyntaxError

        procedure_result = self.procedure_tr(ctx, arg_lst)
        if cnt is False:
            return procedure_result

        #if procedure_result still has to be evaluated
        # this can happen in case if self isinstance of W_Lambda
        if procedure_result[1] is None:
            procedure_result = procedure_result[0]
        else:
            procedure_result = procedure_result[0].eval(procedure_result[1])

        if len(ctx.cont_stack) == 0:
            raise ContinuationReturn(procedure_result)

        cont = ctx.cont_stack.pop()
        return cont.run(ctx, procedure_result)

    def procedure(self, ctx, lst):
        raise NotImplementedError

    def procedure_tr(self, ctx, lst):
        #usually tail-recursive procedure is normal procedure
        # which returns tuple with no further ExecutionContext
        return (self.procedure(ctx, lst), None)

class W_Macro(W_Callable):
    def __init__(self, pname=""):
        self.pname = pname

    def to_string(self):
        return "#<primitive-macro %s>" % (self.pname,)

class W_Promise(W_Root):
    def __init__(self, expr, ctx):
        self.expr = expr
        self.result = None
        self.closure = ctx

    def to_string(self):
        return "#<promise: %s>" % self.expr.to_string()

    def force(self, ctx):
        if self.result is None:
            #XXX cont_stack copy to be cont. friendly
            self.result = self.expr.eval(self.closure.copy())

        return self.result

class Formal(object):
    def __init__(self, name, islist=False):
        self.name = name
        self.islist = islist

class W_Lambda(W_Procedure):
    def __init__(self, args, body, closure, pname="#f"):
        self.args = []
        arg = args
        while not arg is w_nil:
            if isinstance(arg, W_Symbol):
                self.args.append(Formal(arg.to_string(), True))
                break
            else:
                if not isinstance(arg, W_Pair):
                    raise SchemeSyntaxError
                if not isinstance(arg.car, W_Symbol):
                    raise WrongArgType(arg.car, "Identifier")
                #list of argument names, not evaluated
                self.args.append(Formal(arg.car.to_string(), False))
                arg = arg.cdr

        self.body = Body(body)
        self.pname = pname
        self.closure = closure

    def to_string(self):
        return "#<procedure %s>" % (self.pname,)

    def procedure_tr(self, ctx, lst):
        #must be tail-recursive aware, uses eval_body
        #ctx is a caller context, which is joyfully ignored

        local_ctx = self.closure.copy()
        #if lambda procedure should keep caller cont_stack
        local_ctx.cont_stack = ctx.cont_stack #[:]

        #set lambda arguments
        for idx in range(len(self.args)):
            formal = self.args[idx]
            if formal.islist:
                local_ctx.put(formal.name, plst2lst(lst[idx:]))
            else:
                local_ctx.put(formal.name, lst[idx])

        return self.body.eval_tr(local_ctx)

##
# Parser helpers
##
def quote(sexpr):
    return W_Pair(W_Symbol('quote'), W_Pair(sexpr, w_nil))

def qq(sexpr):
    return W_Pair(W_Symbol('quasiquote'), W_Pair(sexpr, w_nil))

def unquote(sexpr):
    return W_Pair(W_Symbol('unquote'), W_Pair(sexpr, w_nil))

def unquote_splicing(sexpr):
    return W_Pair(W_Symbol('unquote-splicing'), W_Pair(sexpr, w_nil))


##
# General helpers
##
def plst2lst(plst, w_cdr=w_nil):
    """coverts python list() of W_Root into W_Pair scheme list"""
    plst.reverse()
    for w_obj in plst:
        w_cdr = W_Pair(w_obj, w_cdr)

    return w_cdr

##
# Continuations
##
class ContinuationReturn(SchemeException):
    def __init__(self, result):
        self.result = result

class ContinuationFrame(object):
    def __init__(self, caller, continuation, evaluated_args = [], enum=0):
        self.caller = caller
        assert isinstance(continuation, W_Root)
        self.continuation = continuation
        assert isinstance(evaluated_args, list)
        self.evaluated_args = evaluated_args
        self.evaluated_args_num = enum

    def run(self, ctx, arg):
        elst = self.evaluated_args[:self.evaluated_args_num]
        elst.append(arg)
        #print 'c>', self.caller, elst, self.continuation
        return self.caller.continue_tr(ctx, self.continuation, elst, True)

class Continuation(W_Procedure):
    def __init__(self, ctx, continuation):
        self.closure = ctx
        #copy of continuation stack this means that cont_stack is not
        # global, so watch out with closures
        self.cont_stack = continuation[:]
        try:
            self.continuation = self.cont_stack.pop()
        except IndexError:
            #continuation captured on top-level
            self.continuation = None

    def __repr__(self):
        return self.to_string()

    def to_string(self):
        return "#<continuation -> %s>" % (self.continuation,)

    def procedure_tr(self, ctx, lst):
        #caller ctx is ignored
        if len(lst) == 0:
            lst.append(w_undefined)

        #print "Continuation called", self.cont_stack
        self.closure.cont_stack = self.cont_stack[:]
        cont = self.continuation
        if cont is None:
            raise ContinuationReturn(lst[0])

        return cont.run(self.closure, lst[0])

class CallCC(W_Procedure):
    _symbol_name = "call/cc"

    def procedure_tr(self, ctx, lst):
        if len(lst) != 1 or not isinstance(lst[0], W_Procedure):
            #print lst[0]
            raise SchemeSyntaxError

        w_lambda = lst[0]
        if not isinstance(w_lambda, W_Procedure):
            raise SchemeSyntaxError
        cc = Continuation(ctx, ctx.cont_stack)
        return w_lambda.call_tr(ctx, W_Pair(cc, w_nil))

