import os
import py

if os.name == 'nt':
    py.test.skip('sandbox not supported on windows', allow_module_level=True)
