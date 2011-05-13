
""" Some support code
"""

import re, sys, os, subprocess

def detect_number_of_processors(filename_or_file='/proc/cpuinfo'):
    if os.environ.get('MAKEFLAGS'):
        return 1    # don't override MAKEFLAGS.  This will call 'make' without any '-j' option
    if sys.platform == 'darwin':
        return darwin_get_cpu_count()
    elif sys.platform != 'linux2':
        return 1    # implement me
    try:
        if isinstance(filename_or_file, str):
            f = open(filename_or_file, "r")
        else:
            f = filename_or_file
        count = max([int(re.split('processor.*(\d+)', line)[1])
                    for line in f.readlines()
                    if line.startswith('processor')]) + 1
        if count >= 4:
            return max(count // 2, 3)
        else:
            return count
    except:
        return 1 # we really don't want to explode here, at worst we have 1

def darwin_get_cpu_count(cmd = "/usr/sbin/sysctl hw.ncpu"):
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        # 'hw.ncpu: 20'
        count = proc.communicate()[0].rstrip()[8:]
        return int(count)
    except (OSError, ValueError):
        return 1
