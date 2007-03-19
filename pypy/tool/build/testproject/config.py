import py

packageparent = py.magic.autopath().dirpath().dirpath().dirpath().dirpath().dirpath()

# general settings, used by both server and client
server = 'localhost'
port = 23432
testport = 43234
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
from compileoption import compile_optiondescription
compile_config = Config(compile_optiondescription)

from tooloption import tool_optiondescription
tool_config = Config(tool_optiondescription)

# settings for the server
projectname = 'testproject'
buildpath = packageparent.ensure('/pypy/tool/build/testproject/builds',
                                 dir=True)
mailhost = 'localhost'
mailport = 25
mailfrom = 'guido@codespeak.net'

# this var is only used below
svnroot = 'http://codespeak.net/svn/pypy/dist/pypy/tool/build/testproject'

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
    return 'http://localhost/testproject/%s/data.zip' % (
                p.relto(py.magic.autopath().dirpath()),)

configpath = 'pypy.tool.build.testproject.config'

