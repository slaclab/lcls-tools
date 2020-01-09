#!/usr/local/lcls/package/python/current/bin/python

from epics import PV,caget,caput
import sys
from time import sleep
import scipy.ndimage as snd
from scipy.optimize import curve_fit
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import math
import datetime
from  scipy.io import loadmat
from fitGaussian import *
from math import pi
from devicesDict import *
import itertools

#TODO: rename the file to LCLS_Devices.py

class Movers(object):
    def __init__(self, device=None):
        #Note: deviceDict = 'device_name': (moverCommand,moverRB,insertVal,retractVal, insertRB, retractRB)
        self.deviceDict = pmDict.copy()
        self.deviceDict.update(shutterDict)
        try:
            self.moverCommand=PV(self.deviceDict[device][0])
            self.moverRB=PV(self.deviceDict[device][1])
            self.insertVal=self.deviceDict[device][2]
            self.retractVal=self.deviceDict[device][3]
            self.insertRB=self.deviceDict[device][4]
            self.retractRB=self.deviceDict[device][5]
            self.checkDelay=1
            self.numberChecks=25         
        except:      
            print 'Missing or invalid device name. Please choose one of the following valid device name: '\
                  + 'GunRF, MechShutLCLS1, LHShut, TD11, BYKIK, AOM, MechShutLCLS2, '\
                  + 'YAG01-03, YAGG1, YAGS1, YAGS2, OTRH1, OTRH2, OTR01-04, OTR11, OTR12, OTR21.'

    def moving_done(self):
        print 'Done moving'

    def checking(self, callback=moving_done,readback=None):
        if callable(callback):
            def pv_callback(value, cb_info=None, *args, **kwargs):
                if value == readback:
                    callback()
                    callback_id, pv = cb_info
                    pv.remove_callback(callback_id)
            self.moverRB.add_callback(pv_callback)
            print 'Device is moving... patience you must have, my young padawan. Wait for done moving confirmation you must.'

    def insert(self,callback=moving_done):
        '''Insert yag screen and make sure it reads back inserted'''
        if self.isInserted() ==  False:
            self.moverCommand.put(self.insertVal)
            self.checking(callback=self.moving_done,readback=self.insertRB)
        else: print 'Device already inserted.'
        return

    def retract(self,callback=moving_done):
        '''Retract yag screen and make sure it reads back extracted'''
        if self.isInserted() ==  True:
            self.moverCommand.put(self.retractVal)
            self.checking(callback=self.moving_done,readback=self.retractRB)
        else: print 'Device already inserted.'
        return

    def isInserted(self):
        position=self.moverCommand.get()
        if position==self.insertVal and self.moverRB.get()==self.insertRB: return True
        else: return False

