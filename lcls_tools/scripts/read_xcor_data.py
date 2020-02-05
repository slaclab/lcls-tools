#!/usr/local/lcls/package/python/current/bin/python
################################################################################
# Modified version of John Sheppard's read_xcor_data script
# Reads in a matlab file of xcor data and fits gaussians to it
# Data must have column names posList, ampList, and ampstdList
################################################################################

from __future__ import division

from pylab import array, plt, floor, show
from numpy import argsort, power, exp, zeros
from scipy.io import loadmat
from scipy.optimize import curve_fit
from operator import itemgetter
from sys import argv, exit

NUM_BUCKS = 10
DEBUG = False


def extract(matlabData, column):
    matLst = matlabData['data'][column][0][0]
    return matLst.flatten()


# An unfortunate consequence of defining step as max/numbucks is that the
# maximum point is in its own bucket (bucket 10), which would break a lot of 
# shit, so it necessitates the error checking
def getBucket(val, step):
    bucket = int(floor(val / step))
    return bucket if bucket < 10 else 9


def findMax(data, run):
    max_index = max(enumerate(data[run]), key=itemgetter(1))[0]
    return run[max_index]


# The very ham-fisted way I'm coming up with a guess for the width of a given
# peak is to get the literal distance between the first element of the
# subsequent run and the last element of the previous run
def findWidths(xdata, peakIdxs, runs, runMap):
    widths = []
    for peakIdx in peakIdxs:
        runIdx = runMap[peakIdx]

        # If it's the first run, just double the distance between the peak and
        # the first element of the next run
        if runIdx == 0:
            widths.append((xdata[runs[1][0]] - xdata[peakIdx]) * 2)

        # If it's the last run, just double the distance between the peak and
        # the last element of the previous run
        elif runIdx == len(runs) - 1:
            widths.append((xdata[peakIdx] - xdata[runs[-2][-1]]) * 2)

        else:
            widths.append(
                xdata[runs[runIdx + 1][0]] - xdata[runs[runIdx - 1][-1]])

    return widths


# Modified from StackOverflow
def genGaussSum(x, *params):
    m = params[0]
    b = params[1]

    y = [m * i + b for i in x]

    for i in range(2, len(params), 3):
        ctr = params[i]
        amp = params[i + 1]
        wid = params[i + 2]
        y = y + gaussian(x, ctr, wid, amp)
    return y


def gaussian(x, ctr, wid, amp):
    return amp * exp(-power(x - ctr, 2.) / (2 * power(wid, 2.)))


def getSlope(x1, y1, x2, y2):
    return (y2 - y1) / (x2 - x1)


# Idea to add a line instead of a really short, fat gaussian was all Ahemd.
# Thanks, yo. You're great.
def findLine(zeroRuns, runs, xdata, ydata):
    x1, y1, x2, y2, m, b = (0, 0, 0, 0, 0, 0)

    # This condition should only be possible if there are peaks on one or both 
    # extremes, or if there is no peak
    if len(zeroRuns) == 1:
        zeroRun = runs[zeroRuns[0]]
        # This should pull out the median index value of the run
        xInd1 = zeroRun[argsort(ydata[zeroRun])[len(zeroRun) / 2]]
        y1 = ydata[xInd1]

        return [m, y1]

    # 0 shouldn't be possible given that the data is normalized to the lowest 
    # point, so it should otherwise be at least 2.
    # Currently just fitting the first point of the first zero run and the last
    # point of the last zero run. Could make it smarter by adding a sum of step
    # functions, but that seems like overkill
    else:
        zero1 = runs[zeroRuns[0]]
        zero2 = runs[zeroRuns[-1]]

        xInd1 = zero1[argsort(ydata[zero1])[len(zero1) / 2]]
        x1 = xdata[xInd1]
        y1 = ydata[xInd1]

        xInd2 = zero2[argsort(ydata[zero2])[len(zero2) / 2]]
        x2 = xdata[xInd2]
        y2 = ydata[xInd2]

        m = getSlope(x1, y1, x2, y2)

        return [m, y1 - m * x1]


