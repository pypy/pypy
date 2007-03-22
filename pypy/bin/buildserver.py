#!/usr/bin/env python

import autopath
import py
from py.execnet import PopenGateway
from pypy.tool.build import outputbuffer

def compile(wc, compileinfo, buildpath):
    code = """\
        import sys
        import os
        import traceback

        # interpolating the path
        pypath = %r

        sys.path = [pypath] + sys.path
        os.chdir(pypath)

        # interpolating config
        compileinfo = %r

        # log locally too
        log = open('%s/compile.log', 'a')
        outbuffer = OutputBuffer(log)
        sys.stdout = outbuffer
        sys.stderr = outbuffer
        try:
            try:
                try:
                    from pypy.interpreter.error import OperationError
                    from pypy.translator.goal import targetpypystandalone
                    from pypy.translator.driver import TranslationDriver
                    from pypy.config import pypyoption
                    from pypy.tool.udir import udir

                    from pypy.config.pypyoption import get_pypy_config
                    from pypy.translator.goal.translate import translate_optiondescr
                    from pypy.tool.build.compileoption import combine_config
                    from pypy.config.config import Config
                    pypy_config = get_pypy_config()
                    translate_config = Config(translate_optiondescr)
                    config = combine_config(pypy_config, translate_config, 'pypy',
                                                    'pypy options')
                    open('/tmp/compileinfo', 'w').write(repr(compileinfo))
                    config.override(compileinfo)

                    targetpypystandalone.PyPyTarget.translateconfig = config

                    driver = TranslationDriver.from_targetspec(
                                targetpypystandalone.__dict__,
                                config=pypy_config,
                                default_goal='compile')
                    driver.proceed(['compile'])
                except Exception, e:
                    # XXX we may want to check
                    exception_occurred = True
                    exc, e, tb = sys.exc_info()
                    print '=' * 79
                    print 'Exception during compilation:'
                    print '%%s: %%s' %% (exc, e)
                    print
                    print '\\n'.join(traceback.format_tb(tb))
                    print '=' * 79
                    del tb
                    channel.send(None)
                else:
                    channel.send(str(udir))
            finally:
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                log.close()
            channel.send(outbuffer.getvalue())
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
    from pypy.tool.build import config
    from pypy.tool.build.buildserver import main

    main(config, path, compile)

