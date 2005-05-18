#
#   Pyrex -- Things that don't belong
#            anywhere else in particular
#

import os, sys

def replace_suffix(path, newsuf):
    base, _ = os.path.splitext(path)
    return base + newsuf
    
def default_open_new_file(path):
    return open(path, "w")

if sys.platform == "mac":
    from Pyrex.Mac.MacUtils import open_new_file
else:
    open_new_file = default_open_new_file

