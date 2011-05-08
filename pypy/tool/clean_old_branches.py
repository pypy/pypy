"""
For branches that have been closed but still have a dangling head
in 'hg heads --topo --closed', force them to join with the branch
called 'closed-branch'.  It reduces the number of heads.
"""

import os, sys

if not os.listdir('.hg'):
    print 'Must run this script from the top-level directory.'
    sys.exit(1)

def heads(args):
    g = os.popen(r"hg heads --topo %s --template '{branches} {node|short}\n'"
                 % args, 'r')
    result = g.read()
    g.close()
    result = result.splitlines(False)
    result = [s for s in result
                if not s.startswith(' ')
                   and not s.startswith('closed-branches ')]
    return result

all_heads = heads("--closed")
opened_heads = heads("")

closed_heads = [s for s in all_heads if s not in opened_heads]

if not closed_heads:
    print >> sys.stderr, 'no dangling closed heads.'
    sys.exit()

# ____________________________________________________________

closed_heads = sorted(set(closed_heads))

for branch_head in closed_heads:
    branch, head = branch_head.split()
    print '\t', branch
print
print 'The branches listed above will be merged to "closed-branches".'
print 'You need to run this script in a clean working copy where you'
print 'don''t mind all files being removed.'
print
if raw_input('Continue? [y/n] ').upper() != 'Y':
    sys.exit(1)

# ____________________________________________________________

def do(cmd):
    print cmd
    err = os.system(cmd)
    if err != 0:
        print '*** error %r' % (err,)
        sys.exit(1)

for branch_head in closed_heads:
    branch, head = branch_head.split()
    print
    print '***** %s ***** %s *****' % (branch, head)
    do("hg up --clean closed-branches")
    do("hg --config extensions.purge= purge --all")
    do("hg merge -y %s" % head)
    for fn in os.listdir('.'):
        if fn.lower() != '.hg':
            do("rm -fr -- '%s'" % fn)
            do("hg rm --after -- '%s' || true" % fn)
    do("hg ci -m'Merge closed head %s on branch %s'" % (head, branch))

print
do("hg ci --close-branch -m're-close this branch'")
do("hg up default")
