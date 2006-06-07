
""" Document Object Model support
http://www.w3.org/DOM/ - main standart
http://www.w3schools.com/dhtml/dhtml_dom.asp - more informal stuff
"""

# FIXME: this should map somehow to xml.dom interface, or something else

import time

from pypy.translator.stackless.test.test_transform import one

class Style(object):
    _rpython_hints = {'_suggested_external' : True}
    
    def __init__(self, s_str):
        self.left = "0"
        self.top = "0"


class Node(object):
    _rpython_hints = {'_suggested_external' : True}
    
    def __init__(self, parent = None):
        self.innerHTML = ""
        self.style = None
        self.subnodes = {}
        self.parent = parent
    
    def getElementById(self, id):
        try:
            return self.subnodes[id]
        except KeyError:
            self.subnodes[id] = Node()
            return self.subnodes[id]
    
    def createElement(self, type):
        return Node()
    
    def setAttribute(self, name, style_str):
        if name == 'style':
            self.style = Style( style_str)
        elif name == 'id':
            self.id = style_str
        elif name == 'src':
            self.src = style_str
    
    def appendChild(self, elem):
        self.subnodes[elem.id] = elem

class Document(Node):
    def __init__(self):
        Node.__init__(self)
        self.body = Node()
    

def get_document():
    return Document()

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

