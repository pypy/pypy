
from pypy.lang.js.jsparser import parse
from pypy.lang.js.jsobj import *

class Node(object):
    # TODO Add line info for debug
#    def __init__(self, lineno = 1):
#        self.lineno = lineno
    pass

class BinaryOp(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    
class BinaryComparisonOp(BinaryOp):
    """super class for binary operators"""
    def call(self, ctx):
        s2 = self.left.call(ctx).GetValue()
        s4 = self.right.call(ctx).GetValue()
        return self.decision(s2, s4)


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
        self.w_Global.Put('prototype', 'Object')
        self.w_Global.Put('Object', self.w_Object)
        self.global_context = global_context(self.w_Global)
        if script_source is not None:
            self.load_source(script_source)
    
    def load_source(self, script_source):
        """load a source script text to the interpreter"""
        temp_dict = parse(script_source)
        #import pprint
        #pprint.pprint(temp_dict)
        self.script = from_dict(temp_dict)
    
    def append_source(self, script_source):
        temp_dict = parse(script_source)
        newscript = from_dict(temp_dict)
        self.script.append_script(newscript)

    def run(self):
        """run the interpreter"""
        return self.script.call(self.global_context)

class PropertyInit(Node):
    def __init__(self, name, value):
        self.name = name
        self.value = value
    
    def __repr__(self):
        return "<%s : %s>"%(str(self.name), str(self.value))



class Undefined(Node):
    def __init__(self):
        pass

        
class Array(Node):
    def __init__(self, items=()):
        self.items = items

    def call(self, ctx):
        d = dict(enumerate(self.items))
        return W_Array(d)

class Assign(Node):
    def __init__(self, LHSExp, AssignmentExp):
        self.LHSExp = LHSExp
        self.AssignmentExp = AssignmentExp
    
    def call(self, ctx):
        print "Assign LHS = ", self.LHSExp
        v1 = self.LHSExp.call(ctx)
        print "Assign Exp = ", self.AssignmentExp
        v3 = self.AssignmentExp.call(ctx).GetValue()
        v1.PutValue(v3, ctx)
        return v3

class Block(Node):
    def __init__(self, nodes):
        self.nodes = nodes

    def call(self, ctx):
        try:
            last = w_Undefined
            for node in self.nodes:
                last = node.call(ctx)
            return last
        except ExecutionReturned, e:
            return e.value

class Call(Node):
    def __init__(self, identifier, arglist):
        self.identifier = identifier
        self.arglist = arglist

    def call(self, ctx):
        name = self.identifier.get_literal()
        if name == 'print':
            writer(",".join([i.GetValue().ToString() for i in self.arglist.call(ctx)]))
        else:    
            w_obj = ctx.resolve_identifier(name).GetValue()
            print "arglist = ", self.arglist
            retval = w_obj.Call(ctx=ctx, args=[i for i in self.arglist.call(ctx)])
            return retval

class Comma(BinaryOp):
    def call(self, ctx):
        self.left.call(ctx)
        return self.right.call(ctx)

class Dot(BinaryOp):
    def call(self, ctx):
        w_obj = self.left.call(ctx).GetValue().ToObject()
        name = self.right.get_literal()
        return Reference(name, w_obj)

class Function(Node):
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body

    def call(self, ctx):
       w_obj = W_FunctionObject(self, ctx)
       return w_obj

class Identifier(Node):
    def __init__(self, name, initialiser=None):
        self.name = name
        self.initialiser = initialiser
    def __str__(self):
        return "<id %s init: %s>"%(str(self.name), str(self.initialiser))
    def call(self, ctx):
        if self.initialiser is not None:
            ref = ctx.resolve_identifier(self.name)
            ref.PutValue(self.initialiser.call(ctx), ctx)
        return ctx.resolve_identifier(self.name)
    
    def get_literal(self):
        return self.name

class If(Node):
    def __init__(self, condition, thenPart=None, elsePart=None):
        self.condition = condition
        self.thenPart = thenPart
        self.elsePart = elsePart

    def call(self, ctx=None):
        temp = self.condition.call(ctx)
        print "if condition = ", temp 
        if temp.ToBoolean():
            return self.thenPart.call(ctx)
        else:
            return self.elsePart.call(ctx)

class Group(Node):
    def __init__(self, expr):
        self.expr = expr

    def call(self, ctx):
        return self.expr.call(ctx)

def ARC(x, y):
    """
    Implements the Abstract Relational Comparison x < y
    Still not 100% to the spec
    """
    # TODO complete the funcion with strings comparison
    s1 = x.ToPrimitive('Number')
    s2 = y.ToPrimitive('Number')
    print "ARC x = %s, y = %s"%(str(s1),str(s2))
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
    def call(self, ctx):
        s2 = self.left.call(ctx).GetValue()
        if s2.ToBoolean():
            return s2
        s4 = self.right.call(ctx).GetValue()
        return s4

class And(BinaryLogicOp):
    def call(self, ctx):
        s2 = self.left.call(ctx).GetValue()
        if not s2.ToBoolean():
            return s2
        s4 = self.right.call(ctx).GetValue()
        return s4

class Ge(BinaryComparisonOp):
    def decision(self, op1, op2):
        s5 = ARC(op1, op2)
        if s5 is None or s5:
            return W_Boolean(False)
        else:
            return W_Boolean(True)

class Gt(BinaryComparisonOp):
    def decision(self, op1, op2):
        s5 = ARC(op2, op1)
        if s5 is None:
            return W_Boolean(False)
        else:
            return W_Boolean(s5)

class Le(BinaryComparisonOp):
    def decision(self, op1, op2):
        s5 = ARC(op2, op1)
        if s5 is None or s5:
            return W_Boolean(False)
        else:
            return W_Boolean(True)

class Lt(BinaryComparisonOp):
    def decision(self, op1, op2):
        s5 = ARC(op1, op2)
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
    def decision(self, op1, op2):
        return W_Boolean(AEC(op1, op2))

class Ne(BinaryComparisonOp):
    def decision(self, op1, op2):
        return W_Boolean(not AEC(op1, op2))


class In(BinaryComparisonOp):
    def decision(self, op1, op2):
        if not isinstance(op2, W_Object):
            raise ThrowException("TypeError")
        name = op1.ToString()
        return W_Boolean(op2.HasProperty(name))


class Index(Node):
    def __init__(self, left, expr):
        self.left = left
        self.expr = expr

    def call(self, ctx):
        w_obj = self.left.call(ctx).GetValue()
        w_member = self.expr.call(ctx).GetValue()
        w_obj = w_obj.ToObject()
        name = w_member.ToString()
        return w_obj.Get(name)

class List(Node):
    def __init__(self, nodes):
        self.nodes = nodes
    def call(self, ctx):
        print "nodes = ", self.nodes
        return [node.call(ctx) for node in self.nodes]

class Minus(BinaryComparisonOp):
    def decision(self, op1, op2):
        x = op1.ToNumber()
        y = op2.ToNumber()
        return W_Number(x - y)

class New(Node):
    def __init__(self, identifier):
        self.identifier = identifier

    def call(self, ctx):
        obj = W_Object()
        #it should be undefined... to be completed
        constructor = ctx.resolve_identifier(self.identifier).GetValue()
        obj.Put('prototype', constructor.Get('prototype'))
        constructor.Call(ctx, this = obj)
        return obj

class Number(Node):
    def __init__(self, num):
        self.num = num

    def call(self, ctx):
        return W_Number(self.num)
    
    def get_literal(self):
        return W_Number(self.num).ToString()

class ObjectInit(Node):
    def __init__(self, properties):
        self.properties = properties

    def call(self, ctx):
        w_obj = W_Object()
        print "properties = ", self.properties
        for property in self.properties:
            name = property.name.get_literal()
            print "prop name = ", name
            w_expr = property.value.call(ctx).GetValue()
            w_obj.Put(name, w_expr)
        return w_obj

class Plus(BinaryComparisonOp):
    def decision(self, op1, op2):
        prim_left = op1.ToPrimitive('Number')
        prim_right = op2.ToPrimitive('Number')
        if isinstance(prim_left, W_String) or isinstance(prim_right, W_String):
            str_left = prim_left.ToString()
            str_right = prim_right.ToString()
            return W_String(str_left + str_right)
        else:
            num_left = prim_left.ToNumber()
            num_right = prim_right.ToNumber()
            return W_Number(num_left + num_right)

class Script(Node):
    def __init__(self, nodes, var_decl, func_decl):
        self.nodes = nodes
        self.var_decl = var_decl
        self.func_decl = func_decl

    def call(self, ctx):
        for var in self.var_decl:
            ctx.variable.Put(var.name, w_Undefined)
        for fun in self.func_decl:
            ctx.variable.Put(fun.name, fun.call(ctx))
    
                
        try:
            last = w_Undefined
            for node in self.nodes:
                last = node.call(ctx)
            return last
        except ExecutionReturned, e:
            return e.value

    def append_script(self, newscript):
        """copy everything from the newscript to this one"""
        self.var_decl.extend(newscript.var_decl)
        self.nodes.extend(newscript.nodes)
        self.func_decl.extend(newscript.func_decl)

class Semicolon(Node):
    def __init__(self, expr = None):
        self.expr = expr

    def call(self, ctx):
        if self.expr is None:
            return
        return self.expr.call(ctx)

class String(Node):
    def __init__(self, strval):
        self.strval = strval

    def call(self, ctx):
        return W_String(self.strval)
    
    def get_literal(self):
        return W_String(self.strval).ToString()

class Return(Node):
    def __init__(self, expr):
        self.expr = expr

    def call(self, ctx):
        raise ExecutionReturned(self.expr.call(ctx))

class Throw(Node):
    def __init__(self, exception):
        self.exception = exception

    def call(self, ctx):
        raise ThrowException(self.exception.call(ctx))

class Try(Node):
    # TODO: rewrite to use 'Undefined'
    def __init__(self, tryblock, catchblock, finallyblock, catchparam):
        self.tryblock = tryblock
        self.catchblock = catchblock
        self.finallyblock = finallyblock
        self.catchparam = catchparam

    def call(self, ctx):
        e = None
        try:
            tryresult = self.tryblock.call(ctx)
        except ThrowException, excpt:
            e = excpt
            if self.catchblock is not None:
                obj = W_Object()
                obj.Put(self.catchparam, e.exception)
                ctx.push_object(obj)
                tryresult = self.catchblock.call(ctx)
                ctx.pop_object()
        
        if self.finallyblock is not None:
            tryresult = self.finallyblock.call(ctx)
        
        #if there is no catchblock reraise the exception
        if (e is not None) and (self.catchblock is None):
            raise e
        
        return tryresult

class Undefined(Node):
    def call(self, ctx):
        return None

class Vars(Node):
    def __init__(self, nodes):
        self.nodes = nodes

    def call(self, ctx):
        print self.nodes
        for var in self.nodes:
            print var.name
            var.call(ctx)

class While(Node):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def call(self, ctx):
        while self.condition.call(ctx).ToBoolean():
            self.body.call(ctx)

def getlist(d):
    if 'length' not in d:
        return []
    lgt = int(d['length'])
    output = [from_dict(d[str(i)]) for i in range(lgt)]
    return output

def build_interpreter(d):
    return from_dict(d)

# FIXME: Continue the translation from if/elif to this dict map
build_map = {'ARRAY_INIT':Array,
             'ASSIGN': Assign,
             'BLOCK': Block}

def from_dict_map(d):
    if d is None:
        return d
    try:
        build_map[d['type']](d)
    except KeyError,e:
        raise NotImplementedError("Don't know how to handle %s" %(d['type'],))
    
    
    
def from_dict(d):
    if d is None:
        return d
    tp = d['type']
    if tp == 'ARRAY_INIT':
        return Array(getlist(d))
    elif tp == 'ASSIGN':
        return Assign(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'BLOCK':
        return Block(getlist(d))
    elif tp == 'CALL':
        return Call(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'COMMA':
        return Comma(from_dict(d['0']),from_dict(d['1']))
    elif tp == 'DOT':
        return Dot(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'EQ':
        return Eq(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'OR':
        return Or(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'AND':
        return And(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'FUNCTION':        
        name = d.get('name', '')
        body = from_dict(d['body'])
        if d['params'] == '':
            params = []
        else:
            params = d['params'].split(',')
        f = Function(name, params, body)
        return f
    elif tp == 'GROUP':
        return Group(from_dict(d['0']))
    elif tp == 'GE':
        return Ge(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'GT':
        return Gt(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'IDENTIFIER':
        return Identifier(d['value'], from_dict(d.get('initializer', None)))
    elif tp == 'IF':
        condition = from_dict(d['condition'])
        if d['thenPart'] == 'null':
            thenPart = Undefined()
        else:
            thenPart = from_dict(d['thenPart'])
        if d['elsePart'] == 'null':
            elsePart = Undefined()
        else:
            elsePart = from_dict(d['elsePart'])
        return If(condition,thenPart,elsePart)
    elif tp == 'IN':
        return In(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'INDEX':
        return Index(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'LIST':
        return List(getlist(d))
    elif tp == 'LE':
        return Le(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'LT':
        return Lt(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'MINUS':
        return Minus(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'NE':
        return Ne(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'NEW':
        return New(d['0']['value'])
    elif tp == 'NUMBER':
        return Number(float(d['value']))
    elif tp == 'OBJECT_INIT':
        return ObjectInit(getlist(d))
    elif tp == 'PLUS':
        return Plus(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'PROPERTY_INIT':
        return PropertyInit(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'RETURN':
        return Return(from_dict(d['value']))
    elif tp == 'SCRIPT':
        if isinstance(d['funDecls'], dict):
            func_decl = [from_dict(d['funDecls']),]
        else:
            func_decl = [from_dict(x) for x in d['funDecls']]
        
        if isinstance(d['varDecls'], dict):
            var_decl = [from_dict(d['varDecls']),]
        else:
            var_decl = [from_dict(x) for x in d['varDecls']]
        return Script(getlist(d), var_decl, func_decl)
    elif tp == 'SEMICOLON':
        if d['expression'] == 'null':
            return Semicolon()
        return Semicolon(from_dict(d['expression']))
    elif tp == 'STRING':
        return String(d['value'])
    elif tp == 'THIS':
        return Identifier(d['value'])
    elif tp == 'THROW':
        return Throw(from_dict(d['exception']))
    elif tp == 'TRY':
        finallyblock = None
        catchblock = None
        catchparam = ''
        if 'finallyBlock' in d:
            finallyblock = from_dict(d['finallyBlock'])
        if 'catchClauses' in d:
            #multiple catch clauses is a spidermonkey extension
            catchblock = from_dict(d['catchClauses']['block'])
            catchparam = d['catchClauses']['varName']
        return Try(from_dict(d['tryBlock']), catchblock, finallyblock, catchparam)
    elif tp == 'VAR':
        return Vars(getlist(d))
    elif tp == 'WHILE':
        body = from_dict(d['body'])
        condition = from_dict(d['condition'])
        return While(condition, body)
    else:
        raise NotImplementedError("Dont know how to handler %s" % tp)
