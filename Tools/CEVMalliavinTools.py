import numba as nb
from Type import nd_array
import numpy as np


@nb.jit("f8[:,:](f8, f8[:,:], f8[:,:])", nopython=True, nogil=True)
def transform_cev_malliavin(rho: float,
                            z_t_paths: nd_array,
                            d_z_t: nd_array):
    dim = z_t_paths.shape
    path_d_z_t = np.empty(shape=dim)

    for i in range(0, dim[0]):
        for j in range(0, dim[1]):
            path_d_z_t[i, j] = d_z_t[i, j] * np.power(z_t_paths[i, j], rho / (1.0 - rho)) / (1.0 - rho)

    return path_d_z_t


# @nb.jit("f8[:](f8[:], f8[:])", nopython=True, nogil=True)
def get_error(y_t_n, y_t):
    n = len(y_t_n)
    error = np.zeros(n)

    for i in range(0, n):
        error[i] = np.abs(y_t_n[i] - y_t[i])

    return error


@nb.jit("f8(f8[:], f8[:])", nopython=True, nogil=True)
def get_mean_error(y_t_n, y_t):
    n = len(y_t_n)
    error = 0.0

    for i in range(0, n):
        error += np.abs(y_t_n[i] - y_t[i]) / n

    return error


@nb.jit("f8(f8[:], f8[:])", nopython=True, nogil=True)
def get_square_error(y_t_n, y_t):
    n = len(y_t_n)
    error = 0.0

    for i in range(0, n):
        error += np.power(y_t_n[i] - y_t[i], 2.0) / n

    return np.sqrt(error)