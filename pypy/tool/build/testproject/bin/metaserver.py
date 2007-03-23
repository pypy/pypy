#!/usr/bin/env python

import autopath
from pypy.tool.build.testproject import config
from pypy.tool.build.metaserver import main

print 'buildpath:', config.buildpath

main(config)

