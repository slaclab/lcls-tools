import unittest
import numpy as np
import matplotlib.pyplot as plt
import os
from lcls_tools.common.data_analysis.fitting.fitting_tool import FittingTool
import statistics 
   # 
def gaussian(x,amp,mu,sig, offset):
    return amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0))) + offset 

x_data = np.arange(500)
test_params = [3,125,45,1.5]
y_data = gaussian(x_data,*test_params)
y_noise = np.random.normal(size=len(x_data),scale = 0.04)
y_test = y_data+y_noise
fitting_tool = FittingTool(y_test)

params = fitting_tool.get_fit()
print('params: ' , params, '   fit params: ', test_params)
y_fitted = gaussian(x_data,*params)

fig, (ax1,ax2,ax3) = plt.subplots(3,1)

ax1.plot(x_data,y_test)
ax1.plot(x_data,y_fitted,'-.')

plt.show()
