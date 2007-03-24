# this is a sketch of how one might one day be able to define a pretty simple
# ctypes-using module, suitable for feeding to the ext-compiler

from pypy.interpreter.mixedmodule import MixedModule

# XXX raw_input needs to check for space.readline_func and use
# it if its there 

class Module(MixedModule):
    """Importing this module enables command line editing using GNU readline."""
    # the above line is the doc string of the translated module  

    def setup_after_space_initialization(self):
        from pypy.module.readline import c_readline 
        c_readline.setup_readline(self.space, self)

    interpleveldefs = {
        'readline'    : 'interp_readline.readline',
    }

    appleveldefs = {
        'parse_and_bind':     'app_stub.stub',
        'get_line_buffer':    'app_stub.stub_str',
        'insert_text':        'app_stub.stub',
        'read_init_file':     'app_stub.stub',
        'read_history_file':  'app_stub.stub',
        'write_history_file': 'app_stub.stub',
        'clear_history':      'app_stub.stub',
        'get_history_length': 'app_stub.stub_int',
        'set_history_length': 'app_stub.stub',
        'get_current_history_length': 'app_stub.stub_int',
        'get_history_item':           'app_stub.stub_str',
        'remove_history_item':        'app_stub.stub',
        'replace_history_item':       'app_stub.stub',
        'redisplay':                  'app_stub.stub',
        'set_startup_hook':           'app_stub.stub',
        'set_pre_input_hook':         'app_stub.stub',
        'set_completer':      'app_stub.stub',
        'get_completer':      'app_stub.stub',
        'get_begidx':         'app_stub.stub_int',
        'get_endidx':         'app_stub.stub_int',
        'set_completer_delims':       'app_stub.stub',
        'get_completer_delims':       'app_stub.stub_str',
        'add_history':        'app_stub.stub',
    }
