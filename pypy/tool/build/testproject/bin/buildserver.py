#!/usr/bin/env python

import autopath
import py
from py.execnet import PopenGateway
from pypy.tool.build import outputbuffer

def compile(wc, compileinfo, buildpath):
    code = """\
        import os
        
        import py

        # interpolating the path
        wc = py.path.local(%r)
        try:
            os.chdir(str(wc))
            try:
                output = py.process.cmdexec("gcc -o test test.c")
            except Exception, e:
                output = str(e)
            upath = wc.join('test')
            channel.send(output)
            channel.send(str(upath))
        finally:
            channel.close()
    """
    gw = PopenGateway()
    interpolated = py.code.Source(outputbuffer,
                                  code % (str(wc), compileinfo,
                                  str(buildpath)))
    channel = gw.remote_exec(interpolated)
    try:
        upath = channel.receive()
        output = channel.receive()
    except channel.RemoteError, e:
        print 'Remote exception:'
        print str(e)
        return (None, str(e))
    channel.close()

    return upath, output

if __name__ == '__main__':
    # main bit
    from pypy.tool.build.bin import path
    from pypy.tool.build.testproject import config
    from pypy.tool.build.buildserver import main

    main(config, path, compile)

