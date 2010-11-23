
""" Some support code
"""

import re

def detect_number_of_processors(filename_or_file='/proc/cpuinfo'):
    try:
        if isinstance(filename_or_file, str):
            f = open(filename_or_file, "r")
        else:
            f = filename_or_file
        return max([int(re.split('processor.*(\d+)', line)[1])
                    for line in f.readlines()
                    if line.startswith('processor')]) + 1
    except:
        return 1 # we really don't want to explode here, at worst we have 1
