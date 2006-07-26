import time
import thread

class PPBClient(object):
    def __init__(self, channel, sysinfo, testing=False):
        self.channel = channel
        self.sysinfo = sysinfo
        self.busy_on = None
        self.testing = testing

        from pypybuilder import ppbserver
        self.server = ppbserver
        self.server.register(self)
        
    def sit_and_wait(self):
        """connect to the host and wait for commands"""
        self.channel.waitclose()
        self.channel.close()

    def compile(self, info):
        """send a compile job to the client side

            this waits until the client is done, and assumes the client sends
            back the whole binary as a single string (XXX this should change ;)
        """
        self.busy_on = info
        self.channel.send(info)
        thread.start_new_thread(self.wait_until_done, (info,))

    def wait_until_done(self, info):
        buildpath = self.server.get_new_buildpath(info)
        
        fp = buildpath.zipfile.open('w')
        if not self.testing:
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
            
        self.server.compilation_done(info, buildpath)
        self.busy_on = None

initcode = """
    import sys
    sys.path += %r
    
    from pypybuilder.client import PPBClient

    try:
        client = PPBClient(channel, %r, %r)
        client.sit_and_wait()
    finally:
        channel.close()
"""
def init(gw, sysinfo, path=None, port=12321, testing=False):
    from pypybuilder import execnetconference
    
    if path is None:
        path = []

    conference = execnetconference.conference(gw, port, False)
    channel = conference.remote_exec(initcode % (path, sysinfo, testing))
    return channel
