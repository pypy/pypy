package pypy;

import java.io.File;
import java.util.List;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Arrays;
import java.util.Map;
import java.text.DecimalFormat;
import java.lang.reflect.Array;

/**
 * Class with a number of utility routines.  One instance of this is
 * created by the PyPy entrypoint, and paired with an appropriate
 * interlink implementation.
 * 
 * I apologize for the Python-esque naming conventions, but it seems
 * I can't switch my mind to camelCase when working so closely with 
 * Python mere minutes before.
 *
 * In general, its methods should be virtual.  In some cases, however,
 * they are static because it is more expedient in the generated code
 * to not have to push the pypy instance before invoking the method.
 */
public class PyPy implements Constants {
    
    public final Interlink interlink;
    public final ll_os os;

    public PyPy(Interlink interlink) {
        this.interlink = interlink;
        this.os = new ll_os(interlink);
    }

    public final static long LONG_MAX = Long.MAX_VALUE;
    public final static long LONG_MIN = Long.MIN_VALUE;
    public final static int INT_MAX = Integer.MAX_VALUE;
    public final static int INT_MIN = Integer.MIN_VALUE;
    public final static double ULONG_MAX = 18446744073709551616.0;

    public static boolean int_between(int a, int b, int c) {
        return a <= b && b < c;
    }

    /** 
     * Compares two unsigned integers (value1 and value2) and returns
     * a value greater than, equal to, or less than zero if value 1 is
     * respectively greater than, equal to, or less than value2.  The
     * idea is that you can do the following:
     * 
     * Call uint_cmp(value1, value2)
     * IFLT ... // jumps if value1 < value2
     * IFEQ ... // jumps if value1 == value2
     * IFGT ... // jumps if value1 > value2
     * etc 
     */
    public static int uint_cmp(int value1, int value2) {
        final int VALUE1BIGGER = 1;
        final int VALUE2BIGGER = -1;
        final int EQUAL = 0;

        if (((value1 | value2) & Integer.MIN_VALUE) == 0) {
            // neither is negative, presumably the common case
            return value1 - value2;
        }

        if (value1 == value2)
            return EQUAL;

        if (value1 < 0) {
            if (value2 < 0) {
                // both are negative
                if (value1 > value2)
                    // example: value1 == -1 (0xFFFF), value2 == -2 (0xFFFE)
                    return VALUE1BIGGER;
                return VALUE2BIGGER;
            }
            else {
                // value1 is neg, value 2 is not
                return VALUE1BIGGER;
            }
        }

        // value1 is not neg, value2 is neg
        return VALUE2BIGGER;
    }

    public int uint_mod(int x, int y) {
        long lx = uint_to_long(x);
        long ly = uint_to_long(y);
        long lr = lx % ly;
        return long_to_uint(lr);
    }

    public int uint_mul(int x, int y)
    {
        long xx = uint_to_long(x);
        long yy = uint_to_long(y);
        return long_to_uint(xx * yy);
    }

    public int uint_div(int x, int y)
    {
        long xx = uint_to_long(x);
        long yy = uint_to_long(y);
        return long_to_uint(xx / yy);
    }
    
    public long ulong_shl(long x, long y) {
        int yi = (int)y;
        return x << yi;
    }

    public long ulong_mod(long x, long y) {
        double dx = ulong_to_double(x);
        try {
            double modulo = Math.IEEEremainder(dx, y);
            return (long)modulo;
        } catch (ArithmeticException e) {
            interlink.throwZeroDivisionError();
            return 0; // never reached
        }
    }

    public static int ulong_cmp(long value1, long value2) {
        final int VALUE2BIGGER = -1;
        final int VALUE1BIGGER = 1;
        final int EQUAL = 0;

        if (value1 == value2)
            return EQUAL;

        if (value1 < 0) {
            if (value2 < 0) {
                // both are negative
                if (value1 > value2)
                    // example: value1 == -1 (0xFFFF), value2 == -2 (0xFFFE)
                    return VALUE1BIGGER;
                return VALUE2BIGGER;
            }
            else {
                // value1 is neg, value 2 is not
                return VALUE1BIGGER;
            }
        }
        else if (value2 < 0) {
            // value1 is not neg, value2 is neg
            return VALUE2BIGGER;
        }
        
        if (value1 > value2)
            return VALUE1BIGGER;
        return VALUE2BIGGER;
    }

