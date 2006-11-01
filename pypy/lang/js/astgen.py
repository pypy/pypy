
from pypy.annotation.pairtype import extendabletype
from pypy.lang.js.context import ExecutionContext
from pypy.lang.js.jsobj import W_Object, w_Undefined
from pypy.lang.js.scope import scope_manager

class Node(object):
    __metaclass__ = extendabletype
#    def __init__(self, lineno = 1):
#        self.lineno = lineno

#    def getlist(d):
#        lgt = int(d['length'])
#        output = [d[str(i)] for i in range(lgt)]
#        return output
#    getlist = staticmethod(getlist)


class Assign(Node):
    def __init__(self, identifier, expr):
        self.identifier = identifier
        self.expr = expr

class Call(Node):
    def __init__(self, identifier, arglist):
        self.identifier = identifier
        self.arglist = arglist

class Dot(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class Function(Node):
    def __init__(self, params, body, scope):
        self.params = params
        self.body = body
        self.scope = scope
        #w_obj = W_Object({}, function=self)
        #self.scope = Scope(copy(scope.dict))
    
class Identifier(Node):
    def __init__(self, name, initialiser):
        self.name = name
        self.initialiser = initialiser

class Index(Node):
    def __init__(self, left, expr):
        self.left = left
        self.expr = expr

class List(Node):
    def __init__(self, nodes):
        self.nodes = nodes

class Number(Node):
    def __init__(self, num):
        self.num = num

class ObjectInit(Node):
    def __init__(self, properties):
        self.properties = properties

class Plus(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class PropertyInit(Node):
    def __init__(self, name, value):
        self.name = name
        self.value = value

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

class Vars(Node):
    def __init__(self, nodes):
        self.nodes = nodes
        [scope_manager.add_variable(id.name, w_Undefined) for id in nodes]

def getlist(d):
    if 'length' not in d:
        return []
    lgt = int(d['length'])
    output = [from_dict(d[str(i)]) for i in range(lgt)]
    return output

def build_interpreter(d):
    return from_dict(d)

def from_dict(d):
    if d is None:
        return d
    tp = d['type']
    if tp == 'SCRIPT':
        # XXX: Cannot parse it right now
        return Script(getlist(d), [], [])
    elif tp == 'SEMICOLON':
        return Semicolon(from_dict(d['expression']))
    elif tp == 'NUMBER':
        return Number(float(d['value']))
    elif tp == 'IDENTIFIER':
        return Identifier(d['value'], from_dict(d.get('initializer', None)))
    elif tp == 'LIST':
        return List(getlist(d))
    elif tp == 'CALL':
        return Call(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'PLUS':
        return Plus(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'ASSIGN':
        return Assign(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'STRING':
        return String(d['value'])
    elif tp == 'PROPERTY_INIT':
        return PropertyInit(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'OBJECT_INIT':
        return ObjectInit(getlist(d))
    elif tp == 'DOT':
        return Dot(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'INDEX':
        return Index(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'FUNCTION':
        scope = scope_manager.enter_scope()
        body = from_dict(d['body'])
        f = Function(d['params'].split(','), body, scope)
        scope_manager.leave_scope()
        return f
    elif tp == 'RETURN':
        return Return(from_dict(d['value']))
    elif tp == 'VAR':
        return Vars(getlist(d))
    else:
        raise NotImplementedError("Dont know how to handler %s" % tp)
