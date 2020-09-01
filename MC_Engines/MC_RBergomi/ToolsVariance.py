import numpy as np
import numba as nb
from Tools.Types import ndarray
from ncephes import hyp2f1
from Tools import Functionals


@nb.jit("f8(f8, f8, f8)", nopython=True, nogil=True)
def get_volterra_covariance(s: float, t: float, h: float):
    # We suppose that t > s
    if s > 0.0:
        gamma = 0.5 - h
        x = s / t
        alpha = ((1.0 - 2.0 * gamma) / (1.0 - gamma)) * np.power(x, gamma) * hyp2f1(1.0, gamma, 2.0 - gamma, x)
        return np.power(s, 2.0 * h) * alpha

    else:
        return 0.0


@nb.jit("f8[:](f8[:], f8)", nopython=True, nogil=True)
def get_volterra_variance(t: ndarray, h: float):
    no_elements = len(t)
    output = np.zeros(no_elements)
    for i in range(0, no_elements):
        output[i] = np.power(t[i], 2.0 * h)
    return output


@nb.jit("f8(f8, f8, f8, f8)", nopython=True, nogil=True)
def get_covariance_w_v_w_t(s: float, t: float, rho: float, h: float):
    d_h = np.sqrt(2.0 * h) / (h + 0.5)
    return rho * d_h * (np.power(t, h + 0.5) - np.power(t - np.minimum(s, t), h + 0.5))


@nb.jit("f8[:,:](f8[:], f8, f8)", nopython=True, nogil=True)
def get_covariance_matrix(t_i_s: ndarray, h: float, rho: float):
    no_time_steps = len(t_i_s)
    cov = np.zeros(shape=(2 * no_time_steps, 2 * no_time_steps))
    for i in range(0, no_time_steps):
        for j in range(0, i + 1):
            cov[i, j] = t_i_s[j]
            cov[j, i] = cov[i, j]

    for i in range(0, no_time_steps):
        for j in range(no_time_steps, 2 * no_time_steps):
            cov[i, j] = get_covariance_w_v_w_t(t_i_s[i], t_i_s[j - no_time_steps], h, rho)
            cov[j, i] = cov[i, j]

    for i in range(0, no_time_steps):
        for j in range(0, i + 1):
            cov[i + no_time_steps, j + no_time_steps] = get_volterra_covariance(t_i_s[j], t_i_s[i], h)
            cov[j + no_time_steps, i + no_time_steps] = cov[i + no_time_steps, j + no_time_steps]

    return cov


@nb.jit("f8[:,:](f8, f8, f8, f8, f8[:,:], f8[:,:], f8[:], i8)", nopython=True, nogil=True)
def generate_paths(s0: float,
                   v0: float,
                   nu: float,
                   h: float,
                   noise: ndarray,
                   cholk_cov: ndarray,
                   t_i_s: ndarray,
                   no_paths: int):
    no_time_steps = len(t_i_s)

    paths = np.zeros(shape=(no_paths, no_time_steps))
    v_i_1 = np.zeros(shape=(no_paths, no_time_steps))

    v_i_1[:, 0] = v0
    paths[:, 0] = s0

    # we compute before a loop of variance of the variance process
    var_w_t = get_volterra_variance(t_i_s[1:], h)

    for k in range(0, no_paths):
        w_i_s = Functionals.apply_lower_tridiagonal_matrix(cholk_cov, noise[:, k])

        w_i_1 = 0.0
        for j in range(1, no_time_steps):
            delta_i_s = t_i_s[j] - t_i_s[j - 1]
            v_i_1[k, j] = v0 * np.exp(- 0.5 * nu * nu * var_w_t[j - 1] + nu * w_i_s[j + no_time_steps - 2])

            d_w_i_1_i = (w_i_s[j - 1] - w_i_1)
            paths[k, j] = paths[k, j - 1] * np.exp(-0.25 * (v_i_1[k, j] + v_i_1[k, j - 1]) * delta_i_s +
                                                   v_i_1[k, j - 1] * d_w_i_1_i)
            w_i_1 = w_i_s[j - 1]

    return paths


@nb.jit("f8(f8, f8)", nopython=True, nogil=True)
def beta(t, m):
    if t < 1.0e-05:
        return t
    else:
        return (1.0 - np.exp(- m * t)) / m


def generate_paths_affine_method(s0: float,
                                 v0: float,
                                 nu: float,
                                 rho: float,
                                 h: float,
                                 z_s_i: ndarray,
                                 z_v_i: ndarray,
                                 t_i_s: ndarray,
                                 no_paths: int):
    no_time_steps = len(t_i_s)
    u_mean = 0.5 - h

    delta_i_s = np.diff(t_i_s)
    paths = np.zeros(shape=(no_paths, no_time_steps))
    y_t_u = np.zeros(shape=(no_paths, no_time_steps))
    v_i_1 = np.zeros(shape=(no_paths, no_time_steps))
    w_s_i = np.zeros(no_paths)
    rho_inv = np.sqrt(1.0 - rho * rho)

    v_i_1[:, 0] = v0
    paths[:, 0] = s0

    for j in range(1, no_time_steps):
        y_t_u[:, j] = np.exp(- u_mean) * y_t_u[:, j - 1] + \
                      np.sqrt(beta(delta_i_s[j-1], 2.0 * u_mean / delta_i_s[j-1])) * z_v_i[:, j - 1]

        v_i_1[:, j] = v_i_1[:, j-1] * np.exp(
            - h * nu * nu * np.power(t_i_s[j - 1] + 0.5 * delta_i_s[j-1], 2.0 * h - 1.0) * delta_i_s[j - 1] +
            np.power(delta_i_s[j - 1], h - 0.5) * y_t_u[:, j - 1] - np.log(v_i_1[:, j-1]/v0) + nu * np.power(delta_i_s[j - 1], h) * z_v_i[:, j - 1])

        np.copyto(w_s_i, np.sqrt(delta_i_s[j - 1]) * (rho * z_v_i[:, j - 1] + rho_inv * z_s_i[:, j - 1]))
        print(j)
        paths[:, j] = paths[:, j - 1] * np.exp(-0.25 * (v_i_1[:, j] + v_i_1[:, j - 1]) * delta_i_s[j - 1] +
                                               v_i_1[:, j - 1] * w_s_i)

    empirical_variance = np.std(np.log(v_i_1 / v0), axis=0)**2
    analytic_variance = get_volterra_variance(t_i_s, h) * nu * nu

    return paths