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

    def eq_symbol(self, w_symb):
        return w_symb is self

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
        #XXX not tests here
        raise SchemeSyntaxError

    def eval_tr(self, ctx):
        #XXX not tests here
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

        #set lambda arguments
        for idx in range(len(self.args)):
            formal = self.args[idx]
            if formal.islist:
                local_ctx.put(formal.name, plst2lst(lst[idx:]))
            else:
                local_ctx.put(formal.name, lst[idx])

        return self.body.eval_tr(local_ctx)

def plst2lst(plst, w_cdr=w_nil):
    """coverts python list() of W_Root into W_Pair scheme list"""
    plst.reverse()
    for w_obj in plst:
        w_cdr = W_Pair(w_obj, w_cdr)

    return w_cdr

class W_Promise(W_Root):
    def __init__(self, expr, ctx):
        self.expr = expr
        self.result = None
        self.closure = ctx

    def to_string(self):
        return "#<promise: %s>" % self.expr.to_string()

    def force(self, ctx):
        if self.result is None:
            self.result = self.expr.eval(self.closure.copy())

        return self.result

##
# operations
##
class ListOper(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) == 0:
            if self.default_result is None:
                raise WrongArgsNumber()

            return self.default_result

        if len(lst) == 1:
            if not isinstance(lst[0], W_Number):
                raise WrongArgType(lst[0], "Number")
            return self.unary_oper(lst[0])

        acc = None
        for arg in lst:
            if not isinstance(arg, W_Number):
                raise WrongArgType(arg, "Number")
            if acc is None:
                acc = arg
            else:
                acc = self.oper(acc, arg)

        return acc

    def unary_oper(self, x):
        if isinstance(x, W_Integer):
            return W_Integer(self.do_unary_oper(x.to_fixnum()))
        elif isinstance(x, W_Number):
            return W_Real(self.do_unary_oper(x.to_float()))
        else:
            raise WrongArgType(x, "Number")

    def oper(self, x, y):
        if isinstance(x, W_Integer) and isinstance(y, W_Integer):
            return W_Integer(self.do_oper(x.to_fixnum(), y.to_fixnum()))
        elif isinstance(x, W_Number) or isinstance(y, W_Number):
            return W_Real(self.do_oper(x.to_float(), y.to_float()))
        else:
            raise WrongArgType(x, "Number")

    def do_oper(self, x, y):
        raise NotImplementedError

    def do_unary_oper(self, x):
        raise NotImplementedError

def create_op_class(oper, unary_oper, title, default_result=None):
    class Op(ListOper):
        pass

    local_locals = {}
    attr_name = "do_oper"

    code = py.code.Source("""
    def %s(self, x, y):
        return x %s y
        """ % (attr_name, oper))

    exec code.compile() in local_locals
    local_locals[attr_name]._annspecialcase_ = 'specialize:argtype(1)'
    setattr(Op, attr_name, local_locals[attr_name])

    attr_name = "do_unary_oper"
    code = py.code.Source("""
    def %s(self, x):
        return %s x
        """ % (attr_name, unary_oper))

    exec code.compile() in local_locals
    local_locals[attr_name]._annspecialcase_ = 'specialize:argtype(1)'
    setattr(Op, attr_name, local_locals[attr_name])

    if default_result is None:
        Op.default_result = None
    else:
        Op.default_result = W_Integer(default_result)

    Op.__name__ = "Op" + title
    Op._symbol_name = oper
    return Op

Add = create_op_class('+', '', "Add", 0)
Sub = create_op_class('-', '-', "Sub")
Mul = create_op_class('*', '', "Mul", 1)
Div = create_op_class('/', '1 /', "Div")

class Equal(W_Procedure):
    _symbol_name = "="

    def procedure(self, ctx, lst):
        if len(lst) < 2:
            return W_Boolean(True)

        prev = lst[0]
        if not isinstance(prev, W_Number):
            raise WrongArgType(prev, "Number")

        for arg in lst[1:]:
            if not isinstance(arg, W_Number):
                raise WrongArgType(arg, "Number")

            if prev.to_number() != arg.to_number():
                return W_Boolean(False)
            prev = arg

        return W_Boolean(True)

class List(W_Procedure):
    _symbol_name = "list"

    def procedure(self, ctx, lst):
        return plst2lst(lst)

