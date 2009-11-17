from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = 'cx_Oracle'

    interpleveldefs = {
        'connect': 'interp_connect.W_Connection',
        'UNICODE': 'interp_variable.VT_NationalCharString',
        'NUMBER': 'interp_variable.VT_Float',
        'STRING': 'interp_variable.VT_String',
        'DATETIME': 'interp_variable.VT_DateTime',
        'Variable': 'interp_variable.W_Variable',
    }

    appleveldefs = {
        'version': 'app_oracle.version',
        'makedsn': 'app_oracle.makedsn',
        'TimestampFromTicks': 'app_oracle.TimestampFromTicks',
    }
    for name in """DataError DatabaseError Error IntegrityError InterfaceError
                   InternalError NotSupportedError OperationalError
                   ProgrammingError Warning""".split():
        appleveldefs[name] = "app_oracle.%s" % (name,)

