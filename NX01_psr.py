#!/usr/bin/env python

"""
Created by stevertaylor
Copyright (c) 2014 Stephen R. Taylor

Code contributions by Rutger van Haasteren (piccard) and Justin Ellis (PAL/PAL2).

"""

import numpy as np
import sys, os, glob
import libstempo as T2
import ephem
from ephem import *
import NX01_utils as utils
from collections import OrderedDict
import cPickle as pickle

f1yr = 1./(86400.0*365.25)

class PsrObj(object):
    T2psr = None
    parfile = None
    timfile = None
    noisefile = None
    psr_locs = None
    toas = None
    toaerrs = None
    res = None
    obs_freqs = None
    G = None
    Mmat = None
    sysflagdict = None
    Fred = None
    Fdm = None
    Ftot = None
    diag_white = None
    res_prime = None
    Ftot_prime = None
    Gc = None
    Te = None
    name = "J0000+0000"
    Gres = None
    epflags = None
    detsig_avetoas = None
    detsig_Uinds = None

    def __init__(self, t2obj):
        self.T2psr = t2obj
        self.parfile = None
        self.timfile = None
        self.noisefile = None
        self.psr_locs = None
        self.toas = None
        self.toaerrs = None
        self.res = None
        self.obs_freqs = None
        self.G = None
        self.Mmat = None
        self.Fred = None
        self.Fdm = None
        self.Ftot = None
        self.diag_white = None
        self.res_prime = None
        self.Ftot_prime = None
        self.Gc = None
        self.Te = None
        self.Umat = None
        self.Uinds = None
        self.name = "J0000+0000"
        self.sysflagdict = None
        self.Gres = None
        self.epflags = None
        self.detsig_avetoas = None
        self.detsig_Uinds = None

    """
    Initialise the libstempo object.
    """
    def grab_all_vars(self, jitterbin=10., makeGmat=False, fastDesign=True): # jitterbin is in seconds

        print "--> Processing {0}".format(self.T2psr.name)
        
        # basic quantities
        self.name = self.T2psr.name
        self.toas = np.double(self.T2psr.toas())
        self.res = np.double(self.T2psr.residuals())
        self.toaerrs = np.double(self.T2psr.toaerrs) * 1e-6
        self.obs_freqs = np.double(self.T2psr.ssbfreqs())
        self.Mmat = np.double(self.T2psr.designmatrix())

        if 'pta' in self.T2psr.flags():
            if 'NANOGrav' in list(set(self.T2psr.flagvals('pta'))):
                # now order everything
                try:
                    isort, iisort = utils.argsortTOAs(self.toas, self.T2psr.flagvals('group'),
                                                      which='jitterext', dt=jitterbin/86400.)
                except KeyError:
                    isort, iisort = utils.argsortTOAs(self.toas, self.T2psr.flagvals('f'),
                                                      which='jitterext', dt=jitterbin/86400.)
        
                # sort data
                self.toas = self.toas[isort]
                self.toaerrs = self.toaerrs[isort]
                self.res = self.res[isort]
                self.obs_freqs = self.obs_freqs[isort]
                self.Mmat = self.Mmat[isort, :]

                print "--> Initial sorting of data."
              
        # get the sky position
        if 'RAJ' and 'DECJ' in self.T2psr.pars():
            self.psr_locs = [np.double(self.T2psr['RAJ'].val),np.double(self.T2psr['DECJ'].val)]
        elif 'ELONG' and 'ELAT' in self.T2psr.pars():
            fac = 180./np.pi
            # check for B name
            if 'B' in self.name:
                epoch = '1950'
            else:
                epoch = '2000'
            coords = Equatorial(Ecliptic(str(self.T2psr['ELONG'].val*fac),
                                         str(self.T2psr['ELAT'].val*fac)),
                                         epoch=epoch)
            self.psr_locs = [float(repr(coords.ra)),float(repr(coords.dec))]

        print "--> Grabbed the pulsar position."
        ################################################################################################
            
        # These are all the relevant system flags used by the PTAs.
        system_flags = ['group','sys','i','f']
        self.sysflagdict = OrderedDict.fromkeys(system_flags)

        # Put the systems into a dictionary which 
        # has the locations of their toa placements.
        for systm in self.sysflagdict:
            try:
                if systm in self.T2psr.flags():
                    sys_uflagvals = list(set(self.T2psr.flagvals(systm)))
                    self.sysflagdict[systm] = OrderedDict.fromkeys(sys_uflagvals)
                    for kk,subsys in enumerate(sys_uflagvals):
                        self.sysflagdict[systm][subsys] = \
                          np.where(self.T2psr.flagvals(systm)[isort] == sys_uflagvals[kk])
            except KeyError:
                pass

        # If we have some NANOGrav data, then separate
        # this off for later ECORR assignment.
        if 'pta' in self.T2psr.flags():
            pta_names = list(set(self.T2psr.flagvals('pta')))
            pta_mask = [self.T2psr.flagvals('pta')[isort]==ptaname for ptaname in pta_names]
            pta_maskdict = OrderedDict.fromkeys(pta_names)
            for ii,item in enumerate(pta_maskdict):
                pta_maskdict[item] = pta_mask[ii]
            if len(pta_names)!=0 and ('NANOGrav' in pta_names):
                try:
                    nanoflagdict = OrderedDict.fromkeys(['nano-f'])
                    nano_flags = list(set(self.T2psr.flagvals('group')[pta_maskdict['NANOGrav']]))
                    nanoflagdict['nano-f'] = OrderedDict.fromkeys(nano_flags)
                    for kk,subsys in enumerate(nano_flags):
                        nanoflagdict['nano-f'][subsys] = \
                          np.where(self.T2psr.flagvals('group')[isort] == nano_flags[kk])
                    self.sysflagdict.update(nanoflagdict)
                except KeyError:
                    nanoflagdict = OrderedDict.fromkeys(['nano-f'])
                    nano_flags = list(set(self.T2psr.flagvals('f')[pta_maskdict['NANOGrav']]))
                    nanoflagdict['nano-f'] = OrderedDict.fromkeys(nano_flags)
                    for kk,subsys in enumerate(nano_flags):
                        nanoflagdict['nano-f'][subsys] = \
                          np.where(self.T2psr.flagvals('f')[isort] == nano_flags[kk])
                    self.sysflagdict.update(nanoflagdict)
                    
        
        # If there are really no relevant flags,
        # then just make a full list of the toa indices.
        if np.all([self.sysflagdict[sys] is None for sys in self.sysflagdict]):
            print "No relevant flags found"
            print "Assuming one overall system for {0}\n".format(self.T2psr.name)
            self.sysflagdict[self.T2psr.name] = OrderedDict.fromkeys([self.T2psr.name])
            self.sysflagdict[self.T2psr.name][self.T2psr.name] = np.arange(len(self.toas))

        print "--> Processed all relevant flags plus associated locations."
        ##################################################################################################

        if 'pta' in self.T2psr.flags():
            if 'NANOGrav' in pta_names:
                # now order everything
                try:
                    #isort_b, iisort_b = utils.argsortTOAs(self.toas, self.T2psr.flagvals('group')[isort],
                    #which='jitterext', dt=jitterbin/86400.)
                    flags = self.T2psr.flagvals('group')[isort]
                except KeyError:
                    #isort_b, iisort_b = utils.argsortTOAs(self.toas, self.T2psr.flagvals('f')[isort],
                    #which='jitterext', dt=jitterbin/86400.)
                    flags = self.T2psr.flagvals('f')[isort]
        
                # sort data
                #self.toas = self.toas[isort_b]
                #self.toaerrs = self.toaerrs[isort_b]
                #self.res = self.res[isort_b]
                #self.obs_freqs = self.obs_freqs[isort_b]
                #self.Mmat = self.Mmat[isort_b, :]
                #flags = flags[isort_b]
                
                print "--> Sorted data."
    
                # get quantization matrix
                avetoas, self.Umat, Ui = utils.quantize_split(self.toas, flags, dt=jitterbin/86400., calci=True)
                print "--> Computed quantization matrix."

                self.detsig_avetoas = avetoas.copy()
                self.detsig_Uinds = utils.quant2ind(self.Umat)

                # get only epochs that need jitter/ecorr
                self.Umat, avetoas, aveflags = utils.quantreduce(self.Umat, avetoas, flags)
                print "--> Excized epochs without jitter."

                # get quantization indices
                self.Uinds = utils.quant2ind(self.Umat)
                self.epflags = flags[self.Uinds[:, 0]]

                print "--> Checking TOA sorting and quantization..."
                print utils.checkTOAsort(self.toas, flags, which='jitterext', dt=jitterbin/86400.)
                print utils.checkquant(self.Umat, flags)
                print "...Finished checks."

        # perform SVD of design matrix to stabilise
        if fastDesign:
            print "--> Stabilizing the design matrix the fast way..."

            Mm = self.Mmat.copy()
            norm = np.sqrt(np.sum(Mm ** 2, axis=0))
            Mm /= norm

            self.Gc = Mm
        else:
            print "--> Performing SVD of design matrix for stabilization..."   

            u,s,v = np.linalg.svd(self.Mmat)

            if makeGmat:
                self.G = u[:,len(s):len(u)]
                self.Gres = np.dot(self.G.T, self.res)

            self.Gc =  u[:,:len(s)]

        print "--> Done reading in pulsar :-) \n"

    def makeFred(self, nmodes, Ttot):
        
        self.Fred = utils.createFourierDesignmatrix_red(self.toas, nmodes, Tspan=Ttot)

    def makeFdm(self, nmodes, Ttot):
        
        self.Fdm = utils.createFourierDesignmatrix_dm(self.toas, nmodes, self.obs_freqs, Tspan=Ttot)
    
    def makeFtot(self, nmodes, Ttot):
        
        self.Fred = utils.createFourierDesignmatrix_red(self.toas, nmodes, Tspan=Ttot)
        self.Fdm = utils.createFourierDesignmatrix_dm(self.toas, nmodes, self.obs_freqs, Tspan=Ttot)

        self.Ftot = np.append(self.Fred, self.Fdm, axis=1)

    def makeTe(self, nmodes, Ttot, makeDM=False):

        self.Fred = utils.createFourierDesignmatrix_red(self.toas, nmodes, Tspan=Ttot)

        if makeDM==True:
            self.Fdm = utils.createFourierDesignmatrix_dm(self.toas, nmodes, self.obs_freqs, Tspan=Ttot)
            self.Ftot = np.append(self.Fred, self.Fdm, axis=1)

        else:
            self.Ftot = self.Fred

        self.Te = np.append(self.Gc, self.Ftot, axis=1)

    def two_comp_noise(self, mlerrors):
        
        efac_bit = np.dot(self.G.T, np.dot( np.diag(mlerrors**2.0), self.G ) )
        equad_bit = np.dot(self.G.T,self.G)
        Lequad = np.linalg.cholesky(equad_bit)
        Lequad_inv = np.linalg.inv(Lequad)
        sand = np.dot(Lequad_inv, np.dot(efac_bit, Lequad_inv.T))
        u,s,v = np.linalg.svd(sand)
        proj = np.dot(u.T, np.dot(Lequad_inv, self.G.T))
        ########
        self.diag_white = s
        self.res_prime = np.dot(proj, self.res)
        if self.Ftot is not None:
            self.Ftot_prime = np.dot(proj, self.Ftot)
        else:
            self.Ftot_prime = np.dot(proj, self.Fred)



