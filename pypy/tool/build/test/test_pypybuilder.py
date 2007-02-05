""" some functional tests (although some of the rest aren't strictly
    unit tests either), to run use --functional as an arg to py.test
"""

import py
import time
import path

from pypy.tool.build import metaserver, buildserver, execnetconference
from pypy.tool.build import config, build
from pypy.tool.build.conftest import option
from pypy.config import config as pypyconfig

from pypy.tool.build.test.repo import create_temp_repo
from pypy.tool.build.test.fake import Container

# XXX this one is a bit messy, it's a quick functional test for the whole
# system, but for instance contains time.sleep()s to make sure all threads
# get the time to perform tasks and such... 

# XXX NOTE: if you encounter failing tests on a slow system, you may want to
# increase the sleep interval a bit to see if that helps...
SLEEP_INTERVAL = 1.0 # 1 sec default, seems okay even on slow machines

def _get_sysconfig():
    return pypyconfig.Config(
        pypyconfig.OptionDescription('foo', '', [
            pypyconfig.ChoiceOption('foo', 'foo', [1,2,3], 1),
        ])
    )

def setup_module(mod):
    if not option.functional:
        py.test.skip('skipping functional test, use --functional to run it')

    mod.repo = repo = create_temp_repo('functional')
    repo.mkdir('foo')
    mod.foourl = str(repo.join('foo'))
    config.checkers = []

    mod.temppath = temppath = py.test.ensuretemp('pypybuilder-functional')

    mod.sgw = sgw = py.execnet.PopenGateway()
    cfg = Container(projectname='pypytest', server='localhost',
                    port=config.testport,
                    path=config.testpath, buildpath=temppath,
                    mailhost=None)
    
    mod.sc = sc = metaserver.init(sgw, cfg)

    def read():
        while 1:
            try:
                print sc.receive()
            except EOFError:
                break
    py.std.thread.start_new_thread(read, ())

    # give the metaserver some time to wake up
    time.sleep(SLEEP_INTERVAL)

def teardown_module(mod):
    mod.sc.close()
    mod.sgw.exit()

def create_buildserver_channel(**conf):
    cgw = py.execnet.PopenGateway()
    sysconfig = _get_sysconfig()
    sysconfig.__dict__.update(conf)
    channel = buildserver.init(cgw, sysconfig, port=config.testport,
                          testing_sleeptime=SLEEP_INTERVAL * 5)
    channel.send(True)
    return cgw, channel

def compile(**sysconfig):
    code = """
        import sys
        sys.path += %r
        
        from pypy.tool.build import metaserver_instance
        from pypy.tool.build import build
        channel.send(metaserver_instance.compile(%r))
        channel.close()
    """
    gw = py.execnet.PopenGateway()
    conf = execnetconference.conference(gw, config.testport)

    try:
        br = build.BuildRequest('foo@bar.com', sysconfig, {}, foourl, 1, 0)
        channel = conf.remote_exec(code % (config.testpath, br))
        try:
            # sorry...
            time.sleep(SLEEP_INTERVAL)
            ret = channel.receive()
        finally:
            channel.close()
    finally:
        gw.exit()

    return ret

def get_info(attr):
    code = py.code.Source("""
        import sys, time
        sys.path += %r
        
        from pypy.tool.build import metaserver_instance
        metaserver_instance._cleanup_builders()
        metaserver_instance._test_waiting()
        metaserver_instance._try_queued()

        # take some time to update all the lists
        time.sleep(%s)

        data = [str(x) for x in metaserver_instance.%s]
        channel.send(data)
        channel.close()
    """ % (config.testpath, SLEEP_INTERVAL, attr))
    gw = py.execnet.PopenGateway()
    try:
        cf = execnetconference.conference(gw, config.testport)
        channel = cf.remote_exec(code)
        try:
            ret = channel.receive()
        finally:
            channel.close()
    finally:
        gw.exit()
    return ret

def test_functional():
    # first we check if the queues are empty
    queued = get_info('_queued')
    assert len(queued) == 0
    waiting = get_info('_waiting')
    assert len(waiting) == 0
    buildservers = get_info('_builders')
    assert len(buildservers) == 0

    # then we request a compilation for sysinfo foo=1, obviously this can not
    # be fulfilled yet
    ispath, data = compile(foo=1)
    assert not ispath
    assert 'no suitable build server' in data
    queued = get_info('_queued')
    assert len(queued) == 1

    # now we register a buildserver with the same sysinfo, note that we don't 
    # tell the metaserver yet that the buildserver actually accepts to handle 
    # the request
    gw, cchannel = create_buildserver_channel(foo=1)
    try:
        buildservers = get_info('_builders')
        assert len(buildservers) == 1

        # XXX quite a bit scary here, the buildserver will take exactly
        # 4 * SLEEP_INTERVAL seconds to fake the compilation... here we should
        # (if all is well) still be compiling
        
        ispath, data = compile(foo=1)
        assert not ispath
        assert 'in progress' in data

        waiting = get_info('_waiting')
        assert len(waiting) == 1

        # this sleep, along with that in the previous compile call, should be
        # enough to reach the end of fake compilation
        time.sleep(SLEEP_INTERVAL * 4)

        # both the jobs should have been done now...
        queued = get_info('_queued')
        assert len(queued) == 0

        waiting = get_info('_waiting')
        assert len(waiting) == 0

        # now a new request for the same build should return in a path being
        # returned
        ispath, data = compile(foo=1)
        assert ispath

        queued = get_info('_queued')
        assert len(queued) == 0
        waiting = get_info('_waiting')
        assert len(waiting) == 0

    finally:
        cchannel.close()
        gw.exit()

    buildservers = get_info('_builders')
    assert len(buildservers) == 0

