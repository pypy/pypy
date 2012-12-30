package pypy;

/** 
 * Class returned by the Stat function.  The Rpython type is a record
 * type which is special-cased in database.py to return an instance of
 * this class.  The fields are named item0...itemN to conform with 
 * Rpython, but there are friendly accessors for humans to use.
 *
 * <p>The actual stat() function is defined in PyPy.java.
 */
public class StatResult {
    public int item0, item3, item4, item5;
    public long item1, item2, item6;
    public double item7, item8, item9;

    public void setMode(int value)  { item0 = value; }
    public void setSize(long value)  { item6 = value; }
    public void setMtime(double value) { item8 = value; }
}
