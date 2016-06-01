#!/usr/bin/python
'''
\brief GUI frame which allows the user to pause the simulation.

\author Thomas Watteyne <watteyne@eecs.berkeley.edu>
\author Kazushi Muraoka <k-muraoka@eecs.berkeley.edu>
\author Nicola Accettura <nicola.accettura@eecs.berkeley.edu>
\author Xavier Vilajosana <xvilajosana@eecs.berkeley.edu>
'''

#============================ logging =========================================

import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('PlayPauseFrame')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

#============================ imports =========================================

import Tkinter
import threading

from SimEngine import SimEngine, \
                      SimSettings

#============================ defines =========================================

#============================ body ============================================

class PlayPauseFrame(Tkinter.Frame):
    
    def __init__(self,guiParent):
        
        # store params
        self.guiParent  = guiParent
        
        # initialize the parent class
        Tkinter.Frame.__init__(
            self,
            self.guiParent,
            relief      = Tkinter.RIDGE,
            borderwidth = 1,
        )
        
        # GUI layout
        self.playButton      = Tkinter.Button(self, text="Play",     command=self._play_clicked)
        self.playButton.grid(row=0,column=0)
        self.pauseButton     = Tkinter.Button(self, text="pause",    command=self._pause_clicked)
        self.pauseButton.grid(row=1,column=0)
        self.nextCycleButton = Tkinter.Button(self, text="nextCycle",command=self._nextCycle_clicked)
        self.nextCycleButton.grid(row=2,column=0)
    
    #======================== public ==========================================
    
    def close(self):
        pass
    
    #======================== attributes ======================================
    
    @property
    def engine(self):
        return SimEngine.SimEngine(failIfNotInit=True)
    
    @property
    def settings(self):
        return SimSettings.SimSettings(failIfNotInit=True)
    
    #======================== private =========================================
    
    def _play_clicked(self):
        #print 'play clicked'
        try:
            self.engine.play()
        except EnvironmentError:
	    print 'Simulation is not running'
            # this happens when we try to update between runs
            pass
    
    def _pause_clicked(self):
        #print 'pause clicked'
        try:
            nowAsn           = self.engine.getAsn()
            print 'pausing'
            self.engine.pauseAtAsn(
                asn          = nowAsn+1,
            )
        except EnvironmentError:
	    print 'Simulation is not running'
            # this happens when we try to update between runs
            pass
    
    def _nextCycle_clicked(self):
        
        try:
            nowAsn           = self.engine.getAsn()
            endCycleAsn      = nowAsn+self.settings.slotframeLength-(nowAsn%self.settings.slotframeLength) #changed to avoid asserts with GUI
            #print 'pause clicked'+str(endCycleAsn)
            self.engine.play()
            self.engine.pauseAtAsn(
                asn          = endCycleAsn,
            )
        except EnvironmentError:
	    print 'Simulation is not running'
            # this happens when we try to update between runs
            pass