class ProMo(Movers):
    def __init__(self, device=None, *args, **kwargs):
        #Note: Profile Monitor dict = 'device_name': (moverCommand,moverRB,insertVal,retractVal, insertRB, retractRB)
        Movers.__init__(self, device)
        try: 
            promo_device = self.deviceDict[device][0].rsplit(':',1)#This variable is dedicated for YAG and OTR. 
            self.promoPVImage=PV(promo_device[0]+':Image:ArrayData')
            self.resolution=caget(promo_device[0]+":RESOLUTION")
            self.ysize,self.xsize=caget(promo_device[0]+':ArraySizeY_RBV'),caget(promo_device[0]+':ArraySizeX_RBV')
            self.lamp=PV(promo_device[0]+':TGT_LAMP_PWR')
            if 'GUN' in promo_device[0]:
                self.connect_shutter=shutterDict['MechShutLCLS2'][0]
            else:
                self.connect_shutter=shutterDict['MechShutLCLS1'][0]
        except:
            print 'Missing or invalid device name. Please choose one of the following valid device name: '\
                  + 'YAG01B, YAG01-03, YAGG1, YAGS1, YAGS2, OTRH1, OTRH2, OTR01-04, OTR11, OTR12, OTR21.'
        self.images=[]#Initialize
        self.bg_img=None

    def acquireImage(self, num_shots=1, acquireBackground=False, fliplr=True, flipud=False, lamp=False, plot=False, plotmm=False, calc_centroid=False, calc_rms=False,load=None,plotstat=False,plotstatum=False):
        if load is not None:
            self.load_from_file(load)
        else:
            lamp_init=self.lamp.get()#Initial lamp stage and assuming lamp at off stage
            if lamp==False:
                self.lamp.put(0)
            elif lamp:
                self.lamp.put(1)
                sleep(1)
            
            self.images = []
            for i in range(num_shots):
                if acquireBackground and (caget(self.connect_shutter)==0):#If want a background and mps shutter is open
                    caput(self.connect_shutter, 1)
                    sleep(2.1)
                    image=self.promoPVImage.get()
                    caput(self.connect_shutter, 0)
                else:
                    image=self.promoPVImage.get()
                image=np.reshape(image,(self.ysize,self.xsize)) 
                if flipud:
                    image=np.flipud(image)
                image=np.fliplr(image) #Note: Flip L&R is set as default. 
                self.images.append(image)

            if self.lamp.get() != lamp_init:
                self.lamp.put(lamp_init)

            self.images = np.array(self.images)

        if plot:
            self.plotimg(self.images.mean(axis=0))
        elif plotmm:
            self.plotimg(self.images.mean(axis=0),plotmm=True)

        centroid = None
        rms = None
        if calc_centroid:
            centroid = self.calculateCent(self.images)
        if calc_rms or plotstat or plotstatum:
            rms  = self.calculateRMS(self.images,plotstat=plotstat,plotstatum=plotstatum)
        return centroid, rms

    def plotimg(self,image,plotmm=False):
        if plotmm:
            '''Convert pixel to mm to match with mathlab profile monitor '''
            ticks_max_x=math.ceil(round(self.images.shape[2]*(self.resolution/1000)/2)/2)*2
            ticks_max_y=math.floor(round(self.images.shape[1]*(self.resolution/1000)/2)/2)*2
            ticks_mm_x=np.arange(-ticks_max_x,ticks_max_x+0.5,0.5)
            ticks_mm_y=np.arange(-ticks_max_y,ticks_max_y+0.5,0.5)           
            ticks_px_x=[i/(self.resolution/1E3)+self.images.shape[2]/2 for i in ticks_mm_x]
            ticks_px_y=[j/(self.resolution/1E3)+self.images.shape[1]/2 for j in ticks_mm_y]
            plt.xticks(ticks_px_x,ticks_mm_x)
            plt.yticks(ticks_px_y,np.flipud(ticks_mm_y))
            plt.xlabel('x (mm)')
            plt.ylabel('y (mm)')
        else:
            plt.xlabel('x (pixel)')
            plt.ylabel('y (pixel)')

