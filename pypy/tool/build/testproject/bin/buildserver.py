#!/usr/bin/env python

import autopath
import py
from py.execnet import PopenGateway
from pypy.tool.build import outputbuffer

def compile(wc, compileinfo, buildpath):
    code = """\
        import os
        import py

        try:
            # interpolating the path
            wc = py.path.local(%r)
            os.chdir(str(wc.join('test')))
            try:
                output = py.process.cmdexec("gcc -o test test.c")
            except Exception, e:
                output = str(e)
                channel.send(None)
            else:
                tempdir = py.test.ensuretemp('compile_testproject_result')
                exe = wc.join('test/test')
                exe.copy(tempdir)
                channel.send(str(tempdir))
            channel.send(output)
        finally:
            channel.close()
    """
    gw = PopenGateway()
    interpolated = py.code.Source(outputbuffer,  code % (str(wc),))
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

