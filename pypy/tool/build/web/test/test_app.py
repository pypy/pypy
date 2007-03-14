import py
from py.__.test.web.webcheck import check_html
from pypy.tool.build.web.app import *
from pypy.tool.build.web.conftest import option
from pypy.tool.build.test import fake
from pypy.tool.build import config as build_config
from pypy.tool.build import build
from pypy.tool.build import metaserver

TESTPORT = build_config.testport

here = py.magic.autopath().dirpath()
pypyparent = here.dirpath().dirpath().dirpath().dirpath().dirpath()

def html_validate(html):
    if not option.webcheck:
        py.test.skip('Skipping XHTML validation (rest of the test passed)')
    check_html(html)

class FakeMetaServer(object):
    def __init__(self):
        self._status = {}
        self._builders = []
        self._queued = []
        self._waiting = []
        self._done = []

_metaserver_init = """
    import sys
    sys.path += %r

    from pypy.tool.build.web.test.test_app import FakeMetaServer
    from pypy.tool.build.build import BuildRequest
    from pypy.tool.build.test import fake
    from pypy.tool import build
    build.metaserver_instance = s = FakeMetaServer()
    channel.send(None)
    try:
        while 1:
            command = channel.receive()
            if command == 'quit':
                break
            command, data = command
            if command == 'add_queued':
                s._queued.append(BuildRequest.fromstring(data))
            elif command == 'add_builder':
                info, compile_info = data
                s._builders.append(fake.FakeBuildserver(info, compile_info))
            channel.send(None)
    finally:
        channel.close()
"""

def init_fake_metaserver(port, path):
    gw = py.execnet.PopenGateway()
    conference = execnetconference.conference(gw, port, True)
    channel = conference.remote_exec(_metaserver_init % (path,))
    channel.receive()
    return channel

def setup_module(mod):
    mod.path = path = pypyparent.strpath
    mod.server_channel = init_fake_metaserver(TESTPORT, path)
    mod.config = fake.Container(port=TESTPORT, path=path, server='localhost')
    mod.gateway = py.execnet.PopenGateway()

def teardown_module(mod):
    mod.server_channel.send('quit')
    mod.gateway.exit()

class TestIndexPage(object):
    def test_call(self):
        a = Application(config)
        headers, html = a.index(None, '/', '')
        assert headers['Content-Type'] == 'text/html; charset=UTF-8'
        assert html.strip().startswith('<!DOCTYPE html')
        assert html.strip().endswith('</html>')
        html_validate(html)

class TestMetaServerStatusPage(object):
    def test_get_status(self):
        p = MetaServerStatusPage(config, gateway)
        status = p.get_status()
        assert status == {'builders': 0,
                          'running': 0,
                          'done': 0,
                          'queued': 0,
                          'waiting': 0}
        br = BuildRequest('foo@bar.com', {'foo': 'bar'}, {}, 'file:///foo',
                          '1234', 1)
        br._nr = '1234'
        server_channel.send(('add_queued', br.serialize()))
        server_channel.receive()
        status = p.get_status()
        assert status == {'builders': 0,
                          'running': 0,
                          'done': 0,
                          'queued': 1,
                          'waiting': 0}

    def test_call(self):
        p = MetaServerStatusPage(config, gateway)
        headers, html = p(None, '/metaserverstatus', '')
        assert headers['Content-Type'] == 'text/html; charset=UTF-8'
        assert html.strip().startswith('<!DOCTYPE html')
        assert html.strip().endswith('</html>')
        html_validate(html)

class TestBuildersInfoPage(object):
    def test_get_builderinfo(self):
        p = BuildersInfoPage(config, gateway)
        assert p.get_buildersinfo() == []
        server_channel.send(('add_builder', [{'foo': 'bar'}, {}]))
        server_channel.receive()
        info = p.get_buildersinfo()
        assert info == [{'sysinfo': [{'foo': 'bar'}],
                         'hostname': 'fake',
                         'busy_on': [],
                         'not_busy': True}]

    def test_call(self):
        class TestPage(BuildersInfoPage):
            def get_buildersinfo(self):
                b = build.BuildRequest('foo@bar.com', {}, {'foo': 'bar'},
                                       'http://codespeak.net/svn/pypy/dist',
                                       10, 2, 123456789)
                binfo = b.todict()
                binfo.update({'href': 'file:///foo',
                              'log': 'everything went well',
                              'error': None,
                              'id': 'somebuild'})
                return [
                    {'hostname': 'host1',
                     'sysinfo': [{
                      'os': 'linux2',
                      'maxint': 9223372036854775807L,
                      'byteorder': 'little'}],
                     'busy_on': [],
                     'not_busy': True},
                    {'hostname': 'host2',
                     'sysinfo': [{
                      'os': 'zx81',
                      'maxint': 255,
                      'byteorder': 'little'}],
                     'busy_on': [binfo],
                     'not_busy': False},
                ]
        p = TestPage(config, gateway)
        headers, html = p(None, '/buildersinfo', '')
        assert headers['Content-Type'] == 'text/html; charset=UTF-8'
        assert html.strip().startswith('<!DOCTYPE html')
        assert html.strip().endswith('</html>')
        html_validate(html)

class TestBuildPage(object):
    def test_call(self):
        pass

class TestBuildsIndexPage(object):
    def test_get_builds(self):
        pass

    def test_call(self):
        p = BuildsIndexPage(config, gateway)
        headers, html = p(None, '/builds/', '')
        assert headers['Content-Type'] == 'text/html; charset=UTF-8'
        assert html.strip().startswith('<!DOCTYPE html')
        assert html.strip().endswith('</html>')
        html_validate(html)

