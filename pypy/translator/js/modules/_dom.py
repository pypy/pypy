
""" Document Object Model support
http://www.w3.org/DOM/ - main standart
http://www.w3schools.com/dhtml/dhtml_dom.asp - more informal stuff
"""

import time
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc

#from pypy.translator.stackless.test.test_transform import one

class Attribute(BasicExternal):
    pass

class Element(BasicExternal):
    pass

class Event(BasicExternal):
    pass

class KeyEvent(Event):
    _fields = {
        'keyCode' : 12,
        'charCode' : 12,
    }

class MouseEvent(Event):
    pass

class Node(Element):
    pass

class Document(Node):
    pass

class Window(Node):
    pass

class Form(Node):
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
        'nodeType' : "aa",
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
        'getElementsByTagName' : MethodDesc(["aa"], [Element()]),
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

def get_document():
    return Document()

def get_window():
    return Window()

get_window.suggested_primitive = True
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
