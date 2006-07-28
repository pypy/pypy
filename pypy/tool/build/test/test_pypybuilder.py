import path
from pypy.tool.build import client, server, execnetconference
from pypy.tool.build import config
from pypy.config import config as pypyconfig
import py

def _get_sysconfig():
    return pypyconfig.Config(
        pypyconfig.OptionDescription('foo', [
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

    sleep_interval = 0.3

    # first initialize a server
    sgw = py.execnet.PopenGateway()
    temppath = py.test.ensuretemp('pypybuilder-functional')
    sc = server.init(sgw, port=config.port, path=config.testpath, 
                        buildpath=str(temppath))

    # give the server some time to wake up
    py.std.time.sleep(sleep_interval)

    # then two clients, both with different system info
    sysconfig1 = _get_sysconfig()
    cgw1 = py.execnet.PopenGateway()
    cc1 = client.init(cgw1, sysconfig1, port=config.port, testing=True)

    sysconfig2 = _get_sysconfig()
    sysconfig2.foo = 2
    cgw2 = py.execnet.PopenGateway()
    cc2 = client.init(cgw2, sysconfig2, port=config.port, testing=True)

    # give the clients some time to register themselves
    py.std.time.sleep(sleep_interval)

    # now we're going to send some compile jobs
    code = """
        import sys
        sys.path += %r
        
        from pypy.tool.build import ppbserver
        channel.send(ppbserver.compile(%r, (%r, {})))
        channel.close()
    """
    compgw = py.execnet.PopenGateway()
    compconf = execnetconference.conference(compgw, config.port)

    # this one should fail because there's no client found for foo = 3
    compc = compconf.remote_exec(code % (config.testpath, 'foo1@bar.com', 
                                            {'foo': 3}))
    
    # sorry...
    py.std.time.sleep(sleep_interval)

    ret = compc.receive()
    assert not ret[0]
    assert ret[1].find('no suitable client found') > -1

    # this one should be handled by client 1
    compc = compconf.remote_exec(code % (config.testpath, 'foo2@bar.com',
                                            {'foo': 1}))
    
    # and another one
    py.std.time.sleep(sleep_interval)
    
    ret = compc.receive()
    assert not ret[0]
    assert ret[1].find('found a suitable client') > -1

    # the messages may take a bit to arrive, too
    py.std.time.sleep(sleep_interval)

    # client 1 should by now have received the info to build for
    cc1.receive() # 'welcome'
    ret = cc1.receive() 
    assert ret == ({'foo': 1}, {})

    # this should have created a package in the temp dir
    assert len(temppath.listdir()) == 1

    # now we're going to satisfy the first request by adding a new client
    sysconfig3 = _get_sysconfig()
    sysconfig3.foo = 3
    cgw3 = py.execnet.PopenGateway()
    cc3 = client.init(cgw3, sysconfig3, port=config.port, testing=True)

    # again a bit of waiting may be desired
    py.std.time.sleep(sleep_interval)

    # _try_queued() should check whether there are new clients available for 
    # queued jobs
    code = """
        import sys, time
        sys.path += %r
        
        from pypy.tool.build import ppbserver
        ppbserver._try_queued()
        # give the server some time, the clients 'compile' in threads
        time.sleep(%s) 
        channel.send(ppbserver._requeststorage._id_to_emails)
        channel.close()
    """
    compgw2 = py.execnet.PopenGateway()
    compconf2 = execnetconference.conference(compgw2, config.port)

    compc2 = compconf2.remote_exec(code % (config.testpath, sleep_interval))


    # we check whether all emails are now sent, since after adding the third
    # client, and calling _try_queued(), both jobs should have been processed
    ret = compc2.receive()
    assert ret.values() == []

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