class Cons(W_Procedure):
    _symbol_name = "cons"

    def procedure(self, ctx, lst):
        w_car = lst[0]
        w_cdr = lst[1]
        #cons is always creating a new pair
        return W_Pair(w_car, w_cdr)

class Car(W_Procedure):
    _symbol_name = "car"

    def procedure(self, ctx, lst):
        w_pair = lst[0]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")
        return w_pair.car

class Cdr(W_Procedure):
    _symbol_name = "cdr"

    def procedure(self, ctx, lst):
        w_pair = lst[0]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")
        return w_pair.cdr

class SetCar(W_Procedure):
    _symbol_name = "set-car!"

    def procedure(self, ctx, lst):
        w_pair = lst[0]
        w_obj = lst[1]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")

        w_pair.car = w_obj
        return w_undefined

class SetCdr(W_Procedure):
    _symbol_name = "set-cdr!"

    def procedure(self, ctx, lst):
        w_pair = lst[0]
        w_obj = lst[1]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")

        w_pair.cdr = w_obj
        return w_undefined

class Quit(W_Procedure):
    _symbol_name = "quit"

    def procedure(self, ctx, lst):
        raise SchemeQuit

class Force(W_Procedure):
    _symbol_name = "force"

    def procedure(self, ctx, lst):
        if len(lst) != 1:
            raise WrongArgsNumber

        w_promise = lst[0]
        if not isinstance(w_promise, W_Promise):
            raise WrongArgType(w_promise, "Promise")

        return w_promise.force(ctx)

##
# Predicate
##
class PredicateNumber(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) != 1:
            raise WrongArgsNumber

        w_obj = lst[0]
        if not isinstance(w_obj, W_Number):
            raise WrongArgType(w_obj, 'Number')

        return W_Boolean(self.predicate(w_obj))

    def predicate(self, w_obj):
        raise NotImplementedError

class IntegerP(PredicateNumber):
    _symbol_name = "integer?"

    def predicate(self, w_obj):
        if not w_obj.exact:
            return w_obj.is_integer()

        return True

class RealP(PredicateNumber):
    _symbol_name = "real?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Real)

class RationalP(RealP):
    _symbol_name = "rational?"

class NumberP(PredicateNumber):
    _symbol_name = "number?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Number)

class ComplexP(NumberP):
    _symbol_name = "complex?"

class ExactP(PredicateNumber):
    _symbol_name = "exact?"

    def predicate(self, w_obj):
        return w_obj.exact

class InexactP(PredicateNumber):
    _symbol_name = "inexact?"

    def predicate(self, w_obj):
        return not w_obj.exact

class ZeroP(PredicateNumber):
    _symbol_name = "zero?"

    def predicate(self, w_obj):
        return w_obj.to_number() == 0.0

class OddP(PredicateNumber):
    _symbol_name = "odd?"

    def predicate(self, w_obj):
        if not w_obj.is_integer():
            raise WrongArgType(w_obj, "Integer")

        return w_obj.round() % 2 != 0

class EvenP(PredicateNumber):
    _symbol_name = "even?"

    def predicate(self, w_obj):
        if not w_obj.is_integer():
            raise WrongArgType(w_obj, "Integer")

        return w_obj.round() % 2 == 0

#XXX no tests for it
class PairP(W_Procedure):
    _symbol_name = "pair?"

    def procedure(self, ctx, lst):
        if len(lst) != 1:
            raise WrongArgsNumber

        w_obj = lst[0]
        if isinstance(w_obj, W_Pair):
            return W_Boolean(True)

        return W_Boolean(False)

##
# Macro
##
class Define(W_Macro):
    _symbol_name = "define"

    def continue_tr(self, ctx, lst, elst, cnt=True):
        w_first = lst
        w_val = elst[0]
        if isinstance(w_first, W_Symbol):
            ctx.set(w_first.name, w_val)
            if len(ctx.cont_stack) == 0:
                raise ContinuationReturn(w_val)

            cont = ctx.cont_stack.pop()
            return cont.run(ctx, w_val)

        raise SchemeSyntaxError

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        w_first = lst.car
        w_second = lst.get_cdr_as_pair()
        if isinstance(w_first, W_Symbol):
            w_val = w_second.car.eval_cf(ctx, self, w_first)
            ctx.set(w_first.name, w_val)
            return w_val #undefined
        elif isinstance(w_first, W_Pair):
            #we have lambda definition here!
            w_name = w_first.car
            if not isinstance(w_name, W_Symbol):
                raise SchemeSyntaxError

            formals = w_first.cdr #isinstance of W_List
            body = w_second
            #remember this! ContinuationFrame creation
            ctx.cont_stack.append(ContinuationFrame(self, w_first))
            w_lambda = W_Lambda(formals, body, ctx, pname=w_name.name)
            ctx.cont_stack.pop()
            ctx.set(w_name.name, w_lambda)
            return w_lambda #undefined

        raise SchemeSyntaxError

