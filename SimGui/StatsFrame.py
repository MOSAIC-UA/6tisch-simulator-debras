#!/usr/bin/python
'''
\brief GUI frame which shows simulator statistics.

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
log = logging.getLogger('StatsFrame')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

#============================ imports =========================================

import Tkinter

from SimEngine     import SimEngine, \
                          SimSettings

#============================ defines =========================================

#============================ body ============================================

class StatsFrame(Tkinter.Frame):
    
    UPDATE_PERIOD = 1000
    
    def __init__(self,guiParent):
        
        # store params
        self.guiParent       = guiParent
        
        # initialize the parent class
        Tkinter.Frame.__init__(
            self,
            self.guiParent,
            relief      = Tkinter.RIDGE,
            borderwidth = 1,
        )
        
        # GUI layout
        self.info  = Tkinter.Label(self,justify=Tkinter.LEFT)
        self.info.grid(row=0,column=0)
        
        self.cell  = Tkinter.Label(self,justify=Tkinter.LEFT)
        self.cell.grid(row=0,column=1)
        
        self.mote  = Tkinter.Label(self,justify=Tkinter.LEFT)
        self.mote.grid(row=0,column=2)
        
        self.link  = Tkinter.Label(self,justify=Tkinter.LEFT)
        self.link.grid(row=0,column=3)
        
        # schedule first update
        self._update=self.after(self.UPDATE_PERIOD,self._updateGui)
        
    #======================== public ==========================================
    
    def close(self):
        self.after_cancel(self._update)
    
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
            self._redrawInfo()
            self._redrawCell()
            self._redrawMote()
            self._redrawLink()
        except EnvironmentError:
            # this happens when we try to update between runs
            pass
        
        self._update=self.after(self.UPDATE_PERIOD,self._updateGui)
    
    def _redrawInfo(self):
        
        asn = self.engine.getAsn()
        output  = []
        output += ["info:"]
        output += ["ASN: {0}".format(asn)]
        output += ["time: {0}".format(asn*self.settings.slotDuration)]
        output  = '\n'.join(output)
        self.info.configure(text=output)
    
    def _redrawCell(self):
        
        cell = self.guiParent.selectedCell
        output  = []
        output += ["Cell:"]
        if cell:
            ts = cell[0]
            ch = cell[1]
            output += ["ts={0} ch={1}".format(ts,ch)]
            for mote in self.engine.motes:
                cellStats = mote.getCellStats(ts,ch)
                if cellStats:
                    output += ["mote {0}:".format(mote.id)]
                    for (k,v) in cellStats.items():
                        output += ["- {0}: {1}".format(k,v)]
        else:
            output += ["No cell selected."]
        output  = '\n'.join(output)
        self.cell.configure(text=output)
    
    def _redrawMote(self):
        
        mote = self.guiParent.selectedMote
        output  = []
        output += ["Mote:"]
        if mote:
            output += ["id={0}".format(mote.id)]
            stats   = mote.getMoteStats()
            for (k,v) in stats.items():
                output += ["- {0}: {1}".format(k,v)]
        else:
            output += ["No mote selected."]
        output  = '\n'.join(output)
        self.mote.configure(text=output)
        
    def _redrawLink(self):
        
        link = self.guiParent.selectedLink
        output  = []
        output += ["Link:"]
        if link:
            fromMote = link[0]
            toMote   = link[1]
            output += ["{0}->{1}".format(fromMote.id,toMote.id)]
        else:
            output += ["No link selected."]
        output  = '\n'.join(output)
        self.link.configure(text=output)
        
