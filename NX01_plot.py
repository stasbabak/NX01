#!/usr/bin/env python

"""
Created by stevertaylor
Copyright (c) 2014 Stephen R. Taylor

Code contributions by Rutger van Haasteren (piccard) and Justin Ellis (PAL/PAL2).

"""

from __future__ import division
import numpy as np
from numpy import *
import os
import optparse
import matplotlib
#matplotlib.use('TkAgg')
matplotlib.use('macosx')
import matplotlib.pyplot as plt
import scipy.interpolate as interp
from matplotlib.ticker import FormatStrFormatter, LinearLocator, NullFormatter, NullLocator, AutoMinorLocator
import matplotlib.ticker
import NX01_bayesutils as bu
#import pylab
import scipy
from scipy.interpolate import interp1d
import acor

def getclr(dat, nedges, cfvalue):
    # get the bound
    counts, edges = np.histogram(dat, nedges)
    counts = np.float64(np.array(counts))/len(dat)
    ind_center = np.argmax(counts)
    maxc = counts[ind_center]
    cedges = (edges[0:-1]+edges[1:])*0.5
    sort_ind = np.argsort(-counts)
    cflevel = np.cumsum(counts[sort_ind])
    ind_cflevel = cflevel <= cfvalue
    conf_data = cedges[sort_ind][ind_cflevel]
    left = np.min(conf_data)
    right = np.max(conf_data)
    return cedges[ind_center], left, right

def getupper(dat, nedges, cfvalue):

    # Create the histogram
    hist, xedges = np.histogram(dat, nedges)
    xedges = np.delete(xedges, -1) + 0.5*(xedges[1] - xedges[0])

    # CDF
    cdf = np.cumsum(hist/hist.sum())

    # interpolate
    x = np.linspace(xedges.min(), xedges.max(), 10000)
    ifunc = interp.interp1d(xedges, cdf, kind='linear')
    y = ifunc(x)

    x2max = y[-1]
    bound = cfvalue
    for i in reversed(range(len(y))):
        if y[i] <= bound:
            x2max = x[i]
            break

    return x2max



parser = optparse.OptionParser(description = 'NX01 - Precursor to the PANTHER Group ENTERPRISE project')

parser.add_option('--chaindir', dest='chaindir', action='store', type=str,
                   help='Provide the directory name containing chain_1.txt')

(args, x) = parser.parse_args()

path = '/Volumes/File Storage/EPTAanisotropy_files/' #os.getcwd()

chain = np.loadtxt(path+args.chaindir+'/chain_1.0.txt') #np.loadtxt(path+'/chains_Analysis/'+args.chaindir+'/chain_1.0.txt')

#######################################################
# trying out intelligent burning-in and thinning here
#######################################################
'''loglike = chain[-3]
dim = chain.shape[1]-4
likemax = loglike.max()

burniter = np.where(loglike > (likemax-dim/2.))[0]
burntdata = chain[burniter:,:]

corrlength, mean, sigma = acor.acor(burntdata[:,0])  # considering GWB strain-amplitude parameter
indsamples = burntdata[::int(corrlength)]
chain = indsamples #indamp = indsamples[:,0]'''

############################################################
# Doing a quick plot to manually cut-off the burn-in stage
############################################################
plt.rcParams['text.usetex'] = True

if 'Gam4p33' in args.chaindir:
    bu.makePostPlots_show(chain,ndim=1,labels=[r'$A_h$']) # checking Agwb
    plt.show()
else:
    bu.makePostPlots_show(chain,ndim=2,labels=[r'$A_h$', r'$\gamma$']) # checking Agwb and gam_gwb
    plt.show()

var = raw_input("\n How many iterations do you want to cut-off as burn-in?: ")  #should be zero for intelligent burning-in
print "\n"
var = int(var)

