
"""Document Object Model support

    this provides a mock browser API, both the standard DOM l. 1 and 2 stuff as
    the browser-specific (level 0) additions

    note that the API is not and will not be complete: more exotic features 
    will most probably not behave as expected
    
    http://www.w3.org/DOM/ - main standard
    http://www.w3schools.com/dhtml/dhtml_dom.asp - more informal stuff
    http://developer.mozilla.org/en/docs/Gecko_DOM_Reference - Gecko reference
"""

import time
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc

from pypy.translator.stackless.test.test_transform import one
from xml.dom import minidom

# XML node (level 2 basically) implementation
#   the following classes are mostly wrappers around minidom nodes that try to
#   mimic HTML DOM behaviour by implementing browser API and changing the
#   behaviour a bit

class Node(BasicExternal):
    """base class of all node types"""
    
    def __init__(self, node=None):
        if node is not None:
            self._original = node
    
    def __getattr__(self, name):
        """attribute access gets proxied to the contained minidom node

            all returned minidom nodes are wrapped as Nodes
        """
        value = getattr(self._original, name)
        return _wrap(value)

class Element(Node):
    """element type"""
    nodeType = 1
    id = ''
    nodeName = ''

    def __init__(self, node=None):
        super(Element, self).__init__(node)
        if node is not None:
            self.id = node.getAttribute('id')
            self.nodeName = node.nodeName.upper()
            self.style = Style()

class Attribute(Node):
    nodeType = 2

class Text(Node):
    nodeType = 3

class Form(Element):
    pass

class Document(Element):
    nodeType = 9
    
    def __init__(self, docnode=None):
        self._original = docnode

    def getElementById(self, id):
        nodes = self.getElementsByTagName('*')
        for node in nodes:
            if node.getAttribute('id') == id:
                return node

class Window(BasicExternal):
    def __init__(self, html=('<html><head><title>Untitled document</title>'
                             '</head><body></body></html>')):
        global document
        self.html = html
        document = Document(minidom.parseString(html))

    def __getattr__(self, name):
        return globals()[name]

# now some functionality to wrap minidom nodes with Node classes, and to make
# sure all methods on the nodes return wrapped nodes rather than minidom ones
class _FunctionWrapper(object):
    """makes sure function return values are wrapped if appropriate"""
    def __init__(self, callable):
        self._original = callable

    def __call__(self, *args, **kwargs):
        value = self._original(*args, **kwargs)
        return _wrap(value)

_typetoclass = {
    1: Element,
    2: Attribute,
    3: Text,
    9: Document,
}
def _wrap(value):
    if isinstance(value, minidom.Node):
        nodeclass = _typetoclass[value.nodeType]
        return nodeclass(value)
    elif callable(value):
        return _FunctionWrapper(value)
    # nothing fancier in minidom, i hope...
    # XXX and please don't add anything fancier either ;)
    elif isinstance(value, list):
        return [_wrap(x) for x in value]
    return value

# more DOM API, the stuff that doesn't directly deal with XML
#   note that we're mimicking the standard (Mozilla) APIs, so things tested
#   against this code may not work on Internet Explorer
class Event(BasicExternal):
    pass

class KeyEvent(Event):
    _fields = {
        'keyCode' : 12,
        'charCode' : 12,
    }

class MouseEvent(Event):
    pass

