#
#   Pyrex - Command Line Parsing
#

import sys

usage = """\
Usage: pyrexc [options] sourcefile...
Options:
  -v, --version                  Display version number of pyrex compiler
  -l, --create-listing           Write error messages to a listing file
  -I, --include-dir <directory>  Search for include files in named directory
  -o, --output-file <filename>   Specify name of generated C file"""

def bad_usage():
    print >>sys.stderr, usage
    sys.exit(1)

def parse_command_line(args):
    from Pyrex.Compiler.Main import \
        CompilationOptions, default_options

    def pop_arg():
        if args:
            return args.pop(0)
        else:
            bad_usage()
    
    def get_param(option):
        tail = option[2:]
        if tail:
            return tail
        else:
            return pop_arg()

    options = CompilationOptions(default_options)
    sources = []
    while args:
        if args[0].startswith("-"):
            option = pop_arg()
            if option in ("-v", "--version"):
                options.show_version = 1
            elif option in ("-l", "--create-listing"):
                options.use_listing_file = 1
            elif option in ("-C", "--compile"):
                options.c_only = 0
            elif option in ("-X", "--link"):
                options.c_only = 0
                options.obj_only = 0
            elif option.startswith("-I"):
                options.include_path.append(get_param(option))
            elif option == "--include-dir":
                options.include_path.append(pop_arg())
            elif option in ("-o", "--output-file"):
                options.output_file = pop_arg()
            else:
                bad_usage()
        else:
            sources.append(pop_arg())
    if options.use_listing_file and len(sources) > 1:
        print >>sys.stderr, \
            "pyrexc: Only one source file allowed when using -o"
        sys.exit(1)
    return options, sources