if 'Gam4p33' in args.chaindir:

    # make a 1D posterior plot of the GWB amplitude
    fig, ax = plt.subplots()
    bu.makesubplot1d(ax, chain[var:,0], bins=60)
    plt.xlabel('$\log_{10}(A_h)$', fontsize=20)
    plt.tick_params(labelsize=18)
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    plt.show()

    if 'MLnoise' in args.chaindir:
        noisetag = 'ML-noise'
    else:
        noisetag = 'Varied-noise'

    if 'Lmax0' in args.chaindir:
        ltag = 'isotropic search'
    else:
        st = args.chaindir.split('_')
        for ii in st:
            if 'Lmax' in ii:
                LMAX = int(ii[-1])

        ltag = 'anisotropic search ($l_{\mathrm{max}}=\;$'+str(LMAX)+')'
        
    
    # make a CDF plot to get the upper limit
    bu.makeCDF(10.0**chain[var:,0]/1.e-15, linestyle='k-', linewidth=3.0, labels=None, legendbox=True,\
               title=noisetag+' '+ltag+', $\gamma_{\mathrm{GWB}}=13/3$')
    plt.xlabel(r'$A_h\; /\; 10^{-15}$', fontsize=20)
    plt.ylabel('Cumulative probability', fontsize=20)
    plt.tick_params(labelsize=18)
    plt.show()

    # if lmax!=0 make a plot of the power spectrum
    if 'Lmax0' not in args.chaindir:
        plt.rcParams['text.usetex'] = True
        fig, ax = plt.subplots()
        #if 'EvAnis' in args.chaindir:
        #clm = chain[var:,-4 - 5*( (LMAX+1)**2 - 1):-4]  # assuming 5 windows
        #else:
        clm = chain[var:,-3-(LMAX+1)**2:-4]
        #clm = chain[var:,-4 - 1*( (LMAX+1)**2 - 1):-4 - 0*( (LMAX+1)**2 - 1)]
        print len(clm[0])
        Cl = [0.0]*(LMAX+1)
        Cl[0] = 4.0*np.pi*np.ones(clm.shape[0])
        ll = np.arange(LMAX+1)
        for ii in ll[:-1]:
            Cl[ii+1] = np.sum( clm[:,(ll[ii]+1)**2-1:(ll[ii+1]+1)**2-1]**2 / (2*ll[ii+1]+1.) , axis=1)

        Cl = np.array(Cl)
        delta_ell = np.linspace(0.0,LMAX*1.0,1000)
        func=np.zeros((len(clm), len(delta_ell)))
        for ii in range(len(clm)):
                tmp = interp1d(ll, Cl[:,ii]/(4.0*np.pi) )
                func[ii,:] = tmp(delta_ell) 

        xx=np.tile(delta_ell,len(clm))
        yy=func.reshape((len(xx),))

        # get the central and bound of the lines
        func_c = np.zeros(len(delta_ell))
        #func_l = np.zeros(len(delta_ell[10:]))
        func_r = np.zeros(len(delta_ell[10:]))
        row,col = func.shape

        for ii in range(len(delta_ell)):
            dat = func[:,ii]
            func_c[ii] = np.mean(dat)

        for ii in range(10,len(delta_ell)):
            dat = func[:,ii]
            #c,l,r = getclr(dat, 100, 0.95)
            r = getupper(dat, 100, 0.95)
            #func_l[ii-10] = l
            func_r[ii-10] = r

        #2D hist of the line distributions
        H, xedges, yedges = np.histogram2d(xx, yy, bins=(100, 100),
                                    range=([0.0,1.0*LMAX], [0.0,1.0]))

        H = H.transpose()

        x2edges = (xedges[:-1] + xedges[1:]) / 2
        y2edges = (yedges[:-1] + yedges[1:]) / 2
        mxx, mxy = np.meshgrid(x2edges, y2edges)
        plt.contourf(mxx, mxy, H/np.sum(H), 50, cmap='Greys')
        plt.colorbar()

        plt.plot(delta_ell, func_c, linestyle='solid', color='black', linewidth=3.0)
        #plt.plot(delta_ell[10:], func_l, linestyle='dashed', color='red', linewidth=3.0)
        plt.plot(delta_ell[10:], func_r, linestyle='dashed', color='red', linewidth=3.0)

        ax.set_xticks(ll)
        plt.tick_params(labelsize=18)
        plt.xlabel('$l$', fontsize=20)
        plt.ylabel('$C_l/4\pi$', fontsize=20)
        plt.show()

        ################################
        ################################

        fig, ax = plt.subplots()
        plt.contourf(mxx, mxy, H/np.sum(H), 50, cmap='Greys')
        plt.colorbar()

        plt.plot(delta_ell, func_c, linestyle='solid', color='black', linewidth=3.0)
        #plt.plot(delta_ell[10:], func_l, linestyle='dashed', color='red', linewidth=3.0)
        plt.plot(delta_ell[10:], func_r, linestyle='dashed', color='red', linewidth=3.0)
        #fil = open('global_lmax4_upperlimits_prior.dat','w')
        #for ii in range(len(func_r)):
        #    print>>fil, delta_ell[10:][ii], func_r[ii]

        ax.set_xticks(ll)
        plt.xlim(xmin=1)
        tmplist = delta_ell.tolist()
        indl1 = min(range(len(tmplist)), key=lambda i: abs(tmplist[i]-1.0))
        plt.ylim(0.0, np.max(func_r[indl1:]))
        plt.tick_params(labelsize=18)
        plt.xlabel('$l$', fontsize=20)
        plt.ylabel('$C_l/4\pi$', fontsize=20)
        plt.show()

        
        ################################
        ################################

        for ii in st:
            if 'pct' in ii:
                snr_tag_ext = ii

        psrlocs = np.loadtxt('PsrPos_SNR_{0}.txt'.format(snr_tag_ext),usecols=[1,2])

        bu.makeSkyMap(clm, lmax=LMAX, psrs=psrlocs)
        plt.show()

        
