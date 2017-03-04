#!/usr/bin/python

"""
Force the PyPy buildmaster to run a builds on all builders that produce
nightly builds for a particular branch.

Taken from http://twistedmatrix.com/trac/browser/sandbox/exarkun/force-builds.py

modified by PyPy team
"""

import os, sys, urllib, subprocess

from twisted.internet import reactor, defer
from twisted.python import log
from twisted.web import client
from twisted.web.error import PageRedirect

BUILDERS = [
    'own-linux-x86-32',
    'own-linux-x86-64',
#    'own-linux-armhf',
    'own-win-x86-32',
    'own-linux-s390x',
#    'own-macosx-x86-32',
    'pypy-c-jit-linux-x86-32',
    'pypy-c-jit-linux-x86-64',
#    'pypy-c-jit-freebsd-9-x86-64',
    'pypy-c-jit-macosx-x86-64',
    'pypy-c-jit-win-x86-32',
    'pypy-c-jit-linux-s390x',
    'build-pypy-c-jit-linux-armhf-raring',
    'build-pypy-c-jit-linux-armhf-raspbian',
    'build-pypy-c-jit-linux-armel',
]

def get_user():
    if sys.platform == 'win32':
        return os.environ['USERNAME']
    else:
        import pwd
        return pwd.getpwuid(os.getuid())[0]

def main(branch, server, user):
    #XXX: handle release tags
    #XXX: handle validity checks
    lock = defer.DeferredLock()
    requests = []
    def ebList(err):
        if err.check(PageRedirect) is not None:
            return None
        log.err(err, "Build force failure")

    for builder in BUILDERS:
        print 'Forcing', builder, '...'
        url = "http://" + server + "/builders/" + builder + "/force"
        args = [
            ('username', user),
            ('revision', ''),
            ('forcescheduler', 'Force Scheduler'),
            ('submit', 'Force Build'),
            ('branch', branch),
            ('comments', "Forced by command line script")]
        url = url + '?' + '&'.join([k + '=' + urllib.quote(v) for (k, v) in args])
        requests.append(
            lock.run(client.getPage, url, followRedirect=False).addErrback(ebList))

    d = defer.gatherResults(requests)
    d.addErrback(log.err)
    d.addCallback(lambda ign: reactor.stop())
    reactor.run()
    print 'See http://buildbot.pypy.org/summary after a while'

if __name__ == '__main__':
    log.startLogging(sys.stdout)
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-b", "--branch", help="branch to build", default='')
    parser.add_option("-s", "--server", help="buildbot server", default="buildbot.pypy.org")
    parser.add_option("-u", "--user", help="user name to report", default=get_user())
    (options, args) = parser.parse_args()
    if  not options.branch:
        parser.error("branch option required")
    try:
        subprocess.check_call(['hg','id','-r', options.branch])
    except subprocess.CalledProcessError:
        print 'branch',  options.branch, 'could not be found in local repository'
        sys.exit(-1) 
    main(options.branch, options.server, user=options.user)