#        plt.title('Profile Monitor '+self.device+' '+str(datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")))
        plt.imshow(image)
        plt.show()

    def changeROI(self):
        pass

    def calculateCent(self,images):
        '''Calculate center of mass x and y coordinates for image'''
        lastx, lasty=0.0,0.0#kludge to start
        xcents,ycents=[],[]
        for image in images:
            centers = snd.center_of_mass(image > (image.mean()+4*image.std()))
            ycent,xcent=centers[0],centers[1]
            xcents.append(xcent)
            ycents.append(ycent)
            lastx,lasty=xcents[-1],ycents[-1]
        xcent=np.mean(xcents)
        ycent=np.mean(ycents)
        return xcent,ycent

    def load_from_file(self, filename):
        #image=loadmat('ProfMon-CAMR_LGUN_950-2019-06-12-165617.mat')#Hardcode file's name here.
        image = loadmat(filename)
        imagedata=image['data'][0][0][1]
        imagedata=np.flipud(imagedata)
        print 'blah'
        self.images=np.array([imagedata])
        self.ysize,self.xsize=self.images.shape[1],self.images.shape[2]
        self.resolution=image['data'][0][0][9]
        
    def calculateRMS(self,images,useCalibration=True,plotimgmm=False,plotimg=False,plotstat=False,plotstatum=False):
        '''Calculate center of mass x and y coordinates for image'''
        xs,ys,sigma_xs,sigma_ys,ampl_xs,ampl_ys = [],[],[],[],[],[]
        
        for image in images:
            xcent, ycent = self.calculateCent([image])
            xdataslice=image[int(ycent)]#Take slice of xdata using ycentroid position
            xdata=range(image.shape[1])#Make simple xdata list with values from 0 to 639 (length 640)
            ydataslice=[]
            for xline in image: ydataslice.append(xline[xcent])
            ydata=range(image.shape[0])

            xdataslice, totalAdjustment, step = processData(xdataslice)
            guess = getGuess(xdata,xdataslice, step, False, numPeaks=1)[0]
            x0_x, a_x, sigma_x = getFit(xdataslice, xdata, guess)[2:]
            ydataslice, totalAdjustment, step = processData(ydataslice)
            guess = getGuess(ydata,ydataslice, step, False, numPeaks=1)[0]
            x0_y, a_y, sigma_y = getFit(ydataslice, ydata, guess)[2:]
            xs.append(x0_x)
            ys.append(x0_y)
            sigma_xs.append(sigma_x)
            sigma_ys.append(sigma_y)
            ampl_xs.append(a_x)
            ampl_ys.append(a_y)
        xcent, ycent, sigma_x, sigma_y, a_x, a_y = map(np.mean, [xs, ys, sigma_xs, sigma_ys, ampl_xs, ampl_ys])

        if plotstat:
            self.plotcentrms(image,xcent,ycent,sigma_x,sigma_y,xdata,ydata,xdataslice,ydataslice,a_x,a_y,x0_x,x0_y,plotum=False)
        elif plotstatum:
            self.plotcentrms(image,xcent,ycent,sigma_x,sigma_y,xdata,ydata,xdataslice,ydataslice,a_x,a_y,x0_x,x0_y,plotum=True)
        return  sigma_x, sigma_y

    def plotcentrms(self,image,xcent,ycent,sigma_x,sigma_y,xdata,ydata,xdataslice,ydataslice,a_x,a_y,x0_x,x0_y,plotum=False):
        fig = plt.figure(figsize=(8,6))
        grid = plt.GridSpec(2,2,width_ratios=[2,2],height_ratios=[2,2])
        main_img = fig.add_subplot(grid[:-1,1:])
        y_px = fig.add_subplot(grid[:-1,0], sharey=main_img)
        x_px = fig.add_subplot(grid[-1,1:], sharex=main_img)
        stat = fig.add_subplot(grid[-1,0])

        main_img.imshow(image)
        t = np.linspace(0,2*pi,100)
        main_img.plot(xcent+sigma_x*np.cos(t),ycent+sigma_y*np.sin(t), 'r')
        main_img.plot(xcent,ycent, '+',ms=20,mew=1)
        x_px.plot(xdata, [self.gaus(x,a_x,x0_x,sigma_x) for x in xdata], 'r--'),x_px.plot(xdata,xdataslice, 'b')
        y_px.plot([self.gaus(y,a_y,x0_y,sigma_y) for y in ydata], ydata, 'r--'),y_px.plot(ydataslice,ydata, 'b')

        if plotum:
            x_px.set_xlabel('x (um)'),y_px.set_ylabel('y (um)')
            stat.plot(range(5), color = 'silver'),stat.axis('off')
            stat.text(1,3, 'xmean = '+str(round(abs(self.xsize/2-xcent)*self.resolution,2))+' um')
            stat.text(1,2.5, 'ymean = '+str(round(abs(self.ysize/2-ycent)*self.resolution,2))+' um')
            stat.text(1,2, 'xrms = '+str(round(sigma_x*self.resolution,2))+' um')
            stat.text(1,1.5, 'yrms = '+str(round(sigma_y*self.resolution,2))+' um')

            ticks_max_x=math.floor(round((self.xsize)*(self.resolution/1E3)/2)/2)*2
            ticks_max_y=math.floor(round((self.ysize)*(self.resolution/1E3)/2)/2)*2
            ticks_mm_x=np.arange(-ticks_max_x,ticks_max_x+1,0.5)*1E3
            ticks_mm_y=np.arange(-ticks_max_y,ticks_max_y+0.5,0.5)*1E3
            ticks_px_x=[i/(self.resolution/1E3)+self.xsize/2 for i in ticks_mm_x/1E3]
            ticks_px_y=[j/(self.resolution/1E3)+self.ysize/2 for j in ticks_mm_y/1E3]
 
            x_px.set_xticks(ticks_px_x),x_px.set_xticklabels(ticks_mm_x)
            y_px.set_yticks(ticks_px_y),y_px.set_yticklabels(ticks_mm_y)
            main_img.set_xticks(ticks_px_x),main_img.set_xticklabels(ticks_mm_x)
            main_img.set_yticks(ticks_px_y),main_img.set_yticklabels(ticks_mm_y)
        else:
            x_px.set_xlabel('x (Pixel)'),y_px.set_ylabel('y (Pixel)')
            stat.plot(range(5), color = 'silver'),stat.axis('off')
            stat.text(1,3, 'xmean = '+str(round(xcent,2))+' Pixel')
            stat.text(1,2.5, 'ymean = '+str(round(ycent,2))+' Pixel')
            stat.text(1,2, 'xrms = '+str(round(sigma_x,2))+' Pixel')
            stat.text(1,1.5, 'yrms = '+str(round(sigma_y,2))+' Pixel')

        x_px.set_xlim(xcent-150,xcent+150)
        y_px.set_ylim(ycent-150,ycent+150)
        plt.show()

    def gaus(self,x,a,x0,sigma):  
        return a*np.exp(-(x-x0)**2/(2*sigma**2))#Function just to return gaussian form for curve_fit

