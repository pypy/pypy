
"""Document Object Model support

    this provides a mock browser API, both the standard DOM level 2 stuff as
    the browser-specific additions

    note that the API is not and will not be complete: more exotic features 
    will most probably not behave as expected, or are not implemented at all
    
    http://www.w3.org/DOM/ - main standard
    http://www.w3schools.com/dhtml/dhtml_dom.asp - more informal stuff
    http://developer.mozilla.org/en/docs/Gecko_DOM_Reference - Gecko reference
"""

import time
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc
from pypy.rlib.nonconst import NonConstant

from pypy.translator.stackless.test.test_transform import one
from xml.dom import minidom

# XML node (level 2 basically) implementation
#   the following classes are mostly wrappers around minidom nodes that try to
#   mimic HTML DOM behaviour by implementing browser API and changing the
#   behaviour a bit

class Node(BasicExternal):
    """base class of all node types"""
    
    def __init__(self, node=None):
        self._original = node
    
    def __getattr__(self, name):
        """attribute access gets proxied to the contained minidom node

            all returned minidom nodes are wrapped as Nodes
        """
        if (name not in self._fields and
                (not hasattr(self, '_methods') or name not in self._methods)):
            raise NameError, name
        value = getattr(self._original, name)
        return _wrap(value)

    def __eq__(self, other):
        original = getattr(other, '_original', other)
        return original is self._original

class Element(Node):
    nodeType = 1

class Attribute(Node):
    nodeType = 2

class Text(Node):
    nodeType = 3

class Document(Node):
    nodeType = 9
    
    def __init__(self, docnode=None):
        super(Document, self).__init__(docnode)
        self._original = docnode

    def createEvent(self, group=''):
        """create an event

            note that the group argument is ignored
        """
        if group in ('KeyboardEvent', 'KeyboardEvents'):
            return KeyEvent()
        elif group in ('MouseEvent', 'MouseEvents'):
            return MouseEvent()
        return Event()

# the standard DOM stuff that doesn't directly deal with XML
#   note that we're mimicking the standard (Mozilla) APIs, so things tested
#   against this code may not work in Internet Explorer

# XXX note that we store the events on the wrapped minidom node to avoid losing
# them on re-wrapping
class EventTarget(BasicExternal): # XXX mixin... is the super correct?!?
    def addEventListener(self, type, listener, useCapture):
        if not hasattr(self._original, '_events'):
            self._original._events = []
        # XXX note that useCapture is ignored...
        self._original._events.append((type, listener, useCapture))

    def dispatchEvent(self, event):
        if event._cancelled:
            return
        event.currentTarget = self
        if event.target is None:
            event.target = self
        if event.originalTarget is None:
            event.originalTarget = self
        if hasattr(self._original, '_events'):
            for etype, handler, capture in self._original._events:
                if etype == event.type:
                    handler(event)
        if event._cancelled or event.cancelBubble:
            return
        parent = getattr(self, 'parentNode', None)
        if parent is not None:
            parent.dispatchEvent(event)

    def removeEventListener(self, type, listener, useCapture):
        if not hasattr(self._original, '_events'):
            raise ValueError('no registration for listener')
        filtered = []
        for data in self._original._events:
            if data != (type, listener, useCapture):
                filtered.append(data)
        if filtered == self._original._events:
            raise ValueError('no registration for listener')
        self._original._events = filtered

class Event(BasicExternal):
    def initEvent(self, type, bubbles, cancelable):
        self.type = type
        self.cancelBubble = not bubbles
        self.cancelable = cancelable
        self.target = None
        self.currentTarget = None
        self.originalTarget = None
        self._cancelled = False

    def preventDefault(self):
        if not self.cancelable:
            raise TypeError('event can not be canceled')
        self._cancelled = True

    def stopPropagation(self):
        self.cancelBubble = True

class KeyEvent(Event):
    pass

class MouseEvent(Event):
    pass

class Style(BasicExternal):
    def __getattr__(self, name):
        if name not in self._fields:
            raise AttributeError, name
        return None

# HTML DOM

