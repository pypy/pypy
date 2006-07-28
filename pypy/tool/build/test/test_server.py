import path
from pypy.tool.build import server
import py
from fake import FakeChannel, FakeClient
from pypy.tool.build.server import RequestStorage
from pypy.tool.build.server import BuildPath
import time

def setup_module(mod):
    mod.temppath = temppath = py.test.ensuretemp('pypybuilder-server')
    mod.svr = server.PPBServer('pypytest', FakeChannel(), str(temppath))
    
    mod.c1 = FakeClient({'foo': 1, 'bar': [1,2]})
    mod.svr.register(mod.c1)

    mod.c2 = FakeClient({'foo': 2, 'bar': [2,3]})
    mod.svr.register(mod.c2)

def test_server_issubdict():
    from pypy.tool.build.server import issubdict
    assert issubdict({'foo': 1, 'bar': 2}, {'foo': 1, 'bar': 2, 'baz': 3})
    assert not issubdict({'foo': 1, 'bar': 2}, {'foo': 1, 'baz': 3})
    assert not issubdict({'foo': 1, 'bar': 3}, {'foo': 1, 'bar': 2, 'baz': 3})
    assert issubdict({'foo': [1,2]}, {'foo': [1,2,3]})
    assert not issubdict({'foo': [1,2,3]}, {'foo': [1,2]})
    assert issubdict({'foo': 1L}, {'foo': 1})
    assert issubdict({}, {'foo': 1})
    assert issubdict({'foo': [1,2]}, {'foo': [1,2,3,4], 'bar': [1,2]})

# XXX: note that the order of the tests matters! the first test reads the
# information from the channels that was set by the setup_module() function,
# the rest assumes this information is already read...
    
def test_register():
    assert len(svr._clients) == 2
    assert svr._clients[0] == c1
    assert svr._clients[1] == c2

    assert c1.channel.receive() == 'welcome'
    assert c2.channel.receive() == 'welcome'
    py.test.raises(IndexError, "c1.channel.receive()")

    assert svr._channel.receive().find('registered') > -1
    assert svr._channel.receive().find('registered') > -1
    py.test.raises(IndexError, 'svr._channel.receive()')

def test_compile():
    # XXX this relies on the output not changing... quite scary
    info = {'foo': 1}
    ret = svr.compile('test@domain.com', (info, None))
    assert not ret[0]
    assert ret[1].find('found a suitable client') > -1
    assert svr._channel.receive().find('going to send compile job') > -1
    assert c1.channel.receive() == 'foo: 1'
    assert c1.channel.receive() is None
    py.test.raises(IndexError, "c2.channel.receive()")

    svr.compile('test@domain.com', ({'foo': 3}, None))
    assert svr._channel.receive().find('no suitable client available') > -1

    info = {'bar': [3]}
    ret = svr.compile('test@domain.com', (info, None))
    assert svr._channel.receive().find('going to send') > -1
    assert c2.channel.receive() == 'bar: [3]'
    assert c2.channel.receive() is None
    py.test.raises(IndexError, "c1.channel.receive()")

    info = {'foo': 1}
    ret = svr.compile('test@domain.com', (info, None))
    assert not ret[0]
    assert ret[1].find('this build is already') > -1
    assert svr._channel.receive().find('currently in progress') > -1

    c1.busy_on = None
    bp = BuildPath(str(temppath / 'foo'))
    svr.compilation_done((info, None), bp)
    ret = svr.compile('test@domain.com', (info, None))
    assert ret[0]
    assert isinstance(ret[1], BuildPath)
    assert ret[1] == bp
    assert svr._channel.receive().find('compilation done for') > -1
    for i in range(2):
        assert svr._channel.receive().find('going to send email to') > -1
    assert svr._channel.receive().find('already a build for this info') > -1
    
def test_buildpath():
    tempdir = py.test.ensuretemp('pypybuilder-buildpath')
    # grmbl... local.__new__ checks for class equality :(
    bp = BuildPath(str(tempdir / 'test1')) 
    assert not bp.check()
    assert bp.info == ({}, {})

    bp.info = ({'foo': 1, 'bar': [1,2]}, {'baz': 1})
    assert bp.info == ({'foo': 1, 'bar': [1,2]}, {'baz': 1})
    assert (sorted((bp / 'system_info.txt').readlines()) == 
            ['bar: [1, 2]\n', 'foo: 1\n'])

    assert isinstance(bp.zipfile, py.path.local)
    bp.zipfile = ['foo', 'bar', 'baz']
    assert bp.zipfile.read() == 'foobarbaz'

def test__create_filename():
    svr._i = 0 # reset counter
    today = time.strftime('%Y%m%d')
    name1 = svr._create_filename()
    assert name1 == 'pypytest-%s-0' % (today,)
    assert svr._create_filename() == ('pypytest-%s-1' % (today,))
    bp = BuildPath(str(temppath / ('pypytest-%s-2' % (today,))))
    try:
        bp.ensure()
        assert svr._create_filename() == 'pypytest-%s-3'% (today,)
    finally:
        bp.remove()
    
def test_get_new_buildpath():
    svr._i = 0
    today = time.strftime('%Y%m%d')

    path1 = svr.get_new_buildpath(({'foo': 'bar'}, {'baz': 'qux'}))
    try:
        assert isinstance(path1, BuildPath)
        assert path1.info == ({'foo': 'bar'}, {'baz': 'qux'})
        assert path1.basename == 'pypytest-%s-0' % (today,)

        try:
            path2 = svr.get_new_buildpath(({'foo': 'baz'}, {'bar': 'qux'}))
            assert path2.info == ({'foo': 'baz'}, {'bar': 'qux'})
            assert path2.basename == 'pypytest-%s-1' % (today,)
        finally:
            path2.remove()
    finally:
        path1.remove()
