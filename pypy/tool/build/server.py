import random
import time
import thread
import smtplib
import py
from pypy.tool.build.build import BuildPath

def issubdict(d1, d2):
    """sees whether a dict is a 'subset' of another dict
    
        dictvalues can be immutable data types and list and dicts of 
        immutable data types and lists and ... (recursive)
    """
    for k, v in d1.iteritems():
        if not k in d2:
            return False
        d2v = d2[k]
        if isinstance(v, dict) and isinstance(d2v, dict):
            if not issubdict(v, d2v):
                return False
        elif isinstance(v, list) and isinstance(d2v, list):
            if not set(v).issubset(set(d2v)):
                return False
        elif v != d2v:
            return False
    return True

class PPBServer(object):
    """ the build server

        this delegates or queues build requests, and stores results and sends
        out emails when they're done
    """
    retry_interval = 10
    
    def __init__(self, projname, channel, builddir, mailhost=None,
                    mailport=None, mailfrom=None):
        self._projname = projname
        self._channel = channel
        self._buildroot = py.path.local(builddir)
        self._mailhost = mailhost
        self._mailport = mailport
        self._mailfrom = mailfrom
        
        self._clients = []

        done = []
        for bp in self._get_buildpaths(builddir):
            if bp.done:
                done.append(bp)
            else:
                # throw away half-done builds...
                bp.remove()

        self._done = done

        self._queued = [] # no compile client available
        self._waiting = [] # compilation already in progress for someone else

        self._queuelock = thread.allocate_lock()
        self._namelock = thread.allocate_lock()
        
    def register(self, client):
        """ register a client (instance) """
        self._clients.append(client)
        self._channel.send('registered %s with info %r' % (
                            client, client.sysinfo))

    def compile(self, request):
        """start a compilation

            requester_email is an email address of the person requesting the
            build, info is a tuple (sysinfo, compileinfo) where both infos
            are configs converted (or serialized, basically) to dict

            returns a tuple (ispath, data)

            if there's already a build available for info, this will return
            a tuple (True, path), if not, this will return (False, message),
            where message describes what is happening with the request (is
            a build made rightaway, or is there no client available?)

            in any case, if the first item of the tuple returned is False,
            an email will be sent once the build is available
        """
        # store the request, if there's already a build available the
        # storage will return that path
        for bp in self._done:
            if request.has_satisfying_data(bp.request):
                path = str(bp)
                self._channel.send('already a build for this info available')
                return (True, path)
        for client in self._clients:
            if client.busy_on and request.has_satisfying_data(client.busy_on):
                self._channel.send('build for %s currently in progress' %
                                   (request,))
                self._waiting.append(request)
                return (False, 'this build is already in progress')
        # we don't have a build for this yet, find a client to compile it
        if self.run(request):
            return (False, 'found a suitable client, going to build')
        self._queuelock.acquire()
        try:
            self._queued.append(request)
        finally:
            self._queuelock.release()
        return (False, 'no suitable client found; your request is queued')
    
    def run(self, request):
        """find a suitable client and run the job if possible"""
        clients = self._clients[:]
        # XXX shuffle should be replaced by something smarter obviously ;)
        random.shuffle(clients)
        for client in clients:
            # if client is busy, or sysinfos don't match, refuse rightaway,
            # else ask client to build it
            if (client.busy_on or
                    not issubdict(request.sysinfo, client.sysinfo) or
                    request in client.refused):
                continue
            else:
                self._channel.send(
                    'going to send compile job for request %s to %s' % (
                        request, client
                    )
                )
                accepted = client.compile(request)
                if accepted:
                    self._channel.send('compile job accepted')
                    return True
                else:
                    self._channel.send('compile job denied')
        self._channel.send(
            'no suitable client available for compilation of %s' % (
                request,
            )
        )

    def serve_forever(self):
        """this keeps the script from dying, and re-tries jobs"""
        self._channel.send('going to serve')
        while 1:
            time.sleep(self.retry_interval)
            self._cleanup_clients()
            self._test_waiting()
            self._try_queued()

    def get_new_buildpath(self, request):
        path = BuildPath(str(self._buildroot / self._create_filename()))
        path.request = request
        return path

    def compilation_done(self, buildpath):
        """client is done with compiling and sends data"""
        self._queuelock.acquire()
        try:
            self._channel.send('compilation done for %s, written to %s' % (
                                                buildpath.request, buildpath))
            emails = [buildpath.request.email]
            self._done.append(buildpath)
            waiting = self._waiting[:]
            for req in waiting:
                if req.has_satisfying_data(buildpath.request):
                    self._waiting.remove(req)
                    emails.append(req.email)
            for emailaddr in emails:
                print 'sending mail to %s' % (emailaddr,)
                self._send_email(emailaddr, buildpath)
        finally:
            self._queuelock.release()

    def _cleanup_clients(self):
        self._queuelock.acquire()
        try:
            clients = self._clients[:]
            for client in clients:
                if client.channel.isclosed():
                    self._channel.send('client %s disconnected' % (client,))
                    if client.busy_on:
                        self._queued.append(client.busy_on)
                    self._clients.remove(client)
        finally:
            self._queuelock.release()

    def _test_waiting(self):
        """ for each waiting request, see if the compilation is still alive

            if the compilation is dead, the request is moved to self._queued
        """
        self._queuelock.acquire()
        try:
            waiting = self._waiting[:]
            for request in waiting:
                for client in self._clients:
                    if request.has_satisfying_data(client.busy_on):
                        break
                else:
                    # move request from 'waiting' (waiting for a compilation
                    # that is currently in progress) to 'queued' (waiting for
                    # a suitable build client to connect)
                    self._waiting.remove(request)
                    self._queued.append(request)
                    continue
        finally:
            self._queuelock.release()

    def _try_queued(self):
        self._queuelock.acquire()
        try:
            toremove = []
            for request in self._queued:
                if self.run(request):
                    toremove.append(request)
            for request in toremove:
                self._queued.remove(request)
        finally:
            self._queuelock.release()

    def _get_buildpaths(self, dirpath):
        for p in py.path.local(dirpath).listdir():
            yield BuildPath(str(p))

    _i = 0
    def _create_filename(self):
        self._namelock.acquire()
        try:
            today = time.strftime('%Y%m%d')
            buildnames = [p.basename for p in 
                            py.path.local(self._buildroot).listdir()]
            while True:
                name = '%s-%s-%s' % (self._projname, today, self._i)
                self._i += 1
                if name not in buildnames:
                    return name
        finally:
            self._namelock.release()

    def _send_email(self, addr, buildpath):
        self._channel.send('going to send email to %s' % (addr,))
        if self._mailhost is not None:
            msg = '\r\n'.join([
                'From: %s' % (self._mailfrom,),
                'To: %s' % (addr,),
                'Subject: %s compilation done' % (self._projname,),
                '',
                'The compilation you requested is done. You can find it at',
                str(build.path),
                '',
                buildpath.log,
            ])
            server = smtplib.SMTP(self._mailhost, self._mailport)
            server.set_debuglevel(0)
            server.sendmail(self._mailfrom, addr, msg)
            server.quit()

initcode = """
    import sys
    sys.path += %r

    try:
        try:
            from pypy.tool.build.server import PPBServer
            server = PPBServer(%r, channel, %r, %r, %r, %r)

            # make the server available to clients as pypy.tool.build.ppbserver
            from pypy.tool import build
            build.ppbserver = server

            server.serve_forever()
        except:
            try:
                import sys, traceback
                exc, e, tb = sys.exc_info()
                channel.send(str(exc) + ' - ' + str(e))
                for line in traceback.format_tb(tb):
                    channel.send(line[:1])
                del tb
            except:
                try:
                    channel.close()
                except:
                    pass
    finally:
        channel.close()
"""
def init(gw, port=12321, path=[], projectname='pypy', buildpath=None,
            mailhost=None, mailport=25, mailfrom=None):
    from pypy.tool.build import execnetconference
    conference = execnetconference.conference(gw, port, True)
    channel = conference.remote_exec(initcode % (path, projectname, buildpath,
                                                    mailhost, mailport,
                                                    mailfrom))
    return channel

