from pypy.interpreter.gateway import unwrap_spec

@unwrap_spec(unicode='text')
def formatter_parser(space, unicode):
    from pypy.objspace.std.newformat import unicode_template_formatter
    tformat = unicode_template_formatter(space, unicode)
    return tformat.formatter_parser()

@unwrap_spec(unicode='text')
def formatter_field_name_split(space, unicode):
    from pypy.objspace.std.newformat import unicode_template_formatter
    tformat = unicode_template_formatter(space, unicode)
    return tformat.formatter_field_name_split()

