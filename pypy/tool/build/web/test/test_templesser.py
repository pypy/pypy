import py
from pypy.tool.build.web.templesser import template

def test_template_conditionals():
    t = template('%(cond)[cfoo%(cond)]c')
    u = t.unicode({'cond': True})
    assert u == u'foo'
    u = t.unicode({'cond': False})
    assert u == u''

def test_template_block():
    t = template('%(block)[b%(foo)s%(block)]b')
    u = t.unicode({'block': [{'foo': 'spam'}, {'foo': 'eggs'}]})
    assert u == u'spam eggs'

def test_combined():
    t = template(u'%(block)[b%(cond)[cfoo%(cond)]c%(block)]b')
    u = t.unicode({'block': [{'cond': False}]})
    assert u == u''
    u = t.unicode({'block': [{'cond': True}]})
    assert u == u'foo'

def test_nested_resolve_conditionals():
    t = template(u'%(cond1)[cfoo%(cond2)[cbar%(cond2)]cbaz%(cond1)]c')
    u = t.unicode({'cond1': False, 'cond2': True})
    assert u == u''
    u = t.unicode({'cond1': True, 'cond2': False})
    assert u == u'foobaz'
    u = t.unicode({'cond1': True, 'cond2': True})
    assert u == u'foobarbaz'

def test_newlines_block():
    t = template(u'foo\n%(block)[b%(bar)s%(block)]b\nbaz')
    u = t.unicode({'block': [{'bar': '1'}, {'bar': '2'}]})
    assert u == u'foo\n1 2\nbaz'

def test_keyerror():
    t = template(u'%(cond)[c foo %(cond)]c')
    py.test.raises(KeyError, 't.unicode({})')

def test_escaping_conditional():
    t = template(u'%%(cond)[c foo %%(cond)]c')
    u = t.unicode({})
    assert u == u'%(cond)[c foo %(cond)]c'

def test_escaping_broken():
    t = template(u'%%(cond)[c foo %(cond)]c')
    py.test.raises(KeyError, 't.unicode({})')

def test_quick_functional():
    t = template(u"""\
<html>
  <head>
    <title>%(title)s</title>
  </head>
  <body>
    %(header)[c
      <h3>%(header)s</h3>
    %(header)]c
    %(items)[b
      %(name)[c<div>%(name)s</div>%(name)]c
      %(values)[b
        <div>%(value)s</div>
      %(values)]b
    %(items)]b
  </body>
</html>
""")
    u = t.unicode({'title': 'foo', 'header': False, 'items': []})
    u = u.replace(' ', '').replace('\n', '')
    assert u == u'<html><head><title>foo</title></head><body></body></html>'
