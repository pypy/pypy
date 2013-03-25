package pypy;

public interface Filter<F, T> {
    public T to(F from);
    public F from(T to);
}
