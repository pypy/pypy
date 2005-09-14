from __future__ import division

EPSILON = 1E-6


class SparseMatrix:

    def __init__(self, height):
        self.lines = [{} for row in range(height)]

    def __getitem__(self, (row, col)):
        return self.lines[row].get(col, 0)

    def __setitem__(self, (row, col), value):
        if abs(value) > EPSILON:
            self.lines[row][col] = value
        else:
            try:
                del self.lines[row][col]
            except KeyError:
                pass

    def copy(self):
        m = SparseMatrix(len(self.lines))
        for line1, line2 in zip(self.lines, m.lines):
            line2.update(line1)
        return m

    def solve(self, vector):
        """Solves  'self * [x1...xn] == vector'; returns the list [x1...xn].
        Raises ValueError if no solution or indeterminate.
        """
        vector = list(vector)
        lines = [line.copy() for line in self.lines]
        columns = [{} for i in range(len(vector))]
        for i, line in enumerate(lines):
            for j, a in line.items():
                columns[j][i] = a
        lines_left = dict.fromkeys(range(len(self.lines)))
        nrows = []
        for ncol in range(len(vector)):
            currentcolumn = columns[ncol]
            lst = [(abs(a), i) for (i, a) in currentcolumn.items()
                               if i in lines_left]
            _, nrow = min(lst)    # ValueError -> no solution
            nrows.append(nrow)
            del lines_left[nrow]
            line1 = lines[nrow]
            mina = line1[ncol]
            for _, i in lst:
                if i != nrow:
                    line2 = lines[i]
                    a = line2.pop(ncol)
                    #del currentcolumn[i]  -- but currentcolumn no longer used
                    factor = a / mina
                    vector[i] -= factor*vector[nrow]
                    for col in line1:
                        if col > ncol:
                            value = line2.get(col, 0) - factor*line1[col]
                            if abs(value) > EPSILON:
                                line2[col] = columns[col][i] = value
                            else:
                                del line2[col]
                                del columns[col][i]
        solution = [None] * len(vector)
        for i in range(len(vector)-1, -1, -1):
            row = nrows[i]
            line = lines[row]
            total = vector[row]
            for j, a in line.items():
                if j != i:
                    total -= a * solution[j]
            solution[i] = total / line[i]
        return solution


def test_sparsemat1():
    import py
    M = SparseMatrix(4)
    M[0,0] = M[1,1] = M[2,2] = M[3,3] = 1
    M[0,1] = -1.0
    M[1,2] = M[1,3] = -0.5
    M[2,1] = -1.0
    res = M.solve([4, 5, 4, 1])
    assert res == [19, 15, 19, 1]

def test_sparsemat2():
    import py
    M = SparseMatrix(4)
    M[0,0] = M[1,1] = M[2,2] = M[3,3] = 1
    M[0,1] = -1.0
    M[1,2] = M[1,3] = -0.5
    M[2,1] = M[2,3] = -0.5
    res = M.solve([6, 3, 6, 0])
    assert res == [14, 8, 10, 0]