######################
######################

class PsrObjFromH5(object):
    h5Obj = None
    psr_locs = None
    parfile = None
    timfile = None
    noisefile = None
    toas = None
    toaerrs = None
    res = None
    obs_freqs = None
    G = None
    Mmat = None
    sysflagdict = None
    Fred = None
    Fdm = None
    Ftot = None
    diag_white = None
    res_prime = None
    Ftot_prime = None
    Gc = None
    Te = None
    name = "J0000+0000"
    Gres = None
    epflags = None
    detsig_avetoas = None
    detsig_Uinds = None
    t2efacs = None
    t2equads = None
    t2ecorrs = None
    parRedamp = None
    parRedind = None
    efacs = None
    equads = None
    ecorrs = None
    Redamp = None
    Redind = None

    def __init__(self, h5Obj):
        self.h5Obj = h5Obj
        self.parfile = None
        self.timfile = None
        self.noisefile = None
        self.psr_locs = None
        self.toas = None
        self.toaerrs = None
        self.res = None
        self.obs_freqs = None
        self.G = None
        self.Mmat = None
        self.Fred = None
        self.Fdm = None
        self.Ftot = None
        self.diag_white = None
        self.res_prime = None
        self.Ftot_prime = None
        self.Gc = None
        self.Te = None
        self.Umat = None
        self.Uinds = None
        self.name = "J0000+0000"
        self.sysflagdict = None
        self.Gres = None
        self.epflags = None
        self.detsig_avetoas = None
        self.detsig_Uinds = None
        self.t2efacs = None
        self.t2equads = None
        self.t2ecorrs = None
        self.parRedamp = None
        self.parRedind = None
        self.efacs = None
        self.equads = None
        self.ecorrs = None
        self.Redamp = None
        self.Redind = None

    """
    Read data from hdf5 file into pulsar object
    """
    def grab_all_vars(self, rescale=True): 

        print "--> Extracting {0} from hdf5 file".format(self.h5Obj['name'].value)
        
        # basic quantities
        self.name = self.h5Obj['name'].value
        self.parfile = self.h5Obj['parfilepath'].value
        self.timfile = self.h5Obj['timfilepath'].value
        try:
            self.noisefile = self.h5Obj['noisefilepath'].value
        except:
            self.noisefile = None
        
        self.toas = self.h5Obj['TOAs'].value
        self.res = self.h5Obj['postfitRes'].value
        self.toaerrs = self.h5Obj['toaErr'].value
        self.obs_freqs = self.h5Obj['freq'].value

        self.psr_locs = self.h5Obj['psrlocs'].value

        self.Mmat = self.h5Obj['designmatrix'].value
        try:
            self.G = self.h5Obj['Gmatrix'].value
            self.Gres = self.h5Obj['Gres'].value
        except:
            self.G = None
            self.Gres = None
        self.Gc = self.h5Obj['GCmatrix'].value
        try:
            self.Umat = self.h5Obj['QuantMat'].value
            self.Uinds = self.h5Obj['QuantInds'].value
            self.epflags = self.h5Obj['EpochFlags'].value
            self.detsig_avetoas = self.h5Obj['DetSigAveToas'].value
            self.detsig_Uinds = self.h5Obj['DetSigQuantInds'].value
        except:
            self.Umat = None
            self.Uinds = None
            self.epflags = None
            self.detsig_avetoas = None
            self.detsig_Uinds = None

        self.sysflagdict = pickle.loads(self.h5Obj['SysFlagDict'].value)

        # Let's rip out EFACS, EQUADS and ECORRS from parfile
        parlines = self.h5Obj['parfile'].value.split('\n')
        t2efacs = []
        t2equads = []
        t2ecorrs = []
        for ll in parlines:
            if 'T2EFAC' in ll:
                t2efacs.append([ll.split()[2], np.double(ll.split()[3])])
            if 'T2EQUAD' in ll:
                t2equads.append([ll.split()[2], np.double(ll.split()[3])*1e-6])
            if 'ECORR' in ll:
                t2ecorrs.append([ll.split()[2], np.double(ll.split()[3])*1e-6])

        self.t2efacs = OrderedDict(t2efacs)
        self.t2equads = OrderedDict(t2equads)
        self.t2ecorrs = OrderedDict(t2ecorrs)

        # Let's rip out the red noise properties if present
        self.parRedamp = 1e-20
        self.parRedind = 0.0
        for ll in parlines:
            if 'RNAMP' in ll:
                self.parRedamp = ll.split()[1] # 1e-6 * f1yr * np.sqrt(12.0*np.pi**2.0) * np.double(ll.split()[1]) 
            if 'RNIDX' in ll:
                self.parRedind = -np.double(ll.split()[1])

        # Let's also find single pulsar analysis EFACS, EQUADS, ECORRS
        self.Redamp = 1e-20
        self.Redind = 0.0
        if self.noisefile is not None:
            noiselines = self.h5Obj['noisefile'].value.split('\n')
            efacs = []
            equads = []
            ecorrs = []
            for ll in noiselines:
                if 'efac' in ll:
                    efacs.append([ll.split()[0].split('efac-')[1], np.double(ll.split()[1])])
                if 'equad' in ll:
                    equads.append([ll.split()[0].split('equad-')[1], 10.0**np.double(ll.split()[1])])
                if 'jitter' in ll:
                    ecorrs.append([ll.split()[0].split('jitter_q-')[1], 10.0**np.double(ll.split()[1])])

            self.efacs = OrderedDict(efacs)
            self.equads = OrderedDict(equads)
            self.ecorrs = OrderedDict(ecorrs)

            # Let's get the red noise properties from single-pulsar analysis
            self.Redamp = 1e-20
            self.Redind = 0.0
            for ll in noiselines:
                if 'RN-Amplitude' in ll:
                    self.Redamp = 10.0**np.double(ll.split()[1]) # 1e-6 * f1yr * np.sqrt(12.0*np.pi**2.0) * np.double(ll.split()[1]) 
                if 'RN-spectral-index' in ll:
                    self.Redind = np.double(ll.split()[1])

            # Time to rescale the TOA uncertainties by single-pulsar EFACS and EQUADS
            systems = self.sysflagdict['f']
            if rescale==True:
                tmp_errs = self.toaerrs.copy()

                for sysname in systems:
                    tmp_errs[systems[sysname]] *= self.efacs[sysname] 

                ###

                t2equad_bit = np.ones(len(tmp_errs))
                for sysname in systems:
                    t2equad_bit[systems[sysname]] *= self.equads[sysname]

                ###

                tmp_errs = np.sqrt( tmp_errs**2.0 + t2equad_bit**2.0 )
                self.toaerrs = tmp_errs
        

        print "--> Done extracting pulsar from hdf5 file :-) \n"

    def makeFred(self, nmodes, Ttot):
        
        self.Fred = utils.createFourierDesignmatrix_red(self.toas, nmodes, Tspan=Ttot)

    def makeFdm(self, nmodes, Ttot):
        
        self.Fdm = utils.createFourierDesignmatrix_dm(self.toas, nmodes, self.obs_freqs, Tspan=Ttot)
    
    def makeFtot(self, nmodes, Ttot):
        
        self.Fred = utils.createFourierDesignmatrix_red(self.toas, nmodes, Tspan=Ttot)
        self.Fdm = utils.createFourierDesignmatrix_dm(self.toas, nmodes, self.obs_freqs, Tspan=Ttot)

        self.Ftot = np.append(self.Fred, self.Fdm, axis=1)

    def makeTe(self, nmodes, Ttot, makeDM=False):

        self.Fred = utils.createFourierDesignmatrix_red(self.toas, nmodes, Tspan=Ttot)

        if makeDM==True:
            self.Fdm = utils.createFourierDesignmatrix_dm(self.toas, nmodes, self.obs_freqs, Tspan=Ttot)
            self.Ftot = np.append(self.Fred, self.Fdm, axis=1)

        else:
            self.Ftot = self.Fred

        self.Te = np.append(self.Gc, self.Ftot, axis=1)

    def two_comp_noise(self, mlerrors):
        
        efac_bit = np.dot(self.G.T, np.dot( np.diag(mlerrors**2.0), self.G ) )
        equad_bit = np.dot(self.G.T,self.G)
        Lequad = np.linalg.cholesky(equad_bit)
        Lequad_inv = np.linalg.inv(Lequad)
        sand = np.dot(Lequad_inv, np.dot(efac_bit, Lequad_inv.T))
        u,s,v = np.linalg.svd(sand)
        proj = np.dot(u.T, np.dot(Lequad_inv, self.G.T))
        ########
        self.diag_white = s
        self.res_prime = np.dot(proj, self.res)
        if self.Ftot is not None:
            self.Ftot_prime = np.dot(proj, self.Ftot)
        else:
            self.Ftot_prime = np.dot(proj, self.Fred)