class Sete(W_Macro):
    _symbol_name = "set!"

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        w_identifier = lst.car

        w_val = lst.get_cdr_as_pair().car.eval(ctx)
        ctx.ssete(w_identifier, w_val)
        return w_val #undefined

class MacroIf(W_Macro):
    _symbol_name = "if"

    def call_tr(self, ctx, lst):
        #if needs to be tail-recursive aware
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        w_condition = lst.car
        lst_cdr = lst.get_cdr_as_pair()
        w_then = lst_cdr.car
        if lst_cdr.cdr is w_nil:
            w_else = W_Boolean(False)
        else:
            w_else = lst_cdr.get_cdr_as_pair().car

        w_cond_val = w_condition.eval(ctx)
        if w_cond_val.to_boolean() is True:
            return (w_then, ctx)
        else:
            return (w_else, ctx)

class Lambda(W_Macro):
    _symbol_name = "lambda"

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError(lst, "Pair")
        w_args = lst.car
        w_body = lst.cdr
        return W_Lambda(w_args, w_body, ctx)

class Begin(W_Macro):
    _symbol_name = "begin"

    def call_tr(self, ctx, lst):
        #begin uses eval_body, so it is tail-recursive aware
        return Body(lst).eval_tr(ctx)

class Let(W_Macro):
    _symbol_name = "let"

    def call_tr(self, ctx, lst):
        #let uses eval_body, so it is tail-recursive aware
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        body = Body(lst.cdr)
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            #evaluate the values in caller ctx
            w_val = w_def.get_cdr_as_pair().car.eval(ctx)
            local_ctx.sput(w_def.car, w_val)
            w_formal = w_formal.cdr

        return body.eval_tr(local_ctx)

class LetStar(W_Macro):
    _symbol_name = "let*"

    def continue_tr(self, ctx, lst, elst, cnt=True):
        ctx = ctx.copy()
        (body, w_def, w_val) = elst
        ctx.sput(w_def, w_val)
        w_formal = lst
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            w_val = w_def.get_cdr_as_pair().car.eval_cf(ctx, \
                    self, lst.cdr, [elst[0], w_def.car], 2)
            ctx.sput(w_def.car, w_val)
            w_formal = w_formal.cdr

        w_result = body.eval(ctx)

        if len(ctx.cont_stack) == 0:
            raise ContinuationReturn(w_result)

        cont = ctx.cont_stack.pop()
        return cont.run(ctx, w_result)

    def call_tr(self, ctx, lst):
        #let* uses eval_body, so it is tail-recursive aware
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        body = Body(lst.cdr)
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            #evaluate the values in local ctx
            w_val = w_def.get_cdr_as_pair().car.eval_cf(local_ctx, \
                    self, w_formal.cdr, [body, w_def.car], 2)
            local_ctx.sput(w_def.car, w_val)
            w_formal = w_formal.cdr

        return body.eval_tr(local_ctx)

class Letrec(W_Macro):
    _symbol_name = "letrec"

    def call_tr(self, ctx, lst):
        """let uses eval_body, so it is tail-recursive aware"""
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        body = Body(lst.cdr)
        map_name_expr = {}
        map_name_symb = {}
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            name = w_def.car.to_string()
            map_name_expr[name] = w_def.get_cdr_as_pair().car
            map_name_symb[name] = w_def.car
            local_ctx.sbind(w_def.car)
            w_formal = w_formal.cdr

        map_name_val = {}
        for (name, expr) in map_name_expr.items():
            map_name_val[name] = expr.eval(local_ctx)

        for (name, w_val) in map_name_val.items():
            local_ctx.ssete(map_name_symb[name], w_val)

        return body.eval_tr(local_ctx)

def quote(sexpr):
    return W_Pair(W_Symbol('quote'), W_Pair(sexpr, w_nil))

