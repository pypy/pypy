import py
from pypy.translator.js.modules import dom
from pypy.translator.js.main import rpython2javascript
from xml.dom.minidom import parseString
import sys

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

def test_init():
    window = dom.Window('<html><body>foo</body></html>')
    nodeType = window.document.nodeType
    assert nodeType == 9
    docel = window.document.documentElement.nodeName
    assert docel == 'HTML'
    # XXX gotta love the DOM API ;)
    somediv = window.document.getElementsByTagName('body')[0].childNodes[0]
    assert somediv.nodeValue == 'foo'

    py.test.raises(py.std.xml.parsers.expat.ExpatError,
                   'dom.Window("<html><body></html>")')

def test_wrap():
    window = dom.Window()
    document = window.document
    div = document.createElement('div')
    assert isinstance(div, dom.Element) # wrapped node
    assert div.nodeType == 1
    document.documentElement.appendChild(div)
    assert document.documentElement.childNodes[-1]._original is div._original

def test_get_element_by_id():
    window = dom.Window('<html><body><div id="foo" /></body></html>')
    div = window.document.getElementById('foo')
    assert div.nodeName == 'DIV'

def test_element_style():
    window = dom.Window()
    document = window.document
    div = document.createElement('div')
    assert div.style
    assert not div.style.backgroundColor
    div.style.backgroundColor = 'green'
    assert div.style.backgroundColor == 'green'
    py.test.raises(AttributeError, 'div.style.nonExistent')

def test_get_elements_by_tag_name():
    window = dom.Window('<html><body><div>foo</div>'
                    '<div>bar</div></body></html>')
    document = window.document
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

def test_read_innerHTML():
    window = dom.Window('<html><body><h1>some document</h1>'
                        '<p id="content">some content</p></body></html>')
    document = window.document
    nodeName = window.document.documentElement.nodeName
    assert nodeName == 'HTML'
    html = window.document.documentElement.innerHTML
    assert html == ('<body><h1>some document</h1>'
                '<p id="content">some content</p></body>')

def test_read_innerHTML_singletons():
    window = dom.Window('<html><head><meta name="foo" content="bar">'
                        '</meta></head></html>')
    metahtml = window.document.getElementsByTagName('head')[0].innerHTML
    assert py.std.re.match('^<meta .* \/>$',
                           '<meta name="foo" content="bar" />')

def test_set_innerHTML():
    window = dom.Window('<html><body>initial content</body></html>')
    body = window.document.getElementsByTagName('body')[0]
    assert body.innerHTML == ''
    body.innerHTML = '<div>some content</div>'
    assert body.innerHTML == '<div>some content</div>'
    assert body.childNodes[0].nodeName == 'DIV'

def test_event_init():
    window = dom.Window()
    e = dom.Event()
    e.initEvent('click', True, True)
    assert e.cancelable == True
    assert e.target == None
    body = window.document.getElementsByTagName('body')[0]
    body.dispatchEvent(e)
    assert e.target is body

def test_event_handling():
    class handler:
        called = False
        def __call__(self, e):
            self.called = True
    h = handler()
    window = dom.Window()
    body = window.document.getElementsByTagName('body')[0]
    body.addEventListener('click', h, False)
    e = dom.Event()
    e.initEvent('click', True, True)
    body.dispatchEvent(e)
    assert h.called == True

def test_event_bubbling():
    class handler:
        called = False
        def __call__(self, e):
            self.called = True
    h = handler()
    window = dom.Window()
    body = window.document.getElementsByTagName('body')[0]
    div = window.document.createElement('div')
    body.appendChild(div)
    body.addEventListener('click', h, False)
    e = dom.Event()
    e.initEvent('click', False, True)
    div.dispatchEvent(e)
    assert h.called == False
    e = dom.Event()
    e.initEvent('click', True, True)
    div.dispatchEvent(e)
    assert h.called == True

def test_remove_event_listener():
    class handler:
        called = False
        def __call__(self, e):
            self.called = True
    window = dom.Window()
    body = window.document.getElementsByTagName('body')[0]
    div = window.document.createElement('div')
    body.appendChild(div)
    py.test.raises(Exception, 'body.removeEventListener("click", h, False)')
    h = handler()
    body.addEventListener('click', h, False)
    e = dom.Event()
    e.initEvent('click', True, True)
    body.dispatchEvent(e)
    assert h.called == True
    h.called = False
    body.removeEventListener('click', h, False)
    e = dom.Event()
    e.initEvent('click', True, True)
    body.dispatchEvent(e)
    assert h.called == False

def test_event_vars():
    class handler:
        event = None # XXX annotator problem?
        def __call__(self, e):
            self.event = e
            e.stopPropagation()
    window = dom.Window()
    body = window.document.getElementsByTagName('body')[0]
    div = window.document.createElement('div')
    body.appendChild(div)
    h = handler()
    body.addEventListener('click', h, False)
    e = dom.Event()
    e.initEvent('click', True, True)
    div.dispatchEvent(e)
    assert h.event.target == div
    assert h.event.originalTarget == div
    assert h.event.currentTarget == body

def test_build():
    py.test.skip("Not implemented yet")
    for var in globals():
        if var.startswith('test_') and var != 'test_build':
            # just build it
            rpython2javascript(sys.modules[__name__], [var])

