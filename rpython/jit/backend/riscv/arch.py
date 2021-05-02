#!/usr/bin/env python

import sys

assert sys.maxint == (2**63 - 1)

# General purpose register width (in bytes)
XLEN = 8

# Floating point register width (in bytes)
FLEN = 8  # Assume "Standard Extension for Double 'D'" is available.