class ChargeMeas(object):
    def __init__(self, device="TORO:GUNB:360"):
        self.checkDelay,self.numberChecks=0.1,50#Delay between checks for PV value change, number of times to check PV (wanted to manually control this and optimize)
        self.scaleFactor=1.0#For scaling from number electrons to coulumbs
        if 'BPMS' in device: 
            self.chargeReadback=PV(device+':TMIT_SLOW')
            self.scaleFactor=1.60217733e-7#Scale num electrons to pC
        elif 'SIOC' in device: self.chargeReadback=PV(device)
        elif ('TORO' in device) or ('FARC' in device): self.chargeReadback=PV(device+':CHRG')
        else: raise ValueError('Specify a valid charge measurement device- ICT, Faraday cup or BPM (i.e. supply "BPMS:IN20:371")')
        print 'Initialized'

    def acquireCharge(self,numberShots=1):
        '''Read charge from chosen device and average multiple shots if specified, return charge in pC'''
        charge=self.chargeReadback.get()*self.scaleFactor
        try:
            numberShots=int(numberShots)
        except:
            print 'Num. shots is not a number; returning one shot only'
            return charge
        if numberShots > 1:
            charges=[charge]
            for i in range(numberShots-1):
                j=1
                while charges[-1]==self.chargeReadback.get()*self.scaleFactor:
                    j+=1
                    sleep(self.checkDelay)
                    if j>self.numberChecks: raise Exception('Charge readback not updating; multiple shot request cancelled')
                charges.append(self.chargeReadback.get()*self.scaleFactor)
            charge=np.mean(charges)
        return charge

class Laser(object):
    def __init__(self,device='Vitara1'):
        '''SIOC:SYS2:ML00:AO011 sch. SP, SIOC:SYS2:ML00:AO012 sch. offset, AO013 zero phase ps, MLOO:CALCOUT007 sets timing in ps corresponding to previous values'''
        #Note: laser dict = 'device_name' : (LaserPhaseSetting,LaserPhaseOffset,rfFeedback,shutterRB)
        try:            
            self.LaserPhaseSetting = PV(laserDict[device][0])
            self.LaserPhaseOffset = PV(laserDict[device][1])
            self.vitara1FB,self.vitara2FB = PV(laserDict['Vitara1'][2]),PV(laserDict['Vitara2'][2])
            self.driveoscFB = PV('ALRM:SYS2:AMPLITUDE1:ALHBERR')
            self.checkDelay,self.numberChecks=0.1,50
            self.initPhaseSetting,self.initPhaseOffset=self.readPhase()
            self.phaseTol=0.2
            self.UVLaserMode=PV('LASR:LR20:1:UV_LASER_MODE')
            #self.activeLaser=self.determineActiveLaser()
            #print 'Active laser is #'+str(self.activeLaser)
        except:
            print 'Missing or invalid device name. Please choose one of the following valid device name: Vitara1 or Vitara2.'
    
    def determineActiveLaser(self):
        if self.UVLaserMode.get() == 0: return 'COHERENT #1'
        elif self.UVLaserMode.get() == 1: return 'COHERENT #2'
        elif self.UVLaserMode.get() == 2: return 'BOTH'
        elif self.UVLaserMode.get() == 3: return 'BOTH (C1 Flipper)'
        else: return 'NONE'
                  
    def readPhase(self):
        '''Return laser phase setting and readback in that order; average readback if multiple shots requested'''
        setting,offset=self.LaserPhaseSetting.get(),self.LaserPhaseOffset.get()
        return setting,offset

    def setPhase(self,newSetting):
        '''Set laser phase'''
        try:
            newSetting=float(newSetting)
        except:
            raise ValueError('Please enter a valid number!')
        self.LaserPhaseSetting.put(newSetting)
        sleep(0.6)#Give laser phase time to set

    def setOffset(self,newSetting):
        '''Set laser offset; this is in ps and should be the true zero phase in ps'''
        try:
            newSetting=float(newSetting)
        except:
            raise ValueError('Please enter a valid number!')
        self.LaserPhaseOffset.put(newSetting)

