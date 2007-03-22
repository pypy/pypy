import py
import threading
from pypy.tool.build import execnetconference
from pypy.tool.build import config
from pypy.tool.build.compile import main, ServerAccessor
from pypy.tool.build.test import fake
from pypy.tool.build import build
from py.__.path.svn.testing import svntestbase
from pypy.tool.build.conftest import option

here = py.magic.autopath().dirpath()
packageparent = here.dirpath().dirpath().dirpath()

class FakeServer(object):
    remote_code = """
        import sys
        sys.path.append(%r)

        from pypy.tool import build
        from pypy.tool.build.build import BuildPath

        class FakeMetaServer(object):
            def __init__(self):
                self._waiting = []
                self._done = []
                
            def compile(self, request):
                self._waiting.append(request)
                return {'path': None, 'id': request.id(), 'isbuilding': True,
                        'message': 'found server'}

            def waiting_ids(self):
                ret = []
                for r in self._waiting:
                    ret.append(r.id())
                return ret

            def compilation_done(self, id, path, log):
                for r in self._waiting:
                    if r.id() == id:
                        self._waiting.remove(r)
                        bp = BuildPath(path)
                        bp.log = log
                        bp.request = r
                        bp.zip = 'foo'
                        self._done.append(bp)

        try:
            build.metaserver_instance = ms = FakeMetaServer()

            # notify we're done
            channel.send(None)

            while 1:
                command, data = channel.receive()
                if command == 'quit':
                    break
                elif command == 'compilation_done':
                    id, path, log = data
                    ms.compilation_done(id, path, log)
                    channel.send(None)
                elif command == 'waiting_ids':
                    channel.send(ms.waiting_ids())
        finally:
            channel.close()
    """ % (str(packageparent),)
    def __init__(self):
        self.gw = gw = py.execnet.PopenGateway()
        conference = execnetconference.conference(gw, config.testport, True)
        self.channel = channel = conference.remote_exec(self.remote_code)
        channel.receive()

    def close(self):
        self.channel.send(('quit', None))
        self.channel.close()
        self.gw.exit()

    def compilation_done(self, id, path, log):
        self.channel.send(('compilation_done', (id, path, log)))
        self.channel.receive()

    def waiting_ids(self):
        self.channel.send(('waiting_ids', None))
        return self.channel.receive()

def get_test_config():
    from pypy.config.config import OptionDescription, IntOption
    from pypy.config.config import ChoiceOption, Config
    sysconfig = Config(OptionDescription('system', '', [
        ChoiceOption('os', 'operating system', ['win32', 'linux2'],
                     default='linux'),
    ]))
    compileconfig = Config(OptionDescription('compileinfo', '', [
        IntOption('somevalue', 'some value', default=0),
    ]))
    return fake.Container(
        server='localhost',
        port=config.testport,
        system_config=sysconfig,
        compile_config=compileconfig,
        path=[str(packageparent)],
        check_svnroot=lambda r: True,
        svnpath_to_url=lambda p: 'file://%s' % (p,),
    )

def create_test_repo_file(name):
    repo, wc = svntestbase.getrepowc('test_compile')
    temp = py.test.ensuretemp('test_compile.%s' % (name,))
    wc.ensure('foo', dir=True)
    wc.commit('added foo')
    path = repo + '/foo'
    return path

