from pypy.interpreter.gateway import unwrap_spec, WrappedDefault
from pypy.interpreter.error import OperationError, oefmt

def create_filter(space, w_category, action):
    return space.newtuple([
        space.wrap(action), space.w_None, w_category,
        space.w_None, space.wrap(0)])

class State:
    def __init__(self, space):
        self.init_filters(space)
        self.w_once_registry = space.newdict()
        self.w_default_action = space.wrap("default")
        self.filters_mutated(space)

    def filters_mutated(self, space):
        self.w_filters_version = space.call_function(space.w_object)

    def init_filters(self, space):
        filters_w = []

        filters_w.append(create_filter(
            space, space.w_DeprecationWarning, "ignore"))
        filters_w.append(create_filter(
            space, space.w_PendingDeprecationWarning, "ignore"))
        filters_w.append(create_filter(
            space, space.w_ImportWarning, "ignore"))

        bytes_warning = space.sys.get_flag('bytes_warning')
        if bytes_warning > 1:
            action = "error"
        elif bytes_warning == 0:
            action = "ignore"
        else:
            action = "default"
        filters_w.append(create_filter(
            space, space.w_BytesWarning, action))

        # note: in CPython, resource usage warnings are enabled by default
        # in pydebug mode
        filters_w.append(create_filter(
            space, space.w_ResourceWarning, "ignore"))

        self.w_filters = space.newlist(filters_w)

def get_warnings_attr(space, name):
    try:
        w_module = space.getitem(space.sys.get('modules'),
                                 space.wrap('warnings'))
    except OperationError as e:
        if not e.match(space, space.w_KeyError):
            raise
        return None

    try:
        return space.getattr(w_module, space.wrap(name))
    except OperationError as e:
        if not e.match(space, space.w_AttributeError):
            raise
    return None

def get_category(space, w_message, w_category):
    # Get category
    if space.isinstance_w(w_message, space.w_Warning):
        w_category = space.type(w_message)
    elif space.is_none(w_category):
        w_category = space.w_UserWarning

    # Validate category
    try:
        if not space.abstract_issubclass_w(w_category, space.w_Warning):
            raise oefmt(space.w_TypeError,
                        "category is not a subclass of Warning")
    except OperationError as e:
        if e.async(space):
            raise
        raise oefmt(space.w_TypeError,
                    "category must be a Warning subclass, not '%T'",
                    w_category)

    return w_category

def is_internal_frame(space, frame):
    if frame is None:
        return False
    code = frame.getcode()
    if code is None or code.co_filename is None:
        return False
    # XXX XXX HAAAACK copied directly from CPython, which I'm particularly
    # unhappy about, but I can't do anything more than say "bah"
    return "importlib" in code.co_filename and "_bootstrap" in code.co_filename

def next_external_frame(space, frame):
    ec = space.getexecutioncontext()
    while True:
        frame = ec.getnextframe_nohidden(frame)
        if frame is None or not is_internal_frame(space, frame):
            return frame

def setup_context(space, stacklevel):
    # Setup globals and lineno
    ec = space.getexecutioncontext()

    # Direct copy of CPython's logic, which has grown its own notion of
    # "internal frames".  xxx not sure I understand this logic.
    frame = ec.gettopframe_nohidden()
    if stacklevel <= 0 or is_internal_frame(space, frame):
        while stacklevel > 1 and frame:
            frame = ec.getnextframe_nohidden(frame)
            stacklevel -= 1
    else:
        while stacklevel > 1 and frame:
            frame = next_external_frame(space, frame)
            stacklevel -= 1

    if frame:
        w_globals = frame.get_w_globals()
        lineno = frame.get_last_lineno()
    else:
        w_globals = space.sys.w_dict
        lineno = 1

    # setup registry
    try:
        w_registry = space.getitem(w_globals, space.wrap("__warningregistry__"))
    except OperationError as e:
        if not e.match(space, space.w_KeyError):
            raise
        w_registry = space.newdict()
        space.setitem(w_globals, space.wrap("__warningregistry__"), w_registry)

    # setup module
    try:
        w_module = space.getitem(w_globals, space.wrap("__name__"))
    except OperationError as e:
        if not e.match(space, space.w_KeyError):
            raise
        w_module = space.wrap("<string>")

    # setup filename
    try:
        w_filename = space.getitem(w_globals, space.wrap("__file__"))
        filename = space.fsencode_w(w_filename)
    except OperationError as e:
        if space.str_w(w_module) == '__main__':
            w_argv = space.sys.getdictvalue(space, 'argv')
            if w_argv and space.len_w(w_argv) > 0:
                w_filename = space.getitem(w_argv, space.wrap(0))
                if not space.is_true(w_filename):
                    w_filename = space.wrap('__main__')
            else:
                # embedded interpreters don't have sys.argv
                w_filename = space.wrap('__main__')
        else:
            w_filename = w_module
    else:
        lc_filename = filename.lower()
        if lc_filename.endswith(".pyc"):
            # strip last character
            w_filename = space.fsdecode(space.newbytes(filename[:-1]))

    return (w_filename, lineno, w_module, w_registry)

