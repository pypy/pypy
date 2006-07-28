import time
import thread

class PPBClient(object):
    def __init__(self, channel, sysinfo, testing=False):
        self.channel = channel
        self.sysinfo = sysinfo
        self.busy_on = None
        self.testing = testing

        from pypy.tool.build import ppbserver
        self.server = ppbserver
        self.server.register(self)
        
    def sit_and_wait(self):
        """connect to the host and wait for commands"""
        self.channel.waitclose()
        self.channel.close()

    def compile(self, info):
        """send a compile job to the client side"""
        self.busy_on = info
        self.channel.send(info)
        thread.start_new_thread(self.wait_until_done, (info,))

    def wait_until_done(self, info):
        efp = open('/tmp/foo', 'w')
        efp.write(repr(info) + '\n')
        buildpath = self.server.get_new_buildpath(info)
        efp.flush()
        
        if not self.testing:
            efp.write('2\n')
            efp.flush()
            fp = buildpath.zipfile.open('w')
            try:
                while True:
                    try:
                        chunk = self.channel.receive()
                    except EOFError:
                        # stop compilation, client has disconnected
                        return 
                    if chunk is None:
                        break
                    fp.write(chunk)
            finally:
                fp.close()
        
        efp.write('3\n')
        efp.flush()
        self.server.compilation_done(info, buildpath)
        self.busy_on = None
        efp.write(repr(info))
        efp.flush()
        efp.close()

initcode = """
    import sys
    sys.path += %r
    
    from pypy.tool.build.client import PPBClient

    try:
        try:
            client = PPBClient(channel, %r, %r)
            client.sit_and_wait()
        except:
            import sys, traceback
            exc, e, tb = sys.exc_info()
            channel.send(str(exc) + ' - ' + str(e))
            for line in traceback.format_tb(tb):
                channel.send(line[:-1])
            del tb
    finally:
        channel.close()
"""
def init(gw, sysconfig, path=None, port=12321, testing=False):
    from pypy.tool.build import execnetconference
    from pypy.tool.build import server
    
    if path is None:
        path = []

    sysinfo = server.config_to_dict(sysconfig)
    conference = execnetconference.conference(gw, port, False)
    channel = conference.remote_exec(initcode % (path, sysinfo, testing))
    return channel
