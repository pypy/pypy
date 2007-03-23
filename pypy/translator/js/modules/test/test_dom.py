
# -*- encoding: utf-8 -*-
import py
from pypy.translator.js.modules import dom
from pypy.translator.js.main import rpython2javascript
from xml.dom.minidom import parseString
import sys

TRANSLATING = False
USE_PDB = False
# XXX: How to get it from config.option???

class handler:
    called = False
    event = dom.Event()
    def __call__(self, e):
        self.called = True
        self.event = e
        e.stopPropagation()

def get_window():
    if TRANSLATING:
        return dom.window
    else:
        return dom.Window()

def test_quote_html():
    assert dom._quote_html('foo&bar') == 'foo&amp;bar'
    assert dom._quote_html('foo"&bar') == 'foo&quot;&amp;bar'

def test_serialize_html():
    def roundtrip(html):
        return dom._serialize_html(parseString(html).documentElement)
    html = '<div class="bar">content</div>'
    assert roundtrip(html) == html
    html = '<iframe src="foo?bar&amp;baz"></iframe>'
    assert roundtrip(html) == html
    html = '<meta name="foo"></meta>'
    assert roundtrip(html) == '<meta name="foo" />'
    html = '<div>\n  <div>foo</div>\n</div>'
    assert roundtrip(html) == html
    html = '<div>foo&amp;bar</div>'
    assert roundtrip(html) == html

def code_init():
    window = get_window()
    nodeType = window.document.nodeType
    docel = window.document.documentElement.nodeName
    children = len(window.document.documentElement.childNodes)
    
    return nodeType, docel, children

def test_init():
    nodeType, docel, children = code_init()
    assert nodeType == 9
    assert docel == 'HTML'
    assert children == 2

def test_init_failing():
    py.test.raises(py.std.xml.parsers.expat.ExpatError,
                   'dom.Window(html="<html><body></html>")')

def code_wrap():
    window = get_window()
    document = window.document
    div = document.createElement('div')
    document.documentElement.appendChild(div)
    return document, div

def test_wrap():
    document, div = code_wrap()
    assert isinstance(div, dom.Element) # wrapped node
    assert div.nodeType == 1
    assert document.documentElement.childNodes[-1]._original is div._original

def code_nodeValue():
    window = get_window()
    document = window.document
    td = document.createElement('td')
    td.appendChild(document.createTextNode('foo'))
    td.childNodes[0].nodeValue = 'bar'
    return td.childNodes[0].nodeValue

def test_nodeValue():
    nodevalue = code_nodeValue()
    assert nodevalue == 'bar'

def code_node_eq():
    window = get_window()
    body = window.document.getElementsByTagName('body')[0]
    firstref = body.parentNode.lastChild
    secondref = window.document.createElement('body')
    return body, firstref, secondref

def test_node_eq():
    body, ref1, ref2 = code_node_eq()
    assert ref1 == body
    assert ref2 != body

def code_get_element_by_id():
    window = get_window()
    document = window.document
    div = document.createElement('div')
    div.id = 'foo'
    window.document.getElementsByTagName('body')[0].appendChild(div)
    div = window.document.getElementById('foo')
    return div

def test_get_element_by_id():
    div = code_get_element_by_id()
    assert div.nodeName == 'DIV'

def code_element_style():
    window = get_window()
    document = window.document
    div = document.createElement('div')
    div.style.backgroundColor = 'green'
    return div

def test_element_style():
    div = code_element_style()
    assert div.style
    assert not div.style.color
    assert div.style.backgroundColor == 'green'
    py.test.raises(AttributeError, 'div.style.nonExistent')

def code_get_elements_by_tag_name():
    window = get_window()
    document = window.document
    div1 = document.createElement('div')
    div1.appendChild(document.createTextNode('foo'))
    div2 = document.createElement('div')
    div2.appendChild(document.createTextNode('bar'))
    body = document.getElementsByTagName('body')[0]
    body.appendChild(div1)
    body.appendChild(div2)
    return document

def test_get_elements_by_tag_name():
    document = code_get_elements_by_tag_name()
    divs = document.getElementsByTagName('div')
    assert len(divs) == 2
    divs = document.getElementsByTagName('DIV')
    assert len(divs) == 2

def test_window_references():
    window = dom.Window()
    assert window is window.window
    assert window is window.self
    assert window is window.parent
    assert window is window.top

    window2 = dom.Window(parent=window)
    assert window2.parent is window
    assert window2.top is window

    window3 = dom.Window(parent=window2)
    assert window3.parent is window2
    assert window3.top is window

def code_read_innerHTML():
    window = get_window()
    document = window.document
    h1 = document.createElement('h1')
    h1.appendChild(document.createTextNode('some document'))
    p = document.createElement('p')
    p.id = 'content'
    p.appendChild(document.createTextNode('some content'))
    body = document.getElementsByTagName('body')[0]
    body.appendChild(h1)
    body.appendChild(p)
    return document.documentElement.innerHTML

def test_read_innerHTML():
    html = code_read_innerHTML()
    assert html == ('<head><title>Untitled document</title></head>'
                    '<body><h1>some document</h1>'
                    '<p id="content">some content</p></body>')

def code_read_innerHTML_singletons():
    window = get_window()
    document = window.document
    head = document.getElementsByTagName('head')[0]
    meta = document.createElement('meta')
    meta.setAttribute('name', 'foo')
    meta.setAttribute('content', 'bar')
    head.appendChild(meta)
    headhtml = window.document.getElementsByTagName('head')[0].innerHTML
    return headhtml