def qq(sexpr):
    return W_Pair(W_Symbol('quasiquote'), W_Pair(sexpr, w_nil))

def unquote(sexpr):
    return W_Pair(W_Symbol('unquote'), W_Pair(sexpr, w_nil))

def unquote_splicing(sexpr):
    return W_Pair(W_Symbol('unquote-splicing'), W_Pair(sexpr, w_nil))

class Quote(W_Macro):
    _symbol_name = "quote"

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        return lst.car

class QuasiQuote(W_Macro):
    _symbol_name = "quasiquote"

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        w_lst = self.unquote(ctx, lst.car, 1)
        return w_lst

    def unquote(self, ctx, w_lst, deep):
        if deep < 1:
            raise SchemeSyntaxError

        if isinstance(w_lst, W_Pair):
            w_oper = w_lst.car
            if isinstance(w_oper, W_Symbol):
                if w_oper.to_string() == "unquote":
 
                    #simply unquote
                    if deep == 1:
                        return w_lst.get_cdr_as_pair().car.eval(ctx)

                    #not first level, look deeper, with lower nesting level
                    if deep > 1:
                        w_unq = self.unquote(ctx,
                                w_lst.get_cdr_as_pair().car,
                                deep-1)

                        return W_Pair(w_oper, W_Pair(w_unq, w_nil))

                #increment nesting level
                if w_oper.to_string() == "quasiquote":
                    w_unq = self.unquote(ctx,
                            w_lst.get_cdr_as_pair().car,
                            deep+1)
                    return W_Pair(w_oper, W_Pair(w_unq, w_nil))

                #not first level, look deeper, with lower nesting level
                if deep > 1 and w_oper.to_string() == "unquote-splicing":
                    w_unq = self.unquote(ctx,
                            w_lst.get_cdr_as_pair().car,
                            deep-1)

                    return W_Pair(w_oper, W_Pair(w_unq, w_nil))

            #for unquote-splice we need to check one level earlier
            #cond = if we have w_oper = (unquote-splice <sexpr>)
            if deep == 1 and isinstance(w_oper, W_Pair) and \
                    isinstance(w_oper.car, W_Symbol) and \
                    w_oper.car.to_string() == "unquote-splicing":

                #rest of list, needed for "stripping away" closing parens
                w_unq_cdr = self.unquote(ctx, w_lst.cdr, deep)

                #unquote into list
                w_unq = w_oper.get_cdr_as_pair().car.eval(ctx)
                #w_unq must be proper list
                if w_unq is w_nil:
                    #if nil: reeturn only rest of list
                    return w_unq_cdr

                #traverse w_unq to find last cdr and set it to w_cdr
                w_pair = w_unq
                while isinstance(w_pair, W_Pair):
                    if w_pair.cdr is w_nil:
                        w_pair.cdr = w_unq_cdr
                        break

                    w_pair = w_pair.cdr

                return w_unq

            #no special cases, traverse tree
            return W_Pair(self.unquote(ctx, w_oper, deep),
                    self.unquote(ctx, w_lst.cdr, deep))

        #trivial case, just return
        return w_lst

class Delay(W_Macro):
    _symbol_name = "delay"

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        return W_Promise(lst.car, ctx)

##
# DerivedMacros
##
class SyntaxRules(W_Macro):
    _symbol_name = "syntax-rules"

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        w_literals = lst.car
        if not isinstance(w_literals, W_List):
            raise SchemeSyntaxError

        literals_map = {}
        while isinstance(w_literals, W_Pair):
            if not isinstance(w_literals.car, W_Symbol):
                raise SchemeSyntaxError

            #XXX locations here
            literal_name = w_literals.car.to_string()
            w_temp = ctx.get_location(literal_name)

            literals_map[literal_name] = w_temp

            w_literals = w_literals.cdr

        w_syntax_lst = lst.cdr
        syntax_lst = []
        while isinstance(w_syntax_lst, W_Pair):
            w_syntax = w_syntax_lst.car
            if not isinstance(w_syntax, W_Pair):
                raise SchemeSyntaxError

            w_pattern = w_syntax.car
            w_template = w_syntax.get_cdr_as_pair().car

            #do stuff with w_syntax rules
            syntax_lst.append(SyntaxRule(w_pattern, w_template, literals_map))
            
            w_syntax_lst = w_syntax_lst.cdr

        #closes template in syntactic enviroment at the point of definition
        return W_Transformer(syntax_lst, ctx)