class RFgun(object):
    def __init__(self, device=None):
        #Note: dictionary = (PhaseSetting, PhaseReadBack, AmplitudeSetting, AmplitudeReadBack)
        try:
            self.PhaseSetting=PV(rfDict[device][0])
            self.PhaseReadback=PV(rfDict[device][1])
            self.AmplitudeSetting=PV(rfDict[device][2])
            self.AmplitudeReadback=PV(rfDict[device][3])
            self.checkDelay,self.numberChecks=0.1,50
            self.Tol=0.2
        except:
            print 'Missing or invalid device name. Please choose one of the following valid device name: LCLS1L1S, LCLS1L1X, LCLS2'

    def readPhase(self,numberShots=1):
        '''Return gun phase setting and readback in that order; average readback if multiple shots requested'''
        setting,readback=self.PhaseSetting.get(),self.PhaseReadback.get()
        try:
            numberShots=int(numberShots)
        except:
            print 'Num. shots is not a number; returning one shot only'
            return setting,readback
        if numberShots > 1:
            readbacks=[readback]
            for i in range(numberShots-1):
                j=1
                while readbacks[-1]==self.PhaseReadback.get():
                    j+=1
                    sleep(self.checkDelay)
                    if j>self.numberChecks: raise Exception('Phase readback not updating; multiple shot request cancelled')
                readbacks.append(self.PhaseReadback.get())
            print readbacks
            readback=np.mean(readbacks)
        return setting,readback

    def setPhase(self,newSetting):
        '''Set buncher phase'''
        try: newSetting=float(newSetting)
        except: raise ValueError('Please enter a valid number!')
        self.PhaseSetting.put(newSetting)
        return True####TESTING BEFORE THE REAL THING!!!!!!####
        #return self.checkPhase()

    def checkPhase(self):
        '''Checks to see that phase readback has converged to phase setting (within 0.2deg)'''
        for i in range(self.numberChecks):
            sleep(self.checkDelay)
            setting,rb=self.readPhase()
            if abs(setting-rb) < self.Tol:
                return True
        return False

    def readAmplitude(self, numberShots=1):
        readback=self.AmplitudeReadback.get()
        if numberShots==1: return readback
        readbacks==[readback]
        for i in range(numberShots-1):
            j=1
            while readbacks[-1]==self.AmplitudeReadback.get():
                j+=1
                sleep(self.checkDelay)
                if j>self.numberChecks: raise Exception('Amplitude readback not updating; multiple shot request cancelled')
            readbacks.append(self.AmplitudeReadback.get())
        readback=np.mean(readbacks)
        return np.mean(readbacks)     