def test_blocking():
    # functional test, sorry :|
    if not option.functional:
        py.test.skip('skipping functional test, use --functional to run it')
    path = create_test_repo_file('test_blocking')

    gw = py.execnet.PopenGateway()
    s = FakeServer()
    try:
        ids = s.waiting_ids()
        assert len(ids) == 0

        # first test a non-blocking compile
        req = build.BuildRequest('foo@bar.com', {'foo': 'bar'}, {}, path, 1, 1)
        reqid = req.id()
        t = threading.Thread(target=main, args=(get_test_config(), req))
        t.start()
        t.join(2)
        assert not t.isAlive()
        ids = s.waiting_ids()
        assert ids == [reqid]
        s.compilation_done(reqid, str(temp), 'no problems')
        ids = s.waiting_ids()
        assert len(ids) == 0

        # now for a blocking one
        req = build.BuildRequest('foo@baz.com', {'foo': 'bar'}, {}, path, 1, 1)
        reqid = req.id()
        t = threading.Thread(target=main, args=(get_test_config(), req, True))
        t.start()
        t.join(5)
        assert t.isAlive() # still blocking after 2 secs
        ids = s.waiting_ids()
        assert ids == [reqid]
        s.compilation_done(reqid, str(temp), 'no problems')
        t.join(15)
        assert not t.isAlive() # should have stopped blocking now
        ids = s.waiting_ids()
        assert ids == []
    finally:
        try:
            s.close()
            gw.exit()
        except IOError:
            pass

class TestServerAccessor(object):
    initcode = """
        import sys
        sys.path += %r

        import py
        from pypy.tool.build.build import BuildPath, BuildRequest

        class FakeMetaServer(object):
            def __init__(self):
                self._done = []
                self._compilation_requested = []

            def compile(self, request):
                self._compilation_requested.append(request)
                return {'id': request.id(), 'path': None,
                        'message': 'compilation started'}
        
        ms = FakeMetaServer()
        from pypy.tool import build
        old_metaserver_instance = getattr(build, 'metaserver_instance', None)
        build.metaserver_instance = ms
        try:
            while 1:
                command, data = channel.receive()
                if command == 'quit':
                    break
                elif command == 'compilation_done':
                    for req in ms._compilation_requested:
                        if req.id() == data:
                            temp = py.test.ensuretemp(
                                'test_compile.TestServerAccessor').join(data)
                            ms._compilation_requested.remove(req)
                            bp = BuildPath(temp.join(data))
                            bp.request = req
                            bp.zipfile = 'foo'
                            ms._done.append(bp)
                            break
                    channel.send(None)
                elif command == 'done':
                    channel.send([bp.request.id() for bp in ms._done])
                elif command == 'requesting':
                    channel.send([br.id() for br in ms._compilation_requested])
        finally:
            channel.close()
            build.metaserver_instance = old_metaserver_instance
    """
    
    def setup_method(self, method):
        self.gw = gw = py.execnet.PopenGateway()
        conference = execnetconference.conference(gw, config.testport, True)
        self.channel = conference.remote_exec(self.initcode % (config.path,))

    def teardown_method(self, method):
        self.channel.close()
        self.gw.exit()

    def test_compilation(self):
        # another functional one, although not too bad because it uses
        # a mock meta server
        if not option.functional:
            py.test.skip('skipping functional test, use --functional to run it')
        path = create_test_repo_file('TestServerAccessor.start_compile')
        req = build.BuildRequest('foo@bar.com', {'foo': 'bar'}, {}, path, 1, 1)
        reqid = req.id()
        self.channel.send(('requesting', None))
        ret = self.channel.receive()
        assert ret == []

        sa = ServerAccessor(fake.Container(server='localhost',
                                           port=config.testport,
                                           path=config.testpath))
        sa.start_compile(req)
        self.channel.send(('requesting', None))
        ret = self.channel.receive()
        assert ret == [req.id()]

        ret = sa.check_in_progress()
        assert not ret

        self.channel.send(('done', None))
        ret = self.channel.receive()
        assert ret == []

        self.channel.send(('compilation_done', req.id()))
        assert self.channel.receive() is None
        self.channel.send(('done', None))
        ret = self.channel.receive()
        assert ret == [req.id()]
        self.channel.send(('requesting', None))
        ret = self.channel.receive()
        assert ret == []

        temppath = py.test.ensuretemp('test_compile.TestServerAccessor.zip')
        zippath = temppath.join('data.zip')
        sa.save_zip(zippath)
        assert zippath.read() == 'foo'