class Ellipsis(W_Root):
    def __init__(self, mdict_lst):
        self.mdict_lst = mdict_lst

    def __repr__(self):
        return "#<e: " + str(self.mdict_lst) + ">"

class EllipsisException(SchemeException):
    def __init__(self, length):
        self.length = length

class EllipsisTemplate(SchemeException):
    pass

class EllipsisPattern(SchemeException):
    pass

class MatchError(SchemeException):
    pass

class SyntaxRule(object):
    def __init__(self, pattern, template, literals):
        assert isinstance(pattern, W_Pair)
        self.pattern = pattern
        self.template = template
        self.literals = literals

    def __str__(self):
        return self.pattern.to_string() + " -> " + self.template.to_string()

    def match(self, ctx, w_expr):
        #we use .cdr here, because keyword should not be a macro variable
        assert isinstance(w_expr, W_Pair)
        return self.matchr(ctx, self.pattern.cdr, w_expr.cdr)

    def matchr(self, ctx, w_patt, w_expr):
        if isinstance(w_patt, W_Pair):
            w_pattcar = w_patt.car
            if isinstance(w_expr, W_Pair):
                mdict_car = self.matchr(ctx, w_pattcar, w_expr.car)
                try:
                    #we catch EllipsisPattern here because in car
                    # we dont know how to deal with it
                    mdict_cdr = self.matchr(ctx, w_patt.cdr, w_expr.cdr)
                except EllipsisPattern:
                    print "ellipsis matched", w_patt, w_expr

                    mdict_lst = []
                    w_pair = w_expr
                    while isinstance(w_pair, W_Pair):
                        mdict = self.matchr(ctx, w_pattcar, w_pair.car)
                        mdict_lst.append(mdict)
                        w_pair = w_pair.cdr

                    mdict_cdr = {}
                    ellipsis = Ellipsis(mdict_lst)
                    for name in mdict_lst[0].keys():
                        mdict_cdr[name] = ellipsis

                    return mdict_cdr

                mdict_car.update(mdict_cdr)
                return mdict_car

            if w_pattcar is w_ellipsis and w_expr is w_nil:
                raise EllipsisPattern

        if w_patt is w_ellipsis:
            raise EllipsisPattern

        if isinstance(w_patt, W_Symbol):
            try:
                w_literal = self.literals[w_patt.name]
                if not isinstance(w_expr, W_Symbol):
                    raise MatchError

                if w_patt.name != w_expr.name:
                    raise MatchError

                w_form = ctx.get_location(w_expr.name)

                if w_form is not w_literal:
                    raise MatchError

            except KeyError:
                pass

            return {w_patt.name: w_expr}

        if w_patt is w_nil and w_expr is w_nil:
            return {}

        #w_patt is w_nil, but w_expr is not
        # or w_patt is W_Pair but w_expr is not
        raise MatchError

class SymbolClosure(W_Symbol):
    def __init__(self, ctx, symbol):
        assert isinstance(symbol, W_Symbol)
        assert not isinstance(symbol, SymbolClosure)
        self.symbol = symbol
        self.name = symbol.name
        self.closure = ctx

    def eval_tr(self, ctx):
        #this symbol is in Syntactic Closure 
        return self.symbol.eval_tr(self.closure)

    def to_string(self):
        #return "#<closure: " + self.sexpr.to_string() + ">"
        return self.symbol.to_string()

    def __repr__(self):
        return "<sc:W_Symbol " + self.to_string() + ">"

class PairClosure(W_Pair):
    def __init__(self, ctx, pair):
        assert isinstance(pair, W_Pair)
        assert not isinstance(pair, PairClosure)
        self.pair = pair
        self.car = pair.car
        self.cdr = pair.cdr
        self.closure = ctx

    def eval_tr(self, ctx):
        #this pair is in Syntactic Closure 
        return self.pair.eval_tr(self.closure)

    def to_string(self):
        #return "#<closure: " + self.sexpr.to_string() + ">"
        return self.pair.to_string()

    def __repr__(self):
        return "<sc:W_Pair " + self.to_string() + ">"

