import py
import pypy
from commands import getoutput, getstatusoutput
ROOT = py.path.local(pypy.__file__).dirpath().dirpath()


def parse_doc(s):
    startrev = None
    branches = set()
    def parseline(line):
        _, value = line.split(':', 1)
        return value.strip()
    #
    for line in s.splitlines():
        if line.startswith('.. startrev:'):
            startrev = parseline(line)
        elif line.startswith('.. branch:'):
            branches.add(parseline(line))
    branches.discard('default')
    return startrev, branches

def get_merged_branches(path, startrev, endrev):
    if getstatusoutput('hg root')[0]:
        py.test.skip('no Mercurial repo')

    # X = take all the merges which are descendants of startrev and are on default
    # revset = all the parents of X which are not on default
    # ===>
    # revset contains all the branches which have been merged to default since
    # startrev
    revset = 'parents(%s::%s and \
                      merge() and \
                      branch(default)) and \
              not branch(default)' % (startrev, endrev)
    cmd = r'hg log -R "%s" -r "%s" --template "{branches}\n"' % (path, revset)
    out = getoutput(cmd)
    branches = set(map(str.strip, out.splitlines()))
    return branches


def test_parse_doc():
    s = """
=====
Title
=====

.. startrev: 12345

bla bla bla bla

.. branch: foobar

xxx yyy zzz

.. branch: hello

qqq www ttt

.. branch: default

"default" should be ignored and not put in the set of documented branches
"""
    startrev, branches = parse_doc(s)
    assert startrev == '12345'
    assert branches == set(['foobar', 'hello'])

def test_get_merged_branches():
    branches = get_merged_branches(ROOT, 'f34f0c11299f', '79770e0c2f93')
    assert branches == set(['numpy-indexing-by-arrays-bool',
                            'better-jit-hooks-2',
                            'numpypy-ufuncs'])

def test_whatsnew():
    doc = ROOT.join('pypy', 'doc')
    whatsnew_list = doc.listdir('whatsnew-*.rst')
    whatsnew_list.sort()
    last_whatsnew = whatsnew_list[-1].read()
    startrev, documented = parse_doc(last_whatsnew)
    merged = get_merged_branches(ROOT, startrev, '')
    not_documented = merged.difference(documented)
    not_merged = documented.difference(merged)
    print 'Branches merged but not documented:'
    print '\n'.join(not_documented)
    print
    print 'Branches documented but not merged:'
    print '\n'.join(not_merged)
    print
    assert not not_documented and not not_merged
