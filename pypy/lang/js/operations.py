# encoding: utf-8
"""
operations.py
Implements the javascript operations nodes for the interpretation tree
"""

#XXX * imports are bad
from pypy.lang.js.jsobj import *
from pypy.rlib.parsing.ebnfparse import Symbol, Nonterminal
from pypy.rlib.rarithmetic import r_uint, intmask
from constants import unescapedict, SLASH

import sys
import os

class Position(object):
    def __init__(self, lineno=-1, start=-1, end=-1):
        self.lineno = lineno
        self.start = start
        self.end = end

    
class Node(object):
    """
    Node is the base class for all the other nodes.
    """
    def __init__(self, pos):
        """
        Initializes the content from the AST specific for each node type
        """
        raise NotImplementedError
        
    def eval(self, ctx):
        """
        Used for expression evaluation
        """
        raise NotImplementedError

    def execute(self, ctx):
        """
        Called on statament execution
        """
        raise NotImplementedError
    
    def get_literal(self):
        raise NotImplementedError
    
    def get_args(self, ctx):
        raise NotImplementedError
    
    def __str__(self):
        return "%s()"%(self.__class__)

class Statement(Node):
    def __init__(self, pos):
        self.pos = pos

class Expression(Statement):
    def execute(self, ctx):
        return self.eval(ctx)

class ListOp(Expression):
    def __init__(self, pos, nodes):
        self.pos = pos
        self.nodes = nodes
        
class UnaryOp(Expression):
    def __init__(self, pos, expr, postfix=False):
        self.pos = pos
        #assert isinstance(expr, Node)
        self.expr = expr
        self.postfix = postfix

class BinaryOp(Expression):
    def __init__(self, pos, left, right):
        self.pos = pos
        self.left = left
        self.right = right
    
class BinaryComparisonOp(BinaryOp):
    def eval(self, ctx):
        s2 = self.left.eval(ctx).GetValue()
        s4 = self.right.eval(ctx).GetValue()
        return self.decision(ctx, s2, s4)
    
    def decision(self, ctx, op1, op2):
        raise NotImplementedError

class BinaryBitwiseOp(BinaryOp):
    def eval(self, ctx):
        s5 = self.left.eval(ctx).GetValue().ToInt32()
        s6 = self.right.eval(ctx).GetValue().ToInt32()
        return self.decision(ctx, s5, s6)
    
    def decision(self, ctx, op1, op2):
        raise NotImplementedError

class Undefined(Statement):
    def eval(self, ctx):
        return w_Undefined
    
    def execute(self, ctx):
        return w_Undefined

astundef = Undefined(Position())

class PropertyInit(BinaryOp):
    pass

class Array(ListOp):
    def eval(self, ctx):
        proto = ctx.get_global().Get('Array').Get('prototype')
        array = W_Array(ctx, Prototype=proto, Class = proto.Class)
        for i in range(len(self.nodes)):
            array.Put(str(i), self.nodes[i].eval(ctx).GetValue())
        return array

class Assignment(Expression):
    def __init__(self, pos, left, right, atype):
        self.pos = pos
        self.left = left
        self.right = right
        self.type = atype

    def eval(self, ctx):
        v1 = self.left.eval(ctx)
        v3 = self.right.eval(ctx).GetValue()
        op = self.type
        if op == "=":
            val = v3
        elif op == "*=":
            val = mult(ctx, v1.GetValue(), v3)
        elif op == "+=":
            val = plus(ctx, v1.GetValue(), v3)
        elif op == "-=":
            val = sub(ctx, v1.GetValue(), v3)
        elif op == "/=":
            val = division(ctx, v1.GetValue(), v3)
        elif op == "%=":
            val = mod(ctx, v1.GetValue(), v3)
        elif op == "&=":
            val = W_Number(v1.GetValue().ToInt32() & v3.ToInt32())
        elif op == "|=":
            val = W_Number(v1.GetValue().ToInt32() | v3.ToInt32())
        elif op == "^=":
            val = W_Number(v1.GetValue().ToInt32() ^ v3.ToInt32())
        else:
            print op
            raise NotImplementedError()
        
        v1.PutValue(val, ctx)
        return val
    

class Block(Statement):
    def __init__(self, pos, nodes):
        self.pos = pos
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
    