    public final double BITS16 = (double)0xFFFF;

    public static double uint_to_double(int value) {
        return (double)uint_to_long(value);
    }

    // XXX: broken if the value is too large
    public static double ulong_to_double(long value) {
        if (value >= 0)
            return value;
        else {
            return ULONG_MAX + value;
        }
    }

    public static long double_to_ulong(double value) {
        if (value < 0)
            return (long)(ULONG_MAX + value);
        else
            return (long)value;
    }
    
    public static int double_to_uint(double value) {
        if (value <= Integer.MAX_VALUE)
            return (int)value;
        return long_to_uint((long)value);
    }

    public static int long_to_uint(long value)
    {
        int loword = (int)(value & 0xFFFF);
        int hiword = (int)(value >>> 16);
        return (hiword << 16) | loword;
    }

    public static long uint_to_long(int value)
    {
        long loword = value & 0xFFFF;
        long hiword = value >>> 16;
        long res = (hiword << 16) | loword;
        return res;
    }

    public long double_to_long(double value)
    {
        //if (value <= LONG_MAX)
        //{
            return (long)value;
        //}
        //TODO: Add some logic here, but I don't think we'll need it
    }

    public long long_bitwise_negate(long value) {
        return ~value;
    }

    public int str_to_int(String s) {
        try {
            return Integer.parseInt(s);
        } catch (NumberFormatException fe) {
            throw new RuntimeException(fe);
        }
    }

    public int str_to_uint(String s) {
        try {
            long l = Long.parseLong(s);
            if (l < Integer.MAX_VALUE)
                return (int)l;
            int lowerword = (int)(l & 0xFFFF);
            int upperword = (int)(l >> 16);
            return lowerword + (upperword << 16);
        } catch (NumberFormatException fe) {
            throw new RuntimeException(fe);
        }
    }

    public long str_to_long(String s) {
        try {
            return Long.parseLong(s);
        } catch (NumberFormatException fe) {
            throw new RuntimeException(fe);
        }
    }

    public long str_to_ulong(String s) {
        long res = 0;
        s = s.trim();
        for(int i=0; i<s.length(); i++) {
            char ch = s.charAt(i);
            if (!Character.isDigit(ch))
                throw new RuntimeException("Invalid ulong: " + s);
            res = res*10 + Character.getNumericValue(ch);
        }
        return res;
    }

    public boolean str_to_bool(String s) {
        // not sure what are considered valid boolean values...
        // let's be very accepting and take both strings and numbers
        if (s.equalsIgnoreCase("true"))
            return true;
        if (s.equalsIgnoreCase("false"))
            return false;

        try {
            int i = Integer.parseInt(s);
            return i != 0;
        } catch (NumberFormatException ex) {
            throw new RuntimeException(ex);
        }
    }

    public double str_to_double(String s) {
        try {
            s = s.trim();
            if (s.equalsIgnoreCase("inf"))
                return Double.POSITIVE_INFINITY;
            else if (s.equalsIgnoreCase("-inf"))
                return Double.NEGATIVE_INFINITY;
            else if (s.equalsIgnoreCase("nan"))
                return Double.NaN;
            else
                return Double.parseDouble(s);
        } catch (NumberFormatException ex) {
            interlink.throwValueError();
            return 0.0;
        }
    }

    public double ooparse_float(String s) {
        try {
            return Double.parseDouble(s);
        } catch(NumberFormatException ex) {
            interlink.throwValueError();
            return 0.0; // not reached
        }
    }

    public char str_to_char(String s) {
        if (s.length() != 1)
            throw new RuntimeException("String not single character: '"+s+"'");
        return s.charAt(0);
    }

    public double bool_to_double(boolean b) { //This should be replaced with JASMIN code later
        double result;
        if (b)
            result = 1.0;
        else
            result = 0.0;
        return result;
    }

    // Used in testing the JVM backend:
    //
    //    A series of methods which serve a similar purpose to repr() in Python:
    //    they create strings that can be exec'd() to rebuild data structures.
    //    Also methods for writing to System.out.
    //
    //    These are static because they never throw exceptions etc, and it
    //    is more convenient that way.

