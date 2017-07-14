import os
import urllib2, py
from os.path import join


def github_raw_file(repo, path, branch='master'):
    return "https://raw.githubusercontent.com/{repo}/{branch}/{path}".format(**dict(
                repo=repo, path=path, branch=branch
            ))


def test_same_file():
    for root, dirs, files in os.walk('rpython/rlib/rvmprof/src/shared'):
        for file in files:
            if not (file.endswith(".c") or file.endswith(".h")):
                continue
            url = github_raw_file("vmprof/vmprof-python", "src/%s" % file)
            source = urllib2.urlopen(url).read()
            #
            dest = py.path.local(join(root, file)).read()
            if source != dest:
                raise AssertionError("%s was updated, but changes were"
                                     "not copied over to PyPy" % url)
            else:
                print("%s matches" % url)
        break # do not walk dirs
