import numpy as np
from scipy.stats import norm

# import matplotlib.pyplot as plt

# Generating 1000 point gaussian distribution
data = np.random.normal(size=1000)
fit = norm.pdf(data)

# Plotting distribution
# plt.plot(data,fit, '.')
# plt.show()

# Saving distribution
np.save("test_gaussian.npy", data)