class TestBuilds(object):
    def test_traverse(self):
        p = Builds(config, gateway)
        assert p.traverse(['index'], '/builds/index') is p.index
        assert p.traverse([''], '/builds/') is p.index
        assert isinstance(p.traverse(['foo'], '/builds/foo'), BuildPage)
        py.test.raises(HTTPError,
                       "p.traverse(['foo', 'bar'], '/builds/foo/bar')")

class TestMetaServerAccessor(object):
    def test_status(self):
        temppath = py.test.ensuretemp('TestMetaServerAccessor.test_status')
        config = fake.Container(projectname='test', buildpath=temppath)
        svr = metaserver.MetaServer(config, fake.FakeChannel())
        svr._done.append('y')
        svr._done.append('z')
        svr._queued.append('spam')
        svr._queued.append('spam')
        svr._queued.append('eggs')
        bs = fake.FakeBuildserver({})
        bs.busy_on = 'foo'
        svr._builders.append(bs)
        assert MetaServerAccessor(svr).status() == {
            'done': 2,
            'queued': 3,
            'waiting': 1,
            'running': 1,
            'builders': 1,
        }

    def test_buildersinfo(self):
        temppath = py.test.ensuretemp(
            'TestMetaServerAccessor.test_buildersinfo')
        config = fake.Container(projectname='test', buildpath=temppath)
        svr = metaserver.MetaServer(config, fake.FakeChannel())
        svr._builders.append(fake.FakeBuildserver({'foo': 'bar'}))
        svr._builders.append(fake.FakeBuildserver({'spam': 'eggs'}))
        bi = MetaServerAccessor(svr).buildersinfo()
        assert len(bi) == 2
        assert bi[0]['sysinfo'] == {'foo': 'bar'}
        assert bi[0]['busy_on'] == None
        assert bi[1]['sysinfo'] == {'spam': 'eggs'}
        req = build.BuildRequest('foo@bar.com', {}, {}, 'file:///tmp/repo',
                                 '10', '10')
        req._nr = '10' # normalized revision
        svr._builders[0].busy_on = req
        bi = MetaServerAccessor(svr).buildersinfo()
        assert bi[0]['busy_on']
        # for now, later more info should be made available
        assert bi[0]['busy_on'] == req.serialize()

    def test_buildrequests(self):
        temppath = py.test.ensuretemp(
            'TestMetaServerAccessor.test_buildersinfo')
        config = fake.Container(projectname='test', buildpath=temppath,
                                path_to_url=lambda p: 'file:///foo')
        svr = metaserver.MetaServer(config, fake.FakeChannel())
        s = MetaServerAccessor(svr)
        req = build.BuildRequest('foo@bar.com', {'foo': 'bar'}, {},
                                 'file:///tmp/repo', '10', '10')
        req._nr = '10'
        svr._queued.append(req)
        brs = s.buildrequests()
        assert len(brs) == 1
        assert brs[0][0] == {'status': 'waiting'}
        assert brs[0][1] == req.serialize()
        svr._queued = []
        assert len(s.buildrequests()) == 0
        req.build_start_time = py.std.time.time()
        req.build_end_time = py.std.time.time()
        svr._done.append(fake.Container(request=req, error=None))
        brs = s.buildrequests()
        assert len(brs) == 1
        assert brs[0][0] == {'status': 'done', 'error': 'None',
                             'buildurl': 'file:///foo'}
        assert brs[0][1] == req.serialize()

    def test_buildrequest(self):
        temppath = py.test.ensuretemp(
            'TestMetaServerAccessor.test_buildersinfo')
        config = fake.Container(projectname='test', buildpath=temppath)
        svr = metaserver.MetaServer(config, fake.FakeChannel())
        s = MetaServerAccessor(svr)
        req = build.BuildRequest('foo@bar.com', {'foo': 'bar'}, {},
                                 'file:///tmp/repo', '10', '10')
        req._nr = '10'
        svr._queued.append(req)
        br = s.buildrequest(req.id())
        assert br[0] == {'status': 'waiting'}
        assert br[1] == req.serialize()

    def test_buildurl(self):
        temppath = py.test.ensuretemp(
            'TestMetaServerAccessor.test_buildersinfo')
        config = fake.Container(projectname='test', buildpath=temppath,
                                path_to_url=lambda p: 'http://foo/bar')
        svr = metaserver.MetaServer(config, fake.FakeChannel())
        s = MetaServerAccessor(svr)
        req = build.BuildRequest('foo@bar.com', {'foo': 'bar'}, {},
                                 'file:///tmp/repo', '10', '10')
        req._nr = '10'
        svr._done.append(fake.Container(request=req))
        url = s.buildurl(req.id())
        assert url == 'http://foo/bar'

class TestServerPage(object):
    def test_call_method_simple(self):
        p = ServerPage(fake.Container(port=build_config.testport, path=str(path)),
                       py.execnet.PopenGateway())
        ret = p.call_method('status', [])
        assert ret

    def test_call_method_reconnect(self):
        p = ServerPage(fake.Container(port=build_config.testport, path=str(path)),
                       py.execnet.PopenGateway())
        ret = p.call_method('status', [])
        assert len(p._channel_holder) == 1
        channel = p._channel_holder[0]
        
        ret = p.call_method('status', [])
        assert len(p._channel_holder) == 1
        assert p._channel_holder[0] is channel
        channel.close()

        ret = p.call_method('status', [])
        assert len(p._channel_holder) == 1
        assert p._channel_holder is not channel

