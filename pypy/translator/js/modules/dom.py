
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
        self.visibility = 'visible'

class Key(object):
    _rpython_hints = {'_suggested_external' : True}
        
    def __init__(self, s):
        self.charCode = s
        self.keyCode = s

def set_on_keydown(func):
    if one():
        func(Key("str"))
    else:
        func(Key("str2"))

set_on_keydown.suggested_primitive = True

def set_on_keyup(func):
    if one():
        func(Key("str"))
    else:
        func(Key("str2"))

set_on_keyup.suggested_primitive = True

class Node(object):
    _rpython_hints = {'_suggested_external' : True}
    
    def __init__(self, parent = None):
        self.innerHTML = ""
        self.style = None
        self.subnodes = {}
        self.parent = parent
        if one():
            self.value = "blah"
        else:
            self.value = "sth"
    
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
        elif name == 'value':
            self.value = style_str
    
    def appendChild(self, elem):
        self.subnodes[elem.id] = elem

class Form(Node):
    pass

class Document(Node):
    def __init__(self):
        Node.__init__(self)
        self.body = Node()
        self.forms = [Form(), Form()]
    

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
