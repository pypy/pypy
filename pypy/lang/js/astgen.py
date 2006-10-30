
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

#class Print(Node):
#    def __init__(self, expr):
#        
