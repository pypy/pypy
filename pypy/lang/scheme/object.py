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
            #XXX cont_stack copy to be cont. friendly
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

class Apply(W_Procedure):
    _symbol_name = "apply"

    def procedure_tr(self, ctx, lst):
        if len(lst) != 2:
            raise WrongArgsNumber

        (w_procedure, w_lst) = lst
        if not isinstance(w_procedure, W_Procedure):
            raise WrongArgType(w_procedure, "Procedure")

        if not isinstance(w_lst, W_List):
            raise WrongArgType(w_lst, "List")

        return w_procedure.call_tr(ctx, w_lst)

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
# Equivalnece Predicates
##
class EquivalnecePredicate(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) != 2:
            raise WrongArgsNumber
        (a, b) = lst
        return W_Boolean(self.predicate(a, b))

class EqP(EquivalnecePredicate):
    _symbol_name = "eq?"

    def predicate(self, a, b):
        return a.eq(b)

class EqvP(EquivalnecePredicate):
    _symbol_name = "eqv?"

    def predicate(self, a, b):
        return a.eqv(b)

class EqualP(EquivalnecePredicate):
    _symbol_name = "equal?"

    def predicate(self, a, b):
        return a.equal(b)

##
# Number Predicates
##
class PredicateNumber(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) != 1:
            raise WrongArgsNumber

        w_obj = lst[0]
        if not isinstance(w_obj, W_Number):
            raise WrongArgType(w_obj, "Number")

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

##
# Type Pradicates
##
class TypePredicate(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) != 1:
            raise WrongArgsNumber

        return W_Boolean(self.predicate(lst[0]))

class BooleanP(TypePredicate):
    _symbol_name = "boolean?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Boolean)

class SymbolP(TypePredicate):
    _symbol_name = "symbol?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Symbol)

class PairP(TypePredicate):
    _symbol_name = "pair?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Pair)

class ProcedureP(TypePredicate):
    _symbol_name = "procedure?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Procedure)

##
# Input/Output procedures
##
#class Display(W_Procedure):
#    _symbol_name = "display"
#
#    def procedure(self, ctx, lst):
#        if len(lst) == 1:
#            obj = lst[0]
#        elif len(lst) == 2:
#            (obj, port) = lst
#            raise NotImplementedError
#        else:
#            raise WrongArgsNumber
#
#        print obj.to_string()
#        return w_undefined

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

    def continue_tr(self, ctx, lst, elst, cnt=True):
        assert cnt == True
        w_symbol = lst
        w_val = elst[0]
        ctx.ssete(w_symbol, w_val)
        if len(ctx.cont_stack) == 0:
            raise ContinuationReturn(w_val)

        cont = ctx.cont_stack.pop()
        return cont.run(ctx, w_val)

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        w_symbol = lst.car

        w_val = lst.get_cdr_as_pair().car.eval_cf(ctx, self, w_symbol)
        ctx.ssete(w_symbol, w_val)
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
                    self, w_formal.cdr, [elst[0], w_def.car], 2)
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

class DictWrapper(W_Root):
    def __init__(self, w_dict):
        self.d = w_dict

class Letrec(W_Macro):
    _symbol_name = "letrec"

    def continue_tr(self, ctx, lst, elst, cnt=True):
        ctx = ctx.copy()
        (body, name_symb, name_val, cont_val) = elst
        assert isinstance(name_symb, DictWrapper)
        assert isinstance(name_val, DictWrapper)
        assert isinstance(lst, W_Symbol)

        cont_name = lst.name
        for (name, w_val) in name_val.d.items():
            if name == cont_name:
                ctx.ssete(lst, cont_val)
            else:
                ctx.ssete(name_symb.d[name], w_val)

        w_result = body.eval(ctx)

        if len(ctx.cont_stack) == 0:
            raise ContinuationReturn(w_result)

        cont = ctx.cont_stack.pop()
        return cont.run(ctx, w_result)

    def call_tr(self, ctx, lst):
        """let uses eval_body, so it is tail-recursive aware"""
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        body = Body(lst.cdr)
        map_name_expr = {}
        map_name_symb = {}
        w_name_symb = DictWrapper(map_name_symb)
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            name = w_def.car.to_string()
            map_name_expr[name] = w_def.get_cdr_as_pair().car
            map_name_symb[name] = w_def.car
            local_ctx.sbind(w_def.car)
            w_formal = w_formal.cdr

        map_name_val = {}
        w_name_val = DictWrapper(map_name_val)
        for (name, expr) in map_name_expr.items():
            map_name_val[name] = expr.eval_cf(local_ctx, self,
                    map_name_symb[name],
                    [body, w_name_symb, w_name_val], 3)

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

