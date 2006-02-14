"""This produces a graph in the style that was manually experimented
with in http://codespeak.net/svn/user/arigo/hack/misc/stackless.c
And is meant to replace stackless support in the PyPy backends.
"""

from pypy.translator.backendopt.support import log, all_operations, annotate
log = log.stackless

def stackless(translator):
    log('starting')
    seen = {}
    for op in all_operations(translator):
        try:
            seen[op.opname] += 1
        except:
            seen[op.opname] = 1

    #statistics...
    for k, v in seen.iteritems():
        log("%dx %s" % (v, k))

    log('finished')
