
from ast import *

class TokenNode(Node):
    pass

def make_subscript( name, source, nodes ):
    """'.' '.' '.' | [test] ':' [test] [ ':' [test] ] | test"""
    n = nodes[0]
    if n.isToken():
        if n.value == '.':
            n1 = nodes[2]
            if n1.isToken() and n1.value == '.':
                return Ellipsis()
        elif n.value == ':':
            return make_slice( name, source, nodes )
    if len(nodes)>1:
        return make_slice( name, source, nodes )
    return n

def make_subscriptlist( name, source, nodes ):
    """ idx (',' idx)* """
    values = []
    for i in range(0, len(nodes), 2):
        values.append( nodes[i] )
    return Subscript( values )

def make_slice( name, source, nodes ):
    """TODO"""
    idx = 0
    
    for n in nodes:
        





for name, factory in globals().items():
    if name.startswith("make_"):
        astfactory[name[5:]] = factory
