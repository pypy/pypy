#!/usr/bin/env python

import autopath
from pypy.tool.build.bin import path
import sys
import random
from pypy.tool.build import config
from pypy.tool.build import build
from pypy.tool.build.tooloption import tool_config

def parse_options(config, tool_config):
    # merge system + compile options into one optionparser
    from py.compat.optparse import OptionParser, OptionGroup
    from pypy.config.config import to_optparse

    optparser = to_optparse(config.system_config)
    to_optparse(config.compile_config, parser=optparser)
    to_optparse(tool_config, parser=optparser)

    (options, args) = optparser.parse_args()

    if not args or len(args) != 1:
        optparser.error('please provide an email address')

    return optparser, options, args

initcode = """
    import sys
    sys.path += %r

    try:
        from pypy.tool.build import metaserver_instance
        from pypy.tool.build import build
        ret = metaserver_instance.compile(%r)
        channel.send(ret)
        channel.close()
    except:
        import sys, traceback
        exc, e, tb = sys.exc_info()
        channel.send(str(exc) + ' - ' + str(e))
        for line in traceback.format_tb(tb):
            channel.send(line[:-1])
        del tb
"""
def init(gw, request, path, port=12321):
    from pypy.tool.build import execnetconference

    conference = execnetconference.conference(gw, port, False)
    channel = conference.remote_exec(initcode % (path, request))
    return channel

if __name__ == '__main__':
    from py.execnet import SshGateway, PopenGateway
    from pypy.config.config import make_dict

    optparser, options, args = parse_options(config, tool_config)

    sysinfo = make_dict(config.system_config)
    compileinfo = make_dict(config.compile_config)

    buildrequest = build.BuildRequest(args[0], sysinfo, compileinfo,
                                      config.svnpath_to_url(
                                                    tool_config.svnpath),
                                      tool_config.svnrev,
                                      tool_config.revrange)

    print 'going to start compile job with info:'
    for k, v in sysinfo.items():
        print '%s: %r' % (k, v)
    print
    print config.compile_config

    if config.server in ['localhost', '127.0.0.1']:
        gw = PopenGateway()
    else:
        gw = SshGateway(config.server)

    channel = init(gw, buildrequest, config.path, port=config.port)
    data = channel.receive()
    if type(data) == str:
        print data
        for line in channel:
            print line
    elif type(data) != dict:
        raise ValueError, 'invalid data returned: %r' % (data,)
    else:
        if data['path']:
            print ('a suitable result is already available, you can find it '
                   'at "%s" on %s' % (data['path'], config.server))
        else:
            print data['message']
            print 'you will be mailed once it\'s ready'
    channel.close()
    gw.exit()

