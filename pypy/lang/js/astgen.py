
from pypy.annotation.pairtype import extendabletype

class Node(object):
    __metaclass__ = extendabletype
#    def __init__(self, lineno = 1):
#        self.lineno = lineno

#    def getlist(d):
#        lgt = int(d['length'])
#        output = [d[str(i)] for i in range(lgt)]
#        return output
#    getlist = staticmethod(getlist)

class Script(Node):
    def __init__(self, nodes, var_decl, func_decl):
        self.nodes = nodes
        self.var_decl = var_decl
        self.func_decl = func_decl

#    def from_dict(d):
#        return Script(self.getlist(d), d['varDecl'], d['funcDecl'])
#    from_dict = staticmethod(from_dict)

class Assign(Node):
    def __init__(self, identifier, expr):
        self.identifier = identifier
        self.expr = expr

class Semicolon(Node):
    def __init__(self, expr):
        self.expr = expr

class Plus(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class Number(Node):
    def __init__(self, num):
        self.num = num

class Call(Node):
    def __init__(self, identifier, arglist):
        self.identifier = identifier
        self.arglist = arglist

class Identifier(Node):
    def __init__(self, name):
        self.name = name

class List(Node):
    def __init__(self, nodes):
        self.nodes = nodes

def getlist(d):
    lgt = int(d['length'])
    output = [from_dict(d[str(i)]) for i in range(lgt)]
    return output

def from_dict(d):
    tp = d['type']
    if tp == 'SCRIPT':
        # XXX: Cannot parse it right now
        return Script(getlist(d), [], [])
    elif tp == 'SEMICOLON':
        return Semicolon(from_dict(d['expression']))
    elif tp == 'NUMBER':
        return Number(float(d['value']))
    elif tp == 'IDENTIFIER':
        return Identifier(d['value'])
    elif tp == 'LIST':
        return List(getlist(d))
    elif tp == 'CALL':
        return Call(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'PLUS':
        return Plus(from_dict(d['0']), from_dict(d['1']))
    elif tp == 'ASSIGN':
        return Assign(from_dict(d['0']), from_dict(d['1']))
    else:
        raise NotImplementedError("Dont know how to handler %s" % tp)
