
import math
from pypy.lang.js.jsparser import parse, parse_bytecode
from pypy.lang.js.jsobj import *
from pypy.rlib.parsing.ebnfparse import Symbol, Nonterminal

DEBUG = False

class Node(object):
    def init_common(self, type='', value='', lineno=0, start=0, end=0):
        self.type = type
        self.value = value
        self.lineno = lineno
        self.start = start
        self.end = end
        
    def eval(self, ctx):
        raise NotImplementedError

    def execute(self, ctx):
        raise NotImplementedError
    
    def get_literal(self):
        raise NotImplementedError
    
    def get_args(self, ctx):
        raise NotImplementedError
        

class Statement(Node):
    pass

class Expression(Statement):
    def eval(self, ctx):
        return W_Root()

    def execute(self, ctx):
        return self.eval(ctx)

class BinaryOp(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    
class BinaryComparisonOp(BinaryOp):
    """super class for binary operators"""
    def eval(self, ctx):
        s2 = self.left.eval(ctx).GetValue()
        s4 = self.right.eval(ctx).GetValue()
        if DEBUG:
            print "bincomp, op1 and op2 ", s2, s4
        return self.decision(ctx, s2, s4)
    
    def decision(self, ctx, op1, op2):
        raise NotImplementedError

class BinaryLogicOp(BinaryOp):
    """super class for binary operators"""
    pass

def writer(x):
    print x

def load_source(script_source):
    temp_tree = parse(script_source)
    return from_tree(temp_tree)

def load_bytecode(bytecode):
    temp_tree = parse_bytecode(bytecode)
    return from_tree(temp_tree)

def evaljs(ctx, args, this):
    if len(args) >= 1:
        code = args[0]
    else:
        code = W_String('')
    return load_source(code.ToString()).execute(ctx)

def printjs(ctx, args, this):
    writer(",".join([i.GetValue().ToString() for i in args]))
    return w_Undefined

def objectconstructor(ctx, args, this):
    return W_Object()

def isnanjs(ctx, args, this):
    return W_Boolean(args[0].ToNumber() == NaN)

def booleanjs(ctx, args, this):
    if len(args) > 0:
        return W_Boolean(args[0].ToBoolean())
    return W_Boolean(False)

def numberjs(ctx, args, this):
    if len(args) > 0:
        return W_Number(args[0].ToNumber())
    return W_Number(0)
        
def absjs(ctx, args, this):
    return W_Number(abs(args[0].ToNumber()))

def floorjs(ctx, args, this):
    return W_Number(math.floor(args[0].ToNumber()))

def versionjs(ctx, args, this):
    return w_Undefined

class Interpreter(object):
    """Creates a js interpreter"""
    def __init__(self):
        w_Global = W_Object()
        ctx = global_context(w_Global)

        w_ObjPrototype = W_Object(Prototype=None, Class='Object')
        
        #Function stuff
        w_Function = W_Object(ctx=ctx, Class='Function', 
                              Prototype=w_ObjPrototype)
        w_Function.Put('prototype', w_Function, dd=True, de=True, ro=True)
        w_Function.Put('constructor', w_Function)
        
        #Object stuff
        w_Object = W_Builtin(Prototype=w_Function)
        w_Object.set_builtin_call(objectconstructor)
        w_Object.Put('length', W_Number(1), ro=True, dd=True)
        w_Object.Put('prototype', w_ObjPrototype, dd=True, de=True, ro=True)
        w_ObjPrototype.Put('constructor', w_Object)
        #And some other stuff
        
        #Math
        w_math = W_Object(Class='Math')
        w_Global.Put('Math', w_math)
        w_math.Put('abs', W_Builtin(absjs, Class='function'))
        w_math.Put('floor', W_Builtin(floorjs, Class='function'))
        
        
        #Global Properties
        w_Global.Put('Object', w_Object)
        w_Global.Put('Function', w_Function)
        w_Global.Put('Array', W_Array())
        w_Global.Put('version', W_Builtin(versionjs))
        
        w_Number = W_Builtin(numberjs, Class="Number")
        w_Number.Put('NaN', W_Number(NaN))
        w_Number.Put('POSITIVE_INFINITY', W_Number(Infinity))
        w_Number.Put('NEGATIVE_INFINITY', W_Number(-Infinity))
        
        w_Global.Put('Number', w_Number)
        w_Global.Put('eval', W_Builtin(evaljs))
        w_Global.Put('print', W_Builtin(printjs))
        w_Global.Put('isNaN', W_Builtin(isnanjs))
        w_Global.Put('Boolean', W_Builtin(booleanjs, Class="Boolean"))

        w_Global.Put('NaN', W_Number(NaN))
        w_Global.Put('Infinity', W_Number(Infinity))
        w_Global.Put('undefined', w_Undefined)
        
        
        self.global_context = ctx
        self.w_Global = w_Global
        self.w_Object = w_Object

    def run(self, script):
        """run the interpreter"""
        return script.execute(self.global_context)

class PropertyInit(Node):
    def __init__(self, name, value):
        self.nameinit = name
        self.valueinit = value
    
    def __repr__(self):
        return "<%s : %s>"%(str(self.namein), str(self.value))


class Array(Expression):
    def __init__(self, items=()):
        self.items = items

    def eval(self, ctx):
        #d = dict(enumerate(self.items))
        d = {}
        for i in range(len(self.items)):
            d[i] = self.items[i]
        return W_Array(d)


class Assign(Expression):
    def __init__(self, LHSExp, AssignmentExp):
        self.LHSExp = LHSExp
        self.AssignmentExp = AssignmentExp
    
    def eval(self, ctx):
        v1 = self.LHSExp.eval(ctx)
        v3 = self.AssignmentExp.eval(ctx).GetValue()
        v1.PutValue(v3, ctx)
        return v3


class Block(Statement):
    def __init__(self, nodes):
        self.nodes = nodes

    def execute(self, ctx):
        try:
            last = w_Undefined
            for node in self.nodes:
                last = node.execute(ctx)
            return last
        except ExecutionReturned, e:
            if e.type == 'return':
                return e.value
            else:
                raise e

class Unconditional(Statement):
    def __init__(self, targtype, targlineno, targstart):
        self.targtype = targtype
        self.targlineno = targlineno
        self.targstart = targstart
        
class Break(Unconditional):
    def execute(self, ctx):
        raise ExecutionReturned('break', None, None)

class Continue(Unconditional):
    def execute(self, ctx):
        raise ExecutionReturned('continue', None, None)

class Call(Expression):
    def __init__(self, identifier, arglist):
        self.identifier = identifier
        self.arglist = arglist

    def eval(self, ctx):
        r1 = self.identifier.eval(ctx)
        r2 = self.arglist.eval(ctx)
        r3 = r1.GetValue()
        if isinstance(r1, W_Reference):
            r6 = r1.GetBase()
        else:
            r6 = None
        if isinstance(r2, ActivationObject):
            r7 = None
        else:
            r7 = r6
        retval = r3.Call(ctx=ctx, args=r2.get_args(), this=r7)
        return retval


class Comma(BinaryOp):
    def eval(self, ctx):
        self.left.eval(ctx)
        return self.right.eval(ctx)


class Conditional(Expression):
    def __init__(self, logicalexpr, trueop, falseop):
        self.logicalexpr = logicalexpr
        self.trueop = trueop
        self.falseop = falseop
        
    def eval(self, ctx):
        cond = self.logicalexpr.eval(ctx).GetValue().ToBoolean()
        if cond == True:
            return self.trueop.eval(ctx).GetValue()
        else:
            return self.falseop.eval(ctx).GetValue()


class Dot(BinaryOp):
    def eval(self, ctx):
        w_obj = self.left.eval(ctx).GetValue().ToObject()
        name = self.right.eval(ctx).GetPropertyName()
        return W_Reference(name, w_obj)

class Function(Expression):
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body

    def eval(self, ctx):
       w_obj = W_Object(ctx=ctx, callfunc = self)
       return w_obj

class Identifier(Expression):
    def __init__(self, name, initialiser=None):
        self.name = name
        self.initialiser = initialiser
        
    def __str__(self):
        return "<id %s init: %s>"%(str(self.name), str(self.initialiser))
    
    def eval(self, ctx):
        if self.initialiser is not None:
            ref = ctx.resolve_identifier(self.name)
            ref.PutValue(self.initialiser.eval(ctx).GetValue(), ctx)
        return ctx.resolve_identifier(self.name)
    
    def get_literal(self):
        return self.name


class If(Statement):
    def __init__(self, condition, thenPart=None, elsePart=None):
        self.condition = condition
        self.thenPart = thenPart
        self.elsePart = elsePart

    def execute(self, ctx):
        temp = self.condition.eval(ctx).GetValue()
        if temp.ToBoolean():
            return self.thenPart.execute(ctx)
        else:
            return self.elsePart.execute(ctx)

class Group(Expression):
    def __init__(self, expr):
        self.expr = expr

    def eval(self, ctx):
        return self.expr.eval(ctx)

def ARC(ctx, x, y):
    """
    Implements the Abstract Relational Comparison x < y
    Still not 100% to the spec
    """
    # TODO complete the funcion with strings comparison
    s1 = x.ToPrimitive(ctx, 'Number')
    s2 = y.ToPrimitive(ctx, 'Number')
    if not (isinstance(s1, W_String) and isinstance(s2, W_String)):
        s4 = s1.ToNumber()
        s5 = s2.ToNumber()
        if s4 == NaN or s5 == NaN:
            return -1
        if s4 < s5:
            return 1
        else:
            return 0
    else:
        return -1

class Or(BinaryLogicOp):
    def eval(self, ctx):
        s2 = self.left.eval(ctx).GetValue()
        if s2.ToBoolean():
            return s2
        s4 = self.right.eval(ctx).GetValue()
        return s4

class And(BinaryLogicOp):
    def eval(self, ctx):
        s2 = self.left.eval(ctx).GetValue()
        if not s2.ToBoolean():
            return s2
        s4 = self.right.eval(ctx).GetValue()
        return s4

class Ge(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        s5 = ARC(ctx, op1, op2)
        if s5 in (-1, 1):
            return W_Boolean(False)
        else:
            return W_Boolean(True)

class Gt(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        s5 = ARC(ctx, op2, op1)
        if s5 == -1:
            return W_Boolean(False)
        else:
            return W_Boolean(s5)

class Le(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        s5 = ARC(ctx, op2, op1)
        if s5 in (-1, 1):
            return W_Boolean(False)
        else:
            return W_Boolean(True)

class Lt(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        s5 = ARC(ctx, op1, op2)
        if s5 == -1:
            return W_Boolean(False)
        else:
            return W_Boolean(s5)

def AEC(x, y):
    """
    Implements the Abstract Equality Comparison x == y
    not following the specs yet
    """
    objtype = x.GetValue().type()
    if objtype == y.GetValue().type():
        if objtype == "undefined" or objtype == "null":
            return True
        
    if isinstance(x, W_String) and isinstance(y, W_String):
        r = x.ToString() == y.ToString()
    else:
        r = x.ToNumber() == y.ToNumber()
    return r

class Eq(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        return W_Boolean(AEC(op1, op2))

class Ne(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        return W_Boolean(not AEC(op1, op2))


class In(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        if not isinstance(op2, W_Object):
            raise ThrowException(W_String("TypeError"))
        name = op1.ToString()
        return W_Boolean(op2.HasProperty(name))

class Increment(Expression):
    def __init__(self, op):
        self.op = op
    
    def eval(self, ctx):
        thing = self.op.eval(ctx)
        val = thing.GetValue()
        x = val.ToNumber()
        resl = Plus(None, None).decision(ctx, W_Number(x), W_Number(1))
        thing.PutValue(resl, ctx)
        return resl

class Index(Expression):
    def __init__(self, left, expr):
        self.left = left
        self.expr = expr

    def eval(self, ctx):
        w_obj = self.left.eval(ctx).GetValue().ToObject()
        name= self.expr.eval(ctx).GetValue().ToString()
        return W_Reference(name, w_obj)

class List(Node):
    def __init__(self, nodes):
        self.nodes = nodes
        
    def eval(self, ctx):
        return W_List([node.eval(ctx).GetValue() for node in self.nodes])

class Minus(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        x = op1.ToNumber()
        y = op2.ToNumber()
        return W_Number(x - y)

class New(Expression):
    def __init__(self, newexpr):
        self.newexpr = newexpr

    def eval(self, ctx):
        x = self.newexpr.eval(ctx).GetValue()
        if not isinstance(x, W_PrimitiveObject):
            raise TypeError()
        
        return x.Construct(ctx=ctx)

class NewWithArgs(Expression):
    def __init__(self, newexpr, arglist):
        self.newexpr = newexpr
        self.arglist = arglist

    def eval(self, ctx):
        x = self.newexpr.eval(ctx).GetValue()
        if not isinstance(x, W_PrimitiveObject):
            raise TypeError()
        args = self.arglist.eval(ctx).get_args()
        return x.Construct(ctx=ctx, args=args)

class Null(Expression):
    def eval(self, ctx):
        return w_Null            

class Number(Expression):
    def __init__(self, num):
        self.num = num

    def eval(self, ctx):
        return W_Number(self.num)
    
    def get_literal(self):
        return W_Number(self.num).ToString()

class ObjectInit(Expression):
    def __init__(self, properties):
        self.properties = properties

    def eval(self, ctx):
        w_obj = W_Object()
        for property in self.properties:
            name = property.nameinit.get_literal()
            w_expr = property.valueinit.eval(ctx).GetValue()
            w_obj.Put(name, w_expr)
        return w_obj

class Plus(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        prim_left = op1.ToPrimitive(ctx, 'Number')
        prim_right = op2.ToPrimitive(ctx, 'Number')
        if DEBUG:
            print "plus", self.left, op1, prim_left, "+", self.right, op2, prim_right
        if isinstance(prim_left, W_String) or isinstance(prim_right, W_String):
            str_left = prim_left.ToString()
            str_right = prim_right.ToString()
            return W_String(str_left + str_right)
        else:
            num_left = prim_left.ToNumber()
            num_right = prim_right.ToNumber()
            return W_Number(num_left + num_right)

class Mult(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        prim_left = op1.ToPrimitive(ctx, 'Number')
        prim_right = op2.ToPrimitive(ctx, 'Number')
        num_left = prim_left.ToNumber()
        num_right = prim_right.ToNumber()
        return W_Number(num_left * num_right)

class Div(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        prim_left = op1.ToPrimitive(ctx, 'Number')
        prim_right = op2.ToPrimitive(ctx, 'Number')
        num_left = prim_left.ToNumber()
        num_right = prim_right.ToNumber()
        return W_Number(num_left / num_right)

class Minus(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        prim_left = op1.ToPrimitive(ctx, 'Number')
        prim_right = op2.ToPrimitive(ctx, 'Number')
        num_left = prim_left.ToNumber()
        num_right = prim_right.ToNumber()
        return W_Number(num_left - num_right)


class Script(Statement):
    def __init__(self, nodes, var_decl, func_decl):
        self.nodes = nodes
        self.var_decl = var_decl
        self.func_decl = func_decl

    def execute(self, ctx):
        for var in self.var_decl:
            ctx.variable.Put(var.name, w_Undefined)
        for fun in self.func_decl:
            ctx.variable.Put(fun.name, fun.eval(ctx))

        try:
            last = w_Undefined
            for node in self.nodes:
                last = node.execute(ctx)
            return last
        except Exception, e:
            if isinstance(e, ExecutionReturned) and e.type == 'return':
                return e.value
            else:
                print "exeception in line: %s, %s - %s"%(node.lineno, node.value, self)
                raise

class Semicolon(Statement):
    def __init__(self, expr = None):
        self.expr = expr

    def execute(self, ctx):
        if self.expr is None:
            return w_Undefined
        return self.expr.execute(ctx)

class String(Expression):
    def __init__(self, strval):
        self.strval = strval

    def eval(self, ctx):
        return W_String(self.strval)
    
    def get_literal(self):
        return W_String(self.strval).ToString()

class Return(Statement):
    def __init__(self, expr):
        self.expr = expr

    def execute(self, ctx):
        if self.expr is None:
            raise ExecutionReturned('return', None, None)
        else:
            raise ExecutionReturned('return', self.expr.eval(ctx), None)
                    

class Throw(Statement):
    def __init__(self, exception):
        self.exception = exception

    def execute(self, ctx):
        raise ThrowException(self.exception.eval(ctx))

class Try(Statement):
    # TODO: rewrite to use 'Undefined'
    def __init__(self, tryblock, catchblock, finallyblock, catchparam):
        self.tryblock = tryblock
        self.catchblock = catchblock
        self.finallyblock = finallyblock
        self.catchparam = catchparam

    def execute(self, ctx):
        e = None
        tryresult = w_Undefined
        try:
            tryresult = self.tryblock.execute(ctx)
        except ThrowException, excpt:
            e = excpt
            if self.catchblock is not None:
                obj = W_Object()
                obj.Put(self.catchparam, e.exception)
                ctx.push_object(obj)
                tryresult = self.catchblock.execute(ctx)
                ctx.pop_object()
        
        if self.finallyblock is not None:
            tryresult = self.finallyblock.execute(ctx)
        
        #if there is no catchblock reraise the exception
        if (e is not None) and (self.catchblock is None):
            raise e
        
        return tryresult

class Typeof(Expression):
    def __init__(self, op):
        self.op = op
    
    def eval(self, ctx):
        val = self.op.eval(ctx)
        if val.GetBase() is None:
            return W_String("undefined")
        return W_String(val.GetValue().type())

class Undefined(Statement):
    def execute(self, ctx):
        return None

class Vars(Statement):
    def __init__(self, nodes):
        self.nodes = nodes

    def execute(self, ctx):
        for var in self.nodes:
            var.execute(ctx)

class Void(Expression):
    def __init__(self, expr):
        self.expr = expr
    
    def eval(self, ctx):
        self.expr.eval(ctx)
        return w_Undefined

class While(Statement):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def execute(self, ctx):
        while self.condition.eval(ctx).ToBoolean():
            try:
                self.body.execute(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    continue

class For(Statement):
    def __init__(self, setup, condition, update, body):
        self.setup = setup
        self.condition = condition
        self.update = update
        self.body = body

    def execute(self, ctx):
        self.setup.eval(ctx)
        while self.condition.eval(ctx).ToBoolean():
            try:
                self.body.execute(ctx)
                self.update.eval(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    continue

class Boolean(Expression):
    def __init__(self, bool):
        self.bool = bool
    
    def eval(self, ctx):
        return W_Boolean(self.bool)

class Not(Expression):
    def __init__(self, op):
        self.op = op
    
    def eval(self, ctx):
        return W_Boolean(not self.op.eval(ctx).GetValue().ToBoolean())

class UMinus(Expression):
    def __init__(self, op):
        self.op = op
    
    def eval(self, ctx):
        return W_Number(-self.op.eval(ctx).GetValue().ToNumber())

def getlist(t):
    item = gettreeitem(t, 'length')
    if item is None:
        return []
    lgt = int(item.additional_info)
    output = [from_tree(gettreeitem(t, str(i))) for i in range(lgt)]
    return output
    
def gettreeitem(t, name):
    for x in t.children:
        if isinstance(x.children[0], Symbol):
            if x.children[0].additional_info == name:
                return x.children[1]
    return None


def from_tree(t):
    if t is None:
        return None
    tp = gettreeitem(t, 'type').additional_info
    if tp == 'ARRAY_INIT':
        node = Array(getlist(t))
    elif tp == 'ASSIGN':
        node = Assign(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'BLOCK':
        node = Block(getlist(t))
    elif tp == 'BREAK':
        targtype, targlineno, targstart = gettreeitem(t, 'target').additional_info.split(',')
        node = Break(targtype, targlineno, targstart)
    elif tp == 'CALL':
        node = Call(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'COMMA':
        node = Comma(from_tree(gettreeitem(t, '0')),from_tree(gettreeitem(t, '1')))
    elif tp == 'CONDITIONAL':
        node = Conditional(from_tree(gettreeitem(t, '0')),
                        from_tree(gettreeitem(t, '1')),
                        from_tree(gettreeitem(t, '2')))
    elif tp == 'CONTINUE':
        targtype, targlineno, targstart = gettreeitem(t, 'target').additional_info.split(',')
        node = Continue(targtype, targlineno, targstart)
    elif tp == 'DOT':
        node = Dot(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'EQ':
        node = Eq(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'OR':
        node = Or(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'AND':
        node = And(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'FOR':
        setup = from_tree(gettreeitem(t, 'setup'))
        condition = from_tree(gettreeitem(t, 'condition'))
        update = from_tree(gettreeitem(t, 'update'))
        body = from_tree(gettreeitem(t, 'body'))
        node = For(setup, condition, update, body)
    elif tp == 'FUNCTION':        
        namesimb = gettreeitem(t, 'name')
        name = None
        if namesimb is not None:
            name = namesimb.additional_info
        body = from_tree(gettreeitem(t, 'body'))
        if gettreeitem(t, 'params').additional_info == '':
            params = []
        else:
            params = gettreeitem(t, 'params').additional_info.split(',')
        f = Function(name, params, body)
        node = f
    elif tp == 'GROUP':
        node = Group(from_tree(gettreeitem(t, '0')))
    elif tp == 'GE':
        node = Ge(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'GT':
        node = Gt(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'IDENTIFIER':
        node = Identifier(gettreeitem(t, 'value').additional_info, from_tree(gettreeitem(t, 'initializer')))
    elif tp == 'IF':
        condition = from_tree(gettreeitem(t, 'condition'))
        thenPart = gettreeitem(t, 'thenPart')
        if isinstance(thenPart, Nonterminal):
            thenPart = from_tree(thenPart)
        else:
            thenPart = Undefined()

        elsePart = gettreeitem(t, 'elsePart')
        if isinstance(elsePart, Nonterminal):
            elsePart = from_tree(elsePart)
        else:
            elsePart = Undefined()
        node = If(condition,thenPart,elsePart)
    elif tp == 'IN':
        node = In(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'INCREMENT':
        node = Increment(from_tree(gettreeitem(t, '0')))
    elif tp == 'INDEX':
        node = Index(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'LIST':
        node = List(getlist(t))
    elif tp == 'LE':
        node = Le(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'LT':
        node = Lt(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'MINUS':
        node = Minus(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'NE':
        node = Ne(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'NEW':
        node = New(from_tree(gettreeitem(t, '0')))
    elif tp == 'NEW_WITH_ARGS':
        node = NewWithArgs(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'NULL':
        node = Null()
    elif tp == 'NUMBER':
        node = Number(float(gettreeitem(t, 'value').additional_info))
    elif tp == 'OBJECT_INIT':
        node = ObjectInit(getlist(t))
    elif tp == 'PLUS':
        node = Plus(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'MUL':
        node = Mult(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'DIV':
        node = Div(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'MIN':
        node = Minus(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))    
    elif tp == 'PROPERTY_INIT':
        node = PropertyInit(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'RETURN':
        valit = gettreeitem(t, 'value')
        if not isinstance(valit, Symbol):
            node = Return(from_tree(valit))
        else:
            node = Return(None)
    elif tp == 'SCRIPT':
        f = gettreeitem(t, 'funDecls')
        if f.symbol == "dict":
            func_decl = [from_tree(f),]
        elif f.symbol == "list":
            func_decl = [from_tree(x) for x in f.children]
        else:
            func_decl = []
        
        v = gettreeitem(t, 'varDecls')
        if v.symbol == "dict":
            var_decl = [from_tree(v),]
        elif v.symbol == "list":
            var_decl = [from_tree(x) for x in v.children]
        else:
            var_decl = []

        node = Script(getlist(t), var_decl, func_decl)
    elif tp == 'SEMICOLON':
        expr = gettreeitem(t, 'expression')
        if isinstance(expr, Symbol):
            node = Semicolon()
        else:
            node = Semicolon(from_tree(expr))
    elif tp == 'STRING':
        node = String(gettreeitem(t, 'value').additional_info)
    elif tp == 'THIS':
        node = Identifier(gettreeitem(t, 'value').additional_info)
    elif tp == 'THROW':
        node = Throw(from_tree(gettreeitem(t, 'exception')))
    elif tp == 'TRY':
        finallyblock = None
        catchblock = None
        catchparam = ''
        final = gettreeitem(t, 'finallyBlock')
        if final is not None:
            finallyblock = from_tree(final)
        catch = gettreeitem(t, 'catchClauses')
        if catch is not None:
            #multiple catch clauses is a spidermonkey extension
            catchblock = from_tree(gettreeitem(catch, 'block'))
            catchparam = gettreeitem(catch, 'varName').additional_info
        node = Try(from_tree(gettreeitem(t, 'tryBlock')), catchblock, finallyblock, catchparam)
    elif tp == 'TYPEOF':
        node = Typeof(from_tree(gettreeitem(t, '0')))
    elif tp == 'VAR':
        node = Vars(getlist(t))
    elif tp == 'VOID':
        node = Void(from_tree(gettreeitem(t, '0')))
    elif tp == 'WHILE':
        body = from_tree(gettreeitem(t, 'body'))
        condition = from_tree(gettreeitem(t, 'condition'))
        node = While(condition, body)
    elif tp == 'TRUE':
        node = Boolean(True)
    elif tp == 'FALSE':
        node = Boolean(False)
    elif tp == 'NOT':
        node = Not(from_tree(gettreeitem(t, '0')))
    elif tp == 'UNARY_MINUS':
        node = UMinus(from_tree(gettreeitem(t, '0')))
    else:
        raise NotImplementedError("Dont know how to handle %s" % tp)
    
    if tp == 'SCRIPT':
        start = 0
        end = 0
    else:
        start = int(gettreeitem(t, 'start').additional_info)
        end = int(gettreeitem(t, 'end').additional_info)
    
    if tp == 'SCRIPT' or tp == 'RETURN':
        value = gettreeitem(t, 'type')
    else:
        value = gettreeitem(t, 'value').additional_info
    
    node.init_common(gettreeitem(t, 'type').additional_info, value,
    int(gettreeitem(t, 'lineno').additional_info), start, end)
    return node

    
