import path
from pypy.tool.build import server
import py
from fake import FakeChannel, FakeClient
from pypy.tool.build import build
import time
from repo import create_temp_repo

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

    py.test.raises(IndexError, "c1.channel.receive()")

    assert svr._channel.receive().find('registered') > -1
    assert svr._channel.receive().find('registered') > -1
    py.test.raises(IndexError, 'svr._channel.receive()')

def test_compile():
    repo = create_temp_repo('compile')
    repodir = repo.mkdir('foo')
    
    br = build.BuildRequest('foo@bar.com', {'foo': 1}, {},
                            str(repodir), 'HEAD', 0)
    ret = svr.compile(br)
    assert not ret[0]
    assert ret[1].find('found a suitable client') > -1
    ret = svr._channel.receive()
    assert ret.find('going to send compile job') > -1
    ret = c1.channel.receive()
    assert ret == br.serialize()
    none = c1.channel.receive()
    assert none is None
    py.test.raises(IndexError, "c2.channel.receive()")

    br2 = build.BuildRequest('foo@baz.com', {'foo': 3}, {},
                             str(repodir), 'HEAD', 0)
    svr.compile(br2)
    ret = svr._channel.receive()
    assert ret.find('no suitable client available') > -1

    br3 = build.BuildRequest('foo@qux.com', {'bar': [3]}, {},
                             str(repodir), 'HEAD', 0)
    svr.compile(br3)
    ret = svr._channel.receive()
    assert ret.find('going to send') > -1
    assert c2.channel.receive() == br3.serialize()
    assert c2.channel.receive() is None
    py.test.raises(IndexError, "c1.channel.receive()")

    br4 = build.BuildRequest('foo@spam.com', {'foo': 1}, {},
                             str(repodir), 'HEAD', 0)
    ret = svr.compile(br4)
    assert not ret[0]
    assert ret[1].find('this build is already') > -1
    assert svr._channel.receive().find('currently in progress') > -1

    c1.busy_on = None
    bp = build.BuildPath(str(temppath / 'foo'))
    print br
    bp.request = br
    svr.compilation_done(bp)
    clone = build.BuildRequest.fromstring(bp.request.serialize())
    clone.email = 'test@domain.com'
    ret = svr.compile(clone)
    assert ret[0]
    assert isinstance(ret[1], str)
    assert build.BuildPath(ret[1]) == bp
    ret = svr._channel.receive()
    assert ret.find('compilation done for') > -1
    for i in range(2):
        ret = svr._channel.receive()
        assert ret.find('going to send email to') > -1
    ret = svr._channel.receive()
    assert ret.find('already a build for this info') > -1

def test__create_filename():
    svr._i = 0 # reset counter
    today = time.strftime('%Y%m%d')
    name1 = svr._create_filename()
    assert name1 == 'pypytest-%s-0' % (today,)
    assert svr._create_filename() == ('pypytest-%s-1' % (today,))
    bp = build.BuildPath(str(temppath / ('pypytest-%s-2' % (today,))))
    try:
        bp.ensure()
        assert svr._create_filename() == 'pypytest-%s-3'% (today,)
    finally:
        bp.remove()

def test_get_new_buildpath():
    repo = create_temp_repo('get_new_buildpath')
    repodir = repo.mkdir('foo')
    
    svr._i = 0
    today = time.strftime('%Y%m%d')
    br = build.BuildRequest('foo@bar.com', {'foo': 'bar'}, {'baz': 'qux'},
                            str(repodir), 'HEAD', 0)

    bp1 = svr.get_new_buildpath(br)
    bp1.log = ['foo']
    try:
        assert isinstance(bp1, build.BuildPath)
        assert bp1.basename == 'pypytest-%s-0' % (today,)

        try:
            bp2 = svr.get_new_buildpath(br)
            bp2.log = ['bar']
            assert bp2.basename == 'pypytest-%s-1' % (today,)
        finally:
            bp2.remove()
    finally:
        bp1.remove()

def test_cleanup_old_builds():
    temppath = py.test.ensuretemp('cleanup_old_builds')
    bp1 = build.BuildPath(temppath.join('bp1'))
    bp1.ensure(dir=True)
    bp2 = build.BuildPath(temppath.join('bp2'))
    bp2.ensure(dir=True)
    bp2.log = 'log'
    svr = server.PPBServer('test', FakeChannel(), str(temppath))
    assert not bp1.check()
    assert bp2.check()

