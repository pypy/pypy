import os
import urllib2, py
from os.path import join

RVMPROF = py.path.local(__file__).join('..', '..')

def github_raw_file(repo, path, branch='master'):
    return "https://raw.githubusercontent.com/{repo}/{branch}/{path}".format(**dict(
                repo=repo, path=path, branch=branch
            ))


def test_same_file():
    shared = RVMPROF.join('src', 'shared')
    files = shared.listdir('*.[ch]')
    assert files, 'cannot find any C file, probably the directory is wrong?'
    no_matches = []
    print
    for file in files:
        url = github_raw_file("vmprof/vmprof-python", "src/%s" % file.basename)
        source = urllib2.urlopen(url).read()
        dest = file.read()
        shortname = file.relto(RVMPROF)
        if source == dest:
            print '%s matches' % shortname
        else:
            print '%s does NOT match' % shortname
            no_matches.append(file)
    #
    if no_matches:
        print
        print 'The following file dit NOT match'
        for f in no_matches:
            print '   ', f.relto(RVMPROF)
        raise AssertionError("some files were updated on github, "
                             "but were not copied here")
