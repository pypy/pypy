
""" Document Object Model support
http://www.w3.org/DOM/ - main standart
http://www.w3schools.com/dhtml/dhtml_dom.asp - more informal stuff
"""

# FIXME: this should map somehow to xml.dom interface, or something else

class Node(object):
    def __init__(self):
        self.innerHTML = ""
    
    def getElementById(self, id):
        return Node()
    
    def setInnerHTML(self, data):
        self.innerHTML = data

def get_document():
    return Node()
