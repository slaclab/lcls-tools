import numpy as np
from scipy.stats import norm
from lcls_tools.common.model import super_gaussian

import matplotlib.pyplot as plt


n = 100
params_0 = {"mean": 50,
            "sigma": 10,
            "amp": 10,
            "off": 10,
            "n": 2}
x = np.array(range(n))
y = super_gaussian.curve(x, **params_0)

params = super_gaussian.fit(x, y)

print(params)

plt.scatter(x, y)
fit_x = x
fit_y = super_gaussian.curve(x, **params)
plt.plot(fit_x, fit_y, color='orange')
plt.show()