def check_matched(space, w_obj, w_arg):
    if space.is_w(w_obj, space.w_None):
        return True
    return space.is_true(space.call_method(w_obj, "match", w_arg))

def get_filter(space, w_category, w_text, lineno, w_module):
    w_filters = get_warnings_attr(space, "filters")
    if w_filters:
        space.fromcache(State).w_filters = w_filters
    else:
        w_filters = space.fromcache(State).w_filters

    # filters could change while we are iterating over it
    for w_item in space.fixedview(w_filters):
        w_action, w_msg, w_cat, w_mod, w_lineno = space.fixedview(
            w_item, 5)
        ln = space.int_w(w_lineno)

        if (check_matched(space, w_msg, w_text) and
            check_matched(space, w_mod, w_module) and
            space.abstract_issubclass_w(w_category, w_cat) and
            (ln == 0 or ln == lineno)):
            return space.str_w(w_action), w_item

    action = get_default_action(space)
    if not action:
        raise oefmt(space.w_ValueError, "warnings.defaultaction not found")
    return action, None

def get_default_action(space):
    w_action = get_warnings_attr(space, "defaultaction");
    if w_action is None:
        return space.str_w(space.fromcache(State).w_default_action)

    space.fromcache(State).w_default_action = w_action
    return space.str_w(w_action)

def get_once_registry(space):
    w_registry = get_warnings_attr(space, "onceregistry");
    if w_registry is None:
        return space.fromcache(State).w_once_registry

    space.fromcache(State).w_once_registry = w_registry
    return w_registry

def update_registry(space, w_registry, w_text, w_category):
    w_key = space.newtuple([w_text, w_category])
    return already_warned(space, w_registry, w_key, should_set=True)

def already_warned(space, w_registry, w_key, should_set=False):
    w_version_obj = space.finditem_str(w_registry, "version")
    state = space.fromcache(State)
    if w_version_obj is not state.w_filters_version:
        space.call_method(w_registry, "clear")
        space.setitem_str(w_registry, "version", state.w_filters_version)
    else:
        w_already_warned = space.finditem(w_registry, w_key)
        if w_already_warned is not None and space.is_true(w_already_warned):
            return True
    # This warning wasn't found in the registry, set it.
    if should_set:
        space.setitem(w_registry, w_key, space.w_True)
    return False

def normalize_module(space, w_filename):
    filename = space.identifier_w(w_filename)
    if len(filename) == 0:
        return space.wrap("<unknown>")
    if filename.endswith(".py"):
        n = len(filename) - 3
        assert n >= 0
        filename = filename[:n]
        return space.newutf8(filename)
    return w_filename

def show_warning(space, w_filename, lineno, w_text, w_category,
                 w_sourceline=None):
    w_name = space.getattr(w_category, space.wrap("__name__"))
    w_stderr = space.sys.get("stderr")

    # Print "filename:lineno: category: text\n"
    message = u"%s:%d: %s: %s\n" % (space.unicode_w(w_filename), lineno,
                                    space.unicode_w(w_name),
                                    space.unicode_w(w_text))
    space.call_method(w_stderr, "write", space.newunicode(message))

    # Print "  source_line\n"
    if not w_sourceline:
        try:
            # sourceline = linecache.getline(filename, lineno).strip()
            w_builtins = space.getbuiltinmodule('builtins')
            w_linecachemodule = space.call_method(w_builtins, '__import__',
                                                  space.wrap("linecache"))
            w_sourceline = space.call_method(w_linecachemodule, "getline",
                                             w_filename, space.wrap(lineno))
            w_sourceline = space.call_method(w_sourceline, "strip")
        except OperationError:
            w_sourceline = None

    if not w_sourceline:
        return
    line = space.unicode_w(w_sourceline)
    if not line:
        return

    message = u"\n"
    for i in range(len(line)):
        c = line[i]
        if c not in u' \t\014':
            message = u"  %s\n" % (line[i:],)
            break
    space.call_method(w_stderr, "write", space.newunicode(message))