class Buncher(RFgun):
    def __init__(self,device='Buncher'):
        RFgun.__init__(self,device)
        try:
            self.OffsetSetting=PV(rfDict[device][4])
        except:
            print 'Missing or invalid buncher name. Please enter (Buncher) for the LCLS2 buncher.'

    def setOffset(self,newSetting):
        '''Set phase offset for buncher'''
        try: newSetting=float(newSetting)
        except: raise ValueError('Please enter a valid number!')
        self.OffsetSetting.put(newSetting)

    def flipPhase(self):
        '''Sets phase to 180 degrees away from current phase, dependent on current setting'''
        currentPhase=self.readPhase()[0]
        if (currentPhase <= 0):
            return self.setPhase(currentPhase+180)
        elif (currentPhase >0):
            return self.setPhase(currentPhase-180)
        else:
            return False

    def rfOnOff(self, request="deact"):
        '''deacts or reacts the buncher, depending on argument provided'''
        if request=="deact" or request=="d":
            self.AmpActive=caget('ACCL:GUNB:455:AOPEN')
            caput('ACCL:GUNB:455:AOPEN', 0)
        elif request=="activate" or request=="a":
            try: reactAmplitude=self.AmpActive
            except: 
                print 'No known react amplitude, no action taken'
                return
            caput('ACCL:GUNB:455:AOPEN', self.AmpActive)
        else:
            print "Option not specified, no action taken.  Provide argument request='deact' or request='activate'"

class Magnet(object):
    def __init__(self,magnet="XCOR:GUNB:293"):
        self.magnetSetting=PV(magnet+':BCTRL')
        self.magnetReadback=PV(magnet+':BACT')
        self.controlFunction=PV(magnet+':CTRL')
        self.magnetConfig=PV(magnet+':BCON')
        self.checkDelay,self.numberChecks,self.checkBTolerance=0.1,80,0.00005
        
    def readB(self):
        '''Return magnet setting and readback'''
        return self.magnetSetting.get(),self.magnetReadback.get()

    def setBcon(self,newSetting):
        try:
            newSetting=float(newSetting)    
            self.magnetConfig.put(newSetting)
        except:
            raise ValueError('Please enter a valid number!')    
        return self.checkB

    def trim(self):
        self.controlFunction.put(1)

    def perturb(self):
        self.controlFunction.put(2)

    def Bcon2Bdes(self): 
        '''Return  BConfig value and assign to Bdesire'''
        bcon = self.magnetConfig.get()
        self.magnetSetting.put(bcon)
        return self.checkB()

    def save(self):
        self.controlFunction.put(4)

    def load(self):
        '''Load previous saved Bdes'''
        self.controlFunction.put(5)

    def undo(self):
        self.controlFunction.put(6)

    def dac_zero(self):
        self.controlFunction.put(7)

    def calib(self):
        self.controlFunction.put(8)

    def stdz(self):
        self.controlFunction.put(9)

    def reset(self):
        self.controlFunction.put(10)    

    def setBdes(self,newSetting,want_trim = False):
        '''Set magnet field and trim'''
        try:
            newSetting=float(newSetting)    
            self.magnetSetting.put(newSetting)
        except:
            raise ValueError('Please enter a valid number!')

        if want_trim:
            self.trim()
            print 'Trim applied'

        return self.checkB()

    def checkB(self):
        '''Checks to see that magnet readback has converged to magnet setting (within tolerance)'''
        for i in range(self.numberChecks):
            sleep(self.checkDelay)
            setting,rb=self.readB()
            if abs(setting-rb) < self.checkBTolerance:
                return True
        return False       

class Mirror(object):
    def __init__(self,mirror=None):
        #Note: mirror dict = 'device_name' : (mirrorSettingH,mirrorSettingV)
        try: 
            self.mirrorSettingH,self.mirrorReadbackH=PV(mirrorDict[mirror][0]),PV(mirrorDict[mirror][0]+'.RBV')
            self.mirrorSettingV,self.mirrorReadbackV=PV(mirrorDict[mirror][1]),PV(mirrorDict[mirror][1]+'.RBV')
            self.checkDelay,self.numberChecks,self.checkPosTolerance=0.1,50,0.001
            self.pvname=mirror
        except:
            print 'Missing or invalid mirror name. Mirrors name goes as follow: (LCLS1 or LCLS2) + mirror name. EX: LCLS1M12 '

    def get(self):
        '''Return mirror setting and readback'''
        return {'HPosition': self.mirrorSettingH.get(),'VPostion': self.mirrorSettingV.get()}
    

    def putH(self,newSetting):
        '''Set mirror'''
        try:
            newSetting=float(newSetting)
        except:
            raise ValueError('Please enter a valid number!')
        self.mirrorSettingH.put(newSetting)
        return self.checkPos()

    def putV(self,newSetting):
        '''Set mirror'''
        try:
            newSetting=float(newSetting)
        except:
            raise ValueError('Please enter a valid number!')
        self.mirrorSettingV.put(newSetting)
        return self.checkPos()
    

    def checkPos(self):
        '''Checks to see that mirror readback has converged to mirror setting (within tolerance)'''
        for i in range(self.numberChecks):
            sleep(self.checkDelay)
            settingH,rbH=self.mirrorSettingH.get(),self.mirrorReadbackH.get()
            settingV,rbV=self.mirrorSettingV.get(),self.mirrorReadbackV.get()
            if abs(settingH-rbH) < self.checkPosTolerance:
                return True
            if abs(settingV-rbV) < self.checkPosTolerance:
                return True
        return False    

