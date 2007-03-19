#!/usr/bin/env python

import autopath
from pypy.tool.build import config
from pypy.tool.build.compile import main, getrequest
from py.execnet import SshGateway, PopenGateway

request, foreground = getrequest(config)
main(config, request, foreground)