class Style(BasicExternal):
    _fields = {
        'azimuth' : 'aa',
        'background' : 'aa',
        'backgroundAttachment' : 'aa',
        'backgroundColor' : 'aa',
        'backgroundImage' : 'aa',
        'backgroundPosition' : 'aa',
        'backgroundRepeat' : 'aa',
        'border' : 'aa',
        'borderBottom' : 'aa',
        'borderBottomColor' : 'aa',
        'borderBottomStyle' : 'aa',
        'borderBottomWidth' : 'aa',
        'borderCollapse' : 'aa',
        'borderColor' : 'aa',
        'borderLeft' : 'aa',
        'borderLeftColor' : 'aa',
        'borderLeftStyle' : 'aa',
        'borderLeftWidth' : 'aa',
        'borderRight' : 'aa',
        'borderRightColor' : 'aa',
        'borderRightStyle' : 'aa',
        'borderRightWidth' : 'aa',
        'borderSpacing' : 'aa',
        'borderStyle' : 'aa',
        'borderTop' : 'aa',
        'borderTopColor' : 'aa',
        'borderTopStyle' : 'aa',
        'borderTopWidth' : 'aa',
        'borderWidth' : 'aa',
        'bottom' : 'aa',
        'captionSide' : 'aa',
        'clear' : 'aa',
        'clip' : 'aa',
        'color' : 'aa',
        'content' : 'aa',
        'counterIncrement' : 'aa',
        'counterReset' : 'aa',
        'cssFloat' : 'aa',
        'cssText' : 'aa',
        'cue' : 'aa',
        'cueAfter' : 'aa',
        'onBefore' : 'aa',
        'cursor' : 'aa',
        'direction' : 'aa',
        'displays' : 'aa',
        'elevation' : 'aa',
        'emptyCells' : 'aa',
        'font' : 'aa',
        'fontFamily' : 'aa',
        'fontSize' : 'aa',
        'fontSizeAdjust' : 'aa',
        'fontStretch' : 'aa',
        'fontStyle' : 'aa',
        'fontVariant' : 'aa',
        'fontWeight' : 'aa',
        'height' : 'aa',
        'left' : 'aa',
        'length' : 'aa',
        'letterSpacing' : 'aa',
        'lineHeight' : 'aa',
        'listStyle' : 'aa',
        'listStyleImage' : 'aa',
        'listStylePosition' : 'aa',
        'listStyleType' : 'aa',
        'margin' : 'aa',
        'marginBottom' : 'aa',
        'marginLeft' : 'aa',
        'marginRight' : 'aa',
        'marginTop' : 'aa',
        'markerOffset' : 'aa',
        'marks' : 'aa',
        'maxHeight' : 'aa',
        'maxWidth' : 'aa',
        'minHeight' : 'aa',
        'minWidth' : 'aa',
        'MozBinding' : 'aa',
        'MozOpacity' : 'aa',
        'orphans' : 'aa',
        'outline' : 'aa',
        'outlineColor' : 'aa',
        'outlineStyle' : 'aa',
        'outlineWidth' : 'aa',
        'overflow' : 'aa',
        'padding' : 'aa',
        'paddingBottom' : 'aa',
        'paddingLeft' : 'aa',
        'paddingRight' : 'aa',
        'paddingTop' : 'aa',
        'page' : 'aa',
        'pageBreakAfter' : 'aa',
        'pageBreakBefore' : 'aa',
        'pageBreakInside' : 'aa',
        'parentRule' : 'aa',
        'pause' : 'aa',
        'pauseAfter' : 'aa',
        'pauseBefore' : 'aa',
        'pitch' : 'aa',
        'pitchRange' : 'aa',
        'playDuring' : 'aa',
        'position' : 'aa',
        'quotes' : 'aa',
        'richness' : 'aa',
        'right' : 'aa',
        'size' : 'aa',
        'speak' : 'aa',
        'speakHeader' : 'aa',
        'speakNumeral' : 'aa',
        'speakPunctuation' : 'aa',
        'speechRate' : 'aa',
        'stress' : 'aa',
        'tableLayout' : 'aa',
        'textAlign' : 'aa',
        'textDecoration' : 'aa',
        'textIndent' : 'aa',
        'textShadow' : 'aa',
        'textTransform' : 'aa',
        'top' : 'aa',
        'unicodeBidi' : 'aa',
        'verticalAlign' : 'aa',
        'visibility' : 'aa',
        'voiceFamily' : 'aa',
        'volume' : 'aa',
        'whiteSpace' : 'aa',
        'widows' : 'aa',
        'width' : 'aa',
        'wordSpacing' : 'aa',
        'zIndex' : 'aa',
    }

    def __getattr__(self, name):
        pass

    def __setattr__(self, name):
        pass

