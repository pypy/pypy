import py
import path
import sys
from StringIO import StringIO
import time
from zipfile import ZipFile

from pypy.tool.build import buildserver
from pypy.tool.build import build
from pypy.tool.build.test.fake import FakeChannel, FakeMetaServer

class BuildServerForTests(buildserver.BuildServer):
    def __init__(self, *args, **kwargs):
        super(BuildServerForTests, self).__init__(*args, **kwargs)
        self._done = []

class BuildRequestForTests(build.BuildRequest):
    normalized_rev = 1

def setup_module(mod):
    mod.temp = temp = py.test.ensuretemp('pypybuilder-buildserver')
    mod.svr = svr = FakeMetaServer(temp)

    import pypy.tool.build
    pypy.tool.build.metaserver_instance = svr

    mod.c1c = c1c = FakeChannel()
    mod.c1 = c1 = BuildServerForTests(c1c, {'foo': 1, 'bar': [1,2]}, "noname")
    svr.register(c1)

    mod.c2c = c2c = FakeChannel()
    mod.c2 = c2 = BuildServerForTests(c2c, {'foo': 2, 'bar': [2,3]}, "noname")
    svr.register(c2)

def test_compile():
    nfo = ({'foo': 1}, {'bar': 2})
    br = BuildRequestForTests('foo@bar.com', {'foo': 1}, {'bar': 1},
                              'file:///foo', 'HEAD', 0)
    c1c.send(True) # notifying we 'accept' the compile
    accepted = c1.compile(br)
    assert accepted
    ret = c1.channel.receive()
    assert build.BuildRequest.fromstring(ret).id() == br.id() # this was still in the buffer
    assert c1.busy_on.id() == br.id()
    c1.channel.send('foo bar')
    c1.channel.send(None)
    c1.channel.send('log')

    # meanwhile the build server starts a thread that waits until there's data 
    # available on its own channel, with our FakeChannel it has data rightaway,
    # though (the channel out and in are the same, and we just sent 'ret'
    # over the out one)
    time.sleep(1)
    
    done = svr._done.pop()
    
    assert str(done) == str(temp / 'build-0')
    assert temp.join('build-0/log').read() == 'log'

def test_channelwrapper():
    class FakeChannel(object):
        i = 0
        def __init__(self):
            self.buffer = []
        def send(self, data):
            self.buffer.append(data)
        def receive(self):
            import time
            while len(self.buffer) < self.i:
                time.sleep(0.1)
            ret = self.buffer[self.i]
            self.i += 1
            return ret
    c = FakeChannel()
    cw = buildserver.ChannelWrapper(c)
    assert cw.tell() == 0
    cw.write('foo')
    cw.write('bar')
    assert cw.tell() == 6
    cw.write('baz')
    cw.close()
    assert c.buffer == ['foo', 'bar', 'baz', None]

def test_failed_checker():
    br = build.BuildRequest('foo@bar.com', {'foo': 1}, {'bar': 2},
                            'file:///foo', 'HEAD', 0)
    br._nr = 1
    c1c.send(False) # notifying we _don't_ 'accept' the compile
    accepted = c1.compile(br)
    assert not accepted
    assert br in c1.refused
    assert c1.busy_on == None

def test_zip_dir():
    tempdir = py.test.ensuretemp('zip_dir')
    tempdir.mkdir('foo')
    tempdir.join('foo/bar.txt').write('bar')
    tempdir.join('foo/bar.o').write('this should not be in the zip (.o file)')

    zip = StringIO()
    buildserver.zip_dir(tempdir, zip)

    zip.seek(0)
    zf = ZipFile(zip)
    data = zf.read('pypy-compiled/foo/bar.txt')
    assert data == 'bar'

    py.test.raises(KeyError, 'zf.read("pypy-compiled/foo/bar.o")')

def test_tempdir():
    parent = py.test.ensuretemp('tempdir')
    for i in range(10):
        t = buildserver.tempdir(parent)
        assert t.basename == 'buildtemp-%s' % (i,)