class HTMLNode(Node, EventTarget):
    def getElementsByTagName(self, name):
        name = name.lower()
        return self.__getattr__('getElementsByTagName')(name)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.nodeName)

    def _getClassName(self):
        return self.getAttribute('class')

    def _setClassName(self, name):
        self.setAttribute('class', name)

    className = property(_getClassName, _setClassName)

    def _getId(self):
        return self.getAttribute('id')

    def _setId(self, id):
        self.setAttribute('id', id)

    id = property(_getId, _setId)

class HTMLElement(HTMLNode, Element):
    id = ''
    style = None

    def __init__(self, node=None):
        super(Element, self).__init__(node)
        self.style = Style()

    def _nodeName(self):
        return self._original.nodeName.upper()
    nodeName = property(_nodeName)

    def _get_innerHTML(self):
        ret = []
        for child in self.childNodes:
            ret.append(_serialize_html(child))
        return ''.join(ret)

    def _set_innerHTML(self, html):
        dom = minidom.parseString('<doc>%s</doc>' % (html,))
        while self.childNodes:
            self.removeChild(self.lastChild)
        for child in dom.documentElement.childNodes:
            child = self.ownerDocument.importNode(child, True)
            self._original.appendChild(child)
        del dom

    innerHTML = property(_get_innerHTML, _set_innerHTML)

class HTMLDocument(Document, HTMLNode):
    def getElementById(self, id):
        nodes = self.getElementsByTagName('*')
        for node in nodes:
            if node.getAttribute('id') == id:
                return node

# non-DOM ('DOM level 0') stuff

# Window is the main environment, the root node of the JS object tree

class Window(EventTarget):
    def __init__(self, html=('<html><head><title>Untitled document</title>'
                             '</head><body></body></html>'), parent=None):
        self._html = html
        self.document = HTMLDocument(minidom.parseString(html))

        # references to windows
        self.content = self
        self.self = self
        self.window = self
        self.parent = parent or self
        self.top = self.parent
        while 1:
            if self.top.parent is self.top:
                break
            self.top = self.top.parent

        # other properties
        self.closed = True
        self._location = 'about:blank'

        self._original = self # for EventTarget interface (XXX a bit nasty)

    def __getattr__(self, name):
        return globals()[name]

    def _getLocation(self):
        return self._location

    def _setLocation(self, newloc):
        url = urllib.urlopen(newloc)
        html = url.read()
        self.document = HTMLDocument(minidom.parseString(html))
    
    location = property(_getLocation, _setLocation)

def setTimeout(func, delay):
    # scheduler call, but we don't want to mess with threads right now
    if one():
        setTimeout(some_fun, delay)
    else:
        func()
    #pass

def alert(msg):
    pass

# some helper functions (XXX imo these can go, but the code seems to use them
# a lot... isn't it possible to just use dom.window and dom.document instead?)

def get_document():
    return NonConstant(window.document)

def get_window():
    return NonConstant(window)

# rtyper stuff

# the Node base class contains just about all XML-related properties
Node._fields = {
    'childNodes' : [Element()],
    'firstChild' : Element(),
    'lastChild' : Element(),
    'localName' : "aa",
    'name' : "aa",
    'namespaceURI' : "aa",
    'nextSibling' : Element(),
    'nodeName' : "aa",
    'nodeType' : 1,
    'nodeValue' : "aa",
    'ownerDocument' : Document(),
    'parentNode' : Element(),
    'prefix' : "aa",
    'previousSibling' : Element(),
    'tagName' : "aa",
    'textContent' : "aa",
}

Node._methods = {
    'appendChild' : MethodDesc([Element()]),
    'cloneNode' : MethodDesc([12], Element()),
    'getElementsByTagName' : MethodDesc(["aa"], [Element(), Element()]),
    'hasChildNodes' : MethodDesc([], True),
    'insertBefore' : MethodDesc([Element(), Element()], Element()),
    'normalize' : MethodDesc([]),
    'removeChild' : MethodDesc([Element()], Element()),
    'replaceChild' : MethodDesc([Element(), Element()], Element()),
}

Element._fields = Node._fields.copy()
Element._fields.update({
    'attributes' : [Attribute()],
})