class BitwiseAnd(BinaryBitwiseOp):
    def decision(self, ctx, op1, op2):
        return W_Number(op1&op2)
    

class BitwiseNot(UnaryOp):
    def eval(self, ctx):
        op1 = self.expr.eval(ctx).GetValue().ToInt32()
        return W_Number(~op1)
    

class BitwiseOr(BinaryBitwiseOp):
    def decision(self, ctx, op1, op2):
        return W_Number(op1|op2)
    


class BitwiseXor(BinaryBitwiseOp):
    def decision(self, ctx, op1, op2):
        return W_Number(op1^op2)
    

class Unconditional(Statement):
    def __init__(self, pos, target):
        self.pos = pos
        self.target = target
    
class Break(Unconditional):
    def execute(self, ctx):
        raise ExecutionReturned('break', None, None)
    

class Continue(Unconditional):
    def execute(self, ctx):
        raise ExecutionReturned('continue', None, None)
    


class Call(BinaryOp):
    def eval(self, ctx):
        r1 = self.left.eval(ctx)
        r2 = self.right.eval(ctx)
        r3 = r1.GetValue()
        if not isinstance(r3, W_PrimitiveObject):
            raise ThrowException(W_String("it is not a callable"))
            
        if isinstance(r1, W_Reference):
            r6 = r1.GetBase()
        else:
            r6 = None
        if isinstance(r2, ActivationObject):
            r7 = None
        else:
            r7 = r6
        
        try:
            res = r3.Call(ctx=ctx, args=r2.get_args(), this=r7)
        except JsTypeError:
            raise ThrowException(W_String('it is not a function'))
        return res

class Comma(BinaryOp):
    def eval(self, ctx):
        self.left.eval(ctx)
        return self.right.eval(ctx)
    

class Conditional(Expression):
    def __init__(self, pos, condition, truepart, falsepart):
        self.pos = pos
        self.condition = condition
        self.truepart = truepart
        self.falsepart = falsepart
    
    def eval(self, ctx):
        if self.condition.eval(ctx).GetValue().ToBoolean():
            return self.truepart.eval(ctx).GetValue()
        else:
            return self.falsepart.eval(ctx).GetValue()
    

class Member(BinaryOp):
    "this is for object[name]"
    def eval(self, ctx):
        w_obj = self.left.eval(ctx).GetValue().ToObject(ctx)
        name = self.right.eval(ctx).GetValue().ToString(ctx)
        return W_Reference(name, w_obj)
    

class MemberDot(BinaryOp):
    "this is for object.name"
    def eval(self, ctx):
        w_obj = self.left.eval(ctx).GetValue().ToObject(ctx)
        name = self.right.get_literal()
        return W_Reference(name, w_obj)
    

class FunctionStatement(Statement):
    def __init__(self, pos, name, params, body):
        self.pos = pos
        self.name = name
        self.body = body
        self.params = params
        
    def eval(self, ctx):
        proto = ctx.get_global().Get('Function').Get('prototype')
        w_func = W_Object(ctx=ctx, Prototype=proto, Class='Function', callfunc=self)
        w_func.Put('length', W_Number(len(self.params)))
        w_obj = create_object(ctx, 'Object')
        w_obj.Put('constructor', w_func, de=True)
        w_func.Put('prototype', w_obj)
        return w_func
    
    def execute(self, ctx):
        return self.eval(ctx)
    

class Identifier(Expression):
    def __init__(self, pos, name):
        self.pos = pos
        self.name = name
    
    def eval(self, ctx):
        return ctx.resolve_identifier(self.name)
    
    def get_literal(self):
        return self.name
    

class This(Identifier):
    pass
    

class If(Statement):
    def __init__(self, pos, condition, thenpart, elsepart=astundef):
        self.pos = pos
        self.condition = condition
        self.thenPart = thenpart
        self.elsePart = elsepart

    def execute(self, ctx):
        temp = self.condition.eval(ctx).GetValue()
        if temp.ToBoolean():
            return self.thenPart.execute(ctx)
        else:
            return self.elsePart.execute(ctx)

class Group(UnaryOp):
    def eval(self, ctx):
        return self.expr.eval(ctx)

##############################################################################
#
# Binary logic comparison ops and suporting abstract operation
#
##############################################################################

