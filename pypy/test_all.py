#! /usr/bin/env python

import tool.autopath
from pypy.tool import testit

if __name__ == '__main__':
    testit.main(tool.autopath.pypydir)

