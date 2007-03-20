import sys
import random
import time
import py
from pypy.tool.build.bin import path
from pypy.tool.build import config
from pypy.tool.build import build
from pypy.tool.build import execnetconference

POLLTIME = 5 # for --foreground polling

def get_gateway(config):
    if config.server in ['localhost', '127.0.0.1']:
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

    (options, args) = optparser.parse_args()

    if not args or len(args) != 1:
        optparser.error('please provide an email address')

    return optparser, options, args

initcode = """
    import sys
    import time
    sys.path += %r
    bufsize = 1024

    try:
        try:
            from pypy.tool.build import metaserver_instance
            from pypy.tool.build import build
            ret = metaserver_instance.compile(%r)
            channel.send(ret)
        except Exception, e:
            channel.send(str(e))
    finally:
        channel.close()
"""
def init(gw, request, path, port):
    conference = execnetconference.conference(gw, port, False)
    channel = conference.remote_exec(initcode % (path, request))
    return channel

checkcode = """
    import sys
    sys.path += %r
    bufsize = 1024
    try:
        reqid = channel.receive()
        from pypy.tool.build import metaserver_instance
        from pypy.tool.build import build
        for tb in metaserver_instance._done:
            if tb.request.id() == reqid:
                channel.send({'error': str(tb.error)})
        else:
            channel.send(None)
    finally:
        channel.close()
"""
def check_server(config, id, path, port):
    gw = get_gateway(config)
    try:
        conference = execnetconference.conference(gw, port, False)
        channel = conference.remote_exec(checkcode % (path,))
        try:
            channel.send(id)
            ret = channel.receive()
        finally:
            channel.close()
    finally:
        gw.exit()
    return ret

zipcode = """
    import sys
    sys.path += %r
    bufsize = 1024
    try:
        reqid = channel.receive()
        from pypy.tool.build import metaserver_instance
        from pypy.tool.build import build
        for tb in metaserver_instance._done:
            if tb.request.id() == reqid:
                fp = tb.zipfile.open('rb')
                try:
                    while 1:
                        data = fp.read(bufsize)
                        channel.send(data)
                        channel.receive()
                        if len(data) < bufsize:
                            channel.send(None)
                            break
                finally:
                    fp.close()
    finally:
        channel.close()
"""
def savezip(config, id, path, port, savepath):
    gw = get_gateway(config)
    savepath = py.path.local(savepath)
    try:
        conference = execnetconference.conference(gw, port, False)
        channel = conference.remote_exec(zipcode % (path,))
        try:
            channel.send(id)
            fp = savepath.open('wb')
            try:
                while 1:
                    data = channel.receive()
                    channel.send(None)
                    if data is None:
                        break
                    fp.write(data)
            finally:
                fp.close()
        finally:
            channel.close()
    finally:
        gw.exit()

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
    gateway = get_gateway(config)

    inprogress = False
    try:
        print 'going to start compile job with info:'
        for k, v in request.sysinfo.items():
            print '%s: %r' % (k, v)
        print
        print config.compile_config

        channel = init(gateway, request, config.path, port=config.port)
        try:
            data = channel.receive()
            if type(data) == str:
                print data
                for line in channel:
                    print line
            elif type(data) != dict:
                raise ValueError, 'invalid data returned: %r' % (data,)
            else:
                if data['path']:
                    print ('a suitable result is already available, you can '
                           'find it at "%s" on %s' % (data['path'],
                                                      config.server))
                else:
                    print data['message']
                    print 'the id of this build request is: %s' % (data['id'],)
                    inprogress = True
        finally:
            channel.close()
    finally:
        gateway.exit()

    if foreground and inprogress:
        print 'waiting until it\'s done'
        error = None
        while 1:
            ret = check_server(config, request.id(), config.path,
                               config.port)
            if ret is not None:
                error = ret['error']
                break
            time.sleep(POLLTIME)
        if error and error != 'None':
            print 'error:', error
        else:
            zipfile = py.path.local('data.zip')
            savezip(config, request.id(), config.path,
                    config.port, zipfile)
            print 'done, the result can be found in "data.zip"'
    elif inprogress:
        print 'you will be mailed once it\'s ready'