Element._methods = Node._methods.copy()
Element._methods.update({
    'getAttribute' : MethodDesc(["aa"], "aa"),
    'getAttributeNS' : MethodDesc(["aa", "aa"], "aa"),
    'getAttributeNode' : MethodDesc(["aa"], Element()),
    'getAttributeNodeNS' : MethodDesc(["aa", "aa"], Element()),
    'hasAttribute' : MethodDesc(["aa"], True),
    'hasAttributeNS' : MethodDesc(["aa", "aa"], True),
    'hasAttributes' : MethodDesc([], True),
    'removeAttribute' : MethodDesc(['aa']),
    'removeAttributeNS' : MethodDesc(["aa", "aa"]),
    'removeAttributeNode' : MethodDesc([Element()], "aa"),
    'setAttribute' : MethodDesc(["aa", "aa"]),
    'setAttributeNS' : MethodDesc(["aa", "aa", "aa"]),
    'setAttributeNode' : MethodDesc([Element()], Element()),
    'setAttributeNodeNS' : MethodDesc(["ns", Element()], Element()),
})

HTMLNode._fields = Node._fields.copy()
HTMLNode._methods = Node._methods.copy()

HTMLElement._fields = HTMLNode._fields.copy()
HTMLElement._fields.update(Element._fields.copy())
HTMLElement._fields.update({
    'className' : "aa",
    'clientHeight' : 12,
    'clientWidth' : 12,
    'clientLeft' : 12,
    'clientTop' : 12,
    'dir' : "aa",
    'innerHTML' : "asd",
    'id' : "aa",
    'lang' : "asd",
    'offsetHeight' : 12,
    'offsetLeft' : 12,
    'offsetParent' : 12,
    'offsetTop' : 12,
    'offsetWidth' : 12,
    'scrollHeight' : 12,
    'scrollLeft' : 12,
    'scrollTop' : 12,
    'scrollWidth' : 12,
    'style' : Style(),
    'tabIndex' : 12,
    'value' : "aa", # XXX?
})

HTMLElement._methods = HTMLNode._methods.copy()
HTMLElement._methods.update(Element._methods.copy())
HTMLElement._methods.update({
    'blur' : MethodDesc([]),
    'click' : MethodDesc([]),
    'focus' : MethodDesc([]),
    'scrollIntoView' : MethodDesc([12]),
    'supports' : MethodDesc(["aa", 1.0]),
})

Document._fields = Node._fields.copy()
Document._fields.update({
    'characterSet' : "aa",
    # 'contentWindow' : Window(), XXX doesn't exist, only on iframe
    'doctype' : "aa",
    'documentElement' : Element(),
    'styleSheets' : [Style(), Style()],
})

Document._methods = Node._methods.copy()
Document._methods.update({
    'createAttribute' : MethodDesc(["aa"], Element()),
    'createDocumentFragment' : MethodDesc([], Element()),
    'createElement' : MethodDesc(["aa"], Element()),
    'createElementNS' : MethodDesc(["aa", "aa"], Element()),
    'createEvent' : MethodDesc(["aa"], Event()),
    'createTextNode' : MethodDesc(["aa"], Element()),
    #'createRange' : MethodDesc(["aa"], Range()) - don't know what to do here
    'getElementById' : MethodDesc(["aa"], Element()),
    'getElementsByName' : MethodDesc(["aa"], [Element(), Element()]),
    'importNode' : MethodDesc([Element(), True], Element()),
})

HTMLDocument._fields = Document._fields.copy()
HTMLDocument._fields.update({
    'alinkColor' : "aa",
    'bgColor' : "aa",
    'body' : Element(),
    'cookie' : "aa",
    'defaultView' : Window(),
    'domain' : "aa",
    'embeds' : [Element(), Element()],
    'fgColor' : "aa",
    'forms' : [Element(), Element()],
    'height' : 123,
    'images' : [Element(), Element()],
    'lastModified' : "aa",
    'linkColor' : "aa",
    'links' : [Element(), Element()],
    'location' : "aa",
    'referrer' : "aa",
    'title' : "aa",
    'URL' : "aa",
    'vlinkColor' : "aa",
    'width' : 123,
})

