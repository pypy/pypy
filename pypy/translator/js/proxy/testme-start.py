#!/usr/bin/python
import pkg_resources
pkg_resources.require("TurboGears")

import cherrypy
from os.path import *
import sys

# first look on the command line for a desired config file,
# if it's not on the command line, then
# look for setup.py in this directory. If it's not there, this script is
# probably installed
if len(sys.argv) > 1:
    cherrypy.config.update(file=sys.argv[1])
elif exists(join(dirname(__file__), "setup.py")):
    cherrypy.config.update(file="dev.cfg")
else:
    cherrypy.config.update(file="prod.cfg")

from testme.controllers import Root

cherrypy.root = Root()
cherrypy.server.start()
