import sys
from rpython.rlib.objectmodel import we_are_translated, fetch_translated_config
from rpython.rlib.objectmodel import specialize
from rpython.rtyper.lltypesystem import lltype, rstr
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.annlowlevel import llhelper


def stop_point(n):
    if we_are_translated():
        if fetch_translated_config().translation.reverse_debugger:
            llop.revdb_stop_point(lltype.Void, n)

def register_debug_command(command, lambda_func):
    pass

def send_output(string):      # monkey-patch this for untranslated tests
    llop.revdb_send_output(lltype.Void, string)

def current_time():
    return llop.revdb_get_value(lltype.Signed, 'c')

def most_recent_fork():
    return llop.revdb_get_value(lltype.Signed, 'm')

def total_time():
    return llop.revdb_get_value(lltype.Signed, 't')

@specialize.arg(1)
def go_forward(time_delta, callback):
    ll_callback = llhelper(_CALLBACK_FNPTR, callback)
    llop.revdb_go_forward(lltype.Void, time_delta, ll_callback)
_CALLBACK_FNPTR = lltype.Ptr(lltype.FuncType([], lltype.Void))


class RegisterDebugCommand(ExtRegistryEntry):
    _about_ = register_debug_command

    def compute_result_annotation(self, s_command, s_lambda_func):
        from rpython.annotator import model as annmodel
        command = s_command.const
        lambda_func = s_lambda_func.const
        assert isinstance(command, str)
        t = self.bookkeeper.annotator.translator
        if t.config.translation.reverse_debugger:
            func = lambda_func()
            try:
                cmds = t.revdb_commands
            except AttributeError:
                cmds = t.revdb_commands = {}
            cmds[command] = func
            s_func = self.bookkeeper.immutablevalue(func)
            self.bookkeeper.emulate_pbc_call(self.bookkeeper.position_key,
                                             s_func, [annmodel.s_Str0])

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