# Every run has the potential to be a peak, but we limit it to the numPeaks
# largest ones
def getPeaks(data, numPeaks, runs):
    # Should be doable in preprocessing
    lenRuns = map(lambda run: len(run), runs)

    # User-proofing. Could probably limit input
    numPeaks = numPeaks if numPeaks <= len(runs) else len(runs)

    # Would be using linear argpartsort if we were running not 2013 builds.
    # Can you tell I'm bitter?
    ind = argsort(array(lenRuns))[-numPeaks:]

    # This is inelegant
    peakIdx, peaks = ([], [])
    for run in array(runs)[ind]:
        idx = findMax(data, run)
        peakIdx.append(idx)
        peaks.append(data[idx])

    max_index, max_value = max(enumerate(data), key=itemgetter(1))

    # Maybe unnecessary precaution to make sure that the max point is used in
    # the fit (a run wouldn't be found if the peak were sufficiently narrow)
    maxInfo = []
    if max_value not in peaks:
        if peaks:
            min_index = min(enumerate(peaks), key=itemgetter(1))[0]
            peaks[min_index] = max_value
            peakIdx[min_index] = max_index
        else:
            peakIdx.append(max_index)
            peaks.append(max_value)
            maxInfo = [max_index, max_value]

    return [peaks, peakIdx, maxInfo]


# Checking for inflection points doesn't work because some data points don't 
# follow the trend line; this groups consecutive data points by bucket, which
# need to be recalculated following an adjustment.
def getRuns(data, step):
    # runMap maps each data point to the run that contains it
    zeroRuns, nonZeroRuns, runs, currRun, runMap = ([], [], [], [], [])
    currBuck = getBucket(data[0], step)
    run_idx = 0

    for idx, point in enumerate(data):
        newBuck = getBucket(point, step)
        if newBuck == currBuck:
            currRun.append(idx)
        else:
            # Plotting the end of a run
            if DEBUG:
                plt.axvline(x=idx)

            # Three points make a curve!
            if len(currRun) > 2:
                runs.append(currRun)
                run_idx += 1
                if currBuck == 0:
                    zeroRuns.append(len(runs) - 1)
                else:
                    nonZeroRuns.append(currRun)

            currRun = [idx]
            currBuck = newBuck

        runMap.append(run_idx)

    # Effectively flushing the cache. There has to be a way to factor this out
    if len(currRun) > 2:
        runs.append(currRun)
        if currBuck == 0:
            zeroRuns.append(len(runs) - 1)
        else:
            nonZeroRuns.append(currRun)

    return [runs, zeroRuns, nonZeroRuns, runMap]


# A whole rigmarole to collapse multiple pedestals.
# It assumes that the pedestal is the bucket with the most elements
def adjustData(data, step):
    normalizedAdjustment = 0

    bucketCount = zeros(NUM_BUCKS)
    bucketContents = [[] for i in xrange(0, NUM_BUCKS)]
    buckets = zeros(len(data))

    for idx, element in enumerate(data):
        bucket = getBucket(element, step)
        bucketCount[bucket] += 1
        bucketContents[bucket] += [idx]
        buckets[idx] = bucket

    zeroBucket = max(enumerate(bucketCount), key=itemgetter(1))[0]

    needsAdjustment = False

    for idx, bucket in enumerate(buckets):
        if bucket < zeroBucket:
            # Inefficient to set this every time, but eh
            needsAdjustment = True
            # Sets them arbitrarily to the value of the first element in the
            # zero bucket, to eliminate the double pedestal
            data[idx] = data[bucketContents[zeroBucket][0]]

    if needsAdjustment:
        normalizedAdjustment = min(data[bucketContents[zeroBucket]])
        data = data - normalizedAdjustment
        step = max(data) / NUM_BUCKS

    return [data, step, normalizedAdjustment]


################################################################################
# So this is a giant clusterfuck of logic where I try to autodetect peaks by 
# detecting "runs" of points, defined as a group of 3 or more consecutive points
# that belong to the same  bucket, while simultaneously tagging those runs that
# belong to the "zeroeth" bucket (the pedestal).
#
# Note that the format of the guess is a list of the form:
# [m, b, center_0, amplitude_0, width_0,..., center_k, amplitude_k, width_k]
# where m and b correspond to the line parameters in y = m*x + b
# and every following group of three corresponds to a gaussian
################################################################################ 
def getGuess(xdata, ydata, step, useZeros, numPeaks):
    runs, zeroRuns, nonZeroRuns, runMap = getRuns(ydata, step)

    peaks, peakIdx, maxInfo = (getPeaks(ydata, numPeaks, nonZeroRuns)
                               if not useZeros
                               else getPeaks(ydata, numPeaks, runs))

    # Gross error handling for the case where the max val isn't detected as a
    # peak (making sure it's added to runs in the correct order)
    if maxInfo:
        maxIdx = maxInfo[0]
        if runMap[maxIdx] >= len(runs):
            runs.append(maxIdx)
        else:
            runs[runMap[maxIdx]].append(maxIdx)

    # This plots my guesses for the peaks
    if DEBUG:
        for idx in peakIdx:
            plt.axvline(x=idx)

    widths = findWidths(xdata, peakIdx, runs, runMap)

    guess = findLine(zeroRuns, runs, xdata, ydata)

    # This plots my guess for the line
    if DEBUG:
        plt.plot([guess[0] * j + guess[1] for j in xdata], '--')

    for idx, amp in enumerate(peaks):
        guess += [xdata[peakIdx[idx]], amp, widths[idx] / 4]

        # Plot my initial guesses for the gaussian(s)
        if DEBUG:
            plt.plot([gaussian(i, xdata[peakIdx[idx]], widths[idx] / 4, amp)
                      for i in xdata], '--')

    return [guess, len(runs) if useZeros else len(nonZeroRuns)]