def ARC(ctx, x, y):
    """
    Implements the Abstract Relational Comparison x < y
    Still not fully to the spec
    """
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
        s4 = s1.ToString(ctx)
        s5 = s2.ToString(ctx)
        if s4 < s5:
            return 1
        if s4 == s5:
            return 0
        return -1

class Or(BinaryOp):
    def eval(self, ctx):
        s2 = self.left.eval(ctx).GetValue()
        if s2.ToBoolean():
            return s2
        s4 = self.right.eval(ctx).GetValue()
        return s4
    

class And(BinaryOp):
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
    

##############################################################################
#
# Bitwise shifts
#
##############################################################################

class Ursh(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        a = op1.ToUInt32()
        b = op2.ToUInt32()
        return W_Number(a >> (b & 0x1F))

class Rsh(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        a = op1.ToInt32()
        b = op2.ToUInt32()
        return W_Number(a >> intmask(b & 0x1F))

class Lsh(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        a = op1.ToInt32()
        b = op2.ToUInt32()
        return W_Number(a << intmask(b & 0x1F))

##############################################################################
#
# Equality and unequality (== and !=)
#
##############################################################################


def AEC(ctx, x, y):
    """
    Implements the Abstract Equality Comparison x == y
    trying to be fully to the spec
    """
    type1 = x.type()
    type2 = y.type()
    if type1 == type2:
        if type1 == "undefined" or type1 == "null":
            return True
        if type1 == "number":
            n1 = x.ToNumber()
            n2 = y.ToNumber()
            nan_string = str(NaN)
            if str(n1) == nan_string or str(n2) == nan_string:
                return False
            if n1 == n2:
                return True
            return False
        elif type1 == "string":
            return x.ToString(ctx) == y.ToString(ctx)
        elif type1 == "boolean":
            return x.ToBoolean() == x.ToBoolean()
        return x == y
    else:
        #step 14
        if (type1 == "undefined" and type2 == "null") or \
           (type1 == "null" and type2 == "undefined"):
            return True
        if type1 == "number" and type2 == "string":
            return AEC(ctx, x, W_Number(y.ToNumber()))
        if type1 == "string" and type2 == "number":
            return AEC(ctx, W_Number(x.ToNumber()), y)
        if type1 == "boolean":
            return AEC(ctx, W_Number(x.ToNumber()), y)
        if type2 == "boolean":
            return AEC(ctx, x, W_Number(y.ToNumber()))
        if (type1 == "string" or type1 == "number") and \
            type2 == "object":
            return AEC(ctx, x, y.ToPrimitive(ctx))
        if (type2 == "string" or type2 == "number") and \
            type1 == "object":
            return AEC(ctx, x.ToPrimitive(ctx), y)
        return False
            
        
    objtype = x.GetValue().type()
    if objtype == y.GetValue().type():
        if objtype == "undefined" or objtype == "null":
            return True
        
    if isinstance(x, W_String) and isinstance(y, W_String):
        r = x.ToString(ctx) == y.ToString(ctx)
    else:
        r = x.ToNumber() == y.ToNumber()
    return r

class Eq(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        return W_Boolean(AEC(ctx, op1, op2))

class Ne(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        return W_Boolean(not AEC(ctx, op1, op2))


##############################################################################
#
# Strict Equality and unequality, usually means same place in memory
# or equality for primitive values
#
##############################################################################

def SEC(ctx, x, y):
    """
    Implements the Strict Equality Comparison x === y
    trying to be fully to the spec
    """
    type1 = x.type()
    type2 = y.type()
    if type1 != type2:
        return False
    if type1 == "undefined" or type1 == "null":
        return True
    if type1 == "number":
        n1 = x.ToNumber()
        n2 = y.ToNumber()
        nan_string = str(NaN)
        if str(n1) == nan_string or str(n2) == nan_string:
            return False
        if n1 == n2:
            return True
        return False
    if type1 == "string":
        return x.ToString(ctx) == y.ToString(ctx)
    if type1 == "boolean":
        return x.ToBoolean() == x.ToBoolean()
    return x == y

class StrictEq(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        return W_Boolean(SEC(ctx, op1, op2))

class StrictNe(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        return W_Boolean(not SEC(ctx, op1, op2))
    

class In(BinaryComparisonOp):
    """
    The in operator, eg: "property in object"
    """
    def decision(self, ctx, op1, op2):
        if not isinstance(op2, W_Object):
            raise ThrowException(W_String("TypeError"))
        name = op1.ToString(ctx)
        return W_Boolean(op2.HasProperty(name))

class Delete(UnaryOp):
    """
    the delete op, erases properties from objects
    """
    def eval(self, ctx):
        r1 = self.expr.eval(ctx)
        if not isinstance(r1, W_Reference):
            return W_Boolean(True)
        r3 = r1.GetBase()
        r4 = r1.GetPropertyName()
        return W_Boolean(r3.Delete(r4))
    

class Increment(UnaryOp):
    """
    ++value (prefix) and value++ (postfix)
    """
    def eval(self, ctx):
        thing = self.expr.eval(ctx)
        val = thing.GetValue()
        x = val.ToNumber()
        resl = plus(ctx, W_Number(x), W_Number(1))
        thing.PutValue(resl, ctx)
        if self.postfix:
            return val
        else:
            return resl
        

class Decrement(UnaryOp):
    """
    same as increment --value and value --
    """
    def eval(self, ctx):
        thing = self.expr.eval(ctx)
        val = thing.GetValue()
        x = val.ToNumber()
        resl = sub(ctx, W_Number(x), W_Number(1))
        thing.PutValue(resl, ctx)
        if self.postfix:
            return val
        else:
            return resl


class Index(BinaryOp):
    def eval(self, ctx):
        w_obj = self.left.eval(ctx).GetValue().ToObject(ctx)
        name= self.right.eval(ctx).GetValue().ToString(ctx)
        return W_Reference(name, w_obj)

class ArgumentList(ListOp):
    def eval(self, ctx):
        return W_List([node.eval(ctx).GetValue() for node in self.nodes])


##############################################################################
#
# Math Ops
#
##############################################################################

class BinaryNumberOp(BinaryOp):
    def eval(self, ctx):
        nleft = self.left.eval(ctx).GetValue().ToPrimitive(ctx, 'Number')
        nright = self.right.eval(ctx).GetValue().ToPrimitive(ctx, 'Number')
        result = self.mathop(ctx, nleft, nright)
        return result
    
    def mathop(self, ctx, n1, n2):
        raise NotImplementedError

def plus(ctx, nleft, nright):
    if isinstance(nleft, W_String) or isinstance(nright, W_String):
        sleft = nleft.ToString(ctx)
        sright = nright.ToString(ctx)
        return W_String(sleft + sright)
    else:
        fleft = nleft.ToNumber()
        fright = nright.ToNumber()
        return W_Number(fleft + fright)

def mult(ctx, nleft, nright):
    fleft = nleft.ToNumber()
    fright = nright.ToNumber()
    return W_Number(fleft * fright)

def mod(ctx, nleft, nright): # XXX this one is really not following spec
    ileft = nleft.ToInt32()
    iright = nright.ToInt32()
    return W_Number(ileft % iright)

def division(ctx, nleft, nright):
    fleft = nleft.ToNumber()
    fright = nright.ToNumber()
    return W_Number(fleft / fright)

def sub(ctx, nleft, nright):
    fleft = nleft.ToNumber()
    fright = nright.ToNumber()
    return W_Number(fleft - fright)


class Plus(BinaryNumberOp):
    def mathop(self, ctx, n1, n2):
        return plus(ctx, n1, n2)


class Mult(BinaryNumberOp):
    def mathop(self, ctx, n1, n2):
        return mult(ctx, n1, n2)


class Mod(BinaryNumberOp):
    def mathop(self, ctx, n1, n2):
        return mod(ctx, n1, n2)


class Division(BinaryNumberOp):
    def mathop(self, ctx, n1, n2):
        return division(ctx, n1, n2)


class Sub(BinaryNumberOp):
    def mathop(self, ctx, n1, n2):
        return sub(ctx, n1, n2)


class Null(Expression):
    def eval(self, ctx):
        return w_Null


##############################################################################
#
# Value and object creation
#
##############################################################################

def commonnew(ctx, obj, args):
    if not isinstance(obj, W_PrimitiveObject):
        raise ThrowException(W_String('it is not a constructor'))
    try:
        res = obj.Construct(ctx=ctx, args=args)
    except JsTypeError:
        raise ThrowException(W_String('it is not a constructor'))
    return res

class New(UnaryOp):
    def eval(self, ctx):
        x = self.expr.eval(ctx).GetValue()
        return commonnew(ctx, x, [])
    

class NewWithArgs(BinaryOp):
    def eval(self, ctx):
        x = self.left.eval(ctx).GetValue()
        args = self.right.eval(ctx).get_args()
        return commonnew(ctx, x, args)
    


class Number(Expression):
    def __init__(self, pos, num):
        self.pos = pos
        assert isinstance(num, float)
        self.num = num

    def eval(self, ctx):
        return W_Number(self.num)

class String(Expression):
    def __init__(self, pos, strval):
        self.pos = pos
        self.strval = self.string_unquote(strval)
    
    def eval(self, ctx):
        return W_String(self.strval)
    
    def get_literal(self):
        return W_String(self.strval).ToString()
    
    def string_unquote(self, string):
        temp = []
        stop = len(string)-1
        assert stop >= 0
        last = ""
        
        #removing the begining quotes (" or \')
        if string.startswith('"'):
            singlequote = False
        else:
            singlequote = True

        internalstring = string[1:stop]
        
        for c in internalstring:
            if last == SLASH:
                unescapeseq = unescapedict[last+c]
                temp.append(unescapeseq)
                c = ' ' # Could be anything
            elif c != SLASH:
                temp.append(c)
            last = c
        return ''.join(temp)
    

class ObjectInit(ListOp):
    def eval(self, ctx):
        w_obj = create_object(ctx, 'Object')
        for prop in self.nodes:
            name = prop.left.eval(ctx).GetPropertyName()
            w_expr = prop.right.eval(ctx).GetValue()
            w_obj.Put(name, w_expr)
        return w_obj

class SourceElements(Statement):
    """
    SourceElements nodes are found on each function declaration and in global code
    """
    def __init__(self, pos, var_decl, func_decl, nodes, sourcename = ''):
        self.pos = pos
        self.var_decl = var_decl
        self.func_decl = func_decl
        self.nodes = nodes
        self.sourcename = sourcename

    def execute(self, ctx):
        for varname in self.var_decl:
            ctx.variable.Put(varname, w_Undefined)
        for funcname, funccode in self.func_decl.items():
            ctx.variable.Put(funcname, funccode.eval(ctx))
        node = self
        
        try:
            last = w_Undefined
            for node in self.nodes:
                last = node.execute(ctx)
            return last
        except Exception, e:
            if isinstance(e, ExecutionReturned) and e.type == 'return':
                return e.value
            else:
                # TODO: proper exception handling
                print "%s:%d: %s"%(self.sourcename, node.pos.lineno, node)
                raise
    

class Program(Statement):
    def __init__(self, pos, body):
        self.pos = pos
        self.body = body

    def execute(self, ctx):
        return self.body.execute(ctx)
    

class Return(Statement):
    def __init__(self, pos, expr):
        self.pos = pos
        self.expr = expr
    
    def execute(self, ctx):
        if isinstance(self.expr, Undefined):
            raise ExecutionReturned('return', None, None)
        else:
            raise ExecutionReturned('return', self.expr.eval(ctx), None)
    

class Throw(Statement):
    def __init__(self, pos, exp):
        self.pos = pos
        self.exp = exp
    
    def execute(self, ctx):
        raise ThrowException(self.exp.eval(ctx).GetValue())

class Try(Statement):
    def __init__(self, pos, tryblock, catchparam, catchblock, finallyblock):
        self.pos = pos
        self.tryblock = tryblock
        self.catchparam = catchparam
        self.catchblock = catchblock
        self.finallyblock = finallyblock
    
    def execute(self, ctx):
        e = None
        tryresult = w_Undefined
        try:
            tryresult = self.tryblock.execute(ctx)
        except ThrowException, excpt:
            e = excpt
            if self.catchblock is not None:
                obj = W_Object()
                obj.Put(self.catchparam.get_literal(), e.exception)
                ctx.push_object(obj)
                tryresult = self.catchblock.execute(ctx)
                ctx.pop_object()
        
        if self.finallyblock is not None:
            tryresult = self.finallyblock.execute(ctx)
        
        #if there is no catchblock reraise the exception
        if (e is not None) and (self.catchblock is None):
            raise e
        
        return tryresult
    

class Typeof(UnaryOp):
    def eval(self, ctx):
        val = self.expr.eval(ctx)
        if isinstance(val, W_Reference) and val.GetBase() is None:
            return W_String("undefined")
        return W_String(val.GetValue().type())

class VariableDeclaration(Expression):
    def __init__(self, pos, identifier, expr=None):
        self.pos = pos
        self.identifier = identifier
        self.expr = expr
    
    def eval(self, ctx):
        name = self.identifier.get_literal()
        if self.expr is None:
            ctx.variable.Put(name, w_Undefined)
        else:
            ctx.variable.Put(name, self.expr.eval(ctx).GetValue())
        return self.identifier.eval(ctx)
    

class VariableDeclList(Expression):
    def __init__(self, pos, nodes):
        self.pos = pos
        self.nodes = nodes
    
    def eval(self, ctx):
        for var in self.nodes:
            var.eval(ctx)
        return w_Undefined
    
class Variable(Statement):
    def __init__(self, pos, body):
        self.pos = pos
        self.body = body
    
    def execute(self, ctx):
        return self.body.eval(ctx)

class Void(UnaryOp):
    def eval(self, ctx):
        self.expr.eval(ctx)
        return w_Undefined
    

class With(Statement):
    def __init__(self, pos, identifier, body):
        self.pos = pos
        self.identifier = identifier
        self.body = body

    def execute(self, ctx):
        obj = self.identifier.eval(ctx).GetValue().ToObject(ctx)
        ctx.push_object(obj)

        try:
            retval = self.body.execute(ctx)
        finally:
            ctx.pop_object()
        return retval


class WhileBase(Statement):
    def __init__(self, pos, condition, body):
        self.pos = pos
        self.condition = condition
        self.body = body

class Do(WhileBase):
    opcode = 'DO'
    
    def execute(self, ctx):
        try:
            self.body.execute(ctx)
        except ExecutionReturned, e:
            if e.type == 'break':
                return
            elif e.type == 'continue':
                pass
        while self.condition.eval(ctx).ToBoolean():
            try:
                self.body.execute(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    continue
    
class While(WhileBase):
    def execute(self, ctx):
        while self.condition.eval(ctx).ToBoolean():
            try:
                self.body.execute(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    continue
    

class ForVarIn(Statement):
    def __init__(self, pos, vardecl, lobject, body):
        self.pos = pos
        self.vardecl = vardecl
        self.object = lobject
        self.body = body
    
    def execute(self, ctx):
        self.vardecl.eval(ctx)
        obj = self.object.eval(ctx).GetValue().ToObject(ctx)
        for prop in obj.propdict.values():
            if prop.de:
                continue
            iterator = self.vardecl.eval(ctx)
            iterator.PutValue(prop.value, ctx)
            try:
                result = self.body.execute(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    continue
    

class ForIn(Statement):
    def __init__(self, pos, iterator, lobject, body):
        self.pos = pos
        #assert isinstance(iterator, Node)
        self.iterator = iterator
        self.object = lobject
        self.body = body

    def execute(self, ctx):
        obj = self.object.eval(ctx).GetValue().ToObject(ctx)
        for prop in obj.propdict.values():
            if prop.de:
                continue
            iterator = self.iterator.eval(ctx)
            iterator.PutValue(prop.value, ctx)
            try:
                result = self.body.execute(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    continue
    

class For(Statement):
    def __init__(self, pos, setup, condition, update, body):
        self.pos = pos
        self.setup = setup
        self.condition = condition
        self.update = update
        self.body = body
    
    def execute(self, ctx):
        self.setup.eval(ctx).GetValue()
        while self.condition.eval(ctx).ToBoolean():
            try:
                self.body.execute(ctx)
                self.update.eval(ctx)
            except ExecutionReturned, e:
                if e.type == 'break':
                    break
                elif e.type == 'continue':
                    self.update.eval(ctx)
                    continue
    
class Boolean(Expression):
    def __init__(self, pos, boolval):
        self.pos = pos
        self.bool = boolval
    
    def eval(self, ctx):
        return W_Boolean(self.bool)
    

class Not(UnaryOp):
    def eval(self, ctx):
        return W_Boolean(not self.expr.eval(ctx).GetValue().ToBoolean())
    

class UMinus(UnaryOp):
    def eval(self, ctx):
        return W_Number(-self.expr.eval(ctx).GetValue().ToNumber())

class UPlus(UnaryOp):
    def eval(self, ctx):
        return W_Number(+self.expr.eval(ctx).GetValue().ToNumber())
    
