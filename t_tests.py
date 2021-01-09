# -*- coding: utf-8 -*-
"""
Created on Thu Jan  2 10:22:00 2020

@author: SMC

t-score = observed difference between sample means / standard error of the difference between the means
t-score = ( mean(X) - mean(Y) ) / sed

sed (standard error of the difference) = sqrt(seX**2 + seY**2)
(seX and seY are standard errors of the first and second samples)

se (standard error of a sample) = std / sqrt(n)
(std is the standard deviation, n is the number of observations in the sample)
(also = sqrt(var/n))

std (sample standard deviation) = sqrt( sum( (X-mean(X))**2 ) / (n-1) )
(X is a vector)

we can get the p_value from the cdf of the t:
    p = scipy.stats.t.cdf(t, df) *2
multiply by 2 if it is two tailed!!

------------
functions for doing independent paired sample t-tests
t-score = (M1-M2) / ( (S1**2)/n1 + (S2**2)/n2 )
S**2 = SUM((x-M)**2)/n-1

To calculate the critical t value we need the degrees of freedom and a choosen alpha value.
df = n1 + n2 - 2
alpha = 0.5
Use scipy's stats to calculate the critical t-value internally

"""


import numpy as np
from scipy import stats


def t_test_1sample(X):
    """
    1 sample t-test: t = (X.mean() - 0) / (np.sqrt(var/n))
        and df = n-1
    Parameters
    ----------
    X : Series; a row of the dataframe
    n : int; nr of values in the sample (participants)

    Returns
    -------
    p : p_value
    """

    X = np.array(X)
    X = X[~np.isnan(X)]
    n = len(X)

    if n == 1:
        print("t-score: 0; n = 1; p = nan")
        return np.nan

    var = calculate_variance(n, X)

    t = np.mean(X) / (np.sqrt(var/n))

    df = n-1
    p = ( 1 - stats.t.cdf(np.abs(t), df=df) ) *2

    return p



def t_test_2samples(X, Y, n):
    """
    calculates the t-score and the p value

    Parameters
    ----------
    n : int; nr of values in the sample (participants)
    X : Series; a row of the interesting dataframe
    Y : Series; a row of the boring dataframe

    Returns
    -------
    p : p_value
    """

    X = np.array(X)
    X = X[~np.isnan(X)]
    Y = np.array(Y)
    Y = Y[~np.isnan(Y)]
    var_x = calculate_variance(n,X)
    var_y = calculate_variance(n,Y)

    # df = 2*n -2

    if var_x != 0:
        numerator = (np.mean(X) - np.mean(Y))
        denominator = np.sqrt( (var_x)/n + (var_y)/n )
        t = numerator / denominator
    else:
        t = 0

    df = ( (var_x)/n + (var_y)/n )**2 / ( ((var_x/n)**2)/(n-1) + ((var_y/n)**2)/(n-1) )

    p = 1 - stats.t.cdf(np.abs(t), df=df)
    print("t-score:", t, ", p-value:", p)

    return p



def calculate_variance(n, X):

    var = np.sum( (X - np.mean(X))**2 ) / (n-1)

    # sd = np.sqrt(var)

    return var


def factory_1samp_t_test(X):

    X = np.array(X)

    t,p = stats.ttest_1samp(X, 0.0, nan_policy="omit")

    print(f"t-score: {t}; p_value: {p}")
#    print("p_value:", p)

    return p


def factory_std(X):

    np.std(X)