Element._fields = {
        'attributes' : [Attribute()],
        'childNodes' : [Element()],
        'className' : "aa",
        'clientHeight' : 12,
        'clientWidth' : 12,
        'clientLeft' : 12,
        'clientTop' : 12,
        'dir' : "aa",
        'firstChild' : Element(),
        'innerHTML' : "asd",
        'lang' : "asd",
        'id' : "aa",
        'lastChild' : Element(),
        'length' : 12,
        'localName' : "aa",
        'name' : "aa",
        'namespaceURI' : "aa",
        'nextSibling' : Element(),
        'nodeName' : "aa",
        'nodeType' : 1,
        'nodeValue' : "aa",
        'offsetHeight' : 12,
        'offsetLeft' : 12,
        'offsetParent' : 12,
        'offsetTop' : 12,
        'offsetWidth' : 12,
        'ownerDocument' : Document(),
        'parentNode' : Element(),
        'prefix' : "aa",
        'previousSibling' : Element(),
        'scrollHeight' : 12,
        'scrollLeft' : 12,
        'scrollTop' : 12,
        'scrollWidth' : 12,
        'style' : Style(),
        'tabIndex' : 12,
        'tagName' : "aa",
        'textContent' : "aa",
        'value' : "aa",
        'onblur' : MethodDesc([Event()]),
        'onclick' : MethodDesc([MouseEvent()]),
        'ondblclick' : MethodDesc([MouseEvent()]),
        'onfocus' : MethodDesc([Event()]),
        'onkeydown' : MethodDesc([KeyEvent()]),
        'onkeypress' : MethodDesc([KeyEvent()]),
        'onkeyup' : MethodDesc([KeyEvent()]),
        'onmousedown' : MethodDesc([MouseEvent()]),
        'onmousemove' : MethodDesc([MouseEvent()]),
        'onmouseup' : MethodDesc([MouseEvent()]),
        'onmouseover' : MethodDesc([MouseEvent()]),
        'onmouseup' : MethodDesc([MouseEvent()]),
        'onresize' : MethodDesc([Event()]),
    }

Element._methods = {
        'addEventListener' : MethodDesc(["aa", lambda : None, True]),
        'appendChild' : MethodDesc([Element()]),
        'blur' : MethodDesc([]),
        'click' : MethodDesc([]),
        'cloneNode' : MethodDesc([12], Element()),
        'dispatchEvent' : MethodDesc(["aa"], True),
        'focus' : MethodDesc([]),
        'getAttribute' : MethodDesc(["aa"], "aa"),
        'getAttributeNS' : MethodDesc(["aa", "aa"], "aa"),
        'getAttributeNode' : MethodDesc(["aa"], Element()),
        'getAttributeNodeNS' : MethodDesc(["aa", "aa"], Element()),
        'getElementsByTagName' : MethodDesc(["aa"], [Element(), Element()]),
        'hasAttribute' : MethodDesc(["aa"], True),
        'hasAttributeNS' : MethodDesc(["aa", "aa"], True),
        'hasAttributes' : MethodDesc([], True),
        'hasChildNodes' : MethodDesc([], True),
        'insertBefore' : MethodDesc([Element(), Element()], Element()),
        'item' : MethodDesc([3], Element()),
        'normalize' : MethodDesc([]),
        'removeAttribute' : MethodDesc(['aa']),
        'removeAttributeNS' : MethodDesc(["aa", "aa"]),
        'removeAttributeNode' : MethodDesc([Element()], "aa"),
        'removeChild' : MethodDesc([Element()], Element()),
        'removeEventListener' : MethodDesc(["aa", lambda : None, True]),
        'replaceChild' : MethodDesc([Element(), Element()], Element()),
        'scrollIntoView' : MethodDesc([12]),
        'setAttribute' : MethodDesc(["aa", "aa"]),
        'setAttributeNS' : MethodDesc(["aa", "aa", "aa"]),
        'setAttributeNode' : MethodDesc([Element()], Element()),
        'setAttributeNodeNS' : MethodDesc(["ns", Element()], Element()),
        'supports' : MethodDesc(["aa", 1.0]),
    }

Document._methods = Element._methods.copy()
Document._methods.update({
    'clear' : MethodDesc([]),
    'close' : MethodDesc([]),
    'createAttribute' : MethodDesc(["aa"], Element()),
    'createDocumentFragment' : MethodDesc([], Element()),
    'createElement' : MethodDesc(["aa"], Element()),
    'createElementNS' : MethodDesc(["aa", "aa"], Element()),
    'createTextNode' : MethodDesc(["aa"], Element()),
    'createEvent' : MethodDesc(["aa"], Event()),
    #'createRange' : MethodDesc(["aa"], Range()) - don't know what to do here
    'getElementById' : MethodDesc(["aa"], Element()),
    'getElementsByName' : MethodDesc(["aa"], [Element(), Element()]),
    'getElementsByTagName' : MethodDesc(["aa"], [Element(), Element()]),
    'importNode' : MethodDesc([Element(), True], Element()),
    'open' : MethodDesc([]),
    'write' : MethodDesc(["aa"]),
    'writeln' : MethodDesc(["aa"]),
})

