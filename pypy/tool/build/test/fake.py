from pypy.tool.build.build import BuildPath

class FakeChannel(object):
    def __init__(self):
        self._buffer = []

    def send(self, item):
        self._buffer.append(item)

    def receive(self):
        return self._buffer.pop(0)

    def close(self):
        pass

    def waitclose(self):
        pass

class FakeBuildserver(object):
    def __init__(self, info, compile_info=None):
        self.channel = FakeChannel()
        self.sysinfo = info
        self.compileinfo = compile_info or {}
        self.busy_on = None
        self.refused = []
        self.hostname = "fake"

    def compile(self, request):
        self.channel.send(request.serialize())
        self.channel.send(None)
        self.busy_on = request
        return True

class FakeMetaServer(object):
    def __init__(self, builddirpath):
        builddirpath.ensure(dir=True)
        self._channel = FakeChannel()
        self._builddirpath = builddirpath
        self._clients = []
        self._done = []

    def register(self, client):
        self._clients.append(client)

    def compilation_done(self, ret):
        self._done.append(ret)
        
    i = 0
    def get_new_buildpath(self, request):
        name = 'build-%s' % (self.i,)
        self.i += 1
        bp = BuildPath(str(self._builddirpath / name))
        bp.request = request
        bp.ensure(dir=1)
        return bp

class Container(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

