from pypy.translator.js.modules import dom

def test_init():
    window = dom.Window('<html><body>foo</body></html>')
    nodeType = window.document.nodeType
    assert nodeType == 9
    docel = window.document.documentElement.nodeName
    assert docel == 'HTML'
    # XXX gotta love the DOM API ;)
    assert window.document.getElementsByTagName('body')[0]\
            .childNodes[0].nodeValue == 'foo'

def test_wrap():
    window = dom.Window()
    document = window.document
    div = document.createElement('div')
    assert div.nodeType == 1
    document.documentElement.appendChild(div)
    assert document.documentElement.childNodes[-1] == div

def test_get_element_by_id():
    window = dom.Window('<html><body><div id="foo" /></body></html>')
    div = window.document.getElementById('foo')
    assert div.nodeName == 'DIV'

def test_html_api():
    window = dom.Window()
    document = window.document
    div = document.createElement('div')
    assert div.style
    assert not div.style.backgroundColor