else:

    # make a triplot of the GWB amplitude and spectral index
    bu.triplot(chain[var:,0:2], labels=[r'$\log_{10}(A_h)$', r'$\gamma$'])
    plt.show()

    # make an upper limit plot for the GWB amplitude as a function of spectral index
    bu.upperlimitplot2d(chain[var:,0], chain[var:,1], sigma=0.68, bins=30, logA=True, \
                     labels=[r'$\gamma=3-2\alpha$', r'$A_h$'], hold=True, linestyle='solid', \
                     color='black', linewidth=3.0, leglabel=r'68\% upper-limit')
    bu.upperlimitplot2d(chain[var:,0], chain[var:,1], sigma=0.95, bins=30, logA=True, \
                     labels=[r'$\gamma=3-2\alpha$', r'$A_h$'], hold=True, linestyle='dashed', \
                     color='black', linewidth=3.0, leglabel=r'95\% upper-limit')
    plt.grid(which='major')
    plt.grid(which='minor')
    plt.legend(fancybox=True, shadow=True)
    plt.tick_params(labelsize=20)
    plt.show()

    # if lmax!=0 make a plot of the power spectrum
    if 'Lmax0' not in args.chaindir:
        st = args.chaindir.split('_')
        for ii in st:
            if 'Lmax' in ii:
                LMAX = int(ii[-1])

        plt.rcParams['text.usetex'] = True
        fig, ax = plt.subplots()
        clm = chain[var:,-3-(LMAX+1)**2:-4] 
        Cl = [0.0]*(LMAX+1)
        Cl[0] = 4.0*np.pi*np.ones(clm.shape[0])
        ll = np.arange(LMAX+1)
        for ii in ll[:-1]:
            Cl[ii+1] = np.sum( clm[:,(ll[ii]+1)**2-1:(ll[ii+1]+1)**2-1]**2 / (2*ll[ii+1]+1.) , axis=1)

        Cl = np.array(Cl)
        delta_ell = np.linspace(0.0,LMAX*1.0,1000)
        func=np.zeros((len(clm), len(delta_ell)))
        for ii in range(len(clm)):
                tmp = interp1d(ll, Cl[:,ii]/(4.0*np.pi) )
                func[ii,:] = tmp(delta_ell) 

        xx=np.tile(delta_ell,len(clm))
        yy=func.reshape((len(xx),))

        # get the central and bound of the lines
        func_c = np.zeros(len(delta_ell))
        #func_l = np.zeros(len(delta_ell[10:]))
        func_r = np.zeros(len(delta_ell[10:]))
        row,col = func.shape

        for ii in range(len(delta_ell)):
            dat = func[:,ii]
            func_c[ii] = np.mean(dat)

        for ii in range(10,len(delta_ell)):
            dat = func[:,ii]
            #c,l,r = getclr(dat, 100, 0.95)
            r = getupper(dat, 100, 0.95)
            #func_l[ii-10] = l
            func_r[ii-10] = r

        #2D hist of the line distributions
        H, xedges, yedges = np.histogram2d(xx, yy, bins=(100, 100),
                                    range=([0.0,1.0*LMAX], [0.0,1.0]))

        H = H.transpose()

        x2edges = (xedges[:-1] + xedges[1:]) / 2
        y2edges = (yedges[:-1] + yedges[1:]) / 2
        mxx, mxy = np.meshgrid(x2edges, y2edges)
        plt.contourf(mxx, mxy, H/np.sum(H), 50, cmap='Greys')
        plt.colorbar()

        plt.plot(delta_ell, func_c, linestyle='solid', color='black', linewidth=3.0)
        #plt.plot(delta_ell[10:], func_l, linestyle='dashed', color='red', linewidth=3.0)
        plt.plot(delta_ell[10:], func_r, linestyle='dashed', color='red', linewidth=3.0)
        print delta_ell[10:], func_r

        ax.set_xticks(ll)
        plt.tick_params(labelsize=18)
        plt.xlabel('$l$', fontsize=20)
        plt.ylabel('$C_l/4\pi$', fontsize=20)
        plt.show()

        ################################
        ################################

        fig, ax = plt.subplots()
        plt.contourf(mxx, mxy, H/np.sum(H), 50, cmap='Greys')
        plt.colorbar()

        plt.plot(delta_ell, func_c, linestyle='solid', color='black', linewidth=3.0)
        #plt.plot(delta_ell[10:], func_l, linestyle='dashed', color='red', linewidth=3.0)
        plt.plot(delta_ell[10:], func_r, linestyle='dashed', color='red', linewidth=3.0)

        ax.set_xticks(ll)
        plt.xlim(xmin=1)
        plt.ylim(ymin=0.0)
        plt.tick_params(labelsize=18)
        plt.xlabel('$l$', fontsize=20)
        plt.ylabel('$C_l/4\pi$', fontsize=20)
        plt.show()

        ################################
        ################################

        for ii in st:
            if 'pct' in ii:
                snr_tag_ext = ii

        psrlocs = np.loadtxt('PsrPos_SNR_{0}.txt'.format(snr_tag_ext),usecols=[1,2])

        bu.makeSkyMap(clm, lmax=LMAX, psrs=psrlocs)
        plt.show()
        

        

        
    
