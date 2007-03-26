#!/usr/bin/env python

import autopath
from pypy.tool.build import config
from pypy.tool.build.compile import main, getrequest

request, foreground = getrequest(config)
main(config, request, foreground)