def processData(data):
    firstAdjustment = min(data)

    # Removing the pedestal
    data = data - firstAdjustment

    # Define the step size by the number of vertical buckets
    step = max(data) / NUM_BUCKS

    data, step, normalizedAdjustment = adjustData(data, step)

    # This prints my vertical buckets
    if DEBUG:
        for i in xrange(1, NUM_BUCKS):
            plt.plot([i * step for _ in xrange(0, len(data))])

    totalAdjustment = firstAdjustment + normalizedAdjustment

    return [data, totalAdjustment, step]


def getFit(data, x, guess):
    # Someday the ability to bound the fit will be available...
    # ...When we're no longer running builds from 2013 :P
    return curve_fit(genGaussSum, x, data, p0=guess)[0]


def plotFit(popt, totalAdjustment, x, isGuess):
    print "adjustment: " + str(totalAdjustment)

    # Print and plot the optmized line fit.
    # Note that popt has the same format as the guess, meaning that the first
    # two parameters are the m and b of the line, respectively
    print "line: " + "m = " + str(popt[0]) + ", b = " + str(popt[1])
    plt.plot([popt[0] * j + popt[1] + totalAdjustment for j in x], '--')

    # Print and plot the optimized gaussian fit(s)
    # Again, the first two elements were the line, and each gaussian is a
    # subsequent group of 3 elements (hence starting at index 2 and incrementing
    # by 3)
    for i in xrange(2, len(popt), 3):
        print ("gaussian " + str(i // 3) + ": center = " + str(popt[i])
               + ", amplitude = " + str(popt[i + 1]) + ", width = "
               + str(popt[i + 2]))
        plt.plot([gaussian(j, popt[i], popt[i + 2], popt[i + 1])
                  + totalAdjustment for j in x], '--')

    if not isGuess:
        fit = genGaussSum(x, *popt)
        plt.plot(fit + totalAdjustment, linewidth=2)

    show()


# This is inelegant, but the only way I could think of to get around the
# inability to pass bounds into curve_fit
def checkBounds(popt, data, x):
    # Assert that the y intercept of the line is bounded by min and max of the
    # data
    assert max(data) >= popt[1] >= min(data)

    for i in xrange(2, len(popt), 3):
        assert x[0] <= popt[i] <= x[-1]
        assert min(data) <= popt[i + 1] <= max(data)


if __name__ == "__main__":
    try:
        filepath = argv[1]
    except IndexError:
        print "Usage: " + argv[0] + " [path to XCor matlab file]"
        exit()

    try:
        axdata = loadmat(filepath)
    except (IOError, ValueError):
        print "Invalid input"
        exit()

    ampList = extract(axdata, 'ampList')

    # TODO: Ask Axel if he needs these
    # posList = extract(axdata, 'posList')
    # ampstdList = extract(axdata, 'ampstdList')

    numPeaks = input("Number of gaussians to fit: ")

    x = range(0, len(ampList))

    # Plot the data
    plt.plot(ampList, '.', marker='o')

    data, totalAdjustment, step = processData(ampList)

    guess = getGuess(x, data, step, False, numPeaks)[0]

    if DEBUG:
        print "----------DEBUG MODE----------"
        plotFit(guess, totalAdjustment, x, True)
    else:
        try:
            popt = getFit(data, x, guess)
            checkBounds(popt, data, x)
            print "----------RESULT----------"
            plotFit(popt, totalAdjustment, x, False)
        except (RuntimeError, AssertionError):
            print "----------OPTIMIZATION NOT FOUND; RETURNING GUESS----------"
            plotFit(guess, totalAdjustment, x, True)
