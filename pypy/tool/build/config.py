import py

packageparent = py.magic.autopath().dirpath().dirpath().dirpath().dirpath()

# general settings, used by both server and client
server = 'codespeak.net'
port = 12321
testport = 32123
path = [str(packageparent)]

# options for webserver
webserver = ''
vhostroot = ''
webport = 8080

# configuration of options for client and startcompile
from pypy.config.config import Config

# system config, on the client everything is set by scanning the system, when
# calling startcompile defaults are taken from the system, overrides are
# possible using cmdline args
from systemoption import system_optiondescription
system_config = Config(system_optiondescription)

# compile option config, used by client to parse info, by startcompile for 
# cmdline args, defaults are taken from the optiondescription
from pypy.config.pypyoption import get_pypy_config
compile_config = get_pypy_config()
compile_config.override({'translation.backend': 'c',
                         'translation.gc': 'boehm'})

# svn path and revision, etc.
from pypy.tool.build.tooloption import tool_optiondescription
tool_config = Config(tool_optiondescription)

# settings for the server
projectname = 'pypy'
buildpath = packageparent.ensure('/pypy/tool/build/builds', dir=True)
mailhost = 'localhost'
mailport = 25
mailfrom = 'guido@codespeak.net'

# settings for the tests
testpath = [str(py.magic.autopath().dirpath().dirpath().dirpath().dirpath())]

# this var is only used below
svnroot = 'http://codespeak.net/svn/pypy'

# when considering a compile job, the checkers below will be called (with
# request as only arg), if one of them returns False the compilation will
# not be accepted
def check_svnroot(req):
    if not req.svnurl.startswith(svnroot):
        return False
    return True

client_checkers = [check_svnroot]

# function to turn SVN paths into full URLs
def svnpath_to_url(p):
    root = svnroot
    if root.endswith('/'):
        root = root[:-1]
    return '%s/%s' % (root, p)

# create an URL from a path, the URL is used in emails
def path_to_url(p):
    return 'http://codespeak.net/pypy/%s/data.zip' % (
                p.relto(py.magic.autopath().dirpath()),)

# this should contain the dotted name of the package where 'config'
# can be found on the metaserver (used for remote imports)
configpath = 'pypy.tool.build.config'

