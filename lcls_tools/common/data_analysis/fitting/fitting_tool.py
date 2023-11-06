import pylab
import numpy as np
from scipy.optimize import curve_fit
from scipy.ndimage import gaussian_filter
from scipy.special import erf
import statistics

#from lmfit import Model 
#want functions for gaussian
#truncated gaussian
#super gaussian 
#rms
#truncated rms



class FittingTool:
    def __init__(self,data:np.array):
        '''tool takes in the data points for some distribution, for now just one distrbution at a time'''
        self.distribution = data
        self.linspace = np.arange(len(data))

        #do some statistical analysis to get 
        self.p0 = self.get_stats(self.distribution,self.linspace)
        self.method = self.guess_method()


    def get_stats(self,distribution,linspace):
        offset = np.min(distribution)
        amp = np.max(distribution) - offset
        num = len(distribution)
        outcomes = distribution*linspace
        mu = np.sum(outcomes)/num
        sigma =np.sqrt(sum((distribution*(linspace-mu)**2)/num))

        pearsons_coefficient = self.check_skewness(outcomes,mu,sigma)
        kurtosis = self.check_kurtosis()
        ##useful for initial guess probably not completely correct

        return [amp,mu,sigma,offset]

    def guess_method(self):
        ''' Perform statistics on data set '''
        return self.gaussian

    def check_skewness(self,outcomes,mu,sigma):
        '''Checks for skewness in dataset, neg if mean<median<mode, pos if opposite'''
        mode = statistics.mode(outcomes)
        pearsons_coeff = (mu - mode)/sigma
        print(pearsons_coeff)
        return pearsons_coeff
    

    def check_kurtosis(self):
        '''greater kurtosis higher the peak'''
        '''how fast tails approaching zero, more outliers with higher kurtosis'''
        '''positive excess - tails approach zero slower'''
        '''negative excess - tails approach zero faster'''
        #do later
        return 0
    
    def find_peaks(self):
        pass
   
    def find_widths(self):
        pass

    def find_runs(self):
        pass

    def find_moments(self):
        ''' mean, sigma, skewness, kurtosis'''
        pass

    def truncate_distribution(x,lower_bound:float=None,upper_bound:float=None):
        if lower_bound is None:
            lower_bound = x.min()
        if upper_bound is None:
            upper_bound = x.max()
        truncated_x = np.clip(x,lower_bound,upper_bound)
        return truncated_x

    def calculate_rms_deviation(x:np.array,fit_x:np.array):
        rms_deviation = np.sqrt(np.power(sum(x-fit_x),2)/len(x))
        return rms_deviation 
    
    def calculate_unbiased_rms_deviated(x:np.array=None):
        mean = np.mean(x)
        rms_deviation = np.sqrt(np.power(sum(x-mean),2)/len(x))
        return rms_deviation 

    def get_fit(self):
        '''Return fit parameters to data y such that y = method(x,parameters)'''
        return curve_fit(self.method,self.linspace,self.distribution,self.p0)[0]

    @staticmethod
    def gaussian(x,amp,mu,sig,offset):
        '''Gaussian Function'''
        '''need a way to guess params if amp =/'''
        return amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0))) + offset
    
    @staticmethod
    def super_gaussian(x,amp,mu,sig,P):
        '''Super Gaussian Function'''
        '''Degree of P related to flatness of curve at peak'''
        return amp * np.exp((-abs(x - mu)**P )/ (2 * sig ** P))
    
    @staticmethod
    def double_gaussian( x, amp, mu, sig , amp2, nu, rho):
        return ( amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0))) +
                amp2 * np.exp(-np.power(x - nu, 2.0) / (2 * np.power(rho, 2.0))) )
   
    @staticmethod
    def two_dim_gaussian(x, y, A, x0, y0, sigma_x, sigma_y):
        '''2-D Gaussian Function'''
        return A*np.exp(-(x-x0)**2/(2*sigma_x**2) -(y-y0)**2/(2*sigma_y**2))



    ####fit batch images