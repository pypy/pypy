import py
import thread
from zipfile import ZipFile, ZIP_DEFLATED
from cStringIO import StringIO
from pypy.tool.build import build

class BuildServer(object):
    def __init__(self, channel, sysinfo, hostname, testing_sleeptime=False):
        self.hostname = hostname
        self.channel = channel
        self.sysinfo = sysinfo
        self.busy_on = None
        self.refused = []
        self.testing_sleeptime = testing_sleeptime

        from pypy.tool.build import metaserver_instance
        self.metaserver = metaserver_instance
        self.metaserver.register(self)
        
    def sit_and_wait(self):
        """connect to the host and wait for commands"""
        self.channel.waitclose()
        self.channel.close()

    def compile(self, request):
        """send a compile job to the client side"""
        self.channel.send(request.serialize())
        accepted = self.channel.receive()
        if accepted:
            self.busy_on = request
            request.build_start_time = py.std.time.time()
            thread.start_new_thread(self.wait_until_done, (request,))
        else:
            self.refused.append(request)
        return accepted

    def wait_until_done(self, request):
        buildpath = self.metaserver.get_new_buildpath(request)
        
        if not self.testing_sleeptime:
            fp = buildpath.zipfile.open('w')
            gotdata = False
            try:
                while True:
                    # read data in chunks
                    try:
                        chunk = self.channel.receive()
                    except EOFError:
                        # stop compilation, build server has disconnected 
                        # (metaserver will check the connection after a while 
                        # and clean up)
                        return
                    # end of data is marked by sending a None
                    if chunk is None:
                        break
                    else:
                        self.channel.send(None)
                    gotdata = True
                    fp.write(chunk)
            finally:
                fp.close()
            # write the log (process stdout/stderr) to the buildpath
            buildpath.log = self.channel.receive()
        else:
            # pretend we're compiling by sleeping a bit...
            py.std.time.sleep(self.testing_sleeptime)

        request.build_end_time = py.std.time.time()
        buildpath.request = request # re-write to disk
        self.metaserver.compilation_done(buildpath)
        self.busy_on = None

initcode = """
    import sys
    sys.path += %r
    
    from pypy.tool.build.buildserver import BuildServer

    try:
        try:
            bs = BuildServer(channel, %r, %r, %r)
            bs.sit_and_wait()
        except:
            try:
                import sys, traceback
                exc, e, tb = sys.exc_info()
                channel.send(str(exc) + ' - ' + str(e))
                for line in traceback.format_tb(tb):
                    channel.send(line[:-1])
                del tb
            except:
                pass
    finally:
        channel.close()
"""
def init(gw, sysconfig, path=None, port=12321, testing_sleeptime=False):
    from pypy.tool.build import execnetconference
    from pypy.config.config import make_dict
    
    if path is None:
        path = []

    sysinfo = make_dict(sysconfig)
    conference = execnetconference.conference(gw, port, False)
    channel = conference.remote_exec(initcode % (path, sysinfo,
                                                 py.std.socket.gethostname(),
                                                 testing_sleeptime))
    return channel

class ChannelWrapper(object):
    """ wrapper around a channel

        implements (a small part of) the file interface, sends the data
        over the wire in chunks, ending with a None
    """
    def __init__(self, channel):
        self.channel = channel
        self.loc = 0

    def write(self, data):
        self.loc += len(data)
        self.channel.send(data)
        self.channel.receive() # to make sure stuff is only sent when required

    def close(self):
        self.channel.send(None)

    def tell(self):
        return self.loc

    def flush(self):
        pass

def zip_dir(res_dir, tofile):
    zip = ZipFile(tofile, 'w', ZIP_DEFLATED)
    for fpath in res_dir.visit():
        if fpath.ext in ['.o']:
            continue
        try:
            zip.writestr("pypy-compiled/" + fpath.relto(res_dir), fpath.read())
        except (py.error.ENOENT, py.error.EISDIR), exc:
            print exc
            continue
    zip.close()

def tempdir(parent=None):
    i = 0
    if parent is None:
        parent = py.path.local('/tmp')
    while 1:
        dirname = 'buildtemp-%s' % (i,)
        if not parent.join(dirname).check():
            return parent.ensure(dirname, dir=True)
        i += 1

def main(config, path, compilefunc):
    """ build server bootstrapping and main loop """
    from py.execnet import SshGateway, PopenGateway

    if config.server in ['localhost', '127.0.0.1']:
        gw = PopenGateway()
    else:
        print "It may be that you have to enter your ssh-password for %s" % (
                config.server, )
        print "if you don't have your keys configured properly"
        gw = SshGateway(config.server)
        
    channel = init(gw,
                   config.system_config,
                   path=config.path,
                   port=config.port)

    print 'connected'
    try:
        while 1:
            # receive compile requests
            request = channel.receive()
            if not isinstance(request, str):
                raise ValueError(
                    'received wrong unexpected data of type %s' % (
                            type(request),)
                )
            try:
                request = build.BuildRequest.fromstring(request)
            except (KeyError, SyntaxError), e:
                print ('exception occurred when trying to '
                       'interpret the following request:')
                print request
                print
                print 'going to continue'
                continue
            accepting = True
            for checker in config.client_checkers:
                if not checker(request):
                    if hasattr(checker, 'im_func'):
                        name = '%s.%s' % (checker.im_class.__name__,
                                          checker.im_func.func_name)
                    else:
                        name = checker.func_name
                    print 'request refused by checker', name
                    accepting = False
                    break
            channel.send(accepting)
            if not accepting:
                print 'refusing compilation'
                continue

            print 'compilation requested for %s' % (request,)

            # subversion checkout
            print 'checking out %s@%s' % (request.svnurl,
                                          request.normalized_rev)
            temp = tempdir()
            svnwc = py.path.svnwc(temp)
            svnwc.checkout(request.svnurl)
            svnwc.update(request.normalized_rev)

            try:
                print 'starting compilation'
                upath, log = compilefunc(svnwc, request.compileinfo,
                                         temp)
            except (SystemExit, KeyboardInterrupt):
                print 'quitting...'
                break

            if upath:
                # send over zip data, end with a None
                print 'compilation successful, sending to server'
                wrapper = ChannelWrapper(channel)
                zip_dir(py.path.local(upath), wrapper)
                wrapper.close()
            else:
                print 'compilation failed, notifying server'
                # just send the None
                channel.send(None)
            
            # send over logs
            print 'sending log'
            channel.send(log)
            
            print 'done with compilation, waiting for next'
    finally:
        channel.close()
        gw.exit()

