import py
import threading
from pypy.tool.build import execnetconference
from pypy.tool.build import config
from pypy.tool.build.compile import main
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

def test_compile():
    # functional test, sorry :|
    if not option.functional:
        py.test.skip('skipping functional test, use --functional to run it')

    repo, wc = svntestbase.getrepowc('test_compile')
    temp = py.test.ensuretemp('test_compile.buildpath')
    wc.ensure('foo', dir=True)
    wc.commit('added foo')
    path = repo + '/foo'
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

