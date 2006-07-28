from pypy.tool.build.server import BuildPath

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

class FakeClient(object):
    def __init__(self, info):
        self.channel = FakeChannel()
        self.sysinfo = info
        self.busy_on = None

    def compile(self, info):
        for k, v in info[0].items():
            self.channel.send('%s: %r' % (k, v))
        self.channel.send(None)
        self.busy_on = info

class FakeServer(object):
    def __init__(self, builddirpath):
        builddirpath.ensure(dir=True)
        self._channel = FakeChannel()
        self._builddirpath = builddirpath
        self._clients = []
        self._done = []

    def register(self, client):
        self._clients.append(client)

    def compilation_done(self, info, data):
        self._done.append((info, data))
        
    i = 0
    def get_new_buildpath(self, info):
        name = 'build-%s' % (self.i,)
        self.i += 1
        bp = BuildPath(str(self._builddirpath / name))
        bp.info = info
        bp.ensure(dir=1)
        return bp

