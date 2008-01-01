
"""Document Object Model support

    this provides a mock browser API, both the standard DOM level 2 stuff as
    the browser-specific additions
    
    in addition this provides the necessary descriptions that allow rpython
    code that calls the browser DOM API to be translated

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

from pypy.rpython.extfunc import genericcallable
from pypy.rpython.extfunc import register_external
from xml.dom import minidom

from pypy.annotation.signature import annotation
from pypy.annotation import model as annmodel

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

class Location(BasicExternal):
    _fields = {
        'hostname' : str,
        'href' : str,
        'hash' : str,
        'host' : str,
        'pathname' : str,
        'port' : str,
        'protocol' : str,
        'search' : str,
    }
    _methods = {
        'assign' : MethodDesc([str]),
        'reload' : MethodDesc([bool]),
        'replace' : MethodDesc([str]),
        'toString' : MethodDesc([], str),
    }

class Navigator(BasicExternal):
    def __init__(self):
        self.appName = 'Netscape'

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

        self.navigator = Navigator()

    def __getattr__(self, name):
        return globals()[name]

    def _getLocation(self):
        return self._location

    def _setLocation(self, newloc):
        url = urllib.urlopen(newloc)
        html = url.read()
        self.document = Document(minidom.parseString(html))
    
    location = property(_getLocation, _setLocation)

scrollX = 0
scrollMaxX = 0
scrollY = 0
scrollMaxY = 0

def some_fun():
    pass

def setTimeout(func, delay):
    pass
register_external(setTimeout, args=[genericcallable([]), int], result=None)

window = Window()
window._render_name = 'window'
document = window.document
document._render_name = 'document'

# rtyper stuff

EventTarget._fields = {
    'onabort' : genericcallable([Event]),
    'onblur' : genericcallable([Event]),
    'onchange' : genericcallable([Event]),
    'onclick' : genericcallable([MouseEvent]),
    'onclose' : genericcallable([MouseEvent]),
    'ondblclick' : genericcallable([MouseEvent]),
    'ondragdrop' : genericcallable([MouseEvent]),
    'onerror' : genericcallable([MouseEvent]),
    'onfocus' : genericcallable([Event]),
    'onkeydown' : genericcallable([KeyEvent]),
    'onkeypress' : genericcallable([KeyEvent]),
    'onkeyup' : genericcallable([KeyEvent]),
    'onload' : genericcallable([KeyEvent]),
    'onmousedown' : genericcallable([MouseEvent]),
    'onmousemove' : genericcallable([MouseEvent]),
    'onmouseup' : genericcallable([MouseEvent]),
    'onmouseover' : genericcallable([MouseEvent]),
    'onresize' : genericcallable([Event]),
    'onscroll' : genericcallable([MouseEvent]),
    'onselect' : genericcallable([MouseEvent]),
    'onsubmit' : genericcallable([MouseEvent]),
    'onunload' : genericcallable([Event]),
}

lambda_returning_true = genericcallable([Event])

EventTarget._methods = {
    'addEventListener' : MethodDesc([str, lambda_returning_true, bool]),
    'dispatchEvent' : MethodDesc([str], bool),
    'removeEventListener' : MethodDesc([str, lambda_returning_true, bool]),
}

Node._fields = EventTarget._fields.copy()
Node._fields.update({
    'childNodes' : [Element],
    'firstChild' : Element,
    'lastChild' : Element,
    'localName' : str,
    'name' : str,
    'namespaceURI' : str,
    'nextSibling' : Element,
    'nodeName' : str,
    'nodeType' : int,
    'nodeValue' : str,
    'ownerDocument' : Document,
    'parentNode' : Element,
    'prefix' : str,
    'previousSibling': Element,
    'tagName' : str,
    'textContent' : str,
})

Node._methods = EventTarget._methods.copy()
Node._methods.update({
    'appendChild' : MethodDesc([Element]),
    'cloneNode' : MethodDesc([int], Element),
    'getElementsByTagName' : MethodDesc([str], [Element]),
    'hasChildNodes' : MethodDesc([], bool),
    'insertBefore' : MethodDesc([Element, Element], Element),
    'normalize' : MethodDesc([]),
    'removeChild' : MethodDesc([Element]),
    'replaceChild' : MethodDesc([Element, Element], Element),
})

Element._fields = Node._fields.copy()
Element._fields.update({
    'attributes' : [Attribute],
    'className' : str,
    'clientHeight' : int,
    'clientWidth' : int,
    'clientLeft' : int,
    'clientTop' : int,
    'dir' : str,
    'innerHTML' : str,
    'id' : str,
    'lang' : str,
    'offsetHeight' : int,
    'offsetLeft' : int,
    'offsetParent' : int,
    'offsetTop' : int,
    'offsetWidth' : int,
    'scrollHeight' : int,
    'scrollLeft' : int,
    'scrollTop' : int,
    'scrollWidth' : int,
    'disabled': bool,
    # HTML specific
    'style' : Style,
    'tabIndex' : int,
    # XXX: From HTMLInputElement to make pythonconsole work.
    'value': str,
    'checked': bool,
    # IMG specific
    'src': str,
})

Element._methods = Node._methods.copy()
Element._methods.update({
    'getAttribute' : MethodDesc([str], str),
    'getAttributeNS' : MethodDesc([str], str),
    'getAttributeNode' : MethodDesc([str], Element),
    'getAttributeNodeNS' : MethodDesc([str], Element),
    'hasAttribute' : MethodDesc([str], bool),
    'hasAttributeNS' : MethodDesc([str], bool),
    'hasAttributes' : MethodDesc([], bool),
    'removeAttribute' : MethodDesc([str]),
    'removeAttributeNS' : MethodDesc([str]),
    'removeAttributeNode' : MethodDesc([Element], str),
    'setAttribute' : MethodDesc([str, str]),
    'setAttributeNS' : MethodDesc([str]),
    'setAttributeNode' : MethodDesc([Element], Element),
    'setAttributeNodeNS' : MethodDesc([str, Element], Element),
    # HTML specific
    'blur' : MethodDesc([]),
    'click' : MethodDesc([]),
    'focus' : MethodDesc([]),
    'scrollIntoView' : MethodDesc([]),
    'supports' : MethodDesc([str, float]),
})

Document._fields = Node._fields.copy()
Document._fields.update({
    'characterSet' : str,
    # 'contentWindow' : Window(), XXX doesn't exist, only on iframe
    'doctype' : str,
    'documentElement' : Element,
    'styleSheets' : [Style],
    'alinkColor' : str,
    'bgColor' : str,
    'body' : Element,
    'cookie' : str,
    'defaultView' : Window,
    'domain' : str,
    'embeds' : [Element],
    'fgColor' : str,
    'forms' : [Element],
    'height' : int,
    'images' : [Element],
    'lastModified' : str,
    'linkColor' : str,
    'links' : [Element],
    'referrer' : str,
    'title' : str,
    'URL' : str,
    'vlinkColor' : str,
    'width' : int,
})

Document._methods = Node._methods.copy()
Document._methods.update({
    'createAttribute' : MethodDesc([str], Element),
    'createDocumentFragment' : MethodDesc([], Element),
    'createElement' : MethodDesc([str], Element),
    'createElementNS' : MethodDesc([str], Element),
    'createEvent' : MethodDesc([str], Event),
    'createTextNode' : MethodDesc([str], Element),
    #'createRange' : MethodDesc(["aa"], Range()) - don't know what to do here
    'getElementById' : MethodDesc([str], Element),
    'getElementsByName' : MethodDesc([str], [Element]),
    'importNode' : MethodDesc([Element, bool], Element),
    'clear' : MethodDesc([]),
    'close' : MethodDesc([]),
    'open' : MethodDesc([]),
    'write' : MethodDesc([str]),
    'writeln' : MethodDesc([str]),
})

Window._fields = EventTarget._fields.copy()
Window._fields.update({
    'content' : Window,
    'closed' : bool,
    # 'crypto' : Crypto() - not implemented in Gecko, leave alone
    'defaultStatus' : str,
    'document' : Document,
    # 'frameElement' :  - leave alone
    'frames' : [Window],
    'history' : [str],
    'innerHeight' : int,
    'innerWidth' : int,
    'length' : int,
    'location' : Location,
    'name' : str,
    # 'preference' : # denied in gecko
    'opener' : Window,
    'outerHeight' : int,
    'outerWidth' : int,
    'pageXOffset' : int,
    'pageYOffset' : int,
    'parent' : Window,
    # 'personalbar' :  - disallowed
    # 'screen' : Screen() - not part of the standard, allow it if you want
    'screenX' : int,
    'screenY' : int,
    'scrollMaxX' : int,
    'scrollMaxY' : int,
    'scrollX' : int,
    'scrollY' : int,
    'self' : Window,
    'status' : str,
    'top' : Window,
    'window' : Window,
    'navigator': Navigator,
})

Window._methods = Node._methods.copy()
Window._methods.update({
    'alert' : MethodDesc([str]),
    'atob' : MethodDesc([str], str),
    'back' : MethodDesc([]),
    'blur' : MethodDesc([]),
    'btoa' : MethodDesc([str], str),
    'close' : MethodDesc([]),
    'confirm' : MethodDesc([str], bool),
    'dump' : MethodDesc([str]),
    'escape' : MethodDesc([str], str),
    #'find' : MethodDesc(["aa"],  - gecko only
    'focus' : MethodDesc([]),
    'forward' : MethodDesc([]),
    'getComputedStyle' : MethodDesc([Element, str], Style),
    'home' : MethodDesc([]),
    'open' : MethodDesc([str]),
})

Style._fields = {
    'azimuth' : str,
    'background' : str,
    'backgroundAttachment' : str,
    'backgroundColor' : str,
    'backgroundImage' : str,
    'backgroundPosition' : str,
    'backgroundRepeat' : str,
    'border' : str,
    'borderBottom' : str,
    'borderBottomColor' : str,
    'borderBottomStyle' : str,
    'borderBottomWidth' : str,
    'borderCollapse' : str,
    'borderColor' : str,
    'borderLeft' : str,
    'borderLeftColor' : str,
    'borderLeftStyle' : str,
    'borderLeftWidth' : str,
    'borderRight' : str,
    'borderRightColor' : str,
    'borderRightStyle' : str,
    'borderRightWidth' : str,
    'borderSpacing' : str,
    'borderStyle' : str,
    'borderTop' : str,
    'borderTopColor' : str,
    'borderTopStyle' : str,
    'borderTopWidth' : str,
    'borderWidth' : str,
    'bottom' : str,
    'captionSide' : str,
    'clear' : str,
    'clip' : str,
    'color' : str,
    'content' : str,
    'counterIncrement' : str,
    'counterReset' : str,
    'cssFloat' : str,
    'cssText' : str,
    'cue' : str,
    'cueAfter' : str,
    'onBefore' : str,
    'cursor' : str,
    'direction' : str,
    'displays' : str,
    'elevation' : str,
    'emptyCells' : str,
    'font' : str,
    'fontFamily' : str,
    'fontSize' : str,
    'fontSizeAdjust' : str,
    'fontStretch' : str,
    'fontStyle' : str,
    'fontVariant' : str,
    'fontWeight' : str,
    'height' : str,
    'left' : str,
    'length' : str,
    'letterSpacing' : str,
    'lineHeight' : str,
    'listStyle' : str,
    'listStyleImage' : str,
    'listStylePosition' : str,
    'listStyleType' : str,
    'margin' : str,
    'marginBottom' : str,
    'marginLeft' : str,
    'marginRight' : str,
    'marginTop' : str,
    'markerOffset' : str,
    'marks' : str,
    'maxHeight' : str,
    'maxWidth' : str,
    'minHeight' : str,
    'minWidth' : str,
    'MozBinding' : str,
    'MozOpacity' : str,
    'orphans' : str,
    'outline' : str,
    'outlineColor' : str,
    'outlineStyle' : str,
    'outlineWidth' : str,
    'overflow' : str,
    'padding' : str,
    'paddingBottom' : str,
    'paddingLeft' : str,
    'paddingRight' : str,
    'paddingTop' : str,
    'page' : str,
    'pageBreakAfter' : str,
    'pageBreakBefore' : str,
    'pageBreakInside' : str,
    'parentRule' : str,
    'pause' : str,
    'pauseAfter' : str,
    'pauseBefore' : str,
    'pitch' : str,
    'pitchRange' : str,
    'playDuring' : str,
    'position' : str,
    'quotes' : str,
    'richness' : str,
    'right' : str,
    'size' : str,
    'speak' : str,
    'speakHeader' : str,
    'speakNumeral' : str,
    'speakPunctuation' : str,
    'speechRate' : str,
    'stress' : str,
    'tableLayout' : str,
    'textAlign' : str,
    'textDecoration' : str,
    'textIndent' : str,
    'textShadow' : str,
    'textTransform' : str,
    'top' : str,
    'unicodeBidi' : str,
    'verticalAlign' : str,
    'visibility' : str,
    'voiceFamily' : str,
    'volume' : str,
    'whiteSpace' : str,
    'widows' : str,
    'width' : str,
    'wordSpacing' : str,
    'zIndex' : str,
}

Event._fields = {
    'bubbles': bool,
    'cancelBubble': bool,
    'cancelable': bool,
    'currentTarget': Element,
    'detail': int,
    'relatedTarget': Element,
    'target': Element,
    'type': str,
    'returnValue': bool,
    'which': int,
    'keyCode' : int,
    'charCode': int,
    'altKey'  : bool,
    'ctrlKey' : bool,
    'shiftKey': bool,
}

Event._methods = {
    'initEvent': MethodDesc([str, bool, bool]),
    'preventDefault': MethodDesc([]),
    'stopPropagation': MethodDesc([]),
}

KeyEvent._methods = Event._methods.copy()

KeyEvent._fields = Event._fields.copy()

Navigator._methods = {
}
Navigator._fields = {
    'appName': str,
}

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

def alert(msg):
    window.alert(msg)

# initialization

# set the global 'window' instance to an empty HTML document, override using
# dom.window = Window(html) (this will also set dom.document)

