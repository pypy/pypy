#
# These are tests for the _sre module. Specifically, they test that it
# it *EXACTLY* conforms to the C implementation of _sre. This is not
# something we want to maintain in the future... it was useful only
# while developing the first version of _sre. Since _sre is considered
# a "private" module, we can modify its behavior as long as the re
# module continues to work the same, so we do not WANT to be running
# tests which ensure that every single non-documented interface of
# _sre works exactly as it does in the C version. Therefore, we should
# NOT be running these tests. In fact, they probably shouldn't even
# get checked in... except that it may be convenient someday to be
# able to look back in svn history and see the contents of this file.
# So just for the moment this file is getting checked in despite the
# fact that it's not a proper test file and we probably don't want
# it anyway... we can delete it soon.
#
# This does not test unicode behavior at all (and, in fact, the module
# doesn't support unicode properly).
#

import _sre

assert _sre.CODESIZE == 4
assert _sre.getcodesize() == 4
assert _sre.getlower(97,2) == 97

def assert_raises(err_type, f, *args, **kwargs):
    try:
        f(*args, **kwargs)
        assert False # Should have raised
    except IndexError:
        pass
    except:
        assert False # Should have raised a different type


# Simple pattern
pat = _sre.compile('a', 0, [16, 8, 3, 1, 1, 1, 1, 97, 0, 18, 97, 1])
assert pat.pattern == 'a'
assert pat.flags == 0
assert pat.groups == 0
assert pat.groupindex == {}
assert pat.match('xxx') is None

m = pat.match('ax')
assert m is not None
assert m
assert m.string == 'ax'
assert m.re is pat
assert m.pos == 0
assert m.endpos == 2
assert m.lastindex is None
assert m.lastgroup is None
assert m.regs == ((0,1),)
assert m.start() == 0
assert m.end() == 1
assert m.span() == (0,1)
assert m.expand('xx') == 'xx'
assert m.groupdict() == {}
assert m.group() == 'a'
assert m.group(0) == 'a'

assert_raises(IndexError, m.start, 1)
assert_raises(IndexError, m.end, 1)
assert_raises(IndexError, m.span, 1)
assert_raises(IndexError, m.group, 1)
assert_raises(IndexError, m.group, -1)

assert pat.search('xxx') is None
ma = pat.search('xxax')
assert ma
assert ma.pos == 0
assert ma.endpos == 4
assert ma.span() == (2,3)

assert pat.findall('__a__a_') == ['a','a']
assert pat.sub('qq', '_a__') == '_qq__'
assert pat.sub('qq', '_aa_a_', 2) == '_qqqq_a_'
assert pat.subn('qq', '_a__') == ('_qq__', 1)
assert pat.subn('qq', '_aa_a_', 2) == ('_qqqq_a_', 2)
assert pat.split('12a34a5') == ['12','34','5']

assert [(x.start(), x.group()) for x in pat.finditer('_a_a_')]  == [(1,'a'), (3,'a')]

def test_scanner_match():
  scan = pat.scanner('x')
  assert scan.match() is None
  scan = pat.scanner('a')
  assert scan.match().start() == 0
  assert scan.match() is None
  scan = pat.scanner('aaxa')
  assert scan.match().start() == 0
  assert scan.match().start() == 1
  assert scan.match() is None
test_scanner_match()

def test_scanner_search():
  scan = pat.scanner('x')
  assert scan.search() is None
  scan = pat.scanner('a')
  assert scan.search().start() == 0
  assert scan.search() is None
  scan = pat.scanner('aaxa')
  assert scan.search().start() == 0
  assert scan.search().start() == 1
  assert scan.search().start() == 3
  assert scan.search() is None
test_scanner_search()

# Pattern with groups
pat2 = _sre.compile('(a)(b)?', 0, 
        [16, 8, 1, 1, 2, 1, 0, 97, 0, 20, 0, 18, 97, 20, 1, 27, 9, 0, 1, 20, 2, 18, 98, 20, 3, 21, 1],
        2, {}, [None, None, None])
m2 = pat2.match('abc')
assert m2.lastindex == 2
assert m2.groups() == ('a', 'b')
assert m2.group(1,2,0) == ('a', 'b', 'ab')
assert_raises(IndexError, m2.start, 99)


m2b = pat2.match('axx')
assert m2b.groups() == ('a', None)
assert m2b.groups(43) == ('a', 43)

assert pat2.findall('_a__abb') == [('a', ''), ('a', 'b')]

# Pattern with named group
pat3 = _sre.compile('(?P<first>a)', 0,
        [16, 8, 1, 1, 1, 1, 0, 97, 0, 20, 0, 18, 97, 20, 1, 1],
        1, {'first': 1}, [None, 'first'])
assert pat3.groupindex == {'first': 1}
m3 = pat3.match('abc')
assert m3.start(0) == 0
assert m3.start(1) == 0
assert m3.start('first') == 0
assert m3.end('first') == 1
assert m3.span('first') == (0,1)
assert_raises(IndexError, m3.start, 2)
assert_raises(IndexError, m3.start, 'second')
assert m3.lastindex == 1
assert m3.lastgroup == 'first'
assert m3.group('first') == 'a'
assert m3.groupdict() == {'first': 'a'}

# Pattern with a named group that doesn't participate in the match
pat4 = _sre.compile('(?P<first>a)(?P<second>b)?', 0, [16, 8, 1, 1, 2, 1, 0, 97, 0, 20, 0, 18, 97, 20, 1, 27, 9, 0, 1, 20, 2, 18, 98, 20, 3, 21, 1], 2, {'second': 2, 'first': 1}, [None, 'first', 'second'])

assert pat4.match('ax').group('second') == None
assert pat4.match('ab').groupdict() == {'first': 'a', 'second': 'b'}
assert pat4.match('ax').groupdict() == {'first': 'a', 'second': None}
assert pat4.match('ax').groupdict(42) == {'first': 'a', 'second': 42}


print 'Tests OK'