    public static void dump(String text) {
        System.out.println(text);
    }

    public static String serialize_void() {
        return "None";
    }

    public static String serialize_uint(int i) {
        if (i >= 0)
            return Integer.toString(i);
        else 
            return Long.toString(uint_to_long(i));
    }

    public static String serialize_ulonglong(long value)
    {
        double d = ulong_to_double(value);
        DecimalFormat fmt = new DecimalFormat("0");
        return fmt.format(d);
    }

    public static String serialize_boolean(boolean l) {
        if (l)
            return "True";
        else
            return "False";
    }

    private static String format_char(char c) {
        String res = "\\x";
        if (c <= 0x0F) res = res + "0";
        res = res + Integer.toHexString(c);
        return res;
    }

    public static String escaped_char(char c) {
        return "'" + format_char(c) + "'";
    }

    public static String escaped_string(String b) {
        if (b == null)
            return "None";
        StringBuffer sb = new StringBuffer();
        sb.append('"');
        for (int i = 0; i < b.length(); i++) {
            char c = b.charAt(i);
            sb.append(format_char(c));
        }
        sb.append('"');
        return sb.toString();
    }

    private static String format_unichar(char c) {
        String res = "\\u";
        if (c <= 0xF)   res = res + "0";
        if (c <= 0xFF)  res = res + "0";
        if (c <= 0xFFF) res = res + "0";
        res = res + Integer.toHexString(c);
        return res;
    }

    public static String escaped_unichar(char c)
    {
        return "u'" + format_unichar(c) + "'";
    }

    public static String escaped_unicode(String b) {
        if (b == null)
            return "None";
        StringBuffer sb = new StringBuffer();
        sb.append("u'");
        for (int i = 0; i < b.length(); i++) {
            char c = b.charAt(i);
            sb.append(format_unichar(c));
        }
        sb.append("'");
        return sb.toString();
    }

    // used in running unit tests
    // not really part of the dump_XXX set of objects, hence the lack
    // of an indent parameter
    public static void dump_exc_wrapper(Object o) {
        String clnm = o.getClass().getName();
        StringBuffer sb = new StringBuffer();
        sb.append("ExceptionWrapper(");
        sb.append(escaped_string(clnm));
        sb.append(")");
        dump(sb.toString());
    }

    public static String serializeObject(Object o) {
        if (o == null)
            return "None";
        if (o instanceof ArrayList) {
            StringBuffer sb = new StringBuffer();
            sb.append("[");
            for (Object obj : (ArrayList)o) 
                sb.append(serializeObject(obj)).append(",");
            sb.append("]");
            return sb.toString();
        }
        if (o.getClass().isArray()) {
            StringBuffer sb = new StringBuffer();
            sb.append("[");
            for (int i = 0; i < Array.getLength(o); i++) {
                sb.append(serializeObject(Array.get(o, i))).append(",");
            }
            sb.append("]");
            return sb.toString();
        }
        if (o instanceof Character)
            return escaped_char(((Character)o).charValue());
        if (o instanceof String) {
            return escaped_string((String)o);
        }
        return o.toString();
    }

    // ----------------------------------------------------------------------
    // Checked Arithmetic - Overflow protection
    public int negate_ovf(int x) 
    {
        if (x == INT_MIN)
        {
            interlink.throwOverflowError();
        }
        return -x;
    }

    public long negate_ovf(long x) 
    {
        if (x == LONG_MIN)
        {
            interlink.throwOverflowError();
        }
        return -x;
    }
    
    public int abs_ovf(int x) 
    {
        if (x == INT_MIN)
        {
            interlink.throwOverflowError();
        }
        return Math.abs(x);
    }

    public long abs_ovf(long x) 
    {
        if (x == LONG_MIN)
        {
            interlink.throwOverflowError();
        }
        return Math.abs(x);
    }

    public int add_ovf(int x, int y) 
    {
        int result = x+y;
        if (!(((result^x) >=0) || ((result^y) >=0)))
        {
            interlink.throwOverflowError();
        }
        return result;
    }