class BPM(object):
    #Note: BPM dict = 'device_name' : (xreadback,yreadback,tmitreadback)
    def __init__(self,bpm=None):
        try:
            self.xreadback=PV(bpmDict[bpm][0])
            self.yreadback=PV(bpmDict[bpm][1])
            self.tmitreadback=PV(bpmDict[bpm][2])
            self.checkDelay,self.numberChecks=0.01,105
        except:
            print 'Missing or invalid device name. Please choose one of the following valid device name: BPM1B or BPM2B.'
            

    def readBPM(self,numberShots=1):
        'Reads xpos, ypos and tmit and returns all three (with averaging if requested by user, position in um)'''
        xRBs,yRBs,tmitRBs=[],[],[]
        try:
            numberShots=int(numberShots)
        except:
            print 'Num. shots is not a number; returning one shot only'
            return xreadback,yreadback,tmitreadback
        if numberShots == 1:
            return self.xreadback.get()*1000.0,self.yreadback.get()*1000.0,self.tmitreadback.get()
        if numberShots > 1:
            for i in range(numberShots):
                xRBs.append(self.xreadback.get())
                yRBs.append(self.yreadback.get())
                tmitRBs.append(self.tmitreadback.get())
                j=0
                while xRBs[-1]==self.xreadback.get():
                    j+=1
                    sleep(self.checkDelay)
                    if j>self.numberChecks: raise Exception('Phase readback not updating; multiple shot request cancelled')
            xRB=np.mean(xRBs)
            yRB=np.mean(yRBs)
            tmitRB=np.mean(tmitRBs)
        return {"Xposition":xRB*1000.0,"Yposition":yRB*1000.0,"TMIT":tmitRB}

