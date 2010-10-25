#!/usr/bin/env python
import os
import sys

os.system('objdump -D --architecture=arm --target=binary %s' % sys.argv[1])