    public int subtract_ovf(int x, int y) 
    {
        int result = x-y;
        if (!(((result^x) >=0) || ((result^(~y)) >=0)))
        {
            interlink.throwOverflowError();
        }
        return result;
    }

    private static boolean int_multiply(int x, int y)
    {
        double dprod = (double)x * (double)y;
        long longprod = x * y;
        double dlongprod = (double)longprod;
        double diff = dlongprod - dprod;
        double absdiff = Math.abs(diff);
        double absprod = Math.abs(dprod);

        if (dlongprod == dprod) //if diff == 0
            return true;
        else if (32.0 * absdiff <= absprod) //if we lost some information, are we at least 5 good bits?
            return true;
        else
            return false;
    }
    public int multiply_ovf(int x, int y) 
    {
        if (!(int_multiply(x, y)))
        {
            interlink.throwOverflowError();
        }
        return x * y;
    }

    public long add_ovf(long x, long y) 
    {
        long result = x+y;
        if (!(((result^x) >=0) || ((result^y) >=0)))
        {
            interlink.throwOverflowError();
        }
        return result;
    }

    public long subtract_ovf(long x, long y) 
    {
        long result = x-y;
        if (!(((result^x) >=0) || ((result^(~y)) >=0)))
        {
            interlink.throwOverflowError();
        }
        return result;
    }

    private static boolean long_multiply(long x, long y)
    {
        double dprod = (double)x * (double)y;
        long longprod = x * y;
        double dlongprod = (double)longprod;
        double diff = dlongprod - dprod;
        double absdiff = Math.abs(diff);
        double absprod = Math.abs(dprod);

        if (dlongprod == dprod) //if diff == 0
            return true;
        else if (32.0 * absdiff <= absprod) //if we lost some information, are we at least 5 good bits?
            return true;
        else
            return false;
    }
    public long multiply_ovf(long x, long y) 
    {
        //if (long_multiply(x, y))
        //{
        //    return x * y;
        //}
        //else
        //    interlink.throwOverflowError();
        if (!(long_multiply(x, y)))
        {
            interlink.throwOverflowError();
        }
        return x*y;
        //else
        //    interlink.throwOverflowError();
    }


    /* floor division */
    public int floordiv_ovf(int x, int y) 
    {
        if ((y == -1) && (x == INT_MIN))
        {
            interlink.throwOverflowError();
        }
        return x/y;
    }

    public int floordiv_zer_ovf(int x, int y) 
    {
        if (y == 0)
            interlink.throwZeroDivisionError();
        return floordiv_ovf(x,y);
    }

    public long floordiv_ovf(long x, long y) 
    {
        if ((y == -1) && (x == LONG_MIN))
        {
            interlink.throwOverflowError();
        }
        return x/y;
    }

    public long floordiv_zer_ovf(long x, long y)
    {
        if (y != 0)
        {
            return floordiv_ovf(x,y);
        }
        else
            throw new ArithmeticException("Floor Division with integer by 0");
    }

    /* modulo */
    public int mod_ovf(int x, int y) 
    {
        if ((y == -1) && (x == INT_MIN))
        {
            interlink.throwOverflowError();
        }
        return x%y;
    }

    public long mod_ovf(long x, long y) 
    {
        if ((y == -1) && (x == LONG_MIN))
        {
            interlink.throwOverflowError();
        }
        return x%y;
    }

    /* shifting */
    public int lshift_ovf(int x, int y) // x << y
    {
        int result = x << y;
        if (x != (result >> y))
        {
            interlink.throwOverflowError();
        }
        return result;
    }

    public long lshift_ovf(long x, long y) // x << y
    {
        long result = x << y;
        if (x != (result >> y))
        {
            interlink.throwOverflowError();
        }
        return result;
    }
    

    // ----------------------------------------------------------------------
    // String

    private static String substring(String str, int start, int end) {
        if (end >= str.length())
            if (start == 0)
                return str;
            else
                end = str.length();
        return str.substring(start, end);
    }

    public static String ll_strconcat(String str1, String str2) {
        return str1 + str2;
    }

    public static boolean ll_contains(String str, char char1) {
        return str.indexOf((int) char1) != -1;
    }

