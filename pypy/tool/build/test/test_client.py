import path
from pypy.tool.build import client
from pypy.tool.build import build
import py
import time
import sys
from zipfile import ZipFile
from StringIO import StringIO
from fake import FakeChannel, FakeServer

class ClientForTests(client.PPBClient):
    def __init__(self, *args, **kwargs):
        super(ClientForTests, self).__init__(*args, **kwargs)
        self._done = []

class BuildRequestForTests(build.BuildRequest):
    normalized_rev = 1

def setup_module(mod):
    mod.temp = temp = py.test.ensuretemp('pypybuilder-client')
    mod.svr = svr = FakeServer(temp)

    import pypy.tool.build
    pypy.tool.build.ppbserver = svr

    mod.c1c = c1c = FakeChannel()
    mod.c1 = c1 = ClientForTests(c1c, {'foo': 1, 'bar': [1,2]})
    svr.register(c1)

    mod.c2c = c2c = FakeChannel()
    mod.c2 = c2 = ClientForTests(c2c, {'foo': 2, 'bar': [2,3]})
    svr.register(c2)

def test_compile():
    nfo = ({'foo': 1}, {'bar': 2})
    br = BuildRequestForTests('foo@bar.com', {'foo': 1}, {'bar': 1},
                              'file:///foo', 'HEAD', 0)
    c1c.send(True) # notifying we 'accept' the compile
    accepted = c1.compile(br)
    assert accepted
    ret = c1.channel.receive()
    assert ret == br.serialize() # this was still in the buffer
    assert c1.busy_on.serialize() == br.serialize()
    c1.channel.send('foo bar')
    c1.channel.send(None)
    c1.channel.send('log')

    # meanwhile the client starts a thread that waits until there's data 
    # available on its own channel, with our FakeChannel it has data rightaway,
    # though (the channel out and in are the same, and we just sent 'ret'
    # over the out one)
    time.sleep(1)
    
    done = svr._done.pop()
    
    assert str(done) == str(temp / 'build-0')
    assert temp.join('build-0/log').read() == 'log'

def test_channelwrapper():
    class FakeChannel(object):
        def __init__(self):
            self.buffer = []
        def send(self, data):
            self.buffer.append(data)
    c = FakeChannel()
    cw = client.ChannelWrapper(c)
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

    zip = StringIO()
    client.zip_dir(tempdir, zip)

    zip.seek(0)
    zf = ZipFile(zip)
    data = zf.read('foo/bar.txt')
    assert data == 'bar'

def test_tempdir():
    parent = py.test.ensuretemp('tempdir')
    for i in range(10):
        t = client.tempdir(parent)
        assert t.basename == 'buildtemp-%s' % (i,)