HTMLDocument._methods = Document._methods.copy()
HTMLDocument._methods.update({
    'clear' : MethodDesc([]),
    'close' : MethodDesc([]),
    'open' : MethodDesc([]),
    'write' : MethodDesc(["aa"]),
    'writeln' : MethodDesc(["aa"]),
})

Window._fields = {
    'content' : Window(),
    'closed' : True,
    # 'crypto' : Crypto() - not implemented in Gecko, leave alone
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
}

Window._methods = {
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
}

Style._fields = {
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

EventTarget._fields = {
    'onabort' : MethodDesc([Event()]),
    'onblur' : MethodDesc([Event()]),
    'onchange' : MethodDesc([Event()]),
    'onclick' : MethodDesc([MouseEvent()]),
    'onclose' : MethodDesc([MouseEvent()]),
    'ondblclick' : MethodDesc([MouseEvent()]),
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
    'onresize' : MethodDesc([Event()]),
    'onscroll' : MethodDesc([MouseEvent()]),
    'onselect' : MethodDesc([MouseEvent()]),
    'onsubmit' : MethodDesc([MouseEvent()]),
    'onunload' : MethodDesc([Event()]),
}

EventTarget._methods = {
    'addEventListener' : MethodDesc(["aa", lambda : None, True]),
    'dispatchEvent' : MethodDesc(["aa"], True),
    'removeEventListener' : MethodDesc(["aa", lambda : None, True]),
}

Event._fields = {
    'bubbles': True,
    'cancelBubble': True,
    'cancelable': True,
    'currentTarget': Element(),
    'detail': 1,
    'relatedTarget': Element(),
    'target': Element(),
    'type': 'aa',
}

Event._methods = {
    'initEvent': MethodDesc(["aa", True, True]),
    'preventDefault': MethodDesc([]),
    'stopPropagation': MethodDesc([]),
}

KeyEvent._fields = Event._fields.copy()
KeyEvent._fields.update({
    'keyCode' : 12,
    'charCode' : 12,
})

get_window.suggested_primitive = True
get_document.suggested_primitive = True
setTimeout.suggested_primitive = True
alert.suggested_primitive = True

# the following code wraps minidom nodes with Node classes, and makes
# sure all methods on the nodes return wrapped nodes

class _FunctionWrapper(object):
    """makes sure function return values are wrapped if appropriate"""
    def __init__(self, callable):
        self._original = callable

    def __call__(self, *args, **kwargs):
        args = list(args)
        for i, arg in enumerate(args):
            if isinstance(arg, Node):
                args[i] = arg._original
        for name, arg in kwargs.iteritems():
            if isinstance(arg, Node):
                kwargs[arg] = arg._original
        value = self._original(*args, **kwargs)
        return _wrap(value)

_typetoclass = {
    1: HTMLElement,
    2: Attribute,
    3: Text,
    9: HTMLDocument,
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

# some helper functions

def _quote_html(text):
    for char, e in [('&', 'amp'), ('<', 'lt'), ('>', 'gt'), ('"', 'quot'),
                    ("'", 'apos')]:
        text = text.replace(char, '&%s;' % (e,))
    return text

_singletons = ['link', 'meta']
def _serialize_html(node):
    ret = []
    if node.nodeType == 1:
        nodeName = getattr(node, '_original', node).nodeName
        ret += ['<', nodeName]
        if len(node.attributes):
            for aname in node.attributes.keys():
                attr = node.attributes[aname]
                ret.append(' %s="%s"' % (attr.nodeName,
                                         _quote_html(attr.nodeValue)))
        if len(node.childNodes) or nodeName not in _singletons:
            ret.append('>')
            for child in node.childNodes:
                if child.nodeType == 1:
                    ret.append(_serialize_html(child))
                else:
                    ret.append(_quote_html(child.nodeValue))
            ret += ['</', nodeName, '>']
        else:
            ret.append(' />')
    return ''.join(ret)

# initialization

# set the global 'window' instance to an empty HTML document, override using
# dom.window = Window(html) (this will also set dom.document)
window = Window()
this = window

