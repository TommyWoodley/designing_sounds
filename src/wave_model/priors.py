import numpy as np

from scipy.special import iv


class SquaredExpPrior:
    def __init__(self, d: int):
        self.w = np.asarray(np.random.randn(d), dtype=np.float32)
        self.b = np.asarray(np.random.uniform(0, 2 * np.pi), dtype=np.float32)
        self.weights = np.asarray(np.random.randn(d), dtype=np.float32)
        self.d = d

    def update(self, a, b):
        pass

    def resample(self):
        self.weights = np.asarray(np.random.randn(self.d), dtype=np.float32)

    def z(self, x, sds, lengthscales):
        return sds[:, None, None] * np.sqrt(2 / len(self.w)) * np.cos(
            ((1 / lengthscales)[:, None, None] * (x[:, None] @ self.w[None, :])[None, :, :]) + self.b)

    def prior(self, x, _, sds, lengthscales):
        return np.sum(self.z(x, sds, lengthscales), axis=0) @ self.weights

    def covariance_matrix(self, x1, x2, freqs, sds, lengthscales):
        x = x1[:, None] - x2
        temp = np.zeros((len(freqs), len(x1), len(x2)), dtype=np.float32)
        for i, freq in enumerate(freqs):
            temp[i] = self.kernel(x, 0, sds[i], lengthscales[i])
        return np.exp(-0.5 * temp)

    def kernel(self, x, _, sd, l):
        return squared_exponential(x, sd, l)


class PeriodicPrior:
    def __init__(self, d: int):
        self.d = d
        self.cos_weights = np.asarray(np.random.randn(d), dtype=np.float32)
        self.sin_weights = np.asarray(np.random.randn(d), dtype=np.float32)
        self.calc = np.zeros((self.d, 1, 1), dtype=np.float32)

    def resample(self):
        self.cos_weights = np.asarray(np.random.randn(self.d), dtype=np.float32)
        self.sin_weights = np.asarray(np.random.randn(self.d), dtype=np.float32)

    def update(self, lengthscale, sd):
        self.calc = np.zeros((self.d, sd.size, 1), dtype=np.float32)
        l = np.power(lengthscale, -2)
        for k in range(self.d):
            if self.d == 0:
                num = 1
            else:
                num = 2
            self.calc[k, :, 0] = sd * np.sqrt(num * iv(k, l) / np.exp(l))

    def prior(self, x, freqs, sds, lengthscales):
        ds = 2 * np.pi * np.asarray(np.arange(self.d), dtype=np.float32)
        vals = ds[:, None, None] * (x[:, None] @ freqs[None, :])[None, :, :]
        return (np.cos(vals) @ self.calc)[:, :, 0].T @ self.cos_weights + (np.sin(vals) @ self.calc)[:, :,
                                                                          0].T @ self.sin_weights

    def covariance_matrix(self, x1, x2, freqs, sds, lengthscales):
        x = x1[:, None] - x2
        temp = np.zeros((len(freqs), len(x1), len(x2)), dtype=np.float32)
        for i, freq in enumerate(freqs):
            temp[i] = self.kernel(x, freq, sds[i], lengthscales[i])
        return temp

    def kernel(self, x, freq, sd, l):
        return squared_exponential(2 * np.sin(np.pi * x * freq), sd, l)

class MultPrior:
    def __init__(self, d: int):
        self.d = d
        self.periodic = PeriodicPrior(self.d)
        self.squared = SquaredExpPrior(self.d)

    def resample(self):
        self.periodic.resample()
        self.squared.resample()

    def update(self, lengthscale, sd):
        self.periodic.update(lengthscale, sd)

    def prior(self, x, freqs, sds, lengthscales):
        return self.periodic.prior(x, freqs, sds, lengthscales) * self.squared.prior(x, freqs, sds, lengthscales)

    def covariance_matrix(self, x1, x2, freqs, sds, lengthscales):
        x = x1[:, None] - x2
        temp = np.zeros((len(freqs), len(x1), len(x2)), dtype=np.float32)
        for i, freq in enumerate(freqs):
            temp[i] = self.kernel(x, freq, sds[i], lengthscales[i])
        return temp

    def kernel(self, x, freq, sd, l):
        return self.periodic.kernel(x, freq, sd, l) * self.squared.kernel(x, freq, sd, l)


def squared_exponential(x, sd, l):
    return sd ** 2 * np.exp(-0.5 * np.square(x / l))