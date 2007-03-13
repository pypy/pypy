import py
from py.__.misc.cache import AgingCache
from py.__.path.svn import urlcommand
from pypy.tool.build import build
from pypy.tool.build.test.repo import create_temp_repo

def setup_module(mod):
    # remove nasty cache from py.path.svnurl to allow this to work...
    mod._oldcache = urlcommand.SvnCommandPath._lsnorevcache
    urlcommand.SvnCommandPath._lsnorevcache = AgingCache(maxentries=1,
                                                         maxseconds=0)

def teardown_module(mod):
    urlcommand.SvnCommandPath._lsnorevcache = mod._oldcache

def test_normalize_revision():
    if py.std.sys.platform.startswith('win'):
        py.test.skip('win32 escaping problems with file:// urls')
    repo = create_temp_repo('normalize')
    repo.ensure('foo', dir=True)
    foourl = str(repo.join('foo'))
    wc = py.path.svnwc(py.test.ensuretemp('build-svnwc').join('wc-foo'))
    wc.checkout(foourl)
    ret = build.normalize_revision(foourl, 'HEAD')
    assert ret == 1
    
    f1 = wc.ensure('file1', file=True, versioned=True)
    f1.write('foo')
    print wc.status().added
    wc.commit('test something')
    wc.update()
    assert int(wc.status().rev) == 2
    ret = build.normalize_revision(foourl, 'HEAD')
    assert ret == 2

    f2 = wc.ensure('file2', file=True, versioned=True)
    f2.write('foo')
    wc.commit('test something')
    wc.update()
    ret = build.normalize_revision(foourl, 'HEAD')
    assert ret == 3

    ret = build.normalize_revision(foourl, 1234)
    assert ret == 3

def test_buildpath():
    tempdir = py.test.ensuretemp('pypybuilder-buildpath')
    bp = build.BuildPath(str(tempdir / 'test'))
    assert not bp.check()
    bp.log = 'foo'
    assert bp.check()

def test_buildpath_request():
    tempdir = py.test.ensuretemp('pypybuilder-buildpath')
    temprepo = create_temp_repo('request')
    repodir = temprepo.mkdir('foo')
    print str(tempdir)
    bp = build.BuildPath(str(tempdir / 'test_request'))
    assert bp.request is None
    br = build.BuildRequest('foo@bar.com', {'foo': 1}, {'bar': 1},
                            str(repodir), 'HEAD', 0)
    bp.request = br
    assert bp.join('request').check()
    assert bp.request.serialize() == br.serialize()

def test_buildpath_zip():
    tempdir = py.test.ensuretemp('pypybuilder-buildpath')
    bp = build.BuildPath(str(tempdir / 'test_zip'))
    assert isinstance(bp.zipfile, py.path.local)
    bp.zipfile = ['foo', 'bar', 'baz']
    assert bp.zipfile.read() == 'foobarbaz'

def test_buildpath_log_and_done():
    tempdir = py.test.ensuretemp('pypybuilder-buildpath')
    bp = build.BuildPath(str(tempdir / 'test_log'))
    log = bp.log
    assert not log
    assert not bp.done
    bp.log = 'log data'
    assert bp.log == 'log data'
    assert bp.done

def test_buildrequest_serialize():
    br = build.BuildRequest('foo@bar.com', {'foo': 'bar'}, {'spam': 'eggs'},
                            'file:///foo/bar', 'HEAD', 0)
    br._nr = 1
    ser = br.serialize()
    assert ser == """\
email: foo@bar.com
sysinfo: {'foo': 'bar'}
compileinfo: {'spam': 'eggs'}
svnurl: file:///foo/bar
svnrev: HEAD
revrange: 0
normalized_rev: 1
request_time: %s
build_start_time: None
build_end_time: None
""" % (br.request_time,)
    assert build.BuildRequest.fromstring(ser).serialize() == ser

    py.test.raises(SyntaxError, 'build.BuildRequest.fromstring("foo")')
    py.test.raises(KeyError, 'build.BuildRequest.fromstring("foo: bar")')

def test_buildrequest_has_satisfying_data():
    if py.std.sys.platform.startswith('win'):
        py.test.skip('win32 escaping problems with file:// urls')

    # note that this implicitly tests rev_in_range() too...

    repo = create_temp_repo('satisfying')
    testproj = repo.ensure('testproj', dir=True)

    testurl = str(testproj)
    
    wc = py.path.svnwc(py.test.ensuretemp('satisfying-svnwc'))
    wc.checkout(testurl)

    br1 = build.BuildRequest('foo@bar.com', {'foo': 'bar'}, {'spam': 'eggs'},
                             testurl, 'HEAD', 0)
    
    br2 = build.BuildRequest('foo@baz.com', {'foo': 'bar'}, {'spam': 'eggs'},
                             testurl, 'HEAD', 0)
    assert br2.has_satisfying_data(br1)

    br3 = build.BuildRequest('foo@baz.com', {'foo': 'bar'}, {'spam': 'eggs'},
                             testurl, 1, 0)
    assert br3.has_satisfying_data(br1)

    # this actually succeeds: because there's no revision 2 yet,
    # normalize_revision will return the highest rev (1), which matches
    br4 = build.BuildRequest('foo@baz.com', {'foo': 'bar'}, {'spam': 'eggs'},
                             testurl, 2, 0)
    assert br4.has_satisfying_data(br1)

    foo = wc.ensure('foo', file=True)
    foo.add()
    wc.commit('commit message')

    # now it should fail...
    br5 = build.BuildRequest('foo@baz.com', {'foo': 'bar'}, {'spam': 'eggs'},
                             testurl, 2, 0)
    assert not br5.has_satisfying_data(br1)

    br6 = build.BuildRequest('foo@baz.com', {'foo': 'bar'}, {'spam': 'eggs'},
                             testurl, 2, 1)
    assert br6.has_satisfying_data(br1)

    br7 = build.BuildRequest('foo@baz.com', {'foo': 'baz'}, {'spam': 'eggs'},
                             testurl, 1, 0)
    assert not br7.has_satisfying_data(br1)

    br8 = build.BuildRequest('foo@baz.com', {'foo': 'bar'}, {'spam': 'eggs'},
                             testurl + '/baz', 1, 0)
    assert not br8.has_satisfying_data(br1)

def test_buildrequest_error():
    tempdir = py.test.ensuretemp('pypybuilder-buildpath')

    bp = build.BuildPath(str(tempdir / 'test_error'))
    assert bp.error is None
    bp.log = """
==============================================================================
Exception during compilation:
SyntaxError: foo
...
traceback here
...
==============================================================================
"""
    e = bp.error
    assert e.__class__ == SyntaxError
    assert str(e) == 'foo'

    bp.log = """
==============================================================================
Exception during compilation:
FooBarException: baz
...
traceback here
...
"""
    e = bp.error
    assert e.__class__ == Exception
    assert str(e) == 'FooBarException: baz'

