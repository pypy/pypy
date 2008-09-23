package pypy;

// This class is used as the superclass of RPython's
// exception.Exception class.  We use this rather than Throwable
// because it makes it easy to catch RPython exceptions in our
// automated tests (just catch any PyPyThrowable instance)
public class PyPyThrowable extends Throwable
{}