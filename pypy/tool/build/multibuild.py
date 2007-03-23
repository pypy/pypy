""" multibuild.py variant that uses startcompile to run the builds

    see pypy/translator/goal/multibuild.py for the original version (by mwh)
    that builds on the local host
"""

import autopath
import sys
import random
import os
import threading
from pypy.translator.goal.multibuild import get_options, exe_name_from_options
from pypy.tool.build import config
from pypy.tool.build.compile import getrequest, main

class ConfigWrapper(object):
    def __init__(self, orgconfig):
        self.__dict__.update(orgconfig.__dict__)

def setconfig(conf, overrides):
    for name, value in overrides.iteritems():
        try:
            homeconfig, name = conf._cfgimpl_get_home_by_path(name)
            homeconfig.setoption(name, value, 'default')
        except AttributeError:
            pass

def override_conf(config, opts):
    for k, v in opts.items():
        for c in (config.system_config, config.compile_config,
                  config.tool_config):
            try:
                c.set(**{k: v})
            except AttributeError:
                pass

def startcompile(exe_name, config, opts):
    try:
        override_conf(config, opts)
    except:
        return exe_name_from_options(newconfig.compile_config, opts), \
               "didn't configure"
    request, foreground = getrequest(config, sys.argv[3:])
    hasbuilt, message = main(config, request, True)
    hasbuilt, message = (True, 'foo')
    return hasbuilt and 'successfully built' or 'not built: %s' % (message,)

def wait_until_done():
    while 1:
        for t in threading.enumerate():
            if t != threading.currentThread() and t.isAlive():
                t.join()
        else:
            break

results = []
def build_pypy_with_options(basedir, opts):
    """ start blocking (--foreground) startcompile with opts
    """
    newconfig = ConfigWrapper(config)
    newconfig.system_config = config.system_config.copy()
    newconfig.compile_config = config.compile_config.copy()
    newconfig.tool_config = config.tool_config.copy()

    exe_name = os.path.join(basedir, exe_name_from_options(
                                      newconfig.compile_config, opts))

    print 'starting: %s' % (exe_name,)
    sys.stdout.flush()

    status = startcompile(exe_name, newconfig, opts)

    results.append((exe_name, status))

    print '%s: %s' % (exe_name, status)

if __name__ == '__main__':
    basedir = sys.argv[1]
    optionsfile = sys.argv[2]
    results = []
    options = list(get_options(optionsfile))
    random.shuffle(options)
    for opts in options:
        t = threading.Thread(target=build_pypy_with_options,
                             args=(basedir, opts))
        t.start()
    wait_until_done()
    print 'done'

    out = open(os.path.join(basedir, 'results'), 'w')
    for exe, r in results:
        print >>out, exe, r