class W_Transformer(W_Procedure):
    def __init__(self, syntax_lst, ctx, pname=""):
        self.pname = pname
        self.syntax_lst = syntax_lst
        self.closure = ctx

    def match(self, ctx, w_expr):
        for rule in self.syntax_lst:
            try:
                match_dict = rule.match(ctx, w_expr)
                return (rule.template, match_dict)
            except MatchError:
                pass

        raise MatchError

    def expand(self, ctx, w_expr):
        try:
            (template, match_dict) = self.match(ctx, w_expr)
        except MatchError:
            raise SchemeSyntaxError

        return self.substitute(ctx, template, match_dict)

    def find_elli(self, expr, mdict):
        #filter mdict, returning only ellipsis which appear in expr
        if isinstance(expr, W_Pair):
            edict_car = self.find_elli(expr.car, mdict)
            edict_cdr = self.find_elli(expr.cdr, mdict)
            edict_car.update(edict_cdr)
            return edict_car

        if isinstance(expr, W_Symbol):
            val = mdict.get(expr.name, None)
            if val is None:
                return {}

            if isinstance(val, Ellipsis):
                return {expr.name: val}

        return {}

    def plst_append(self, plst, w_cdr=None):
        first_cons = plst[0]

        last_cons = None
        for lst in plst:
            if last_cons is not None:
                last_cons.cdr = lst

            while isinstance(lst, W_Pair):
                last_cons = lst
                lst = lst.cdr

        if w_cdr is not None:
            last_cons.cdr = w_cdr

        return first_cons

    def substituter(self, ctx, sexpr, match_dict, flatten=False):
        if isinstance(sexpr, W_Pair):
            w_car = self.substituter(ctx, sexpr.car, match_dict)
            try:
                w_cdr = self.substituter(ctx, sexpr.cdr, match_dict)
            except EllipsisTemplate:
                print "ellipsis expand", sexpr
                sexprcdr = sexpr.get_cdr_as_pair()
                try:
                    #we can still have something behind ellipsis
                    w_cdr = self.substituter(ctx, sexprcdr.cdr, match_dict)
                except EllipsisTemplate:
                    #it can also be ellipsis
                    # lets pretend its usual <(obj ...) ...>
                    # instead of <obj ... ...>
                    # we will *flatten* the result later
                    w_inner = W_Pair(sexpr.car, W_Pair(sexprcdr.car, w_nil))
                    w_outer = W_Pair(w_inner, sexprcdr.cdr)
                    return self.substituter(ctx, w_outer, match_dict, True)

                plst = []
                #find_elli gets ellipses from match_dict relevant to sexpr.car
                mdict_elli = self.find_elli(sexpr.car, match_dict)
                elli_len = 0
                for (key, val) in mdict_elli.items():
                    if elli_len == 0 or elli_len == len(val.mdict_lst):
                        elli_len = len(val.mdict_lst)
                    else:
                        #we can treat is as an error if ellipsis has
                        # different match length
                        # # or get the shortest one
                        raise SchemeSyntaxError

                #generate elli_len substitutions for ellipsis
                for i in range(elli_len):
                    #one level of ellipsis nesting lower
                    new_mdict = match_dict.copy()
                    for (key, val) in mdict_elli.items():
                        new_mdict[key] = val.mdict_lst[i][key]

                    sub = self.substituter(ctx, sexpr.car, new_mdict)
                    plst.append(sub)

                if flatten:
                    #we have to flatten these list, it means append them
                    # together, and remember about w_cdr
                    w_lst = self.plst_append(plst, w_cdr)

                else:
                    w_lst = plst2lst(plst, w_cdr)

                return w_lst

            w_pair = W_Pair(w_car, w_cdr)
            if isinstance(w_car, W_Symbol):
                try:
                    w_macro = ctx.get(w_car.name)
                    # recursive macro expansion
                    if isinstance(w_macro, W_DerivedMacro):
                        if w_macro.transformer is self:
                            return w_macro.expand(ctx, w_pair)
                except UnboundVariable:
                    pass

            return w_pair

        if isinstance(sexpr, W_Symbol):
            if sexpr is w_ellipsis:
                raise EllipsisTemplate

            w_sub = match_dict.get(sexpr.name, None)
            if w_sub is not None:
                #Hygenic macros close their input forms in the syntactic
                # enviroment at the point of use

                if isinstance(w_sub, Ellipsis):
                    return w_sub

                #not always needed, because w_sub can have no W_Symbol inside
                if isinstance(w_sub, W_Symbol) and \
                        not isinstance(w_sub, SymbolClosure):
                    return SymbolClosure(ctx, w_sub)

                if isinstance(w_sub, W_Pair) and \
                        not isinstance(w_sub, PairClosure):
                    return PairClosure(ctx, w_sub)

                return w_sub

        return sexpr

    substitute = substituter

    def expand_eval(self, ctx, sexpr):
        #we have lexical scopes:
        # 1. macro was defined - self.closure
        # 2. macro is called   - ctx
        # 3. macro is expanded, can introduce new bindings - expand_ctx
        expanded = self.expand(ctx, sexpr)
        expand_ctx = self.closure.copy()
        return expanded.eval(expand_ctx)

    def procedure(self, ctx, lst):
        return self.expand_eval(ctx, lst[0])