    public static int ll_find(String haystack, String needle, 
                              int start, int end) {
        // if it is impossible for the needle to occur: this deals w/
        //   a disparity in how java and python handle when needle=""
        if (start > haystack.length())
            return -1;

        haystack = substring(haystack, start, end);
        int res = haystack.indexOf(needle);
        if (res == -1) return res;
        return res + start;
    }

    public static int ll_rfind(String haystack, String needle, 
                               int start, int end) {
        if (start > haystack.length())
            return -1;

        haystack = substring(haystack, start, end);
        int res = haystack.lastIndexOf(needle);
        if (res == -1) return res;
        return res + start;
    }

    public static int ll_count(String haystack, String needle, 
                               int start, int end) {
        haystack = substring(haystack, start, end);

        if (needle.length() == 0) {
            return haystack.length()+1;
        }

        int cnt = 0;
        int lastidx = 0, idx = -1;
        while ((idx = haystack.indexOf(needle, lastidx)) != -1) {
            cnt++;
            lastidx = idx + needle.length(); // avoid overlapping occurrences
        }
        return cnt;
    }

    public static int ll_find_char(String haystack, char needle, 
                                   int start, int end) {
        // see ll_find for why this if is needed
        if (start > haystack.length())
            return -1;
        haystack = substring(haystack, start, end);
        int res = haystack.indexOf(needle);
        if (res == -1) return res;
        return res + start;
    }

    public static int ll_rfind_char(String haystack, char needle, 
                                    int start, int end) {
        haystack = substring(haystack, start, end);
        int res = haystack.lastIndexOf(needle);
        if (res == -1) return res;
        return res + start;
    }

    public static int ll_count_char(String haystack, char needle, 
                                    int start, int end) {
        haystack = substring(haystack, start, end);
        int cnt = 0;
        int idx = -1;
        while ((idx = haystack.indexOf(needle, idx+1)) != -1) {
            cnt++;
        }
        return cnt;
    }

    public static String ll_strip(String str, char ch, 
                                  boolean left, boolean right) {
        int start = 0;
        int end = str.length();

        if (left) {
            while (start <= str.length() && str.charAt(start) == ch) start++;
        }

        if (right) {
            while (end > start && str.charAt(end-1) == ch) end--;
        }

        return str.substring(start, end);
    }

    public static Object[] ll_split_chr(String str, char c, int max) {
        ArrayList list = new ArrayList();
        int lastidx = 0, idx = 0;
        while ((idx = str.indexOf(c, lastidx)) != -1)
        {
            if (max >= 0 && list.size() >= max)
                break;
            String sub = str.substring(lastidx, idx);
            list.add(sub);
            lastidx = idx+1;
        }
        list.add(str.substring(lastidx));
        return list.toArray(new String[list.size()]);
    }

    public static Object[] ll_rsplit_chr(String str, char c, int max) {
        ArrayList list = new ArrayList();
        int lastidx = str.length(), idx = 0;
        while ((idx = str.lastIndexOf(c, lastidx - 1)) != -1)
        {
            if (max >= 0 && list.size() >= max)
                break;
            String sub = str.substring(idx + 1, lastidx);
            list.add(0, sub);
            lastidx = idx;
        }
        list.add(0, str.substring(0, lastidx));
        return list.toArray(new String[list.size()]);
    }

    public static String ll_substring(String str, int start, int cnt) {
        return str.substring(start,start+cnt);
    }

    // ----------------------------------------------------------------------
    // StringBuffer

    public static void ll_append_char(StringBuilder sb, byte c) {
        // annoyingly, the actual return code is StringBuilder, so I have
        // to make this wrapper to ignore the return value
        sb.append((char)c);
    }

    public static void ll_append_char(StringBuilder sb, char c) {
        // annoyingly, the actual return code is StringBuilder, so I have
        // to make this wrapper to ignore the return value
        sb.append(c);
    }

    public static void ll_append(StringBuilder sb, String s) {
        // annoyingly, the actual return code is StringBuilder, so I have
        // to make this wrapper to ignore the return value
        sb.append(s);
    }

    public static void ll_append(StringBuilder sb, byte[] s) {
        // This is only used when we are using byte arrays instead of
        // strings.  We should really replace StringBuilder with some
        // kind of ByteBuilder in that case...
        for (byte b : s) {
            sb.append((char)b);
        }
    }

