package pypy;

// This class is used as the superclass of RPython's
// exception.Exception class.  We use this rather than Throwable
// because it makes it easy to catch RPython exceptions in our
// automated tests (just catch any PyPyThrowable instance)
public class PyPyThrowable extends Throwable
{
    // set the property pypy.keep.stack.trace if you want it:
    public static final boolean pypyStackTrace =
        Boolean.valueOf(System.getProperty("pypy.keep.stack.trace", "false"));
        
    // we don't use this in PyPy, so just do nothing:
    public Throwable fillInStackTrace() {
        if (pypyStackTrace)
            return super.fillInStackTrace();
        return this;
    }
}