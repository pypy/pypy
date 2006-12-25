
from pypy.annotation.pairtype import extendabletype
from pypy.lang.js.jsobj import W_Object, w_Undefined, ExecutionContext

class Node(object):
    __metaclass__ = extendabletype
    # TODO Add line info for debug
#    def __init__(self, lineno = 1):
#        self.lineno = lineno

class BinaryOperator(Node):
    """super class for binary operators"""
    def __init__(self, left, right):
        self.left = left
        self.right = right


class Array(Node):
    def __init__(self, items=()):
        self.items = items

class Assign(Node):
    def __init__(self, LHSExp, AssignmentExp):
        self.LHSExp = LHSExp
        self.AssignmentExp = AssignmentExp

class Block(Node):
    def __init__(self, nodes):
        self.nodes = nodes


class Call(Node):
    def __init__(self, identifier, arglist):
        self.identifier = identifier
        self.arglist = arglist

class Comma(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class Dot(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class Function(Node):
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body

class Group(Node):
    def __init__(self, expr):
        self.expr = expr

class Gt(BinaryOperator): pass

class Identifier(Node):
    def __init__(self, name, initialiser=None):
        self.name = name
        self.initialiser = initialiser
    def __str__(self):
        return "<id %s init: %s>"%(str(self.name), str(self.initialiser))

class If(Node):
    def __init__(self, condition, thenPart=None, elsePart=None):
        self.condition = condition
        self.thenPart = thenPart
        self.elsePart = elsePart

class Index(Node):
    def __init__(self, left, expr):
        self.left = left
        self.expr = expr

class List(Node):
    def __init__(self, nodes):
        self.nodes = nodes

class Lt(BinaryOperator): pass

class New(Node):
    def __init__(self, identifier):
        self.identifier = identifier

class Number(Node):
    def __init__(self, num):
        self.num = num

class ObjectInit(Node):
    def __init__(self, properties):
        self.properties = properties

class Plus(BinaryOperator):pass

class PropertyInit(Node):
    def __init__(self, name, value):
        self.name = name
        self.value = value
    
    def __repr__(self):
        return "<%s : %s>"%(str(self.name), str(self.value))

class Return(Node):
    def __init__(self, expr):
        self.expr = expr

class Script(Node):
    def __init__(self, nodes, var_decl, func_decl):
        self.nodes = nodes
        self.var_decl = var_decl
        self.func_decl = func_decl

class Semicolon(Node):
    def __init__(self, expr):
        self.expr = expr

class String(Node):
    def __init__(self, strval):
        self.strval = strval

class Throw(Node):
    def __init__(self, exception):
        self.exception = exception

class Try(Node):
    # TODO: rewrite to use 'Undefined'
    def __init__(self, tryblock, catchblock, finallyblock, catchparam):
        self.tryblock = tryblock
        self.catchblock = catchblock
        self.finallyblock = finallyblock
        self.catchparam = catchparam


class Undefined(Node):
    def __init__(self):
        pass

class Vars(Node):
    def __init__(self, nodes):
        self.nodes = nodes

class While(Node):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

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
    elif tp == 'INDEX':
        return Index(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'LIST':
        return List(getlist(d))
    elif tp == 'LT':
        return Lt(from_dict(d['0']), from_dict(d['1']))
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
        # TODO: get function names
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