class W_DerivedMacro(W_Macro):
    def __init__(self, name, transformer):
        self.name = name
        self.transformer = transformer

    def to_string(self):
        return "#<derived-macro %s>" % (self.name,)

    def call(self, ctx, lst):
        return self.transformer.expand_eval(ctx,
                W_Pair(W_Symbol(self.name), lst))

    def expand(self, ctx, lst):
        return self.transformer.expand(ctx, lst)

class DefineSyntax(W_Macro):
    _symbol_name = "define-syntax"

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        w_def = lst.car
        if not isinstance(w_def, W_Symbol):
            raise SchemeSyntaxError

        w_syntax_rules = lst.get_cdr_as_pair().car
        w_transformer = w_syntax_rules.eval(ctx)
        if not isinstance(w_transformer, W_Transformer):
            raise SchemeSyntaxError

        w_macro = W_DerivedMacro(w_def.name, w_transformer)
        ctx.set(w_def.name, w_macro)
        return w_macro #undefined
 
class LetSyntax(W_Macro):
    _symbol_name = "let-syntax"

    def call_tr(self, ctx, lst):
        #let uses eval_body, so it is tail-recursive aware
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            w_transformer = w_def.get_cdr_as_pair().car.eval(ctx)
            if not isinstance(w_transformer, W_Transformer):
                raise SchemeSyntaxError

            w_name = w_def.car
            if not isinstance(w_name, W_Symbol):
                raise SchemeSyntaxError

            w_macro = W_DerivedMacro(w_name.name, w_transformer)

            local_ctx.put(w_name.name, w_macro)
            w_formal = w_formal.cdr

        return Body(lst.cdr).eval_tr(local_ctx)

class ContinuationReturn(SchemeException):
    def __init__(self, result):
        self.result = result

class ContinuationFrame(object):
    def __init__(self, callable, continuation, evaluated_args = [], enum=0):
        assert hasattr(callable, "continue_tr")
        self.callable = callable
        assert isinstance(continuation, W_Root)
        self.continuation = continuation
        assert isinstance(evaluated_args, list)
        self.evaluated_args = evaluated_args
        self.evaluated_args_num = enum

    def run(self, ctx, arg):
        elst = self.evaluated_args[:self.evaluated_args_num]
        elst.append(arg)
        print self.callable.to_string(), elst, self.continuation
        return self.callable.continue_tr(ctx, self.continuation, elst, True)

class Continuation(W_Procedure):
    def __init__(self, ctx, continuation):
        self.closure = ctx #to .copy() ot not to .copy()
        #copy of continuation stack
        self.cont_stack = continuation[:]
        try:
            self.continuation = self.cont_stack.pop()
        except IndexError:
            #continuation captured on top-level
            self.continuation = None

    def to_string(self):
        return "#<continuation -> %s>" % (self.continuation,)

    def procedure_tr(self, ctx, lst):
        if len(lst) == 0:
            lst.append(w_undefined)

        print "Continuation called", self.cont_stack
        self.closure.cont_stack = self.cont_stack[:]
        cont = self.continuation
        if cont is None:
            raise ContinuationReturn(lst[0])

        return cont.run(self.closure, lst[0])

class CallCC(W_Procedure):
    _symbol_name = "call/cc"

    def procedure_tr(self, ctx, lst):
        if len(lst) != 1 or not isinstance(lst[0], W_Procedure):
            raise SchemeSyntaxError

        w_lambda = lst[0]
        cc = Continuation(ctx, ctx.cont_stack)
        return w_lambda.call_tr(ctx, W_Pair(cc, w_nil))

