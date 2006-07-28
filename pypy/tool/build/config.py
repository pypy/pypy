import py

packageparent = py.magic.autopath().dirpath().dirpath().dirpath().dirpath()

# general settings, used by both server and client
server = 'localhost'
port = 12321
path = [str(packageparent)]

# configuration of options for client and startcompile
from pypy.config.config import Config, to_optparse

# system config, on the client everything is set by scanning the system, when
# calling startcompile defaults are taken from the system, overrides are
# possible using cmdline args
from systemoption import system_optiondescription
system_config = Config(system_optiondescription)

# compile option config, used by client to parse info, by startcompile for 
# cmdline args, defaults are taken from the optiondescription
from pypy.config.pypyoption import pypy_optiondescription
compile_config = Config(pypy_optiondescription)

# settings for the server
projectname = 'pypy'
buildpath = packageparent.join('/pypy/tool/build/builds')
mailhost = '127.0.0.1'
mailport = 25
mailfrom = 'johnny@johnnydebris.net'

# settings for the tests
testpath = [str(py.magic.autopath().dirpath().dirpath())] 

