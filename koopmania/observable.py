import sympy as sp
import numpy as np
from typing import Sequence
import abc


class KoopmanObservable(abc.ABC):
    def __init__(self):
        pass

    def __call__(self, X: np.ndarray) -> np.ndarray:
        return self.obs_fcn(X)

    @abc.abstractmethod
    def obs_fcn(self, X: np.ndarray) -> np.ndarray:
        pass

    def obs_grad(self, X: np.ndarray) -> np.ndarray:
        pass

    def __or__(self, obs: 'KoopmanObservable'):
        return CombineObservable([self, obs])


class IdentityObservable(KoopmanObservable):
    def obs_fcn(self, X: np.ndarray) -> np.ndarray:
        return np.atleast_2d(X)

    def obs_grad(self, X: np.ndarray) -> np.ndarray:
        assert len(X.shape) == 1
        return np.eye(len(X))


class SymbolicObservable(KoopmanObservable):
    def __init__(self, variables: Sequence[sp.Symbol], observables: Sequence[sp.Expr]):
       super(SymbolicObservable, self).__init__()
       self.length = len(variables)
       self._observables = observables
       self._variables = variables
       G = sp.Matrix(self._observables)
       GD = sp.Matrix([sp.diff(G, xi).T for xi in self._variables])
       self._g = sp.lambdify((self._variables,), G)
       self._gd = sp.lambdify((self._variables,), GD)

    def obs_fcn(self, X: np.ndarray) -> np.ndarray:
        return np.array(self._g(list(X.flatten())))

    def obs_grad(self, X: np.ndarray) -> np.ndarray:
        return np.array(self._gd(list(X)))

    def __add__(self, obs: 'SymbolicObservable'):
        return SymbolicObservable(list({*self._variables, *obs._variables}),
                                  [xi + yi for xi, yi in zip(self._observables, obs._observables)])

    def __sub__(self, obs: 'SymbolicObservable'):
        return SymbolicObservable(list({*self._variables, *obs._variables}),
                                  [xi - yi for xi, yi in zip(self._observables, obs._observables)])

    def __mul__(self, obs: 'SymbolicObservable'):
        return SymbolicObservable(list({*self._variables, *obs._variables}),
                                  [xi * yi for xi, yi in zip(self._observables, obs._observables)])

    def __truediv__(self, obs: 'SymbolicObservable'):
        return SymbolicObservable(list({*self._variables, *obs._variables}),
                                  [xi / yi for xi, yi in zip(self._observables, obs._observables)])

    def __rdiv__(self, other):
        if isinstance(other, SymbolicObservable):
            return SymbolicObservable(list({*self._variables, *other._variables}),
                                      [xi / yi for xi, yi in zip(self._observables, other._observables)])
        else:
            return SymbolicObservable(self._variables, [other / yi for yi in self._observables])

    def __rmul__(self, other):
        if isinstance(other, SymbolicObservable):
            return SymbolicObservable(list({*self._variables, *other._variables}),
                                      [xi * yi for xi, yi in zip(self._observables, other._observables)])
        else:
            return SymbolicObservable(self._variables, [other * yi for yi in self._observables])

    def __or__(self, other):
        if isinstance(other, SymbolicObservable):
            return SymbolicObservable(list({*self._variables, *other._variables}),
                                      [*self._observables, *other._observables])
        else:
            return CombineObservable([self, other])


class IdentitySymbolicObservable(SymbolicObservable):
    def __init__(self, variables: Sequence[sp.Symbol]):
        super(IdentitySymbolicObservable, self).__init__(variables, variables)


class QuadraticObservable(SymbolicObservable):
    def __init__(self, length):
        """inefficient implementation to get quadratic koopman observables and its gradient functions"""
        vec = sp.symbols(' '.join([f"x{idx}" for idx in range(length)]))
        x = sp.Matrix((*vec, 1))
        U = x*x.T
        lv = [U[i, j] for i, j in zip(*np.tril_indices(len(x)))]
        super(QuadraticObservable, self).__init__(vec, lv)


class CombineObservable(KoopmanObservable):
    def __init__(self, observables: Sequence[KoopmanObservable]):
        super(CombineObservable, self).__init__()
        self.observables = observables

    def obs_fcn(self, X: np.ndarray) -> np.ndarray:
        return np.vstack([obs.obs_fcn(X) for obs in self.observables])

    def obs_grad(self, X: np.ndarray) -> np.ndarray:
        return np.hstack([obs.obs_grad(X) for obs in self.observables])
