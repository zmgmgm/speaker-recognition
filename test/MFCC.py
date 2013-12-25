#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
# File: MFCC.py
# Date: Tue Dec 24 20:37:10 2013 +0800
# Author: Yuxin Wu <ppwwyyxxc@gmail.com>

POWER_SPECTRUM_FLOOR = 1e-100

from numpy import *
import numpy.linalg as linalg


def hamming(n):
    """ Generate a hamming window of n points as a numpy array.  """
    return 0.54 - 0.46 * cos(2 * pi / n * (arange(n) + 0.5))

class MFCCExtractor(object):

    def __init__(self, fs, FFT_SIZE=2048, n_bands=40, n_coefs=13,
                 PRE_EMPH=0.95, verbose = False):
        self.PRE_EMPH = PRE_EMPH
        self.fs = fs
        self.n_bands = n_bands
        self.coefs = n_coefs
        self.FFT_SIZE = FFT_SIZE

        self.FRAME_LEN = int(0.02 * fs)
        self.FRAME_SHIFT = int(0.01 * fs)

        self.window = hamming(self.FRAME_LEN)


        self.M, self.CF = self._mel_filterbank()

        dctmtx = MFCCExtractor.dctmtx(self.n_bands)
        self.D = dctmtx[1: self.coefs + 1]
        self.invD = linalg.inv(dctmtx)[:, 1: self.coefs + 1]

        self.verbose = verbose
        # The inverse DCT matrix. Change the index to [0:COEFS] if you want to keep the 0-th coefficient


    def dprint(self, msg):
        """ Debug print """
        if self.verbose:
            print(msg)

    def extract(self, signal, diff=False):
        """
        Extract MFCC coefficients of the sound x in numpy array format.
        """
        if signal.ndim > 1:
            self.dprint("INFO: Input signal has more than 1 channel; the channels will be averaged.")
            signal = mean(signal, axis=1)
        frames = (len(signal) - self.FRAME_LEN) / self.FRAME_SHIFT + 1
        feature = []
        for f in xrange(frames):
            # Windowing
            frame = signal[f * self.FRAME_SHIFT : f * self.FRAME_SHIFT +
                           self.FRAME_LEN] * self.window
            # Pre-emphasis
            frame[1:] -= frame[:-1] * self.PRE_EMPH
            # Power spectrum
            X = abs(fft.fft(frame, self.FFT_SIZE)[:self.FFT_SIZE / 2 + 1]) ** 2
            X[X < POWER_SPECTRUM_FLOOR] = POWER_SPECTRUM_FLOOR  # Avoid zero
            # Mel filtering, logarithm, DCT
            X = dot(self.D, log(dot(self.M, X)))
            feature.append(X)
        feature = row_stack(feature)
        # Show the MFCC spectrum before normalization
        # Mean & variance normalization
        if feature.shape[0] > 1:
            mu = mean(feature, axis=0)
            sigma = std(feature, axis=0)
            feature = (feature - mu) / sigma

        if diff:
            ret = []
            for feat in feature:
                diff = lambda f: [x - f[i - 1] for i, x in enumerate(f)][1:]
                diff1 = diff(feat)
                diff2 = diff(diff1)
                ret.append(concatenate((feat, diff1, diff2)))
            return ret
        return feature

    def _mel_filterbank(self):
        """
        Return a Mel filterbank matrix as a numpy array.
        Ref. http://www.ifp.illinois.edu/~minhdo/teaching/speaker_recognition/code/melfb.m
        """
        f0 = 700.0 / self.fs
        fn2 = int(floor(self.FFT_SIZE / 2))
        lr = log(1 + 0.5 / f0) / (self.n_bands + 1)
        CF = self.fs * f0 * (exp(arange(1, self.n_bands + 1) * lr) - 1)
        bl = self.FFT_SIZE * f0 * (exp(array([0, 1, self.n_bands, self.n_bands + 1]) * lr) - 1)
        b1 = int(floor(bl[0])) + 1
        b2 = int(ceil(bl[1]))
        b3 = int(floor(bl[2]))
        b4 = min(fn2, int(ceil(bl[3]))) - 1
        pf = log(1 + arange(b1, b4 + 1) / f0 / self.FFT_SIZE) / lr
        fp = floor(pf)
        pm = pf - fp
        M = zeros((self.n_bands, 1 + fn2))
        for c in xrange(b2 - 1, b4):
            r = int(fp[c] - 1)
            M[r, c+1] += 2 * (1 - pm[c])
        for c in xrange(b3):
            r = int(fp[c])
            M[r, c+1] += 2 * pm[c]
        return M, CF

    @staticmethod
    def dctmtx(n):
        """ Return the DCT-II matrix of order n as a numpy array.  """
        x, y = meshgrid(range(n), range(n))
        D = sqrt(2.0 / n) * cos(pi * (2 * x + 1) * y / (2 * n))
        D[0] /= sqrt(2)
        return D

extractors = dict()
def get_mfcc_extractor(fs, verbose = False):
    global extractors
    if fs not in extractors:
        extractors[fs] = MFCCExtractor(fs, verbose = verbose)
        if verbose:
            print("new extractor " . format(fs))
    return extractors[fs]

def extract(fs, signal=None):
    """accept two argument, or one as a tuple"""
    if signal is None:
        assert type(fs) == tuple
        fs, signal = fs[0], fs[1]
    return get_mfcc_extractor(fs).extract(signal)
