package pypy;

import java.io.*;
import java.util.HashMap;
import java.util.ArrayList;
import java.util.Map;

abstract class FileWrapper
{
    public abstract void write(String buffer);
    public abstract String read(int count);
}

class PrintStreamWrapper extends FileWrapper
{
    private PrintStream stream;

    public PrintStreamWrapper(PrintStream stream)
    {
        this.stream = stream;
    }

    public void write(String buffer)
    {
        this.stream.print(buffer);
    }

    public String read(int count)
    {
        ll_os.throwOSError(PyPy.EBADF, "Write-only fd");
        return null; // never reached
    }
}

class InputStreamWrapper extends FileWrapper
{
    private InputStream stream;

    public InputStreamWrapper(InputStream stream)
    {
        this.stream = stream;
    }

    public void write(String buffer)
    {
        ll_os.throwOSError(PyPy.EBADF, "Read-only fd");
    }

    public String read(int count)
    {
        try {
            byte[] buf = new byte[count];
            int n = stream.read(buf, 0, count);
            return new String(buf);
        }
        catch(IOException e) {
            ll_os.throwOSError(PyPy.EIO, e.getMessage());
            return null; // never reached
        }
    }
}


public class ll_os {

    // NB: these values are those used by Windows and they differs
    // from the Unix ones; the os module is patched with these
    // values before flowgraphing to make sure we get the very
    // same values on each platform we do the compilation.
    private static final int O_RDONLY = 0x0000;
    private static final int O_WRONLY = 0x0001;
    private static final int O_RDWR   = 0x0002;
    private static final int O_APPEND = 0x0008;
    private static final int O_CREAT  = 0x0100;
    private static final int O_TRUNC  = 0x0200;
    private static final int O_TEXT   = 0x4000;
    private static final int O_BINARY = 0x8000;
    
    private static final int S_IFMT = 61440;
    private static final int S_IFDIR = 16384;
    private static final int S_IFREG = 32768;

    private static Map<Integer, FileWrapper> FileDescriptors = new HashMap<Integer, FileWrapper>();
    private static Map<Integer, String> ErrorMessages = new HashMap<Integer, String>();

    static {
        FileDescriptors.put(new Integer(0), new PrintStreamWrapper(System.out));
        FileDescriptors.put(new Integer(1), new InputStreamWrapper(System.in));
        FileDescriptors.put(new Integer(2), new PrintStreamWrapper(System.err));
    }

    public static void throwOSError(int errno, String errText) {
        ErrorMessages.put(new Integer(errno), errText);
        PyPy.interlink.throwOSError(errno);
    }

    public static int ll_os_open(String name, int flags, int mode)
    {
        throwOSError(PyPy.ENOENT, "DUMMY ll_os_open");
        return -1;
    }

    public static StatResult ll_os_lstat(String path)
    {
        return ll_os_stat(path); // XXX
    }

    public static String ll_os_strerror(int errno)
    {
        String msg = ErrorMessages.remove(new Integer(errno));
        if (msg == null)
            return "errno: " + errno;
        else
            return msg;
    }

    public static int ll_os_write(int fd, String text) {
        FileWrapper f = FileDescriptors.get(new Integer(fd));
        if (f == null)
            throwOSError(PyPy.EBADF, "Invalid fd: " + fd);
        f.write(text);
        return text.length();
    }

    public static ArrayList ll_os_envitems()
    {
        return new ArrayList(); // XXX
    }

    public static String ll_os_getcwd()
    {
        return System.getProperty("user.dir");
    }

    public static StatResult ll_os_stat(String path)
    {
        if (path.equals(""))
            ll_os.throwOSError(PyPy.ENOENT, "No such file or directory: ''");

        File f = new File(path);
        
        if (f.exists()) {
            StatResult res = new StatResult();
            if (f.isDirectory())
                res.setMode(S_IFDIR);
            else {
                res.setMode(S_IFREG);
                res.setSize(f.length());
                res.setMtime((int)f.lastModified());
            }
            return res;
        }

        ll_os.throwOSError(PyPy.ENOENT, "No such file or directory: '"+path+"'");
        return null; // never reached
    }
}
