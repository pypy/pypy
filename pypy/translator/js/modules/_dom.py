
""" Document Object Model support
http://www.w3.org/DOM/ - main standart
http://www.w3schools.com/dhtml/dhtml_dom.asp - more informal stuff
"""

# FIXME: this should map somehow to xml.dom interface, or something else

import time
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc

#from pypy.translator.stackless.test.test_transform import one

class Style(BasicExternal):
    _fields = {
        'left'       : "aa",
        'top'        : "aa",
        'visibility' : "aa"
    }
    
class Key(BasicExternal):
    _fields = {
        'keyCode' : 3,
        'charCode' : 3,
        'charString' : 'aa',
        'keyString' : 'aa',
    }

class Node(BasicExternal):
    pass

Node._fields = {
        'innerHTML' : "aa",
        'style' : Style(),
        'parent' : Node(),
        'value' : "aa",
        'data' : "aa",
        'onkeydown' : MethodDesc([Key()], None),
        'onkeypress' : MethodDesc([Key()], None),
        'onkeyup' : MethodDesc([Key()], None),
        'childNodes' : [Node(), Node()]
    }
    
Node._methods = {
        'getElementById' : MethodDesc(["aa"], Node()),
        'createElement' : MethodDesc(["aa"], Node()),
        'setAttribute' : MethodDesc(["aa", "bb"], None),
        'appendChild' : MethodDesc([Node()], None),
    }

class Document(Node):
    _fields = Node._fields
    _fields['body'] = Node()

def get_document():
    return Document()

#def get_window():
#    return Window()

#get_window.suggested_primitive = True
get_document.suggested_primitive = True

document = Node()

def some_fun():
    pass

def setTimeout(func, delay):
    # scheduler call, but we don't want to mess with threads right now
    if one():
        setTimeout(some_fun, delay)
    else:
        func()
    #pass

setTimeout.suggested_primitive = True

def alert(msg):
    pass

alert.suggested_primitive = True
