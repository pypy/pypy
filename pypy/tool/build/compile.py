import sys
import random
import time
import py
from pypy.tool.build.bin import path
from pypy.tool.build import config
from pypy.tool.build import build
from pypy.tool.build import execnetconference

POLLTIME = 5 # for --foreground polling

class ServerAccessor(object):
    remote_code = """
        import sys
        sys.path += %r

        from pypy.tool.build import metaserver_instance
        from pypy.tool.build.build import BuildRequest

        def getbp(ms, id):
            for bp in ms._done:
                if bp.request.id() == id:
                    return bp
        
        chunksize = 1024

        try:
            while 1:
                cmd, data = channel.receive()
                if cmd == 'compile':
                    ret = metaserver_instance.compile(
                            BuildRequest.fromstring(data))
                elif cmd == 'check':
                    ret = False
                    bp = getbp(metaserver_instance, data)
                    if bp:
                        ret = str(bp.error)
                elif cmd == 'zip':
                    bp = getbp(metaserver_instance, data)
                    zipfp = bp.zipfile.open('rb')
                    try:
                        while 1:
                            chunk = zipfp.read(chunksize)
                            channel.send(chunk)
                            channel.receive()
                            if len(chunk) < chunksize:
                                channel.send(None)
                                break
                    finally:
                        zipfp.close()
                channel.send(ret)
        finally:
            channel.close()
    """
    def __init__(self, config):
        self.config = config
        self.requestid = None
        self._connect()

    def _send_twice(self, data):
        try:
            self.channel.send(data)
        except EOFError:
            print 'error during send: %s, retrying' % (e,)
            self.close()
            self._connect()
            self.channel.send(data)

    def _receive(self):
        ret = self.channel.receive()
        if isinstance(ret, Exception):
            raise ret.__class__, ret # tb?
        return ret

    def _try_twice(self, command, data):
        try:
            self._send_twice((command, data))
            return self._receive()
        except EOFError:
            self._send_twice((command, data))
            return self._receive()

    def start_compile(self, request):
        req = request.serialize()
        ret = self._try_twice('compile', req)
        if isinstance(ret, dict):
            self.requestid = ret['id']
        return ret
        
    def check_in_progress(self):
        return self._try_twice('check', self.requestid)

    def save_zip(self, path):
        self._send_twice(('zip', self.requestid))
        # XXX let's not try to fiddle about with re-sending the zip on
        # failures, people can always go to the web page
        fp = path.open('w')
        try:
            while 1:
                chunk = self.channel.receive()
                if chunk is None:
                    break
                fp.write(chunk)
                self.channel.send(None)
        finally:
            fp.close()

    def close(self):
        try:
            self.channel.close()
        except EOFError:
            pass
        self.gateway.exit()
        
    def _connect(self):
        self.gateway = gw = self._get_gateway()
        conference = execnetconference.conference(gw, self.config.port, False)
        self.channel = conference.remote_exec(self.remote_code % (
                                               self.config.path,))

    def _get_gateway(self):
        if self.config.server in ['localhost', '127.0.0.1']:
            gw = py.execnet.PopenGateway()
        else:
            gw = py.execnet.SshGateway(config.server)
        return gw

def parse_options(config, args=None):
    # merge system + compile options into one optionparser
    from py.compat.optparse import OptionParser, OptionGroup
    from pypy.config.config import to_optparse

    optparser = to_optparse(config.system_config)
    to_optparse(config.compile_config, parser=optparser)
    to_optparse(config.tool_config, parser=optparser)
    optparser.add_option('', '--foreground', action="store_true",
                         dest='foreground', default=False,
                         help='block until build is available and download it '
                              'immediately')

    (options, args) = optparser.parse_args(args)

    if not args or len(args) != 1:
        optparser.error('please provide an email address')

    return optparser, options, args

def getrequest(config, args=None):
    from pypy.config.config import make_dict

    optparser, options, args = parse_options(config, args=args)

    sysinfo = make_dict(config.system_config)
    compileinfo = make_dict(config.compile_config)

    buildrequest = build.BuildRequest(args[0], sysinfo, compileinfo,
                                      config.svnpath_to_url(
                                                config.tool_config.svnpath),
                                      config.tool_config.svnrev,
                                      config.tool_config.revrange)
    return buildrequest, options.foreground

def main(config, request, foreground=False):
    inprogress = False

    print 'going to start compile job with info:'
    for k, v in request.sysinfo.items():
        print '%s: %r' % (k, v)
    print
    print config.compile_config

    msa = ServerAccessor(config)
    print 'going to start compile'
    ret = msa.start_compile(request)
    reqid = ret['id']
    path = ret['path']
    message = ret['message']
    if path:
        print ('a suitable result is already available, you can '
               'find it at "%s" on %s' % (path, config.server))
    else:
        print message
        print 'the id of this build request is: %s' % (reqid,)
        inprogress = True

    if foreground and inprogress:
        print 'waiting until it\'s done'
        error = None
        while 1:
            ret = msa.check_in_progress()
            if ret is not False:
                error = ret
                break
            time.sleep(POLLTIME)
        if error and error != 'None':
            print 'error compiling:', error
            return (False, error)
        else:
            print 'compilation finished successfully, downloading zip file'
            zipfile = py.path.local('pypy-%s.zip' % (reqid,))
            msa.save_zip(zipfile)
            print 'done, the result can be found in %s' % (zipfile,)
            return (True, message)
    elif not foreground and inprogress and not path:
        print 'you will be mailed once it\'s ready'
    elif foreground:
        return (False, message)

