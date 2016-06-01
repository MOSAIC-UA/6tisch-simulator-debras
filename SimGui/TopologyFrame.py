#!/usr/bin/python
'''
\brief GUI frame which shows the topology.

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
log = logging.getLogger('TopologyFrame')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

#============================ imports =========================================

import Tkinter

from SimEngine import SimEngine, \
                      SimSettings

#============================ defines =========================================

#============================ body ============================================

class TopologyFrame(Tkinter.Frame):
    
    UPDATE_PERIOD       = 1000
    MOTE_SIZE           = 10
    HEIGHT              = 300
    WIDTH               = 300
    
    def __init__(self,guiParent):
        
        # store params
        self.guiParent  = guiParent
        
        # variables
        self.motes      = {}
        self.moteIds    = {}
        self.links      = {}
        
        # initialize the parent class
        Tkinter.Frame.__init__(
            self,
            self.guiParent,
            relief      = Tkinter.RIDGE,
            borderwidth = 1,
        )
        
        # GUI layout
        self.topology   = Tkinter.Canvas(self, width=self.WIDTH, height=self.HEIGHT)
        self.topology.grid(row=0,column=0)
        self._update=self.topology.after(self.UPDATE_PERIOD,self._updateGui)
    
    #======================== public ==========================================
    
    def close(self):
        self.topology.after_cancel(self._update)
    
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
            self._redrawTopology()
        except EnvironmentError:
            # this happens when we try to update between runs
            pass
        
        self._update=self.topology.after(self.UPDATE_PERIOD,self._updateGui)
    
    def _redrawTopology(self):
        
        #===== mark all elements to be removed
        
        for (k,v) in self.motes.items():
            self.topology.itemconfig(v,tags=("deleteMe"))
        for (k,v) in self.moteIds.items():
            self.topology.itemconfig(v,tags=("deleteMe",))
        for (k,v) in self.links.items():
            self.topology.itemconfig(v,tags=("deleteMe",))
        
        #===== draw links
        
        # go over all links in the network
        for mote in self.engine.motes:
            for (ts,ch,neighbor) in mote.getTxCells():
                if (mote,neighbor) not in self.links:
                    # create
                    newLink = self.topology.create_line(self._linkCoordinates(mote,neighbor))
                    self.topology.itemconfig(newLink,activefill='red')
                    self.topology.tag_bind(newLink, '<ButtonPress-1>', self._linkClicked)
                    self.links[(mote,neighbor)] = newLink
		    #print "NEW LINK BETWEEN "+str((mote.id,neighbor.id))
                else:
                    # move
                    self.topology.dtag(self.links[(mote,neighbor)],"deleteMe")
                    # TODO:move
        
        #===== draw motes and moteIds
        
        # go over all motes in the network
        for m in self.engine.motes:
            if m not in self.motes:
                # create
                newMote = self.topology.create_oval(self._moteCoordinates(m),fill='blue')
                self.topology.itemconfig(newMote,activefill='red')
                self.topology.tag_bind(newMote, '<ButtonPress-1>', self._moteClicked)
                self.motes[m] = newMote
                
                newMoteId = self.topology.create_text(self._moteIdCoordinates(m))
                self.topology.itemconfig(newMoteId,text=m.id)
                self.moteIds[m] = newMoteId
            else:
                # move
                self.topology.dtag(self.motes[m],"deleteMe")
                self.topology.dtag(self.moteIds[m],"deleteMe")
                # TODO: move
        
        #===== remove all elements still marked
        
        for elem in self.topology.find_withtag("deleteMe"):
            self.topology.delete(elem)
    
    #======================== helpers =========================================
    
    #===== handle click events
    
    def _linkClicked(self,event):
        linkGui = event.widget.find_closest(event.x, event.y)[0]
        link    = None
        for (k,v) in self.links.items():
            if v==linkGui:
                link = k
                break
        assert link
        print "selected link {0}->{1}".format(link[0].id,link[1].id)
        self.guiParent.selectedLink = link
    
    def _moteClicked(self,event):
        moteGui = event.widget.find_closest(event.x, event.y)[0]
        mote    = None
        for (k,v) in self.motes.items():
            if v==moteGui:
                mote = k
                break
        assert mote
        print "selected mote {0}".format(mote.id)
        self.guiParent.selectedMote = mote
    
    #===== coordinate calculation
    
    def _moteCoordinates(self,m):
        (x,y) = self._normalizeLocation(m.getLocation())
        return (
            self.WIDTH*x-self.MOTE_SIZE/2,
            self.HEIGHT*y-self.MOTE_SIZE/2,
            self.WIDTH*x+self.MOTE_SIZE/2,
            self.HEIGHT*y+self.MOTE_SIZE/2,
        )
    
    def _moteIdCoordinates(self,m):
        (x,y) = self._normalizeLocation(m.getLocation())
        return (
            self.WIDTH*x,
            self.HEIGHT*y+self.MOTE_SIZE,
        )
    
    def _linkCoordinates(self,fromMote,toMote):
        (fromX, fromY)  = self._normalizeLocation(fromMote.getLocation())
        (toX,   toY)    = self._normalizeLocation(toMote.getLocation())
        return (
            fromX*self.WIDTH,
            fromY*self.HEIGHT,
            toX*self.WIDTH,
            toY*self.HEIGHT,
        )
    
    def _normalizeLocation(self,xy):
        (x,y) = xy
        return (
            x/self.settings.squareSide,
            y/self.settings.squareSide
        )
