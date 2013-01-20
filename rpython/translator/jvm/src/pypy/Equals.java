package pypy;

/** @see Callback */
public interface Equals extends Callback {
    public boolean invoke(Object one, Object two);
}