    public static byte[] ll_build(StringBuilder sb) {
        // This is only used when we are using byte arrays instead of
        // strings.  We should really replace StringBuilder with some
        // kind of ByteBuilder in that case...
        return string2bytes(sb.toString());
    }

    // ----------------------------------------------------------------------
    // Type Manipulation Routines

    public static Object RuntimeNew(Class c) {
        // all classes in our system have constructors w/ no arguments
        try {
            return c.getConstructor().newInstance();
        } catch (Exception exc) {
            throw new RuntimeException("Unexpected", exc);
        }
    }

    // ----------------------------------------------------------------------
    // Helpers
    
    public static byte[] string2bytes(String s) {
        return s.getBytes();
    }

    public static ArrayList array_to_list(Object[] array)
    {
        ArrayList list = new ArrayList(java.util.Arrays.asList(array));
        list.add(0, "dummy_executable_name");
        return list;
    }

    // ----------------------------------------------------------------------
    // OOString support
    
    public String oostring(int n, int base_) {
        // XXX needs special case for unsigned ints
        if (base_ == -1)
            base_ = 10;
        if (n < 0 && base_ != 10)
            return "-" + Integer.toString(-n, base_);
        else
            return Integer.toString(n, base_);
    }

    public String oostring(long n, int base_) {
        if (base_ == -1)
            base_ = 10;
        if (n < 0 && base_ != 10)
            return "-" + Long.toString(-n, base_);
        else
            return Long.toString(n, base_);
    }

    public String oostring(double d, int base_) {
        if (d == Double.POSITIVE_INFINITY)
            return "inf";
        else if (d == Double.NEGATIVE_INFINITY)
            return "-inf";
        else if (Double.isNaN(d)) 
            return "nan";
        else
            return Double.toString(d);
    }

    public String oostring(Object obj, int base_)
    {
        String clnm = obj.getClass().getName();
        int underscore = clnm.lastIndexOf('_');
        // strip "pypy." from the start, and _NN from the end
        clnm = clnm.substring(5, underscore);
        return String.format("<%s object>", new Object[] { clnm });
    }

    public String oostring(char ch, int base_)
    {
        return Character.toString(ch);
    }

    public byte[] oostring(byte[] s, int base_)
    {
        return s;
    }

    public String oostring(String s, int base_)
    {
        return s;
    }

    public String oostring(boolean b, int base_)
    {
        if (b) return "True";
        return "False";
    }

    // ----------------------------------------------------------------------
    // OOUnicode support

    public String oounicode(char ch)
    {
        return new Character(ch).toString();
    }

    public String oounicode(String s)
    {
        for(int i=0; i<s.length(); i++) {
            char ch = s.charAt(i);
            if ((int)ch > 127)
                interlink.throwUnicodeDecodeError();
        }
        return s;
    }

    // ----------------------------------------------------------------------
    // Primitive built-in functions

    public double ll_time_clock() {
        return System.currentTimeMillis()/1000.0; // XXX: processor time?
    }

    public double ll_time_time() {
        return System.currentTimeMillis()/1000.0;
    }
    
    public void ll_time_sleep(double seconds)
    {
        double startTime = ll_time_time();
        double endTime = startTime + seconds;
        do {
            try {
                Thread.sleep((int)((endTime-startTime)*1000));
                return;
            } catch (InterruptedException exc) {}
            startTime = ll_time_time();
        } while (startTime < endTime);
    }
    
    public String ll_join(String a, String b)
    {
        return a + File.separator + b;
    }

    public String ll_strtod_formatd(double d, char code, int precision, int flags)
    {
        // XXX: this is really a quick hack to make things work.
        // it should disappear, because this function is not
        // supported by ootypesystem.
        DecimalFormat format = new DecimalFormat("0.###");
        format.setMinimumFractionDigits(precision);
        format.setMaximumFractionDigits(precision);
        return format.format(d);
    }

    // ----------------------------------------------------------------------
    // Dicts
    //
    // Note: it's easier to cut and paste a few methods here than
    // make the code generator smarter to avoid the duplicate code.

    public static boolean ll_remove(HashMap map, Object key) {
        if (map.containsKey(key)) {
            map.remove(key); // careful: we sometimes use null as a value
            return true;
        }
        return false;
    }

