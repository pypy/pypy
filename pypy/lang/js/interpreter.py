
from pypy.lang.js.jsparser import parse, parse_bytecode
from pypy.lang.js.jsobj import *
from pypy.rlib.parsing.ebnfparse import Symbol, Nonterminal

class Node(object):
    # TODO Add line info for debug
#    def __init__(self, lineno = 1):
#        self.lineno = lineno
    pass

class Statement(Node):
    def execute(self, ctx):
        raise NotImplementedError

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
        return self.decision(ctx, s2, s4)


class BinaryLogicOp(BinaryOp):
    """super class for binary operators"""
    pass

def writer(x):
    print x

class Interpreter(object):
    """Creates a js interpreter"""
    def __init__(self, script_source=None):
        self.w_Object = W_Object() #creating Object
        self.w_Global = W_Object()
        self.w_Global.Prototype = self.w_Object
        self.w_Global.Put('prototype', W_String('Object'))
        self.w_Global.Put('Object', self.w_Object)
        self.global_context = global_context(self.w_Global)
        if script_source is not None:
            self.load_source(script_source)
    
    def load_source(self, script_source):
        """load a source script text to the interpreter"""
        temp_tree = parse(script_source)
        self.script = from_tree(temp_tree)
    
    def append_source(self, script_source):
        temp_tree = parse(script_source)
        newscript = from_tree(temp_tree)
        self.script.append_script(newscript)

    def load_bytecode(self, bytecode):
        temp_tree = parse_bytecode(bytecode)
        self.script = from_tree(temp_tree)

    def run(self):
        """run the interpreter"""
        return self.script.execute(self.global_context)

class PropertyInit(Node):
    def __init__(self, name, value):
        self.name = name
        self.value = value
    
    def __repr__(self):
        return "<%s : %s>"%(str(self.name), str(self.value))


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
        #print "Assign LHS = ", self.LHSExp
        v1 = self.LHSExp.eval(ctx)
        #print "Assign Exp = ", self.AssignmentExp
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
            return e.value

class Call(Expression):
    def __init__(self, identifier, arglist):
        self.identifier = identifier
        self.arglist = arglist

    def eval(self, ctx):
        name = self.identifier.get_literal()
        if name == 'print':
            writer(",".join([i.GetValue().ToString() for i in self.arglist.get_args(ctx)]))
        else:    
            w_obj = ctx.resolve_identifier(name).GetValue()
            #print "arglist = ", self.arglist
            retval = w_obj.Call(ctx=ctx, args=[i for i in self.arglist.get_args(ctx)])
            return retval

class Comma(BinaryOp):
    def eval(self, ctx):
        self.left.eval(ctx)
        return self.right.eval(ctx)

class Dot(BinaryOp):
    def eval(self, ctx):
        w_obj = self.left.eval(ctx).GetValue().ToObject()
        name = self.right.get_literal()
        return W_Reference(name, w_obj)

class Function(Expression):
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body

    def eval(self, ctx):
       w_obj = W_FunctionObject(self, ctx)
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
            ref.PutValue(self.initialiser.eval(ctx), ctx)
        return ctx.resolve_identifier(self.name)
    
    def get_literal(self):
        return self.name

class If(Statement):
    def __init__(self, condition, thenPart=None, elsePart=None):
        self.condition = condition
        self.thenPart = thenPart
        self.elsePart = elsePart

    def execute(self, ctx=None):
        temp = self.condition.eval(ctx)
        #print "if condition = ", temp 
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
    #print "ARC x = %s, y = %s"%(str(s1),str(s2))
    if not (isinstance(s1, W_String) and isinstance(s2, W_String)):
        s4 = s1.ToNumber()
        s5 = s2.ToNumber()
        if s4 == NaN or s5 == NaN:
            return None
        if s4 < s5:
            return True
        else:
            return False
    else:
        pass 

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
        if s5 is None or s5:
            return W_Boolean(False)
        else:
            return W_Boolean(True)