class Klystron(object):
    def __init__(self):
        self.checkDelay,self.numberChecks=0.1,50
        self.phaseTol=0.2
        return

    def desireKlystron(self,sector,klystron):
        try:
            PVList,kLyst,msgList,pdesList,phasList=[],[],[],[],[]
            user_input = [(index1,i) for index1,index2 in zip(sector,klystron) for i in index2]
            for s,k in user_input:
                 l = (str(s)+':'+str(k))
                 beamcode1_clt=PV('KLYS:LI'+l+'1:BEAMCODE1_TCTL')
                 last_msg=PV('KLYS:LI'+l+'1:BEAMCODE1_msg')
                 pdes=PV('KLYS:LI'+l+'1:PDES')
                 phas=PV('KLYS:LI'+l+'1:PHAS')
                 kLyst+=[l]
                 PVList+=[beamcode1_clt]
                 msgList+=[last_msg]
                 pdesList+=[pdes]
                 phasList+=[phas]
            return kLyst,PVList,msgList,pdesList,phasList
        except: print 'Invalid input. Sector and Klystron must be input as a list.'\
                      + ' Single Klystron must be enter as following: sector=[##],klystron=[[#]] and not klystron=[#].'

    def changestates(self,sector,klystron,state=None):
        kLyst,PVList,msgList,pdesList,phasList = self.desireKlystron(sector,klystron)
        for (k,p,m) in zip(kLyst,PVList,msgList):
            klyst_num = k
            p.put(state)
            klyst_msg = m.get()
            print str(klyst_num) +' ' +str(klyst_msg)
               
    def deActivate(self,sector,klystron):
        self.changestates(sector,klystron,state=0)
   
    def reActivate(self,sector,klystron):
        self.changestates(sector,klystron,state=1)
 
    def isActivate(self,sector,klystron):
        kLyst,PVList,msgList,pdesList,phasList = self.desireKlystron(sector,klystron)
        for (k,p) in zip(kLyst,PVList): 
            num = k
            status = p.get()
            if status==0: print str(num) + ' Deactivate'
            elif status==1: print str(num) + ' Activate'
  
    def readPhase(self,sector,klystron,numberShots=1):
        kLyst,PVList,msgList,pdesList,phasList = self.desireKlystron(sector,klystron)
        for (k,s,r) in zip(kLyst,pdesList,phasList):
            klyst_num = k
            setting=s.get()
            readback=r.get()
            try:
                numberShots=int(numberShots)
            except:
                print 'Num. shots is not a number; returning one shot only'
                return k,setting,readback
            if numberShots > 1:
                readbacks=[]
                for i in range(numberShots):
                    readbacks.append(readback)
                    j=0
                    while readbacks[-1]==self.stationPhaseReadback.get():
                        j+=1
                        sleep(self.checkDelay)
                        if j>self.numberChecks: raise Exception('Phase readback not updating; multiple shot request cancelled')
                readback=np.mean(readbacks)
            print k,readback,setting

    def setPhase(self,sector,klystron,newSetting):
        try: newSetting=float(newSetting)
        except: raise ValueError('Please enter a valid number!')
        pdes=PV('KLYS:LI'+str(sector)+':'+str(klystron)+'1:PDES')
        trim=PV('KLYS:LI'+str(sector)+':'+str(klystron)+'1:TRIMPHAS')
        pdes.put(newSetting)
        trim.put(1)
        return self.checkPhase(sector,klystron)

    def checkPhase(self,sector,klystron):
        '''Checks to see that phase readback has converged to phase setting (within 0.2deg)'''
        for i in range(self.numberChecks):
            sleep(self.checkDelay)
            k,rb,setting=self.readPhase(sector,klystron)
            if abs(setting-rb) < self.phaseTol:
                return True
        return False

class GeneralStation(object):
    def __init__(self,cm='DUMMY',cav='DUMMY'):
        #self.stationPhaseSetting,self.stationPhaseReadback=PV('Dummy'),PV('Dummy')
        self.checkDelay,self.numberChecks=0.1,50
        self.phaseTol=0.2

    def readPhase(self,numberShots=1):
        '''Return station phase setting and readback in that order; average readback if multiple shots requested'''
        setting,readback=stationPhaseSetting.get(),stationPhaseReadback.get()
        try:
            numberShots=int(numberShots)
        except:
            print 'Num. shots is not a number; returning one shot only'
            return setting,readback
        if numberShots > 1:
            readbacks=[]
            for i in range(numberShots):
                readbacks.append(readback)
                j=0
                while readbacks[-1]==self.stationPhaseReadback.get():
                    j+=1
                    sleep(self.checkDelay)
                    if j>self.numberChecks: raise Exception('Phase readback not updating; multiple shot request cancelled')
            readback=np.mean(readbacks)
        return setting,readback

    def setPhase(self,newSetting):
        '''Set station phase'''
        try: newSetting=float(newSetting)
        except: raise ValueError('Please enter a valid number!')
        self.stationPhaseSetting.put(newSetting)
        return self.checkPhase()

    def checkPhase(self):
        '''Checks to see that phase readback has converged to phase setting (within 0.2deg)'''
        for i in range(self.numberChecks):
            sleep(self.checkDelay)
            setting,rb=self.readPhase()
            if abs(setting-rb) < self.phaseTol:
                return True
        return False

class Status(object):
    def data(self):
        bpm_stat,promo_stat=BPM(),ProMo()
        bpm=bpm_stat.readBPM()
        cent=promo_stat.calculateCent()
        status={
            'bpm': {'x': bpm[0],'y':  bpm[1], 'tmit':  bpm[2]},
            'cent': {'x': cent[0] , 'y': cent[1]}

            }
        return status
        



        
  
        
