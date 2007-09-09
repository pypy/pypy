package pypy;

/** 
 * Class returned by the Stat function.  The Rpython type is a record
 * type which is special-cased in database.py to return an instance of
 * this class.  The fields are named item0...itemN to conform with 
 * Rpython, but there are friendly accessors for humans to use.
 *
 * <p>The actual stat() function is defined in PyPy.java.
 */
class StatResult {
    public int item0;
    public long item6, item8;

    public void setMode(int value)  { item0 = value; }
    public void setSize(long value)  { item6 = value; }
    public void setMtime(long value) { item8 = value; }

}