#!/usr/bin/python

"""
Force the PyPy buildmaster to run a builds on all builders that produce
nightly builds for a particular branch.

Taken from http://twistedmatrix.com/trac/browser/sandbox/exarkun/force-builds.py

modified by PyPy team
"""

import os, sys, pwd, urllib

from twisted.internet import reactor, defer
from twisted.python import log
from twisted.web import client
from twisted.web.error import PageRedirect

BUILDERS = [
    'own-linux-x86-32',
    'own-linux-x86-64',
#    'own-macosx-x86-32',
#    'pypy-c-app-level-linux-x86-32',
#    'pypy-c-app-level-linux-x86-64',
#    'pypy-c-stackless-app-level-linux-x86-32',
    'pypy-c-app-level-win-x86-32',
    'pypy-c-jit-linux-x86-32',
    'pypy-c-jit-linux-x86-64',
#    'pypy-c-jit-macosx-x86-32',
    'pypy-c-jit-win-x86-32',
]

def main():
    #XXX: handle release tags
    #XXX: handle validity checks
    branch = sys.argv[1]
    lock = defer.DeferredLock()
    requests = []
    def ebList(err):
        if err.check(PageRedirect) is not None:
            return None
        log.err(err, "Build force failure")

    for builder in BUILDERS:
        print 'Forcing', builder, '...'
        url = "http://buildbot.pypy.org/builders/" + builder + "/force"
        args = [
            ('username', pwd.getpwuid(os.getuid())[0]),
            ('revision', ''),
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
    main()