def do_warn(space, w_message, w_category, stacklevel):
    context_w = setup_context(space, stacklevel)
    do_warn_explicit(space, w_category, w_message, context_w)

def do_warn_explicit(space, w_category, w_message, context_w,
                     w_sourceline=None):
    w_filename, lineno, w_module, w_registry = context_w

    # normalize module
    if space.is_w(w_module, space.w_None):
        w_module = normalize_module(space, w_filename)

    # normalize message
    if space.isinstance_w(w_message, space.w_Warning):
        w_text = space.str(w_message)
        w_category = space.type(w_message)
    elif (not space.isinstance_w(w_message, space.w_unicode) or
          not space.isinstance_w(w_message, space.w_str)):
        w_text = space.str(w_message)
        w_message = space.call_function(w_category, w_message)
    else:
        w_text = w_message
        w_message = space.call_function(w_category, w_message)

    w_lineno = space.wrap(lineno)

    # create key
    w_key = space.newtuple([w_text, w_category, w_lineno])

    if not space.is_w(w_registry, space.w_None):
        if already_warned(space, w_registry, w_key):
            return
        # else this warning hasn't been generated before

    action, w_item = get_filter(space, w_category, w_text, lineno, w_module)

    if action == "error":
        raise OperationError(w_category, w_message)

    # Store in the registry that we've been here, *except* when the action is
    # "always".
    warned = False
    if action != 'always':
        if not space.is_w(w_registry, space.w_None):
            space.setitem(w_registry, w_key, space.w_True)
        if action == 'ignore':
            return
        elif action == 'once':
            if space.is_w(w_registry, space.w_None):
                w_registry = get_once_registry(space)
            warned = update_registry(space, w_registry, w_text, w_category)
        elif action == 'module':
            if not space.is_w(w_registry, space.w_None):
                warned = update_registry(space, w_registry, w_text, w_category)
        elif action != 'default':
            try:
                err = space.str_w(space.str(w_item))
            except OperationError:
                err = "???"
            raise oefmt(space.w_RuntimeError,
                        "Unrecognized action (%s) in warnings.filters:\n %s",
                        action, err)

    if warned:
        # Already warned for this module
        return
    w_show_fxn = get_warnings_attr(space, "showwarning")
    if w_show_fxn is None:
        show_warning(space, w_filename, lineno, w_text, w_category,
                     w_sourceline)
    else:
        space.call_function(
            w_show_fxn, w_message, w_category, w_filename, w_lineno)

@unwrap_spec(stacklevel=int)
def warn(space, w_message, w_category=None, stacklevel=1):
    "Issue a warning, or maybe ignore it or raise an exception."
    w_category = get_category(space, w_message, w_category);
    do_warn(space, w_message, w_category, stacklevel)


def get_source_line(space, w_globals, lineno):
    if space.is_none(w_globals):
        return None

    # Check/get the requisite pieces needed for the loader.
    try:
        w_loader = space.getitem(w_globals, space.wrap("__loader__"))
        w_module_name = space.getitem(w_globals, space.wrap("__name__"))
    except OperationError as e:
        if not e.match(space, space.w_KeyError):
            raise
        return None

    # Make sure the loader implements the optional get_source() method.
    try:
        w_get_source = space.getattr(w_loader, space.wrap("get_source"))
    except OperationError as e:
        if not e.match(space, space.w_AttributeError):
            raise
        return None

    # Call get_source() to get the source code.
    w_source = space.call_function(w_get_source, w_module_name)
    if space.is_w(w_source, space.w_None):
        return None

    # Split the source into lines.
    w_source_list = space.call_method(w_source, "splitlines")

    # Get the source line.
    w_source_line = space.getitem(w_source_list, space.wrap(lineno - 1))
    return w_source_line

@unwrap_spec(lineno=int, w_module = WrappedDefault(None),
             w_registry = WrappedDefault(None),
             w_module_globals = WrappedDefault(None))
def warn_explicit(space, w_message, w_category, w_filename, lineno,
                  w_module=None, w_registry=None, w_module_globals=None):
    "Low-level inferface to warnings functionality."

    w_source_line = get_source_line(space, w_module_globals, lineno)

    do_warn_explicit(space, w_category, w_message,
                     (w_filename, lineno, w_module, w_registry),
                     w_source_line)

def filters_mutated(space):
    space.fromcache(State).filters_mutated(space)
