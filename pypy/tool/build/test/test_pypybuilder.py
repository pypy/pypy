import path
from pypy.tool.build import client, server, execnetconference
from pypy.tool.build import config
from pypy.tool.build import build
from pypy.config import config as pypyconfig
import py
from repo import create_temp_repo

# XXX NOTE: if you encounter failing tests on a slow system, you may want to
# increase the sleep interval a bit to see if that helps...
SLEEP_INTERVAL = 1.0

def _get_sysconfig():
    return pypyconfig.Config(
        pypyconfig.OptionDescription('foo', '', [
            pypyconfig.ChoiceOption('foo', 'foo', [1,2,3], 1),
        ])
    )

# some functional tests (although some of the rest aren't strictly
# unit tests either), to run use --functional as an arg to py.test
def test_functional_1():
    if not py.test.pypybuilder_option.functional:
        py.test.skip('skipping functional test, use --functional to run it')

    # XXX this one is a bit messy, it's a quick functional test for the whole
    # system, but for instance contains time.sleep()s to make sure all threads
    # get the time to perform tasks and such... 

    repo = create_temp_repo('functional')
    repo.mkdir('foo')
    foourl = str(repo.join('foo'))

    # first initialize a server
    sgw = py.execnet.PopenGateway()
    temppath = py.test.ensuretemp('pypybuilder-functional')
    sc = server.init(sgw, port=config.testport, path=config.testpath,
                     buildpath=str(temppath))

    # give the server some time to wake up
    py.std.time.sleep(SLEEP_INTERVAL)

    # then two clients, both with different system info
    sysconfig1 = _get_sysconfig()
    cgw1 = py.execnet.PopenGateway()
    cc1 = client.init(cgw1, sysconfig1, port=config.testport, testing=True)
    cc1.receive() # welcome message

    sysconfig2 = _get_sysconfig()
    sysconfig2.foo = 2
    cgw2 = py.execnet.PopenGateway()
    cc2 = client.init(cgw2, sysconfig2, port=config.testport, testing=True)
    cc2.receive() # welcome message

    # give the clients some time to register themselves
    py.std.time.sleep(SLEEP_INTERVAL)

    # now we're going to send some compile jobs
    code = """
        import sys
        sys.path += %r
        
        from pypy.tool.build import ppbserver
        from pypy.tool.build import build
        channel.send(ppbserver.compile(%r))
        channel.close()
    """
    compgw = py.execnet.PopenGateway()
    compconf = execnetconference.conference(compgw, config.testport)

    # we're going to have to closely mimic the bin/client script to avoid
    # freezes (from the app waiting for input)
    
    # this one should fail because there's no client found for foo = 3
    br = build.BuildRequest('foo1@bar.com', {'foo': 3}, {}, foourl,
                            1, 0)
    compc = compconf.remote_exec(code % (config.testpath, br))
    
    # sorry...
    py.std.time.sleep(SLEEP_INTERVAL)

    ret = compc.receive()
    assert not ret[0]
    assert ret[1].find('no suitable client found') > -1

    # this one should be handled by client 1
    br = build.BuildRequest('foo2@bar.com', {'foo': 1}, {}, foourl,
                            1, 0)
    compc = compconf.remote_exec(code % (config.testpath, br))
    
    # client 1 will now send a True to the server to tell it wants to compile
    cc1.send(True)

    # and another one
    py.std.time.sleep(SLEEP_INTERVAL)
    
    ret = compc.receive()
    print repr(ret)
    assert not ret[0]
    assert ret[1].find('found a suitable client') > -1

    # the messages may take a bit to arrive, too
    py.std.time.sleep(SLEEP_INTERVAL)

    # client 1 should by now have received the info to build for
    ret = cc1.receive()
    request = build.BuildRequest.fromstring(ret)
    assert request.sysinfo == {'foo': 1}

    # this should have created a package in the temp dir
    assert len(temppath.listdir()) == 1

    # now we're going to satisfy the first request by adding a new client
    sysconfig3 = _get_sysconfig()
    sysconfig3.foo = 3
    cgw3 = py.execnet.PopenGateway()
    cc3 = client.init(cgw3, sysconfig3, port=config.testport, testing=True)

    # add True to the buffer just like we did for channels 1 and 2
    cc3.send(True)

    # again a bit of waiting may be desired
    py.std.time.sleep(SLEEP_INTERVAL)

    # _try_queued() should check whether there are new clients available for 
    # queued jobs
    code = """
        import sys, time
        sys.path += %r
        
        from pypy.tool.build import ppbserver
        ppbserver._try_queued()
        # give the server some time, the clients 'compile' in threads
        time.sleep(%s) 
        channel.send(ppbserver._waiting)
        channel.close()
    """
    compgw2 = py.execnet.PopenGateway()
    compconf2 = execnetconference.conference(compgw2, config.testport)

    compc2 = compconf2.remote_exec(code % (config.testpath, SLEEP_INTERVAL))
    cc2.send(True)

    # we check whether all emails are now sent, since after adding the third
    # client, and calling _try_queued(), both jobs should have been processed
    ret = compc2.receive()
    assert ret == []

    # this should also have created another package in the temp dir
    assert len(temppath.listdir()) == 2

    # some cleanup (this should all be in nested try/finallys, blegh)
    cc1.close()
    cc2.close()
    cc3.close()
    compc.close()
    compc2.close()
    sc.close()

    cgw1.exit()
    cgw2.exit()
    compgw.exit()
    compgw2.exit()
    sgw.exit()