def test_read_innerHTML_singletons():
    headhtml = code_read_innerHTML_singletons()
    assert py.std.re.search('<meta [^>]*\/>', headhtml)

def code_set_innerHTML():
    window = get_window()
    body = window.document.getElementsByTagName('body')[0]
    body.innerHTML = '<div>some content</div>'
    return body

def test_set_innerHTML():
    body = code_set_innerHTML()
    assert body.innerHTML == '<div>some content</div>'
    assert body.childNodes[0].nodeName == 'DIV'
    div = body.childNodes[0]
    html = div.innerHTML
    assert html == 'some content'

def code_set_innerHTML_empty():
    window = get_window()
    body = window.document.getElementsByTagName('body')[0]
    body.innerHTML = ''
    body.appendChild(window.document.createTextNode('foobar'))
    return body

def test_set_innerHTML_empty():
    body = code_set_innerHTML_empty()
    html = body.innerHTML
    assert html == 'foobar'

def code_event_init_1():
    window = get_window()
    e = window.document.createEvent()
    e.initEvent('click', True, True)
    return window, e

def code_event_init_2():
    window, event = code_event_init_1()
    body = window.document.getElementsByTagName('body')[0]
    body.dispatchEvent(event)
    return body, event

def test_event_init():
    window, e = code_event_init_1()
    assert e.cancelable == True
    assert e.target == None
    body, e = code_event_init_2()
    assert e.target is body

def code_event_handling():
    h = handler()
    window = get_window()
    body = window.document.getElementsByTagName('body')[0]
    body.addEventListener('click', h, False)
    e = window.document.createEvent()
    e.initEvent('click', True, True)
    body.dispatchEvent(e)
    return h

def test_event_handling():
    h = code_event_handling()
    assert h.called == True

def code_event_bubbling_1():
    h = handler()
    window = get_window()
    body = window.document.getElementsByTagName('body')[0]
    div = window.document.createElement('div')
    body.appendChild(div)
    body.addEventListener('click', h, False)
    e = window.document.createEvent()
    e.initEvent('click', False, True)
    div.dispatchEvent(e)
    return div, h

def code_event_bubbling_2():
    div, h = code_event_bubbling_1()
    e = div.ownerDocument.createEvent()
    e.initEvent('click', True, True)
    div.dispatchEvent(e)
    return h

def test_event_bubbling():
    div, h = code_event_bubbling_1()
    assert not h.called
    h = code_event_bubbling_2()
    assert h.called == True

def code_remove_event_listener():
    window = get_window()
    body = window.document.getElementsByTagName('body')[0]
    div = window.document.createElement('div')
    body.appendChild(div)
    h = handler()
    body.addEventListener('click', h, False)
    e = window.document.createEvent()
    e.initEvent('click', True, True)
    body.dispatchEvent(e)
    return body, h

def code_remove_event_listener_2():
    body, h = code_remove_event_listener()
    h.called = False
    body.removeEventListener('click', h, False)
    e = body.ownerDocument.createEvent()
    e.initEvent('click', True, True)
    body.dispatchEvent(e)
    return h

def test_remove_event_listener():
    body, h = code_remove_event_listener()
    assert h.called == True
    h = code_remove_event_listener_2()
    assert h.called == False

def code_event_vars():
    window = get_window()
    body = window.document.getElementsByTagName('body')[0]
    div = window.document.createElement('div')
    body.appendChild(div)
    h = handler()
    body.addEventListener('click', h, False)
    e = window.document.createEvent()
    e.initEvent('click', True, True)
    div.dispatchEvent(e)
    return body, div, h

def test_event_vars():
    body, div, h = code_event_vars()
    assert h.event.target == div
    assert h.event.originalTarget == div
    assert h.event.currentTarget == body

def code_class_name():
    window = get_window()
    document = window.document
    body = document.getElementsByTagName('body')[0]
    div = document.createElement('div')
    div.appendChild(document.createTextNode('foo'))
    div.setAttribute('class', 'foo')
    body.appendChild(div)
    div = window.document.getElementsByTagName('div')[0]
    return body, div

def test_class_name():
    body, div = code_class_name()
    assert div.className == 'foo'
    assert not body.className
    div.className = 'bar'
    assert div.className == 'bar'
    assert body.innerHTML == '<div class="bar">foo</div>'

def code_read_styles():
    window = get_window()
    body = window.document.getElementsByTagName('body')[0]
    body.innerHTML = ('<div style="color: red; background-color: green">foo'
                      '</div>')
    return body.childNodes[0].style

def test_read_styles():
    style = code_read_styles()
    assert style.color == 'red'
    bgcolor = style.backgroundColor
    assert bgcolor == 'green'

def code_write_styles():
    window = get_window()
    body = window.document.getElementsByTagName('body')[0]
    body.style.color = 'green'
    body.style.backgroundColor = 'red'
    return body

def test_write_styles():
    body = code_write_styles()
    assert dom._serialize_html(body) == ('<body style="background-color: red; '
                                         'color: green;"></body>')

def test_document_location():
    py.test.skip("To be written")

def test_build():
    py.test.skip('Børken')
    global TRANSLATING
    TRANSLATING = True
    for var in globals():
        if var.startswith('code_'):
            # just build it
            #def f():
            assert rpython2javascript(sys.modules[__name__], [var], use_pdb=False)
    
    TRANSLATING = False

def test_navigator():
    window = get_window()
    assert window.navigator.appName == 'Netscape'
