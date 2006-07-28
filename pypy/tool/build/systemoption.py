import py
from pypy.config.config import OptionDescription, BoolOption, IntOption
from pypy.config.config import ChoiceOption, to_optparse, Config

import sys
system_optiondescription = OptionDescription('system', [
    ChoiceOption('maxint', 'maximum int value in bytes (32/64)', ['32', '64'],
                    sys.maxint, '-i --maxint'),
    ChoiceOption('byteorder', 'endianness, byte order (little/big)', 
                    sys.byteorder, ['little', 'big'], '-b --byteorder'),
])
