import numpy as np
import sympy as sp
import scipy.sparse as sparse

x, y = sp.symbols('x,y')

class Poisson2D:
    r"""Solve Poisson's equation in 2D::

        \nabla^2 u(x, y) = f(x, y), in [0, L]^2

    where L is the length of the domain in both x and y directions.
    Dirichlet boundary conditions are used for the entire boundary.
    The Dirichlet values depend on the chosen manufactured solution.

    """

    def __init__(self, L, ue):
        """Initialize Poisson solver for the method of manufactured solutions

        Parameters
        ----------
        L : number
            The length of the domain in both x and y directions
        ue : Sympy function
            The analytical solution used with the method of manufactured solutions.
            ue is used to compute the right hand side function f.
        """
        self.L = L
        self.ue = ue
        self.f = sp.diff(self.ue, x, 2)+sp.diff(self.ue, y, 2)

    def create_mesh(self, N):
        """Create 2D mesh and store in self.xij and self.yij"""
        self.xy = np.linspace(0, self.L, N+1)
        self.xij, self.yij = np.meshgrid(self.xy,
                                         self.xy,
                                         indexing='ij')
        self.N = N
        self.h = self.L/N

    def D2(self):
        """Return second order differentiation matrix"""
        D = sparse.diags([1, -2, 1], [-1, 0, 1], (self.N+1, self.N+1), 'lil')
        D[0, :4] = 2, -5, 4, -1
        D[-1, -4:] = -1, 4, -5, 2
        return D/self.h**2

    def laplace(self):
        """Return vectorized Laplace operator"""
        D2 = self.D2()
        I = sparse.eye(self.N + 1)
        return (sparse.kron(D2, I) + sparse.kron(I, D2))

    def get_boundary_indices(self): 
        """Return indices of vectorized matrix that belongs to the boundary"""
        indices = np.ones((self.N+1, self.N+1))
        indices[1:-1,1:-1] = 0
        bnds = np.where(indices.ravel() == 1)[0]      
        return bnds

    def assemble(self):
        """Return assembled matrix A and right hand side vector b"""
        # return A, b
        A = self.laplace().tolil()
        bnds = self.get_boundary_indices()
        for i in bnds:
            A[i] = 0
            A[i, i] = 1
        #A = A.tocsr()
        F = sp.lambdify((x,y), self.f)(self.xij, self.yij)
        self.u_exact = sp.lambdify((x,y), self.ue)(self.xij, self.yij)
        b = F.ravel()
        b[bnds] = self.u_exact.ravel()[bnds]
        return A, b

    def l2_error(self, u):
        """Return l2-error norm"""
        return np.sqrt(self.h * self.h * np.sum((self.u_exact - u)**2))

    def __call__(self, N):
        """Solve Poisson's equation.

        Parameters
        ----------
        N : int
            The number of uniform intervals in each direction

        Returns
        -------
        The solution as a Numpy array

        """
        self.create_mesh(N)
        A, b = self.assemble()
        self.U = sparse.linalg.spsolve(A.tocsr(), b.flatten()).reshape((N+1, N+1))
        return self.U

    def convergence_rates(self, m=6):
        """Compute convergence rates for a range of discretizations
    
        Parameters
        ----------
        m : int
            The number of discretization levels to use

        Returns
        -------
        3-tuple of arrays. The arrays represent:
            0: the orders
            1: the l2-errors
            2: the mesh sizes
        """
        E = []
        h = []
        N0 = 8
        for m in range(m):
            u = self(N0)
            E.append(self.l2_error(u))
            h.append(self.h)
            N0 *= 2
        r = [np.log(E[i-1]/E[i])/np.log(h[i-1]/h[i]) for i in range(1, m+1, 1)]
        return r, np.array(E), np.array(h)

    def eval(self, x, y):
        """Return u(x, y)

        Parameters
        ----------
        x, y : numbers
            The coordinates for evaluation

        Returns
        -------
        The value of u(x, y)

        """
        from scipy.interpolate import RectBivariateSpline
        object =  RectBivariateSpline(self.xy,self.xy,self.U)
        return object(x,y)

def test_convergence_poisson2d():
    # This exact solution is NOT zero on the entire boundary
    ue = sp.exp(sp.cos(4*sp.pi*x)*sp.sin(2*sp.pi*y))
    sol = Poisson2D(1, ue)
    r, E, h = sol.convergence_rates()
    assert abs(r[-1]-2) < 1e-2

def test_interpolation():
    ue = sp.exp(sp.cos(4*sp.pi*x)*sp.sin(2*sp.pi*y))
    sol = Poisson2D(1, ue)
    U = sol(100)
    assert abs(sol.eval(0.52, 0.63) - ue.subs({x: 0.52, y: 0.63}).n()) < 1e-3
    assert abs(sol.eval(sol.h/2, 1-sol.h/2) - ue.subs({x: sol.h, y: 1-sol.h/2}).n()) < 1e-3

