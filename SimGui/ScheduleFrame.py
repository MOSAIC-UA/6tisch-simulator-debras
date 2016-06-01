#!/usr/bin/python
'''
\brief GUI frame which shows the TSCH schedule.

\author Thomas Watteyne <watteyne@eecs.berkeley.edu>
\author Kazushi Muraoka <k-muraoka@eecs.berkeley.edu>
\author Nicola Accettura <nicola.accettura@eecs.berkeley.edu>
\author Xavier Vilajosana <xvilajosana@eecs.berkeley.edu>
'''

'''
added changes by Esteban Municio <esteban.municio@uantwerpen.be>
'''

#============================ logging =========================================

import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('ScheduleFrame')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

#============================ imports =========================================

import Tkinter

from SimEngine             import SimEngine, \
                                  SimSettings

#============================ defines =========================================

#============================ body ============================================

class ScheduleFrame(Tkinter.Frame):
    
    UPDATE_PERIOD            = 100
    HEIGHT                   = 200
    WIDTH                    = 1014
    
    COLOR_OK                 = "blue"
    COLOR_ERROR              = "red"
    COLOR_NOREALCOLLISION    = "cyan"
    
    COLOR_TX                 = "green"
    COLOR_RX                 = "magenta"
    COLOR_SHARED             = "yellow"
    
    def __init__(self,guiParent):
        
        # store params
        self.guiParent       = guiParent
        
        # variables
        self.cells           = []
        
        # initialize the parent class
        Tkinter.Frame.__init__(
            self,
            self.guiParent,
            relief           = Tkinter.RIDGE,
            borderwidth      = 1,
        )
        
        # GUI layout
        self.schedule = Tkinter.Canvas(self, width=self.WIDTH, height=self.HEIGHT)
        self.schedule.grid(row=0,column=0)
        
        # schedule first GUI update
        self._update=self.schedule.after(self.UPDATE_PERIOD,self._updateGui)
    
    #======================== public ==========================================
    
    def close(self):
        self.schedule.after_cancel(self._update)
    
    #======================== attributes ======================================
    
    @property
    def engine(self):
        return SimEngine.SimEngine(failIfNotInit=True)
    
    @property
    def settings(self):
        return SimSettings.SimSettings(failIfNotInit=True)
    
    #======================== private =========================================
    
    def _updateGui(self):
        
        try:
            self._redrawSchedule()
        except EnvironmentError:
            # this happens when we try to update between runs
            pass
        
        self._update=self.schedule.after(self.UPDATE_PERIOD,self._updateGui)
    
    def _redrawSchedule(self):
        
        # initialize grid
        if not self.cells:
            for ts in range(self.settings.slotframeLength):
                self.cells.append([])
                for ch in range(self.settings.numChans):
                    newCell = self.schedule.create_rectangle(self._cellCoordinates(ts,ch))
                    self.schedule.tag_bind(newCell, '<ButtonPress-1>', self._cellClicked)
                    self.cells[ts] += [newCell]
        
        # clear all colors
        for ts in self.cells:
            for c in ts:
                self.schedule.itemconfig(c, fill='', outline='black', width=1.0)
        
        # color according to usage
	
        for m in self.engine.motes:
            for (ts,ch,neighbor) in m.getTxCells():


		color = self.schedule.itemcget(self.cells[ts][ch], "fill")
		if not color:		
		    self.schedule.itemconfig(self.cells[ts][ch], fill=self.COLOR_OK)
 
                else:
		    for n in self.engine.motes: 
		    	if n.id!=m.id: 
			     for (ts1,ch1,neigh1) in n.getTxCells():
				  if ts==ts1 and ch==ch1:
					if (n.getRSSI(neighbor)+(-97-(-105))) >= neighbor.minRssi:
						self.schedule.itemconfig(self.cells[ts][ch], fill=self.COLOR_ERROR)
					else:
						self.schedule.itemconfig(self.cells[ts][ch], fill=self.COLOR_NOREALCOLLISION)

        for (ts,ch,_) in m.getSharedCells():
            self.schedule.itemconfig(self.cells[ts][ch], fill=self.COLOR_SHARED)

        # color selected mote's cells
        mote = self.guiParent.selectedMote
        if mote:
            for (ts,ch,_) in mote.getTxCells():
                self.schedule.itemconfig(self.cells[ts][ch], outline=self.COLOR_TX)
                self.schedule.itemconfig(self.cells[ts][ch], width=2.0)
            for (ts,ch,_) in mote.getRxCells():
                self.schedule.itemconfig(self.cells[ts][ch], outline=self.COLOR_RX)
                self.schedule.itemconfig(self.cells[ts][ch], width=2.0)
	    
    
    #======================== helpers =========================================
    
    #===== handle click events
    
    def _cellClicked(self,event):
        cellGui = event.widget.find_closest(event.x, event.y)[0]
        cell    = None
        for ts in range(len(self.cells)):
            for ch in range(len(self.cells[ts])):
                if self.cells[ts][ch]==cellGui:
                    cell = (ts,ch)
                    break
        assert cell
        print "selected cell {0}".format(cell)
        self.guiParent.selectedCell = cell
    
    #===== coordinate calculation
    
    def _cellCoordinates(self,ts,ch):
        
        step  = min(
            (self.WIDTH-4)/self.settings.slotframeLength,
            (self.HEIGHT-4)/self.settings.numChans
        )
        
        return (
            2+ts*step,
            2+ch*step,
            2+(ts+1)*step,
            2+(ch+1)*step,
        )