    public static boolean ll_remove(CustomDict map, Object key) {
        if (map.containsKey(key)) {
            map.remove(key); // careful: we sometimes use null as a value
            return true;
        }
        return false;
    }
    
    public static DictItemsIterator ll_get_items_iterator(HashMap map) {
        return new DictItemsIterator(map);
    }
    
    public static DictItemsIterator ll_get_items_iterator(CustomDict map) {
        return new DictItemsIterator(map);
    }

    public static <K,V> CustomDict<K,V> ll_copy(CustomDict<K,V> map) {
        CustomDict<K,V> cd = new CustomDict<K,V>(map.equals, map.hashCode);
        for (Map.Entry<K,V> me : map.entrySet()) {
            cd.put(me.getKey(), me.getValue());
        }
        return cd;
    }
    
    // ----------------------------------------------------------------------
    // Lists

    public static void ll_setitem_fast(ArrayList self, int index, Object val)
    {
        // need a wrapper because set returns the old value
        self.set(index, val);
    }

    public static void _ll_resize_ge(ArrayList self, int length) {
        while (self.size() < length) {
            self.add(null);
        }
    }

    public static void _ll_resize_le(ArrayList self, int length) {
        //System.err.println("ll_resize_le: self.size()="+self.size()+" length="+length);
        while (self.size() > length) {
            self.remove(self.size()-1);
        }
    }

    public static void _ll_resize(ArrayList self, int length) {
        if (length > self.size())
            _ll_resize_ge(self, length);
        else if (length < self.size())
            _ll_resize_le(self, length); 
    }

    // ----------------------------------------------------------------------
    // ll_math
    //
    // not sure how many of these functions are needed.  we should add
    // something in the backend to redirect to the Math module by
    // default, perhaps.

    public double ll_math_ceil(double x) {
        return Math.ceil(x);
    }

    public double ll_math_fabs(double x) {
        return Math.abs(x);
    }

    public double ll_math_floor(double x) {
        return Math.floor(x);
    }

    public double ll_math_fmod(double x, double y) {
        return x % y;
    }

    public Object ll_math_frexp(double x) {
        /*
          Return the mantissa and exponent of x as the pair (m, e). m
          is a float and e is an integer such that x == m * 2**e
          exactly. If x is zero, returns (0.0, 0), otherwise 0.5 <=
          abs(m) < 1. This is used to "pick apart" the internal
          representation of a float in a portable way.
        */

        // NaN: Python returns (NaN, 0)
        if (Double.isNaN(x))
            return interlink.recordFloatSigned(x, 0);

        // Infinity: Python throws exception
        if (Double.isInfinite(x))
            interlink.throwOverflowError();

        // Extract the various parts of the format:
        final long e=11, f=52; // number of bits in IEEE format
        long bits = Double.doubleToLongBits(x);
        long bits_mantissa = bits & ((1 << f) - 1);
        int bits_exponent = (int)((bits >> f) & ((1 << e) - 1));
        int bits_sign = (int)(bits >> (e+f));

        // [+-]0
        if (bits_exponent == 0 && bits_mantissa == 0)
            return interlink.recordFloatSigned(x, 0);

        // TODO: Non-looping impl
        double mantissa = Math.abs(x);
        int exponent = 0;
        while (mantissa >= 1.0) {
            mantissa /= 2;
            exponent += 1;
        }
        while (mantissa < 0.5) {
            mantissa *= 2;
            exponent -= 1;
        }
        mantissa = (x < 0 ? -mantissa : mantissa);
        return interlink.recordFloatSigned(mantissa, exponent); 
    }
          
    public double ll_math_ldexp(double v, int w) {
        return check(v * Math.pow(2.0, w));
    }

    public Object ll_math_modf(double x) {
        double integer_x = (x >= 0 ? Math.floor(x) : Math.ceil(x));
        return interlink.recordFloatFloat(x - integer_x, integer_x);
    }

    public double ll_math_exp(double x) {
        return Math.exp(x);
    }

    public double ll_math_log(double x) {
        return Math.log(x);
    }

    public double ll_math_log10(double v) {
        return check(Math.log10(v));
    }

