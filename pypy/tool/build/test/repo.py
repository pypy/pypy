import py

def create_temp_repo(reponame):
    t = py.test.ensuretemp('build-svnrepo')
    repo = t.join(reponame)
    ret = py.std.os.system('svnadmin create %r' % (str(repo),))
    if ret:
        py.test.skip('could not create temporary svn repository')
    return py.path.svnurl('file://%s' % (repo,))

