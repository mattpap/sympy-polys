
class GenericMatrix(object):
    """ """

class DenseMatrix(GenericMatrix):


    @cythonized('i,j')
    def row(self, i, func):
        """Elementary row operation using a functor. """
        for j in xrange(self.cols):
            self[i, j] = func(self[i, j], j)

    @cythonized('i,j')
    def col(self, j, func):
        """Elementary column operation using a functor. """
        for i in xrange(self.rows):
            self[i, j] = func(self[i, j], i)

    @cythonized('i,j,k')
    def row_swap(self, i, j):
        """Swap rows $r_i$ and $r_j$. """
        for k in xrange(self.cols):
            self[i, k], self[j, k] = self[j, k], self[i, k]

    @cythonized('i,j,k')
    def col_swap(self, i, j):
        """Swap columns $c_i$ and $c_j$. """
        for k in xrange(self.rows):
            self[k, i], self[k, j] = self[k, j], self[k, i]

    @cythonized('i')
    def row_del(self, i):
        """Remove $i$--th row from the matrix. """
        self.rep = self.rep[:i*self.cols] + self.rep[(i+1)*self.cols:]
        self.rows -= 1

    @cythonized('i,j')
    def col_del(self, i):
        for j in xrange(self.rows-1, -1, -1):
            del self.rep[i + j*self.cols]
        self.cols -= 1

    @cythonized('i,j,k')
    def det_bareis(M, K):
        """Compute determinant using Bareis' algorithm. """
        M = self.copy()

        if n == 1:
            det = M[0, 0]
        elif n == 2:
            det = M[0, 0]*M[1, 1] - M[0, 1]*M[1, 0]
        else:
            sign = 1 # track current sign in case of column swap

            for k in xrange(n-1):
                # look for a pivot in the current column
                # and assume det == 0 if none is found
                if not M[k, k]:
                    for i in xrange(k+1, n):
                        if M[i, k]:
                            M.row_swap(i, k)
                            sign *= -1
                            break
                    else:
                        return K.zero

                # proceed with Bareis' fraction-free (FF)
                # form of Gaussian elimination algorithm
                for i in xrange(k+1, n):
                    for j in xrange(k+1, n):
                        elt = M[k, k]*M[i, j] - M[i, k]*M[k, j]

                        if k != 0:
                            M.dom.exquo(elt, M[k-1, k-1])

                        M[i, j] = elt

            det = sign * M[n-1, n-1]

        return det

