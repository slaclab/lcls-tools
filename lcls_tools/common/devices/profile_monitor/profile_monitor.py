#!/usr/local/lcls/package/python/current/bin/python

from epics import PV
import profmon_constants as pc
from inspect import getmembers
from time import sleep
from threading import Thread
from numpy import array_equal
from functools import partial

# Implementation needs to be thought out, just a POC

def get_profile_monitors():
    """Return MAD names of all profile monitors that have models"""
    return sorted(pc.PROFS.keys())

class ProfMon(object):
    """Generic Profile Monitor Object Class that references profile monitor MAD name"""
    def __init__(self, prof_name='OTR02'):
        if prof_name not in pc.PROFS.keys():
            raise ValueError('You have not specified a valid profile monitor')
        prof_dict = pc.PROFS[prof_name]
        self._prof_name = prof_name
        self._prof_set = PV(prof_dict['set'])
        self._prof_get = PV(prof_dict['get'])
        self._prof_image = PV(prof_dict['image'])
        self._prof_res = PV(prof_dict['res'])
        self._x_size = PV(prof_dict['xsize'])
        self._y_size = PV(prof_dict['ysize'])
        self._rate = PV(prof_dict['rate'])
        self._images = []
        self._data_thread = None
        self._gathering_data = False
        self._get_vars = self._prof_get.get_ctrlvars()['enum_strs']
        self._set_vars = self._prof_set.get_ctrlvars()['enum_strs']
        self._motion_state = self._get_vars[self._prof_get.get()]
        self._prof_get.add_callback(self._state_clbk, index=1)
        self._insert_clbk = None
        self._extract_clbk = None

    def _state_clbk(self, pvName=None, value=None, char_value=None, **kw):
        """Keep track of position/motion state"""
        self._motion_state = self._get_vars[value]

    @property
    def prof_name(self):
        """Get the profile monitor MAD name"""
        return self._prof_name
        
    @property
    def cur_image(self):
        """Get the current image array"""
        return self._prof_image.get()

    @property
    def saved_images(self):
        """Get the images collected"""
        return self._images

    @property
    def resolution(self):
        """Get the resolution"""
        return self._prof_res.get()

    @property
    def arr_dims(self):
        """Get the x and y dimensions"""
        return (self._x_size.get(), self._y_size.get())

    @property
    def rate(self):
        """Get the current rate"""
        return self._rate.get()

    @property
    def motion_state(self):
        """Get the current motion state of the profile monitor"""
        return self._motion_state

    @property
    def state(self):
        """Get the overall state of the profile monitor"""
        return self.__dict__

    def insert(self, user_clbk=None):
        """Generic call to insert profile monitor, can specify callback to be run"""
        if self._motion_state == pc.IN:
            print('{0}: {1}'.format(self._prof_name, pc.ALREADY_INSERTED))
            return

        if user_clbk:
            self._insert_clbk = user_clbk
        
        self._prof_get.add_callback(self._inserted, index=0)
        self._prof_set.put(pc.IN)

    def _inserted(self, pv_name=None, value=None, char_value=None, **kw):
        """Generic callback after profile monitor has been inserted, default"""
        if self._get_vars[value] == pc.IN:
            print('{0}: {1}'.format(self._prof_name, pc.INSERTED))

            if self._insert_clbk:
                self._insert_clbk()
                self._insert_clbk = None

            self._prof_get.remove_callback(index=0)
    
    def extract(self, usr_clbk=None):
        """Extract profile monitor command, can specify callback to be run"""        
        if self._motion_state == pc.OUT:
            print('{0}: {1}'.format(self._prof_name, pc.ALREADY_EXTRACTED))
            return

        if user_clbk:
            self._extract_clbk = user_clbk

        self._prof_get.add_callback(self._extracted, index=0)
        self._prof_set.put(pc.OUT)
        
    def _extracted(self, pv_name=None, value=None, char_value=None, **kw):
        """Generic Callback for profile monitor that has been extracted, default"""
        if self._get_vars[value] == pc.OUT:
            print('{0}: {1}'.format(self._prof_name, pc.EXTRACTED))

            if self._extract_clbk:
                self._extract_clbk()
                self._extract_clbk = None

            self._prof_get.remove_callback(index=0)

    def acquire_images(self, images=1):
        """Start the thread"""
        self._data_thread = Thread(target=self._collect_image_data, args=(images,))
        self._data_thread.start()

    def _collect_image_data(self, images, callback):
        """Threaded data collection"""
        self._gathering_data = True
        delay = 1.0 / self._rate.get()  # Rate must be in Hz
        i = 0
        while i < images:
            image = self._prof_image.get()
            if len(self._images) > 0 and array_equal(image, self._images[-1]):
                sleep(0.01)
            else:
                self._images.append(image)
                sleep(delay)
                i += 1
        if callback:  # Would want this to be pyqtSignal or Event notification type thing
            callback()
        self._gathering_data = False
        return  # No join, waste of a function