    public double ll_math_pow(double x, double y) {
        return Math.pow(x, y);
    }

    public double ll_math_sqrt(double x) {
        return Math.sqrt(x);
    }

    public double ll_math_acos(double x) {
        return Math.acos(x);
    }

    public double ll_math_asin(double x) {
        return Math.asin(x);
    }

    public double ll_math_atan(double x) {
        return Math.atan(x);
    }

    public double ll_math_atan2(double x, double y) {
        return Math.atan2(x, y);
    }

    public double ll_math_cos(double x) {
        return Math.cos(x);
    }

    public double ll_math_hypot(double x, double y) {
        return Math.hypot(x, y);
    }

    public double ll_math_sin(double x) {
        return Math.sin(x);
    }

    public double ll_math_tan(double x) {
        return Math.tan(x);
    }

    public double ll_math_degrees(double x) {
        return Math.toDegrees(x);
    }

    public double ll_math_radians(double x) {
        return Math.toRadians(x);
    }

    public double ll_math_cosh(double x) {
        return Math.cosh(x);
    }

    public double ll_math_sinh(double x) {
        return Math.sinh(x);
    }

    public double ll_math_tanh(double x) {
        return Math.tanh(x);
    }

    public double ll_math_copysign(double x, double y) {
        return Math.copySign(x, y);
    }

    public boolean ll_math_isnan(double x) {
        return Double.isNaN(x);
    }

    public boolean ll_math_isinf(double x) {
        return Double.isInfinite(x);
    }

    public boolean ll_math_isfinite(double x) {
        return !Double.isNaN(x) && !Double.isInfinite(x);
    }

    private double check(double v) {
        if (Double.isNaN(v))
            interlink.throwValueError();
        if (Double.isInfinite(v))
            interlink.throwOverflowError();
        return v;
    }
    
    public int tolower(int c) {
        return Character.toLowerCase(c);
    }

    public int locale_tolower(int chr)
    {
        return Character.toLowerCase(chr);
    }

    public int locale_isupper(int chr)
    {
        return boolean2int(Character.isUpperCase(chr));
    }

    public int locale_islower(int chr)
    {
        return boolean2int(Character.isLowerCase(chr));
    }

    public int locale_isalpha(int chr)
    {
        return boolean2int(Character.isLetter(chr));
    }

    public int locale_isalnum(int chr)
    {
        return boolean2int(Character.isLetterOrDigit(chr));
    }


    // ----------------------------------------------------------------------
    // Self Test

    public static int boolean2int(boolean b)
    {
        if (b)
            return 1;
        return 0;
    }

    public static int __counter = 0, __failures = 0;
    public static void ensure(boolean f) {
        if (f) {
            System.out.println("Test #"+__counter+": OK");
        }
        else {
            System.out.println("Test #"+__counter+": FAILED");
            __failures++;
        }
        __counter++;
    }

    public static void main(String args[]) {
        // Small self test:

        PyPy pypy = new PyPy(null);

        ensure(uint_cmp(0xFFFFFFFF, 0) > 0);
        ensure(uint_cmp(0, 0xFFFFFFFF) < 0);
        ensure(uint_cmp(0x80000000, 0) > 0);
        ensure(uint_cmp(0, 0x80000000) < 0);
        ensure(uint_cmp(0xFFFF, 0) > 0);
        ensure(uint_cmp(0, 0xFFFF) < 0);
        ensure(uint_cmp(0xFFFFFFFF, 0xFFFF) > 0);
        ensure(uint_cmp(0xFFFF, 0xFFFFFFFF) < 0);

        ensure(ulong_cmp(0xFFFFFFFFFFFFFFFFL, 0) > 0);
        ensure(ulong_cmp(0, 0xFFFFFFFFFFFFFFFFL) < 0);
        ensure(ulong_cmp(0xFFFFFFFFFFFFFFFFL, 0xFFFF) > 0);
        ensure(ulong_cmp(0xFFFF, 0xFFFFFFFFFFFFFFFFL) < 0);
        ensure(ulong_cmp(0x8000000000000000L, 0xFFFF) > 0);
        ensure(ulong_cmp(0xFFFF, 0x8000000000000000L) < 0);

        System.out.println("Total Failures: "+__failures);
    }
}
