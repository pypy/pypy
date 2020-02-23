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

def get_merged_branches(path, startrev, endrev, current_branch=None):
    errcode, wc_branch = getstatusoutput('hg branch')
    if errcode != 0:
        py.test.skip('no Mercurial repo')
    if current_branch is None:
        current_branch = wc_branch

    # X = take all the merges which are descendants of startrev and are on default
    # revset = all the parents of X which are not on default
    # ===>
    # revset contains all the branches which have been merged to default since
    # startrev
    revset = "parents(%s::%s and \
                      merge() and \
                      branch('%s')) and \
              not branch('%s')" % (startrev, endrev,
                                   current_branch, current_branch)
    cmd = r'hg log -R "%s" -r "%s" --template "{branches}\n"' % (path, revset)
    out = getoutput(cmd)
    branches = set()
    for item in out.splitlines():
        item = item.strip()
        if not item.startswith('release-'):
            branches.add(item)
    branches.discard("default")
    return branches, current_branch


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
    branches, _ = get_merged_branches(ROOT, 'f34f0c11299f', '79770e0c2f93',
                                      'default')
    assert branches == set(['numpy-indexing-by-arrays-bool',
                            'better-jit-hooks-2',
                            'numpypy-ufuncs'])

def test_whatsnew():
    doc = ROOT.join('pypy', 'doc')
    #whatsnew_list = doc.listdir('whatsnew-*.rst')
    #whatsnew_list.sort()
    #last_whatsnew = whatsnew_list[-1].read()
    last_whatsnew = doc.join('whatsnew-head.rst').read()
    startrev, documented = parse_doc(last_whatsnew)
    merged, branch = get_merged_branches(ROOT, startrev, '')
    merged.discard('default')
    merged.discard('')
    not_documented = merged.difference(documented)
    not_merged = documented.difference(merged)
    print 'Branches merged but not documented:'
    print '\n'.join(not_documented)
    print
    print 'Branches documented but not merged:'
    print '\n'.join(not_merged)
    print
    assert not not_documented
    if branch == 'default':
        assert not not_merged
    else:
        assert branch in documented, 'Please document this branch before merging: %s' % branch

def test_startrev_on_default():
    doc = ROOT.join('pypy', 'doc')
    last_whatsnew = doc.join('whatsnew-head.rst').read()
    startrev, documented = parse_doc(last_whatsnew)
    errcode, wc_branch = getstatusoutput(
        "hg log -r %s --template '{branch}'" % startrev)
    if errcode != 0:
        py.test.skip('no Mercurial repo')
    assert wc_branch in ('default', "'default'") # sometimes the ' leaks (windows)