class Gt(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        s5 = ARC(ctx, op2, op1)
        if s5 is None:
            return W_Boolean(False)
        else:
            return W_Boolean(s5)

class Le(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        s5 = ARC(ctx, op2, op1)
        if s5 is None or s5:
            return W_Boolean(False)
        else:
            return W_Boolean(True)

class Lt(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        s5 = ARC(ctx, op1, op2)
        if s5 is None:
            return W_Boolean(False)
        else:
            return W_Boolean(s5)

def AEC(x, y):
    """
    Implements the Abstract Equality Comparison x == y
    not following the specs yet
    """
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
            raise ThrowException("TypeError")
        name = op1.ToString()
        return W_Boolean(op2.HasProperty(name))


class Index(Expression):
    def __init__(self, left, expr):
        self.left = left
        self.expr = expr

    def eval(self, ctx):
        w_obj = self.left.eval(ctx).GetValue()
        w_member = self.expr.eval(ctx).GetValue()
        w_obj = w_obj.ToObject()
        name = w_member.ToString()
        return w_obj.Get(name)

class List(Node):
    def __init__(self, nodes):
        self.nodes = nodes
        
    def get_args(self, ctx):
        #print "nodes = ", self.nodes
        return [node.eval(ctx) for node in self.nodes]

class Minus(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        x = op1.ToNumber()
        y = op2.ToNumber()
        return W_Number(x - y)

class New(Expression):
    def __init__(self, identifier):
        self.identifier = identifier

    def eval(self, ctx):
        obj = W_Object()
        #it should be undefined... to be completed
        constructor = ctx.resolve_identifier(self.identifier).GetValue()
        obj.Put('prototype', constructor.Get('prototype'))
        constructor.Call(ctx, this = obj)
        return obj

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
        ##print "properties = ", self.properties
        for property in self.properties:
            name = property.name.get_literal()
            #print "prop name = ", name
            w_expr = property.value.eval(ctx).GetValue()
            w_obj.Put(name, w_expr)
        return w_obj

class Plus(BinaryComparisonOp):
    def decision(self, ctx, op1, op2):
        prim_left = op1.ToPrimitive(ctx, 'Number')
        prim_right = op2.ToPrimitive(ctx, 'Number')
        if isinstance(prim_left, W_String) or isinstance(prim_right, W_String):
            str_left = prim_left.ToString()
            str_right = prim_right.ToString()
            return W_String(str_left + str_right)
        else:
            num_left = prim_left.ToNumber()
            num_right = prim_right.ToNumber()
            return W_Number(num_left + num_right)

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
        except ExecutionReturned, e:
            return e.value

    def append_script(self, newscript):
        """copy everything from the newscript to this one"""
        self.var_decl.extend(newscript.var_decl)
        self.nodes.extend(newscript.nodes)
        self.func_decl.extend(newscript.func_decl)

class Semicolon(Statement):
    def __init__(self, expr = None):
        self.expr = expr

    def execute(self, ctx):
        if self.expr is None:
            return
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
        raise ExecutionReturned(self.expr.eval(ctx))

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

class Undefined(Statement):
    def execute(self, ctx):
        return None

class Vars(Statement):
    def __init__(self, nodes):
        self.nodes = nodes

    def execute(self, ctx):
        #print self.nodes
        for var in self.nodes:
            #print var.name
            var.execute(ctx)

class While(Statement):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def execute(self, ctx):
        while self.condition.eval(ctx).ToBoolean():
            self.body.execute(ctx)

def getlist(t):
    item = gettreeitem(t, 'length')
    if item is None:
        return []
    lgt = int(item.additional_info)
    output = [from_tree(gettreeitem(t, str(i))) for i in range(lgt)]
    return output
    
def gettreeitem(t, name):
    for x in t.children:
        if x.children[0].additional_info == name:
            return x.children[1]
    return

def from_tree(t):
    if t is None:
        return
    tp = gettreeitem(t, 'type').additional_info
    if tp == 'ARRAY_INIT':
        return Array(getlist(t))
    elif tp == 'ASSIGN':
        return Assign(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'BLOCK':
        return Block(getlist(t))
    elif tp == 'CALL':
        return Call(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'COMMA':
        return Comma(from_tree(gettreeitem(t, '0')),from_tree(gettreeitem(t, '1')))
    elif tp == 'DOT':
        return Dot(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'EQ':
        return Eq(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'OR':
        return Or(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'AND':
        return And(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'FUNCTION':        
        name = gettreeitem(t, 'name')
        if name is not None:
            name = name.additional_info
        body = from_tree(gettreeitem(t, 'body'))
        if gettreeitem(t, 'params').additional_info == '':
            params = []
        else:
            params = gettreeitem(t, 'params').additional_info.split(',')
        f = Function(name, params, body)
        return f
    elif tp == 'GROUP':
        return Group(from_tree(gettreeitem(t, '0')))
    elif tp == 'GE':
        return Ge(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'GT':
        return Gt(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'IDENTIFIER':
        return Identifier(gettreeitem(t, 'value').additional_info, from_tree(gettreeitem(t, 'initializer')))
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
        return If(condition,thenPart,elsePart)
    elif tp == 'IN':
        return In(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'INDEX':
        return Index(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'LIST':
        return List(getlist(t))
    elif tp == 'LE':
        return Le(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'LT':
        return Lt(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'MINUS':
        return Minus(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'NE':
        return Ne(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'NEW':
        return New(gettreeitem(gettreeitem(t, '0'),'value').additional_info)
    elif tp == 'NUMBER':
        return Number(float(gettreeitem(t, 'value').additional_info))
    elif tp == 'OBJECT_INIT':
        return ObjectInit(getlist(t))
    elif tp == 'PLUS':
        return Plus(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'PROPERTY_INIT':
        return PropertyInit(from_tree(gettreeitem(t, '0')), from_tree(gettreeitem(t, '1')))
    elif tp == 'RETURN':
        return Return(from_tree(gettreeitem(t, 'value')))
    elif tp == 'SCRIPT':
        print "*funDecls:'' ", gettreeitem(t, 'funDecls') == ''
        f = gettreeitem(t, 'funDecls')
        print f.symbol
        if f.symbol == "dict":
            func_decl = [from_tree(f),]
        elif f.symbol == "list":
            func_decl = [from_tree(x) for x in f.children]
        else:
            func_decl = []
        
        v = gettreeitem(t, 'varDecls')
        print v.symbol
        if v.symbol == "dict":
            var_decl = [from_tree(v),]
        elif v.symbol == "list":
            var_decl = [from_tree(x) for x in v.children]
        else:
            var_decl = []

        return Script(getlist(t), var_decl, func_decl)
    elif tp == 'SEMICOLON':
        if gettreeitem(t, 'expression') == 'null':
            return Semicolon()
        return Semicolon(from_tree(gettreeitem(t, 'expression')))
    elif tp == 'STRING':
        return String(gettreeitem(t, 'value').additional_info)
    elif tp == 'THIS':
        return Identifier(gettreeitem(t, 'value').additional_info)
    elif tp == 'THROW':
        return Throw(from_tree(gettreeitem(t, 'exception')))
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
        return Try(from_tree(gettreeitem(t, 'tryBlock')), catchblock, finallyblock, catchparam)
    elif tp == 'VAR':
        return Vars(getlist(t))
    elif tp == 'WHILE':
        body = from_tree(gettreeitem(t, 'body'))
        condition = from_tree(gettreeitem(t, 'condition'))
        return While(condition, body)
    else:
        raise NotImplementedError("Dont know how to handler %s" % tp)
