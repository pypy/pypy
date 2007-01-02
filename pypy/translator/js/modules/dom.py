
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
import re
import urllib
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc
from pypy.rlib.nonconst import NonConstant

from pypy.translator.stackless.test.test_transform import one
from xml.dom import minidom

# EventTarget is the base class for Nodes and Window
class EventTarget(BasicExternal):
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

# XML node (level 2 basically) implementation
#   the following classes are mostly wrappers around minidom nodes that try to
#   mimic HTML DOM behaviour by implementing browser API and changing the
#   behaviour a bit

class Node(EventTarget):
    """base class of all node types"""
    _original = None
    
    def __init__(self, node=None):
        self._original = node
    
    def __getattr__(self, name):
        """attribute access gets proxied to the contained minidom node

            all returned minidom nodes are wrapped as Nodes
        """
        try:
            return super(Node, self).__getattr__(name)
        except AttributeError:
            pass
        if (name not in self._fields and
                (not hasattr(self, '_methods') or name not in self._methods)):
            raise NameError, name
        value = getattr(self._original, name)
        return _wrap(value)

    def __setattr__(self, name, value):
        """set an attribute on the wrapped node"""
        if name in dir(self) or name.startswith('_'):
            return super(Node, self).__setattr__(name, value)
        if name not in self._fields:
            raise NameError, name
        setattr(self._original, name, value)

    def __eq__(self, other):
        original = getattr(other, '_original', other)
        return original is self._original

    def __ne__(self, other):
        original = getattr(other, '_original', other)
        return original is not self._original

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

class Element(Node):
    nodeType = 1
    style = None

    def _style(self):
        style = getattr(self._original, '_style', None)
        if style is not None:
            return style
        styles = {}
        if self._original.hasAttribute('style'):
            for t in self._original.getAttribute('style').split(';'):
                name, value = t.split(':')
                dashcharpairs = re.findall('-\w', name)
                for p in dashcharpairs:
                    name = name.replace(p, p[1].upper())
                styles[name.strip()] = value.strip()
        style = Style(styles)
        self._original._style = style
        return style
    style = property(_style)

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

    def scrollIntoView(self):
        pass

class Attribute(Node):
    nodeType = 2

class Text(Node):
    nodeType = 3

class Comment(Node):
    nodeType = 8

class Document(Node):
    nodeType = 9
    
    def createEvent(self, group=''):
        """create an event

            note that the group argument is ignored
        """
        if group in ('KeyboardEvent', 'KeyboardEvents'):
            return KeyEvent()
        elif group in ('MouseEvent', 'MouseEvents'):
            return MouseEvent()
        return Event()

    def getElementById(self, id):
        nodes = self.getElementsByTagName('*')
        for node in nodes:
            if node.getAttribute('id') == id:
                return node

# the standard DOM stuff that doesn't directly deal with XML
#   note that we're mimicking the standard (Mozilla) APIs, so things tested
#   against this code may not work in Internet Explorer

# XXX note that we store the events on the wrapped minidom node to avoid losing
# them on re-wrapping
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
    def __init__(self, styles={}):
        for name, value in styles.iteritems():
            setattr(self, name, value)
    
    def __getattr__(self, name):
        if name not in self._fields:
            raise AttributeError, name
        return None

    def _tostring(self):
        ret = []
        for name in sorted(self._fields):
            value = getattr(self, name, None)
            if value is not None:
                ret.append(' ')
                for char in name:
                    if char.upper() == char:
                        char = '-%s' % (char.lower(),)
                    ret.append(char)
                ret.append(': %s;' % (value,))
        return ''.join(ret[1:])

# non-DOM ('DOM level 0') stuff

# Window is the main environment, the root node of the JS object tree

class Window(EventTarget):
    def __init__(self, html=('<html><head><title>Untitled document</title>'
                             '</head><body></body></html>'), parent=None):
        super(Window, self).__init__()
        self._html = html
        self.document = Document(minidom.parseString(html))

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
        self.document = Document(minidom.parseString(html))
    
    location = property(_getLocation, _setLocation)

def some_fun():
    pass
    
def setTimeout(func, delay):
    # scheduler call, but we don't want to mess with threads right now
    if one():
        setTimeout(some_fun, delay)
    else:
        func()
    #pass

window = Window()
document = window.document
window._render_name = 'window'
document._render_name = 'document'

# rtyper stuff

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

Node._fields = EventTarget._fields.copy()
Node._fields.update({
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
    'previousSibling': Element(),
    'tagName' : "aa",
    'textContent' : "aa",
})

Node._methods = EventTarget._methods.copy()
Node._methods.update({
    'appendChild' : MethodDesc([Element()]),
    'cloneNode' : MethodDesc([12], Element()),
    'getElementsByTagName' : MethodDesc(["aa"], [Element(),
                                                 Element()]),
    'hasChildNodes' : MethodDesc([], True),
    'insertBefore' : MethodDesc([Element(), Element()], Element()),
    'normalize' : MethodDesc([]),
    'removeChild' : MethodDesc([Element()], Element()),
    'replaceChild' : MethodDesc([Element(), Element()], Element()),
})

Element._fields = Node._fields.copy()
Element._fields.update({
    'attributes' : [Attribute()],
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
    # HTML specific
    'style' : Style(),
    'tabIndex' : 12,
    # XXX: From HTMLInputElement to make pythonconsole work.
    'value': 'aa',
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
    # HTML specific
    'blur' : MethodDesc([]),
    'click' : MethodDesc([]),
    'focus' : MethodDesc([]),
    'scrollIntoView' : MethodDesc([]),
    'supports' : MethodDesc(["aa", 1.0]),
})

Document._fields = Node._fields.copy()
Document._fields.update({
    'characterSet' : "aa",
    # 'contentWindow' : Window(), XXX doesn't exist, only on iframe
    'doctype' : "aa",
    'documentElement' : Element(),
    'styleSheets' : [Style(), Style()],
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
    'clear' : MethodDesc([]),
    'close' : MethodDesc([]),
    'open' : MethodDesc([]),
    'write' : MethodDesc(["aa"]),
    'writeln' : MethodDesc(["aa"]),
})

Window._fields = EventTarget._fields.copy()
Window._fields.update({
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
})

Window._methods = Node._methods.copy()
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
})

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

setTimeout.suggested_primitive = True

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
    1: Element,
    2: Attribute,
    3: Text,
    8: Comment,
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

# some helper functions

def _quote_html(text):
    for char, e in [('&', 'amp'), ('<', 'lt'), ('>', 'gt'), ('"', 'quot'),
                    ("'", 'apos')]:
        text = text.replace(char, '&%s;' % (e,))
    return text

_singletons = ['link', 'meta']
def _serialize_html(node):
    ret = []
    if node.nodeType in [3, 8]:
        return node.nodeValue
    elif node.nodeType == 1:
        original = getattr(node, '_original', node)
        nodeName = original.nodeName
        ret += ['<', nodeName]
        if len(node.attributes):
            for aname in node.attributes.keys():
                if aname == 'style':
                    continue
                attr = node.attributes[aname]
                ret.append(' %s="%s"' % (attr.nodeName,
                                         _quote_html(attr.nodeValue)))
        styles = getattr(original, '_style', None)
        if styles:
            ret.append(' style="%s"' % (_quote_html(styles._tostring()),))
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
    else:
        raise ValueError('unsupported node type %s' % (node.nodeType,))
    return ''.join(ret)

# initialization

# set the global 'window' instance to an empty HTML document, override using
# dom.window = Window(html) (this will also set dom.document)