Document._fields = Element._fields.copy()
Document._fields.update({
    'alinkColor' : "aa",
    'bgColor' : "aa",
    'body' : Element(),
    'characterSet' : "aa",
    'cookie' : "aa",
    'contentWindow' : Window(),
    'defaultView' : Window(),
    'doctype' : "aa",
    'documentElement' : Element(),
    'domain' : "aa",
    'embeds' : [Element(), Element()],
    'fgColor' : "aa",
    'firstChild' : Element(),
    'forms' : [Form(), Form()],
    'height' : 123,
    'images' : [Element(), Element()],
    'lastModified' : "aa",
    'linkColor' : "aa",
    'links' : [Element(), Element()],
    'location' : "aa",
    'namespaceURI' : "aa",
    'referrer' : "aa",
    'styleSheets' : [Style(), Style()],
    'title' : "aa",
    'URL' : "aa",
    'vlinkColor' : "aa",
    'width' : 123,
})

Window._fields = Element._fields.copy()
Window._fields.update({
    'content' : Window(),
    'closed' : True,
    #'crypto' : Crypto() - not implemented in Gecko, leave alone
    'defaultStatus' : "aa",
    'document' : Document(),
    # 'frameElement' :  - leave alone
    'frames' : [Window(), Window()],
    'history' : ["aa", "aa"],
    'innerHeight' : 123,
    'innerWidth' : 123,
    'length' : 12,
    'location' : "aa",
    'name' : "aa",
    # 'preference' : # denied in gecko
    'opener' : Window(),
    'outerHeight' : 123,
    'outerWidth' : 123,
    'pageXOffset' : 12,
    'pageYOffset' : 12,
    'parent' : Window(),
    # 'personalbar' :  - disallowed
    # 'screen' : Screen() - not part of the standard, allow it if you want
    'screenX' : 12,
    'screenY' : 12,
    'scrollMaxX' : 12,
    'scrollMaxY' : 12,
    'scrollX' : 12,
    'scrollY' : 12,
    'self' : Window(),
    'status' : "asd",
    'top' : Window(),
    'window' : Window(),
})

Window._methods = Element._methods.copy()
Window._methods.update({
    'alert' : MethodDesc(["aa"]),
    'atob' : MethodDesc(["aa"], "aa"),
    'back' : MethodDesc([]),
    'blur' : MethodDesc([]),
    'btoa' : MethodDesc(["aa"], "aa"),
    'close' : MethodDesc([]),
    'confirm' : MethodDesc(["aa"], True),
    'dump' : MethodDesc(["aa"]),
    'escape' : MethodDesc(["aa"], "aa"),
    #'find' : MethodDesc(["aa"],  - gecko only
    'focus' : MethodDesc([]),
    'forward' : MethodDesc([]),
    'getComputedStyle' : MethodDesc([Element(), "aa"], Style()),
    'home' : MethodDesc([]),
    'open' : MethodDesc(["aa", "aa"]),
    'onabort' : MethodDesc([Event()]),
    'onblur' : MethodDesc([Event()]),
    'onchange' : MethodDesc([Event()]),
    'onclick' : MethodDesc([MouseEvent()]),
    'onclose' : MethodDesc([MouseEvent()]),
    'ondragdrop' : MethodDesc([MouseEvent()]),
    'onerror' : MethodDesc([MouseEvent()]),
    'onfocus' : MethodDesc([Event()]),
    'onkeydown' : MethodDesc([KeyEvent()]),
    'onkeypress' : MethodDesc([KeyEvent()]),
    'onkeyup' : MethodDesc([KeyEvent()]),
    'onload' : MethodDesc([KeyEvent()]),
    'onmousedown' : MethodDesc([MouseEvent()]),
    'onmousemove' : MethodDesc([MouseEvent()]),
    'onmouseup' : MethodDesc([MouseEvent()]),
    'onmouseover' : MethodDesc([MouseEvent()]),
    'onmouseup' : MethodDesc([MouseEvent()]),
    'onresize' : MethodDesc([MouseEvent()]),
    'onscroll' : MethodDesc([MouseEvent()]),
    'onselect' : MethodDesc([MouseEvent()]),
    'onsubmit' : MethodDesc([MouseEvent()]),
    'onunload' : MethodDesc([Event()]),
})

# set the global 'window' instance to an empty HTML document, override using
# dom.window = Window(html) (this will also set dom.document)
window = Window()
def get_document():
    return document

def get_window():
    return window

get_window.suggested_primitive = True
get_document.suggested_primitive = True

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
