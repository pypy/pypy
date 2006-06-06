
""" Document Object Model support
http://www.w3.org/DOM/ - main standart
http://www.w3schools.com/dhtml/dhtml_dom.asp - more informal stuff
"""

# FIXME: this should map somehow to xml.dom interface, or something else

import time

class Style(object):
    _rpython_hints = {'_suggested_external' : True}
    
    def __init__(self, s_str):
        self.left = "0"
        self.top = "0"


class Node(object):
    _rpython_hints = {'_suggested_external' : True}
    
    def __init__(self):
        self.innerHTML = ""
        self.style = None
    
    def getElementById(self, id):
        return Node()
    
    def setAttribute(self, name, style_str):
        if name == 'style':
            self.style = Style( style_str)

def get_document():
    return Node()

get_document.suggested_primitive = True

document = Node()

def setTimeout(func, delay):
    # scheduler call, but we don't want to mess with threads right now
    return func

setTimeout.suggested_primitive = True
