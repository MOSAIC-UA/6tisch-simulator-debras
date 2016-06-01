#!/usr/bin/python
'''
\brief Model of a 6TiSCH mote.

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
log = logging.getLogger('Mote')
log.setLevel(logging.DEBUG)
log.addHandler(NullHandler())

#============================ imports =========================================

import copy
import random
import threading
import math

import SimEngine
import SimSettings
import Propagation
import Topology

#============================ defines =========================================

#============================ body ============================================

class Mote(object):
    
    # sufficient num. of tx to estimate pdr by ACK
    NUM_SUFFICIENT_TX                  = 10
    # maximum number of tx for history
    NUM_MAX_HISTORY                    = 32
    
    DIR_TX                             = 'TX'
    DIR_RX                             = 'RX'
    DIR_SHARED                         = 'SHARED'
    
    BROAD                              = 'BROADCAST'
    
    DEBUG                              = 'DEBUG'
    INFO                               = 'INFO'
    WARNING                            = 'WARNING'
    ERROR                              = 'ERROR'
    
    #=== app
    APP_TYPE_DATA                      = 'DATA'
    APP_TYPE_MYTRAFFIC                 = 'TRAFFICOMIO'
    SIXP_TYPE_MYSCHEDULE                 = 'SIXP_TYPE_MYSCHEDULE'
    
    #=== rpl
    RPL_PARENT_SWITCH_THRESHOLD        = 384 # 2*ETX
    #RPL_PARENT_SWITCH_THRESHOLD        = 768 # corresponds to 1.5 hops. 6tisch minimal draft use 384 for 2*ETX.

    #RPL_MIN_HOP_RANK_INCREASE          = 256
    RPL_MIN_HOP_RANK_INCREASE          =  1536#(256*6)

    RPL_MAX_ETX                        = 1.3
    RPL_MAX_RANK_INCREASE              = RPL_MAX_ETX*RPL_MIN_HOP_RANK_INCREASE*2 # 4 transmissions allowed for rank increase for parents
    RPL_MAX_TOTAL_RANK                 = 256*RPL_MIN_HOP_RANK_INCREASE*2 # 256 transmissions allowed for total path cost for parents
    RPL_PARENT_SET_SIZE                = 1
    DEFAULT_DIO_INTERVAL_MIN           = 3 # log2(DIO_INTERVAL_MIN), with DIO_INTERVAL_MIN expressed in ms
    DEFAULT_DIO_INTERVAL_DOUBLINGS     = 20 # maximum number of doublings of DIO_INTERVAL_MIN (DIO_INTERVAL_MAX = 2^(DEFAULT_DIO_INTERVAL_MIN+DEFAULT_DIO_INTERVAL_DOUBLINGS) ms)
    DEFAULT_DIO_REDUNDANCY_CONSTANT    = 10 # number of hearings to suppress next transmission in the current interval
    
    #=== otf
    OTF_TRAFFIC_SMOOTHING              = 0.5
    #=== 6top
    #=== tsch
    TSCH_QUEUE_SIZE                    = 10
    TSCH_MAXTXRETRIES                  = 5    
    #=== radio
    RADIO_MAXDRIFT                     = 30 # in ppm
    #=== battery
    # see A Realistic Energy Consumption Model for TSCH Networks.
    # Xavier Vilajosana, Qin Wang, Fabien Chraim, Thomas Watteyne, Tengfei
    # Chang, Kris Pister. IEEE Sensors, Vol. 14, No. 2, February 2014.
    CHARGE_Idle_uC                     = 24.60
    CHARGE_TxDataRxAck_uC              = 64.82
    CHARGE_TxData_uC                   = 49.37
    CHARGE_RxDataTxAck_uC              = 76.90
    CHARGE_RxData_uC                   = 64.65
    
    def __init__(self,id):
        
        self.x=0
        self.y=0        
        
        
        random.seed(5)        
        
        # store params
        self.id                        = id
        # local variables
        self.dataLock                  = threading.RLock()
        
        self.engine                    = SimEngine.SimEngine()
        self.settings                  = SimSettings.SimSettings()
        self.propagation               = Propagation.Propagation()
        
        # app
        self.pkPeriod                  = self.settings.pkPeriod        
        # role
        self.dagRoot                   = False
        # rpl
        self.rank                      = None
        self.dagRank                   = None
        self.parentSet                 = []
        self.preferredParent           = None
        self.rplRxDIO                  = {}                    # indexed by neighbor, contains int
        self.neighborRank              = {}                    # indexed by neighbor
        self.neighborDagRank           = {}                    # indexed by neighbor
        self.trafficPortionPerParent   = {}                    # indexed by parent, portion of outgoing traffic
        # otf
        self.asnOTFevent               = None
        self.otfHousekeepingPeriod     = self.settings.otfHousekeepingPeriod
        self.timeBetweenOTFevents      = []
        self.inTraffic                 = {}                    # indexed by neighbor
        self.inTrafficMovingAve        = {}                    # indexed by neighbor
        # 6top
        self.numCellsToNeighbors       = {}                    # indexed by neighbor, contains int
        self.numCellsFromNeighbors     = {}                    # indexed by neighbor, contains int
        
        # changing this threshold the detection of a bad cell can be
        # tuned, if as higher the slower to detect a wrong cell but the more prone
        # to avoid churn as lower the faster but with some chances to introduces
        # churn due to unstable medium
        self.sixtopPdrThreshold           = self.settings.sixtopPdrThreshold
        self.sixtopHousekeepingPeriod  = self.settings.sixtopHousekeepingPeriod
        # tsch
        self.txQueue                   = []
        self.pktToSend                 = []                 #list of packets to send in one ts (in different channels)
        self.schedule                  = {}                 # indexed by ts and ch  contains info of the all the channels in each ts 
        self.scheduleNeigborhood       = {}               # indexed by ts and ch contains the cells used in my neighborhood                    
        
        #self.waitingFor                = None               #not used, using multichannel capabilities
        self.timeCorrectedSlot         = None
        # radio
        self.txPower                   = 0                     # dBm
        self.antennaGain               = 0                     # dBi
        self.minRssi                   = self.settings.minRssi # dBm
        self.noisepower                = -105                  # dBm
        self.drift                     = random.uniform(-self.RADIO_MAXDRIFT, self.RADIO_MAXDRIFT)
        # wireless
        self.RSSI                      = {}                    # indexed by neighbor
        self.PDR                       = {}                    # indexed by neighbor
        # location
        # battery
        self.chargeConsumed            = 0
        
        # stats
        self._stats_resetMoteStats()
        self._stats_resetQueueStats()
        self._stats_resetLatencyStats()
        self._stats_resetHopsStats()
        self._stats_resetRadioStats()
        
        #emunicio
        self.numPacketSent                 = 0 #total number of packets sent     
        self.numPacketReceived             = 0 #total number of packets received 
	self.probePacketsGenerated	   = 0 #total number of packets sent in the probe period
        self.probeNumPacketReceived	   = 0 #total number of packets received in the probe period

        self.finishMyFlow                  = False #when to finish sending
        
        self.numReqCells=0		   # requested cells
        
        self.myMaxCellDemand		   = 0 # only used when otf is not enabled because cell demand is predefined and an ideal PHY is used	   

        self.numTransmissions=0		   #number of transmissions
        self.numReceptions=0		   #number of reception
        
        self.otfTriggered=False      
        
        self.maxWin=None       		   # maximum number of cycles a node have to wait to send its EB broadcast message
        self.numberOfWaitings=None	   # current number of cycles a node have to wait to send its EB broadcast message

        self.chosenBroadCell_id=None	  # broadcast cell id used for this mote
        self.myBrTs=None		  # broadcast cell ts used
        self.myBrCh=None		  # broadcast cell ch used
       
        self.hopsToRoot=0		  # hops to root
        
        self.threq=0			  # theoretical throughput per node according the cells needed in links closer to the root
                                       
        self.numRandomSelections=0	  # random selections performed (when no cells are available, or when OTF-sf0 is used)
                        
        #emunicio debug
        self.DEBUG=False       


    #======================== stack ===========================================
    
    #===== role
    
    def role_setDagRoot(self):
        self.dagRoot              = True
        self.rank                 = 0
        self.dagRank              = 0
        self.packetLatencies      = [] # in slots
        self.packetHops           = []
        
    
    #===== application
    #emunicio 
    def _app_schedule_sendSinglePacket(self,firstPacket=False):
        '''
        create an event that is inserted into the simulator engine to send the data according to the traffic
        '''  
        with self.dataLock:
            if not self.finishMyFlow:
                if not firstPacket:
                    # compute random delay
                    delay            = self.pkPeriod*(1+random.uniform(-self.settings.pkPeriodVar,self.settings.pkPeriodVar)) 
                else:
                    # compute initial time within the range of [next asn, next asn+pkPeriod]
                    delay            = self.settings.slotDuration + (self.settings.slotframeLength/6)*random.random() + (self.settings.slotframeLength/6) 
		    # max at 16.9 or 33 seconds for a frame length of 101
                         
                assert delay>0   
                              
                if (self.engine.asn < (96*self.settings.slotframeLength)):  #cycle 96
                       
                    # schedule
                    self.engine.scheduleIn(
                        delay            = delay,
                        cb               = self._app_action_sendSinglePacket,
                        uniqueTag        = (self.id, '_app_action_sendSinglePacket'),
                        priority         = 2,
                    )
                        
    #not used for the moment      
    def _app_schedule_sendPacketBurst(self):
        ''' create an event that is inserted into the simulator engine to send a data burst'''
        print "Preparing packet bursts in "+str(self.id)
        # schedule numPacketsBurst packets at burstTimestamp
        for i in xrange(self.settings.numPacketsBurst):
            self.engine.scheduleIn(
                delay        = self.settings.burstTimestamp,
                cb           = self._app_action_enqueueData,
                uniqueTag    = (self.id, '_app_action_enqueueData_burst1'),
                priority     = 2,
            )
            self.engine.scheduleIn(
                delay        = 3*self.settings.burstTimestamp,
                cb           = self._app_action_enqueueData,
                uniqueTag    = (self.id, '_app_action_enqueueData_burst2'),
                priority     = 2,
            )
            
    def _app_action_sendSinglePacket(self):
        ''' actual send data function. Evaluates queue length too '''
       
        # enqueue data
        self._app_action_enqueueData()
        
        # schedule next _app_action_sendSinglePacket
        self._app_schedule_sendSinglePacket()
    
    def _app_action_enqueueData(self):
        ''' enqueue data packet into stack '''
                      
        #print "Sending packet at: "
        self._stats_incrementMoteStats('appGenerated')
  
        self.threq=self.hopsToRoot 
    
        if (self.engine.asn < (96*self.settings.slotframeLength)) and (self.engine.asn > (63*self.settings.slotframeLength)): #calc 97-131 rows
            self.probePacketsGenerated+=1


	#emunicio
        self.numPacketSent+=1  # from app layer  

        # only start sending data if I have some TX cells
        if self.getTxCells():
            newPacket = {
                'asn':            self.engine.getAsn(),
                'type':           self.APP_TYPE_MYTRAFFIC,
                'payload':        [self.id,self.engine.getAsn(),1], # the payload is used for latency and number of hops calculation
                'retriesLeft':    self.TSCH_MAXTXRETRIES
            }
            
                        
                      
            # enqueue packet in TSCH queue
            isEnqueued = self._tsch_enqueue(newPacket)
            
            if isEnqueued:
                # increment traffic
                
                self._otf_incrementIncomingTraffic(self)
            else:

                self._stats_incrementMoteStats('droppedAppFailedEnqueue')
                #queue is full
               
        else:
	    # no tx cell availables
            self._stats_incrementMoteStats('droppedAppFailedEnqueue')
                
            self._stats_incrementMoteStats('droppedNoTxCells')
            # update mote stats

            
    
    #===== rpl
    
    def _rpl_schedule_sendDIO(self,firstDIO=False):
        
        with self.dataLock:

            asn    = self.engine.getAsn()
            ts     = asn%self.settings.slotframeLength
            
            if not firstDIO:
                
                cycle = int(math.ceil(self.settings.dioPeriod/(self.settings.slotframeLength*self.settings.slotDuration)))
            else:
                cycle = 1 
            

            if self.preferredParent != None:                
                self.hopsToRoot=self.recalculateNumHopsToRoot()
                if self.id!=0 and self.otfTriggered != True:
                    self._otf_schedule_housekeeping(firstOtf=True)
                    self.otfTriggered=True
                                                
            # schedule at start of next cycle
            self.engine.scheduleAtAsn(
                asn         = asn-ts+cycle*self.settings.slotframeLength,
                cb          = self._rpl_action_sendDIO,
                uniqueTag   = (self.id,'_rpl_action_sendDIO'),
                priority    = 3,
            )
    
    def _rpl_action_sendDIO(self):
        
        with self.dataLock:
         
            if self.rank!=None and self.dagRank!=0 or self.dagRoot==True:

                # update mote stats
                self._stats_incrementMoteStats('rplTxDIO')
              
                # "send" DIO to all neighbors
                for neighbor in self._myNeigbors():
                    # don't update DAGroot
                    if neighbor.dagRoot:
                        continue
                    
                    
                    #emunicio
		    #don't update poor link
                    #with the 256 it is forced to use only high quality links. CAUTION! CAN CREATE LOOPS!!
                                        
                    if neighbor._rpl_calcRankIncrease(self)>(self.RPL_MAX_RANK_INCREASE):

                        continue
                       
                    # in neighbor, update my rank/DAGrank
                    neighbor.neighborDagRank[self]    = self.dagRank
                    neighbor.neighborRank[self]       = self.rank
                    
                    # in neighbor, update number of DIOs received
                    if self not in neighbor.rplRxDIO:
                        neighbor.rplRxDIO[self]       = 0
                    neighbor.rplRxDIO[self]          += 1
                    
                    # update my mote stats
                    self._stats_incrementMoteStats('rplRxDIO') # TODO: TX DIO?
                    
                    # skip useless housekeeping
                    if not neighbor.rank or self.rank<neighbor.rank:
                        # in neighbor, do RPL housekeeping
                        neighbor._rpl_housekeeping()                        
                    
                    # update time correction
                   
                    if neighbor.preferredParent == self:
                        
                        asn                        = self.engine.getAsn() 

                        neighbor.timeCorrectedSlot = asn
            
            # schedule to send the next DIO
            self._rpl_schedule_sendDIO()
    
    def _rpl_housekeeping(self):
        with self.dataLock:
            
            #===
            # refresh the following parameters:
            # - self.preferredParent
            # - self.rank
            # - self.dagRank
            # - self.parentSet

            
            # calculate my potential rank with each of the motes I have heard a DIO from
            potentialRanks = {}
            for (neighbor,neighborRank) in self.neighborRank.items():
                # calculate the rank increase to that neighbor
                rankIncrease = self._rpl_calcRankIncrease(neighbor)

                if rankIncrease!=None and rankIncrease<=min([self.RPL_MAX_RANK_INCREASE, self.RPL_MAX_TOTAL_RANK-neighborRank]): 

                    #check if there is a loop and if exists, skip the neighbor         
		    rootReached=False
		    skipNeighbor=False
	            inode=neighbor
		    while rootReached==False:
			if inode.preferredParent!=None:
			    if inode.preferredParent.id==self.id:
				skipNeighbor=True
			    if inode.preferredParent.id==0:
				rootReached=True
			    else:
				inode=inode.preferredParent
			else:
			    rootReached=True
		    if skipNeighbor==True:
		        continue
  
		    # record this potential rank                   
                    potentialRanks[neighbor] = neighborRank+rankIncrease
            
            # sort potential ranks
            
            sorted_potentialRanks = sorted(potentialRanks.iteritems(), key=lambda x:x[1])

            # switch parents only when rank difference is large enough
            for i in range(1,len(sorted_potentialRanks)):
                if sorted_potentialRanks[i][0] in self.parentSet:
                    # compare the selected current parent with motes who have lower potential ranks 
                    # and who are not in the current parent set 
                    
                    for j in range(i):                    
                        if sorted_potentialRanks[j][0] not in self.parentSet:
                            if sorted_potentialRanks[i][1]-sorted_potentialRanks[j][1]<self.RPL_PARENT_SWITCH_THRESHOLD:
                                mote_rank = sorted_potentialRanks.pop(i)
                                sorted_potentialRanks.insert(j,mote_rank)
                                break
            
            
            
            # pick my preferred parent and resulting rank
            if sorted_potentialRanks:                
                
                oldParentSet = set([parent.id for parent in self.parentSet])             
                (newPreferredParent,newrank) = sorted_potentialRanks[0]

                # compare a current preferred parent with new one
                if self.preferredParent and newPreferredParent!=self.preferredParent:
                    for (mote,rank) in sorted_potentialRanks[:self.RPL_PARENT_SET_SIZE]:
                        
                        if mote == self.preferredParent:                      
                            # switch preferred parent only when rank difference is large enough
                            if rank-newrank<self.RPL_PARENT_SWITCH_THRESHOLD:
                                (newPreferredParent,newrank) = (mote,rank)
                                
                            
                    # update mote stats
                    self._stats_incrementMoteStats('rplChurnPrefParent')
                    # log
                    self._log(
                        self.INFO,
                        "[rpl] churn: preferredParent {0}->{1}",
                        (self.preferredParent.id,newPreferredParent.id),
                    )
                
                # update mote stats
                if self.rank and newrank!=self.rank:
                    self._stats_incrementMoteStats('rplChurnRank')
                    # log
                    self._log(
                        self.INFO,
                        "[rpl] churn: rank {0}->{1}",
                        (self.rank,newrank),
                    )

                # store new preferred parent and rank
                (self.preferredParent,self.rank) = (newPreferredParent,newrank)
                
                # calculate DAGrank
                self.dagRank = int(self.rank/self.RPL_MIN_HOP_RANK_INCREASE)

                # pick my parent set
                self.parentSet = [n for (n,_) in sorted_potentialRanks if self.neighborRank[n]<self.rank][:self.RPL_PARENT_SET_SIZE]

                assert self.preferredParent in self.parentSet
                                
                if oldParentSet!=set([parent.id for parent in self.parentSet]):
                    self._stats_incrementMoteStats('rplChurnParentSet')
      
            #===
            # refresh the following parameters:
            # - self.trafficPortionPerParent
            
            etxs        = dict([(p, 1.0/(self.neighborRank[p]+self._rpl_calcRankIncrease(p))) for p in self.parentSet])
            sumEtxs     = float(sum(etxs.values()))
                        
            self.trafficPortionPerParent = dict([(p, etxs[p]/sumEtxs) for p in self.parentSet])
                       
            # remove TX cells to neighbor who are not in parent set
            for neighbor in self.numCellsToNeighbors.keys():
                if neighbor not in self.parentSet:

                    # log
                    self._log(
                        self.INFO,
                        "[otf] removing cell to {0}, since not in parentSet {1}",
                        (neighbor.id,[p.id for p in self.parentSet]),
                    )
                
                    tsList=[(ts,ch) for (ts,ch), cell in self.schedule.iteritems() if cell['neighbor']==neighbor and cell['dir']==self.DIR_TX]

                    if tsList:                                            
                        cellsToNewParent=[(ts,ch) for (ts,ch), cell in self.schedule.iteritems() if cell['neighbor']==self.parentSet[0] and cell['dir']==self.DIR_TX]    
                        if len(cellsToNewParent)!=0:
                            self._sixtop_cell_deletion_sender(neighbor,tsList)
 
    def _rpl_calcRankIncrease(self, neighbor):
        
        with self.dataLock:
                                    
            # estimate the ETX to that neighbor
            etx = self._estimateETX(neighbor)
                 
            # return if that failed
            if not etx:
                return
            
            # per draft-ietf-6tisch-minimal, rank increase is 2*ETX*RPL_MIN_HOP_RANK_INCREASE
            return int(2*self.RPL_MIN_HOP_RANK_INCREASE*etx)
    
    #===== otf
    
    def _otf_schedule_housekeeping(self,firstOtf=False):
        
        if firstOtf:
            delay= (self.otfHousekeepingPeriod*(0.5+random.random()))
        else:
            delay=self.otfHousekeepingPeriod*(0.9+0.2*random.random())
                  
        
        
        self.engine.scheduleIn(
            delay       = delay,
            cb          = self._otf_action_housekeeping,
            uniqueTag   = (self.id,'_otf_action_housekeeping'),
            priority    = 4,
        )
        
    
    def _otf_action_housekeeping(self):
        '''
        OTF algorithm: decides when to add/delete cells.
        '''
        with self.dataLock:
        
          
            # collect all neighbors I have RX cells to
            rxNeighbors = [cell['neighbor'] for ((ts,ch),cell) in self.schedule.items() if cell['dir']==self.DIR_RX]
  
            # remove duplicates
            rxNeighbors = list(set(rxNeighbors))          
            
            # reset inTrafficMovingAve                
            neighbors = self.inTrafficMovingAve.keys()
            for neighbor in neighbors:
                
                if neighbor not in rxNeighbors:
                    del self.inTrafficMovingAve[neighbor]
            
            # set inTrafficMovingAve 
            for neighborOrMe in rxNeighbors+[self]:
                if neighborOrMe in self.inTrafficMovingAve:
                    newTraffic   = 0
                    newTraffic  += self.inTraffic[neighborOrMe]*self.OTF_TRAFFIC_SMOOTHING               # new
                    newTraffic  += self.inTrafficMovingAve[neighborOrMe]*(1-self.OTF_TRAFFIC_SMOOTHING)  # old
                    self.inTrafficMovingAve[neighborOrMe] = newTraffic
                elif self.inTraffic[neighborOrMe] != 0:
                    self.inTrafficMovingAve[neighborOrMe] = self.inTraffic[neighborOrMe]
            
            # reset the incoming traffic statistics, so they can build up until next housekeeping
            self._otf_resetInboundTrafficCounters()
            
            # calculate my total generated traffic, in pkt/s
            genTraffic       = 0
            # generated/relayed by me
            for neighborOrMe in self.inTrafficMovingAve:
                genTraffic  += self.inTrafficMovingAve[neighborOrMe]/self.otfHousekeepingPeriod
              
            
            # convert to pkts/cycle
            genTraffic      *= self.settings.slotframeLength*self.settings.slotDuration
                                   
            remainingPortion = 0.0
            parent_portion   = self.trafficPortionPerParent.items()
            # sort list so that the parent assigned larger traffic can be checked first
            sorted_parent_portion = sorted(parent_portion, key = lambda x: x[1], reverse=True)
                                 
            # split genTraffic across parents, trigger 6top to add/delete cells accordingly
            for (parent,portion) in sorted_parent_portion:
                # if some portion is remaining, this is added to this parent
                if remainingPortion!=0.0:
                    portion                               += remainingPortion
                    remainingPortion                       = 0.0
                    self.trafficPortionPerParent[parent]   = portion
                    
                # calculate required number of cells to that parent
                etx = self._estimateETX(parent)
                                                
                if etx>self.RPL_MAX_ETX: # cap ETX
                    etx  = self.RPL_MAX_ETX
                               
                # calculate the OTF threshold
                threshold     = int(math.ceil(portion*self.settings.otfThreshold))
                
                # measure how many cells I have now to that parent
                nowCells      = self.numCellsToNeighbors.get(parent,0)
                if self.settings.otfEnabled==True:
                    reqCells      = int(math.ceil(portion*genTraffic*etx))  
                else: #optimal allocation, only for an ideal PHY 
                    self.myMaxCellDemand=self.getMyMaxCellDemand()
                    reqCells=self.myMaxCellDemand                                                                                   

                self.numReqCells=reqCells
    
                if nowCells==0 or nowCells<reqCells:
                    # I don't have enough cells
                    
                    # calculate how many to add
                    if reqCells>0:
                        # according to traffic                        
                        numCellsToAdd = reqCells-nowCells+(threshold+1)/2
                    else:
                        # have at least one cell                        
                        numCellsToAdd = 1                    
                    # log
                    self._log(
                        self.INFO,
                        "[otf] not enough cells to {0}: have {1}, need {2}, add {3}",
                        (parent.id,nowCells,reqCells,numCellsToAdd),
                    )
                    
                    # update mote stats
                    self._stats_incrementMoteStats('otfAdd')
                    
                    # have 6top add cells
                    self._sixtop_cell_reservation_request(parent,numCellsToAdd)
                    
                    # measure how many cells I have now to that parent
                    nowCells     = self.numCellsToNeighbors.get(parent,0)
                    
                    # store handled portion and remaining portion
                    if nowCells<reqCells:
                        if genTraffic > 0:    #to avoid float division by zero
                            handledPortion   = (float(nowCells)/etx)/genTraffic
                            remainingPortion = portion - handledPortion
                            self.trafficPortionPerParent[parent] = handledPortion
                    
                    # remember OTF triggered
                    otfTriggered = True
                
                elif reqCells<nowCells-threshold:
                    # I have too many cells
                    
                    # calculate how many to remove
                    #emunicio, I want always there is at least 1 cell available
		    # cells that are scheduled to non-parent nodes, will be removed later
                    numCellsToRemove = nowCells-reqCells
                    if reqCells==0:
                      numCellsToRemove=numCellsToRemove-1  
                     
                    # log
                    self._log(
                        self.INFO,
                        "[otf] too many cells to {0}:  have {1}, need {2}, remove {3}",
                        (parent.id,nowCells,reqCells,numCellsToRemove),
                    )
                    
                    # update mote stats
                    self._stats_incrementMoteStats('otfRemove')
                    
                    # have 6top remove cells
                    self._sixtop_removeCells(parent,numCellsToRemove)
                    
                    # remember OTF triggered
                    otfTriggered = True
                    
                else:
                    # nothing to do
                    # remember OTF did NOT trigger
                    otfTriggered = False
                
                # maintain stats
                if otfTriggered:
                    now = self.engine.getAsn()
                    if not self.asnOTFevent:
                        assert not self.timeBetweenOTFevents
                    else:
                        self.timeBetweenOTFevents += [now-self.asnOTFevent]
                    self.asnOTFevent = now
            
            # schedule next housekeeping
            self._otf_schedule_housekeeping()

    def _otf_resetInboundTrafficCounters(self):
        with self.dataLock:
            for neighbor in self._myNeigbors()+[self]:
                self.inTraffic[neighbor] = 0
    
    def _otf_incrementIncomingTraffic(self,neighbor):
        with self.dataLock:
            self.inTraffic[neighbor] += 1
    
    #===== 6top
    
    def _sixtop_schedule_housekeeping(self):
        
        self.engine.scheduleIn(
            delay       = self.sixtopHousekeepingPeriod*(0.9+0.2*random.random()),
            cb          = self._sixtop_action_housekeeping,
            uniqueTag   = (self.id,'_sixtop_action_housekeeping'),
            priority    = 5,
        )
    
    def _sixtop_action_housekeeping(self):
        '''
        For each neighbor I have TX cells to, relocate cells if needed.
        '''
        
        #=== tx-triggered housekeeping 
        
        # collect all neighbors I have TX cells to
        txNeighbors = [cell['neighbor'] for ((ts,ch),cell) in self.schedule.items() if cell['dir']==self.DIR_TX]
        
        # remove duplicates
        txNeighbors = list(set(txNeighbors))
        
        
        for neighbor in txNeighbors:
            nowCells = self.numCellsToNeighbors.get(neighbor,0)

            assert nowCells == len([t for ((t,ch),c) in self.schedule.items() if c['dir']==self.DIR_TX and c['neighbor']==neighbor])
       
        # do some housekeeping for each neighbor
        for neighbor in txNeighbors:
            self._sixtop_txhousekeeping_per_neighbor(neighbor)
        
        #=== rx-triggered housekeeping 
        
        # collect neighbors from which I have RX cells that is detected as collision cell
        rxNeighbors = [cell['neighbor'] for ((ts,ch),cell) in self.schedule.items() if cell['dir']==self.DIR_RX and cell['rxDetectedCollision']]
               
        # remove duplicates
        rxNeighbors = list(set(rxNeighbors))
              
        for neighbor in rxNeighbors:
            nowCells = self.numCellsFromNeighbors.get(neighbor,0)
            assert nowCells == len([t for ((t,ch),c) in self.schedule.items() if c['dir']==self.DIR_RX and c['neighbor']==neighbor])
            
        # do some housekeeping for each neighbor
        for neighbor in rxNeighbors:
            self._sixtop_rxhousekeeping_per_neighbor(neighbor)
               
        #=== schedule next housekeeping
        
        self._sixtop_schedule_housekeeping()
    
    def _sixtop_txhousekeeping_per_neighbor(self,neighbor):
        '''
        For a particular neighbor, decide to relocate cells if needed.
        '''
        #===== step 1. collect statistics
 
        # pdr for each cell
        cell_pdr = []
        for ((ts,ch),cell) in self.schedule.items():
            if cell['neighbor']==neighbor and cell['dir']==self.DIR_TX:
                # this is a TX cell to that neighbor
                # abort if not enough TX to calculate meaningful PDR
                if cell['numTx']<self.NUM_SUFFICIENT_TX:
                    continue
                
                # calculate pdr for that cell
                recentHistory = cell['history'][-self.NUM_MAX_HISTORY:]
                pdr = float(sum(recentHistory)) / float(len(recentHistory))
                
                # store result
                cell_pdr += [((ts,ch),pdr)]
       
        # pdr for the bundle as a whole
        bundleNumTx     = sum([len(cell['history'][-self.NUM_MAX_HISTORY:]) for cell in self.schedule.values() if cell['neighbor']==neighbor and cell['dir']==self.DIR_TX])
        bundleNumTxAck  = sum([sum(cell['history'][-self.NUM_MAX_HISTORY:]) for cell in self.schedule.values() if cell['neighbor']==neighbor and cell['dir']==self.DIR_TX])
        if bundleNumTx<self.NUM_SUFFICIENT_TX:
            bundlePdr   = None
        else:
            bundlePdr   = float(bundleNumTxAck) / float(bundleNumTx)
        
        #===== step 2. relocate worst cell in bundle, if any
        # this step will identify the cell with the lowest PDR in the bundle.
        # If its PDR is self.sixtopPdrThreshold lower than the average of the bundle
        # this step will move that cell.
        
        relocation = False
        
        if cell_pdr:
            
            # identify the cell with worst pdr, and calculate the average
            
            worst_tsch   = None
            worst_pdr  = None
            
            for ((ts,ch),pdr) in cell_pdr:
                if worst_pdr==None or pdr<worst_pdr:
                    worst_tsch  = (ts,ch)
                    worst_pdr = pdr
            
            assert worst_tsch!=None
            assert worst_pdr!=None
            
            # ave pdr for other cells
            othersNumTx      = sum([len(cell['history'][-self.NUM_MAX_HISTORY:]) for ((ts,ch),cell) in self.schedule.items() if cell['neighbor']==neighbor and cell['dir']==self.DIR_TX and ts != worst_tsch])
            othersNumTxAck   = sum([sum(cell['history'][-self.NUM_MAX_HISTORY:]) for ((ts,ch),cell) in self.schedule.items() if cell['neighbor']==neighbor and cell['dir']==self.DIR_TX and ts != worst_tsch])           
            if othersNumTx<self.NUM_SUFFICIENT_TX:
                ave_pdr      = None
            else:
                ave_pdr      = float(othersNumTxAck) / float(othersNumTx)

            # relocate worst cell if "bad enough"
            if ave_pdr and worst_pdr<(ave_pdr/self.sixtopPdrThreshold):
                
                # log
                self._log(
                    self.INFO,
                    "[6top] relocating cell ts {0} to {1} (pdr={2:.3f} significantly worse than others {3})",
                    (worst_tsch,neighbor.id,worst_pdr,cell_pdr),
                )
                
                # measure how many cells I have now to that parent
                nowCells = self.numCellsToNeighbors.get(neighbor,0)
                # relocate: add new first
                if self._sixtop_cell_reservation_request(neighbor,1) == 1:
                   
                
                    # relocate: remove old only when successfully added 
                    if nowCells < self.numCellsToNeighbors.get(neighbor,0):
                        if len(self.getTxCells())!=0:
                            self._sixtop_cell_deletion_sender(neighbor,[worst_tsch])
                    
                            # update stats
                            self._stats_incrementMoteStats('topTxRelocatedCells')
                            # remember I relocated a cell for that bundle
                            relocation = True                                  
        
        #===== step 3. relocate the complete bundle
        # this step only runs if the previous hasn't, and we were able to
        # calculate a bundle PDR.
        # This step verifies that the average PDR for the complete bundle is
        # expected, given the RSSI to that neighbor. If it's lower, this step
        # will move all cells in the bundle.
        
        bundleRelocation = False
        
        if (not relocation) and bundlePdr!=None:
            
            # calculate the theoretical PDR to that neighbor, using the measured RSSI
            rssi            = self.getRSSI(neighbor)
            theoPDR         = Topology.Topology.rssiToPdr(rssi)
            
            # relocate complete bundle if measured RSSI is significantly worse than theoretical
            if bundlePdr<(theoPDR/self.sixtopPdrThreshold):
                for ((ts,ch),_) in cell_pdr:
                    
                    # log
                    self._log(
                        self.INFO,
                        "[6top] relocating cell ts {0} to {1} (bundle pdr {2} << theoretical pdr {3})",
                        (ts,neighbor,bundlePdr,theoPDR),
                    )

                    # measure how many cells I have now to that parent
                    nowCells = self.numCellsToNeighbors.get(neighbor,0)
                    # relocate: add new first
                    if self._sixtop_cell_reservation_request(neighbor,1) == 1:

                        # relocate: remove old only when successfully added 
                        if nowCells < self.numCellsToNeighbors.get(neighbor,0):
                            if len(self.getTxCells())!=0:
                                self._sixtop_cell_deletion_sender(neighbor,[(ts,ch)])
                                bundleRelocation = True                        
                # update stats
                if bundleRelocation:
                    self._stats_incrementMoteStats('topTxRelocatedBundles')
    
    def _sixtop_rxhousekeeping_per_neighbor(self,neighbor):
        '''
        The RX node triggers a relocation when it has heard a packet
        from a neighbor it did not expect ('rxDetectedCollision')
        '''    
        
        rxCells = [((ts,ch),cell) for ((ts,ch),cell) in self.schedule.items() if cell['dir']==self.DIR_RX and cell['rxDetectedCollision'] and cell['neighbor']==neighbor]
       
        relocation = False
        for (ts,ch),cell in rxCells:
            
            # measure how many cells I have now from that child
            nowCells = self.numCellsFromNeighbors.get(neighbor,0)
            
            # relocate: add new first
            #bug! before remove, it is necessary to check if a new cell has been really reserved, this happens in all calls to _sixtop_cell_deletion_sender 
            # fixed cheking the return value of _sixtop_cell_reservation_request
                        
            if self._sixtop_cell_reservation_request(neighbor,1,dir=self.DIR_RX) == 1:
            
                # relocate: remove old only when successfully added 
                if nowCells < self.numCellsFromNeighbors.get(neighbor,0):
                    if self.getTxCells():
                        neighbor._sixtop_cell_deletion_sender(self,[(ts,ch)])
                        # remember I relocated a cell
                        relocation = True
        if relocation:
            # update stats
            self._stats_incrementMoteStats('topRxRelocatedCells')
    
    def _sixtop_cell_reservation_request(self,neighbor,numCells,dir=DIR_TX):
        ''' tries to reserve numCells cells to a neighbor. '''
        
        with self.dataLock:
            
            #request numCells to my parent

            givenCells={}
            givenCells_firstRound={}
            givenCells_secondRound={} 

            if self.engine.scheduler=='none': #OTF-sf0
                givenCells       = neighbor._sixtop_cell_reservation_response_random(self,numCells,dir)
            elif self.engine.scheduler=='cen': #Centralized without overlapping
                #print "Using cen"
                givenCells       = neighbor._sixtop_cell_reservation_response_centralized_noOverlapping(self,numCells,dir)
            elif self.engine.scheduler=='opt2': #Centralized with overlapping
                givenCells_firstRound       = neighbor._sixtop_cell_reservation_response_centralized_optimized(self,numCells,dir)
                if len(givenCells_firstRound)<numCells:
                    givenCells_secondRound = neighbor._sixtop_cell_reservation_response_random(self,numCells-len(givenCells_firstRound),dir)           
	    elif self.engine.scheduler=='deBras':
		allCells = []
            	for x in range(0,self.settings.slotframeLength):
                    for y in range(0,self.settings.numChans):
		            cell=['0','0']
		            cell[0]=x
		            cell[1]=y
		            allCells.append(cell)

		#remove my busy cells
		availableCells = []
                for cell in allCells:
                    if self.schedule.has_key((cell[0],cell[1]))==False:
                        availableCells.append(cell)  
		
		#remove the busy cells in my neighborhood
		for neigh in self.scheduleNeigborhood.keys():
                    if neigh != neighbor:
	                for cell in self.scheduleNeigborhood[neigh]:
			    if neigh.schedule[(cell[0],cell[1])]['dir']!='SHARED':
			        if [cell[0],cell[1]] in availableCells:				    
				    if neigh.schedule[(cell[0],cell[1])]['dir']=='RX':
			    		availableCells.remove([cell[0],cell[1]])
				    else:
					if neighbor.getRSSI(neigh)+(-97-(-105)) >= self.minRssi:
						availableCells.remove([cell[0],cell[1]])

                givenCells_firstRound       = neighbor._sixtop_cell_reservation_response_deBras(self,numCells,dir,availableCells)
		
                if len(givenCells_firstRound)<numCells:
                    givenCells_secondRound = neighbor._sixtop_cell_reservation_response_random(self,numCells-len(givenCells_firstRound),dir)
            else:
                print "Unknown scheduler"
                assert False
            
            i=0
            while i < len(givenCells_firstRound):
                givenCells[i]=givenCells_firstRound[i]
                i+=1
            j=i
            i=0
            while i < len(givenCells_secondRound):
                givenCells[i+j]=givenCells_secondRound[i]
                i+=1
        
            if len(givenCells) != numCells:                                                
                for i in range(numCells-len(givenCells)):               	
                    	self._stats_incrementMoteStats('cellsNotGiven')


            cellList    = []
            for i,val in givenCells.iteritems():
                self._log(
                    self.INFO,
                    '[6top] add RX cell ts={0},ch={1} from {2} to {3}',
                    (val[0],val[1],self.id,neighbor.id),
                )
                cellList         += [(val[0],val[1],dir)]

            self._tsch_addCells(neighbor,cellList)

            # update counters
            if dir==self.DIR_TX:
                if neighbor not in self.numCellsToNeighbors:
                    self.numCellsToNeighbors[neighbor]     = 0
                self.numCellsToNeighbors[neighbor]        += len(givenCells)
            else:
                if neighbor not in self.numCellsFromNeighbors:
                    self.numCellsFromNeighbors[neighbor]   = 0
                self.numCellsFromNeighbors[neighbor]      += len(givenCells)
                
            if len(givenCells)!=numCells:
                # log
                self._log(
                    self.ERROR,
                    '[6top] scheduled {0} cells out of {1} required between motes {2} and {3}',
                    (len(givenCells),numCells,self.id,neighbor.id),
                )
            return len(givenCells)
   
            

    def _sixtop_cell_reservation_response_random(self,neighbor,numCells,dirNeighbor):
        ''' get a response from the neighbor. '''
         
        with self.dataLock:
           
            #in the parent, numCells are tried to be reserved
            
	    self.numRandomSelections+=1

            # set direction of cells
            if dirNeighbor == self.DIR_TX:
                dir = self.DIR_RX
            else:
                dir = self.DIR_TX
            
            #this are all my cells
            allCells = []
            for x in range(0,self.settings.slotframeLength):
                for y in range(0,self.settings.numChans):
                #if x==0:
                    cell=['0','0']
                    cell[0]=x
                    cell[1]=y
                    allCells.append(cell)
            
            availableCells = []

            for cell in allCells: 
                if not (cell[0],cell[1]) in self.schedule:
                    if not (cell[0],cell[1]) in neighbor.schedule:
                        availableCells.append(cell) 

            selectedCells={}
            if len(availableCells) > 0:
                random.shuffle(availableCells)

               
                #if they request more cells than I have, I try to give them the maxium available
                while len(availableCells) < numCells:
                    numCells=numCells-1 
                
                ranChosen=random.sample(range(0, len(availableCells)), numCells)
                
                #these are my selected cells
                for i in range(numCells):
                    selectedCells[i]=availableCells[ranChosen[i]]         
                
                cellList              = []
                
                for i,val in selectedCells.iteritems():
                    # log
                    self._log(
                        self.INFO,
                        '[6top] add RX cell ts={0},ch={1} from {2} to {3}',
                        (val[0],val[1],self.id,neighbor.id),
                    )
                    cellList         += [(val[0],val[1],dir)]
                self._tsch_addCells(neighbor,cellList)            
                                    
                # update counters
                if dir==self.DIR_TX:
                    if neighbor not in self.numCellsToNeighbors:
                        self.numCellsToNeighbors[neighbor]     = 0
                    self.numCellsToNeighbors[neighbor]        += len(selectedCells)
                else:
                    if neighbor not in self.numCellsFromNeighbors:
                        self.numCellsFromNeighbors[neighbor]   = 0
                    self.numCellsFromNeighbors[neighbor]      += len(selectedCells)

            
            return selectedCells

    def _sixtop_cell_reservation_response_deBras(self,neighbor,numCells,dirNeighbor, candidates):
	with self.dataLock:

	    availableCells=[]
	    for c in candidates:
		availableCells.append(c)
	
	    # set direction of cells
            if dirNeighbor == self.DIR_TX:
                dir = self.DIR_RX
            else:
                dir = self.DIR_TX
		
	    #remove my busy cells
	    for cell in self.schedule.keys():
		if self.schedule[(cell[0],cell[1])]['dir']!='SHARED':
		    if [cell[0],cell[1]] in candidates:
		        availableCells.remove([cell[0],cell[1]])	

	
	    for neigh in self.scheduleNeigborhood.keys():

                if neigh != neighbor:
	            for cell in self.scheduleNeigborhood[neigh]:
		    	if neigh.schedule[(cell[0],cell[1])]['dir']!='SHARED':
			    if [cell[0],cell[1]] in availableCells:
				if neigh.schedule[(cell[0],cell[1])]['dir']=='TX':
			    		availableCells.remove([cell[0],cell[1]])
				else:
					if neigh.schedule[(cell[0],cell[1])]['neighbor'].getRSSI(self)+(-97-(-105)) >= self.minRssi:
						availableCells.remove([cell[0],cell[1]])

            selectedCells={}
            if len(availableCells) > 0:
                random.shuffle(availableCells)
                               
                #if they request more cells than I have, I try to give them the maxium available
                while len(availableCells) < numCells:
                    numCells=numCells-1 
                
                ranChosen=random.sample(range(0, len(availableCells)), numCells)
                
                #these are my selected cells
                for i in range(numCells):
                    selectedCells[i]=availableCells[ranChosen[i]]         
                
                cellList              = []
                
                for i,val in selectedCells.iteritems():
                    # log
                    self._log(
                        self.INFO,
                        '[6top] add RX cell ts={0},ch={1} from {2} to {3}',
                        (val[0],val[1],self.id,neighbor.id),
                    )
                    cellList         += [(val[0],val[1],dir)]		

                self._tsch_addCells(neighbor,cellList)            
                                    
                # update counters
                if dir==self.DIR_TX:
                    if neighbor not in self.numCellsToNeighbors:
                        self.numCellsToNeighbors[neighbor]     = 0
                    self.numCellsToNeighbors[neighbor]        += len(selectedCells)
                else:
                    if neighbor not in self.numCellsFromNeighbors:
                        self.numCellsFromNeighbors[neighbor]   = 0
                    self.numCellsFromNeighbors[neighbor]      += len(selectedCells)
            
            return selectedCells




    def _sixtop_cell_reservation_response_centralized_noOverlapping(self,neighbor,numCells,dirNeighbor):
        ''' get a response from the neighbor. '''
         
        with self.dataLock:
           
            #in the parent, numCells are tried to be reserved
           
            # set direction of cells
            if dirNeighbor == self.DIR_TX:
                dir = self.DIR_RX
            else:
                dir = self.DIR_TX
            
            #this are all my cells
            allCells = []
            for x in range(0,self.settings.slotframeLength):
                for y in range(0,self.settings.numChans):
		    if (x,y) != (0,0):
		        cell=['0','0']
		        cell[0]=x
		        cell[1]=y
		        allCells.append(cell)         
            
	    #these are all my available cells       
            availableCells = []
            for cell in allCells: 
                if not (cell[0],cell[1]) in self.schedule:
                    if not (cell[0],cell[1]) in neighbor.schedule:
                        availableCells.append(cell) 

            


       
            #this make the scheduler centralized (no collisions at all)            
            for neigh in self.engine.motes:
                if neigh != self and neigh != neighbor:
                    #print "I am 3 my signal to "+str(neigh.id)+" is "+str(self.getRSSI(neigh))+" mins: (self, neigh) "+str((self.minRssi,neigh.minRssi))
                    #print "I am "+str(neigh.id)+" my signal to 3 is "+str(neigh.getRSSI(self))+" mins: (self, neigh) "+str((self.minRssi,neigh.minRssi))
                    for cell in neigh.schedule.keys():
                        #assert False
                        if cell != (0,0):			   
                            if [cell[0],cell[1]] in availableCells:				
                                availableCells.remove([cell[0],cell[1]])

             
            #if I have cells, I try to assign them
            selectedCells={}
            if len(availableCells) > 0:
                random.shuffle(availableCells)
                               
                #if they request more cells than I have, I try to give them the maxium available
                while len(availableCells) < numCells:
                    numCells=numCells-1 
                
                ranChosen=random.sample(range(0, len(availableCells)), numCells)
                
                #these are my selected cells
                for i in range(numCells):
                    selectedCells[i]=availableCells[ranChosen[i]]

                cellList              = []
                
                for i,val in selectedCells.iteritems():
                    # log
                    self._log(
                        self.INFO,
                        '[6top] add RX cell ts={0},ch={1} from {2} to {3}',
                        (val[0],val[1],self.id,neighbor.id),
                    )
                    cellList         += [(val[0],val[1],dir)]
                self._tsch_addCells(neighbor,cellList)            
                                    
                # update counters
                if dir==self.DIR_TX:
                    if neighbor not in self.numCellsToNeighbors:
                        self.numCellsToNeighbors[neighbor]     = 0
                    self.numCellsToNeighbors[neighbor]        += len(selectedCells)
                else:
                    if neighbor not in self.numCellsFromNeighbors:
                        self.numCellsFromNeighbors[neighbor]   = 0
                    self.numCellsFromNeighbors[neighbor]      += len(selectedCells)

            return selectedCells
            
            
            
            
    def _sixtop_cell_reservation_response_centralized_optimized(self,neighbor,numCells,dirNeighbor):
        ''' get a response from the neighbor. '''
         
        with self.dataLock:
           
            #in the parent, numCells are tried to be reserved
           
            # set direction of cells
            if dirNeighbor == self.DIR_TX:
                dir = self.DIR_RX
            else:
                dir = self.DIR_TX

            #this are all my cells
            allCells = []
            for x in range(0,self.settings.slotframeLength):
                for y in range(0,self.settings.numChans):
                    cell=['0','0']
                    cell[0]=x
                    cell[1]=y
                    allCells.append(cell)

            #these are all my available cells    
            availableCells = []
            for cell in allCells: 
                if not (cell[0],cell[1]) in self.schedule:
                    if not (cell[0],cell[1]) in neighbor.schedule:
                        availableCells.append(cell) 

            collidingCells=[]            

            #even fastest version
	    for mote in self.engine.motes:    
                if mote != self and mote != neighbor:
                    if self.getRSSI(mote)+(-97-(-105)) >= mote.minRssi:
		        for cell in mote.schedule.keys():
			    if mote.schedule[(cell[0],cell[1])]['dir']!='SHARED':
				if [cell[0],cell[1]] in availableCells:
				    if mote.schedule[(cell[0],cell[1])]['dir']=='TX':
					availableCells.remove([cell[0],cell[1]])
				    else:
					if mote.getRSSI(neighbor)+(-97-(-105)) >= self.minRssi:
					    availableCells.remove([cell[0],cell[1]])
					
		    if neighbor.getRSSI(mote)+(-97-(-105)) >= mote.minRssi:   
    		        for cell in mote.schedule.keys():
			    if mote.schedule[(cell[0],cell[1])]['dir']!='SHARED':
				if [cell[0],cell[1]] in availableCells:
				    if mote.schedule[(cell[0],cell[1])]['dir']=='RX':
			    		availableCells.remove([cell[0],cell[1]])
				    else:
				        if self.getRSSI(mote)+(-97-(-105)) >= self.minRssi:
					    availableCells.remove([cell[0],cell[1]])
             
            #if I have cells, I try to assign them
            selectedCells={}
            if len(availableCells) > 0:
                random.shuffle(availableCells)
                
               
                #if they request more cells than I have, I try to give them the maxium available
                while len(availableCells) < numCells:
                    numCells=numCells-1 
                
                ranChosen=random.sample(range(0, len(availableCells)), numCells)
                
                #these are my selected cells
                for i in range(numCells):
                    selectedCells[i]=availableCells[ranChosen[i]]
                
                cellList              = []
                
                for i,val in selectedCells.iteritems():
                    # log
                    self._log(
                        self.INFO,
                        '[6top] add RX cell ts={0},ch={1} from {2} to {3}',
                        (val[0],val[1],self.id,neighbor.id),
                    )
                    cellList         += [(val[0],val[1],dir)]
                self._tsch_addCells(neighbor,cellList)            
                                    
                # update counters
                if dir==self.DIR_TX:
                    if neighbor not in self.numCellsToNeighbors:
                        self.numCellsToNeighbors[neighbor]     = 0
                    self.numCellsToNeighbors[neighbor]        += len(selectedCells)
                else:
                    if neighbor not in self.numCellsFromNeighbors:
                        self.numCellsFromNeighbors[neighbor]   = 0
                    self.numCellsFromNeighbors[neighbor]      += len(selectedCells)

            return selectedCells
   
    def _sixtop_cell_deletion_sender(self,neighbor,tsList):
        with self.dataLock:

            # log
            self._log(
                self.INFO,
                "[6top] remove timeslots={0} with {1}",
                (tsList,neighbor.id),
            )
            self._tsch_removeCells2(
                neighbor     = neighbor,
                tsList       = tsList,
            )

            neighbor._sixtop_cell_deletion_receiver(self,tsList)

            self.numCellsToNeighbors[neighbor]       -= len(tsList)

            assert self.numCellsToNeighbors[neighbor]>=0

    
    def _sixtop_cell_deletion_receiver(self,neighbor,tsList):
        with self.dataLock:
               
            self._tsch_removeCells2(
                neighbor     = neighbor,
                tsList       = tsList,
            )

            if self.numCellsFromNeighbors[neighbor]:
                self.numCellsFromNeighbors[neighbor]     -= len(tsList)
          
            assert self.numCellsFromNeighbors[neighbor]>=0
            
    
    def _sixtop_removeCells(self,neighbor,numCellsToRemove):
        '''
        Finds cells to neighbor, and remove it.
        '''

        scheduleList = []
        
        # worst cell removing initialized by theoretical pdr
        for ((ts,ch),cell) in self.schedule.iteritems():
            if cell['neighbor']==neighbor and cell['dir']==self.DIR_TX:
                cellPDR           = (float(cell['numTxAck'])+(self.getPDR(neighbor)*self.NUM_SUFFICIENT_TX))/(cell['numTx']+self.NUM_SUFFICIENT_TX)
                scheduleList     += [(ts,ch,cell['numTxAck'],cell['numTx'],cellPDR)]

        # introduce randomness in the cell list order
        random.shuffle(scheduleList)
               
        if not self.settings.sixtopNoRemoveWorstCell:
            # triggered only when worst cell selection is due
            # (cell list is sorted according to worst cell selection)
            scheduleListByPDR     = {}
            for tscell in scheduleList:
                if not scheduleListByPDR.has_key(tscell[3]):
                    scheduleListByPDR[tscell[3]]=[]
                scheduleListByPDR[tscell[3]]+=[tscell]
            rssi                  = self.getRSSI(neighbor)
            theoPDR               = Topology.Topology.rssiToPdr(rssi)
            scheduleList          = []
            for pdr in sorted(scheduleListByPDR.keys()):
                if pdr<theoPDR:
                    scheduleList += sorted(scheduleListByPDR[pdr], key=lambda x: x[2], reverse=True)
                else:
                    scheduleList += sorted(scheduleListByPDR[pdr], key=lambda x: x[2])        
            
        # remove a given number of cells from the list of available cells (picks the first numCellToRemove)
        tsList=[]
        for tscell in scheduleList[:numCellsToRemove]:
            
            # log
            self._log(
                self.INFO,
                "[otf] remove cell ts={0} to {1} (pdr={2:.3f})",
                ((tscell[0],tscell[1]),neighbor.id,tscell[3]),
            )
            tsList += [(tscell[0],tscell[1])]
        
        # remove cells
        self._sixtop_cell_deletion_sender(neighbor,tsList)
    
    #===== tsch
    
    def _tsch_enqueue(self,packet):

        if not self.preferredParent:
            # I don't have a route
            print "No route!"
            # increment mote state
            self._stats_incrementMoteStats('droppedNoRoute')
            assert False
            return False
        
        elif not self.getTxCells():
            # I don't have any transmit cells
            self._stats_incrementMoteStats('droppedNoTxCells')

            return False
        
        elif len(self.txQueue)==self.TSCH_QUEUE_SIZE:
            # my TX queue is full
            # update mote stats
            self._stats_incrementMoteStats('droppedQueueFull')

            return False
        
        else:
            # all is good           
            # enqueue packet
            self.txQueue    += [packet]

            return True
    
    def _tsch_schedule_activeCell(self):
        
        asn        = self.engine.getAsn()
        tsCurrent  = asn%self.settings.slotframeLength
        
        # find closest active slot in schedule
        with self.dataLock:
            
            if not self.schedule:
                self.engine.removeEvent(uniqueTag=(self.id,'_tsch_action_activeCell'))
                return
            
            tsDiffMin             = None
            for ((ts,ch),cell) in self.schedule.items():
                if   ts==tsCurrent:
                    tsDiff        = self.settings.slotframeLength
                elif ts>tsCurrent:
                    tsDiff        = ts-tsCurrent
                elif ts<tsCurrent:
                    tsDiff        = (ts+self.settings.slotframeLength)-tsCurrent
                else:
                    raise SystemError()
                
                if (not tsDiffMin) or (tsDiffMin>tsDiff):
                    tsDiffMin     = tsDiff

        self.engine.scheduleAtAsn(
            asn         = asn+tsDiffMin,
            cb          = self._tsch_action_activeCell,
            uniqueTag   = (self.id,'_tsch_action_activeCell'),
            priority    = 0,
        )
        
    
    def _tsch_action_activeCell(self):
        '''
        active slot starts. Determine what todo, either RX or TX, use the propagation model to introduce
        interference and Rx packet drops.
        '''
        
        asn = self.engine.getAsn()
        ts  = asn%self.settings.slotframeLength
       
        with self.dataLock:
            
            self.pktToSend = []
         
            tss=[row[0] for row in self.schedule.keys()]

            assert ts in tss
           
            numberPacketSentInThisTs=0
            for i_ch in range(0,self.settings.numChans):
                if (ts,i_ch) in self.schedule.keys():
                    cell = self.schedule[(ts,i_ch)]
                    if (cell['dir']==self.DIR_SHARED):
                        if asn > ((2*self.settings.slotframeLength)-1):
                                                                             
                            if i_ch == (self.myBrCh) and ts==(self.myBrTs):    
                                                               
                                assert cell['dir']==self.DIR_SHARED
                                
                                if self.numberOfWaitings==0:
                                    #I have to send a Broadcast cell                              
                                    self.numberOfWaitings=self.maxWin-1
                                    assert i_ch == self.myBrCh
                                    assert ts == self.myBrTs
                                    cell = self.schedule[(ts,i_ch)]
                                                                       
                                    schedulingPacket = {
                                                'asn':            self.engine.getAsn(),
                                                'type':           self.SIXP_TYPE_MYSCHEDULE,
                                                'payload':        [self.id,self.engine.getAsn(),self.schedule], # the payload is used for latency and number of hops calculation
                                                'retriesLeft':    self.TSCH_MAXTXRETRIES
                                                }

                                    self.schedule[(ts,i_ch)]['waitingfor']=self.DIR_SHARED
                                    
                                    self.engine.bcstTransmitted+=1                                
                                    
                                    self.propagation.startTx(
                                                    channel   = cell['ch'],
                                                    type      = schedulingPacket['type'],
                                                    smac      = self,
                                                    dmac      = self._myNeigbors(),
                                                    payload   = schedulingPacket['payload'],
                                                )
                                                                                                                                   
                                    # log charge usage
                                    self._logChargeConsumed(self.CHARGE_TxData_uC)                        
                                else:
                                    #if it is not my turn to transmit broadcast, I try to receive                                                                        
                                    self.numberOfWaitings=self.numberOfWaitings-1
                                    self.schedule[(ts,i_ch)]['waitingfor']=self.DIR_SHARED
                                    self.propagation.startRx(
                                        mote          = self,
                                        channel       = cell['ch'],
                                    )
                                
                            else:
                                self.schedule[(ts,i_ch)]['waitingfor']=self.DIR_SHARED
                                self.propagation.startRx(
                                    mote          = self,
                                    channel       = cell['ch'],
                                )
                                 
                    
                
                    else:    
                        
                        cell = self.schedule[(ts,i_ch)]
                        assert cell
                        
                        if  cell['dir']==self.DIR_RX:
          
                            self.schedule[(ts,i_ch)]['waitingfor']=self.DIR_RX
                            self.propagation.startRx(
                                mote          = self,
                                channel       = cell['ch'],
                            ) 
                    
                        elif cell['dir']==self.DIR_TX:
                            if self.txQueue:
                                if len(self.txQueue) >= (numberPacketSentInThisTs+1):                                
                                    self.pktToSend.append(self.txQueue[numberPacketSentInThisTs])
                            
                            # send packet
                            if bool(self.pktToSend) == True:
                                if len(self.pktToSend) >= (numberPacketSentInThisTs+1):                                      
                                        cell['numTx'] += 1
                                        self.numTransmissions += 1
                                        self.schedule[(ts,i_ch)]['waitingfor']=self.DIR_TX                                     
                                        
                                        self.propagation.startTx(
                                            channel   = cell['ch'],
                                            type      = self.pktToSend[numberPacketSentInThisTs]['type'],
                                            smac      = self,
                                            dmac      = cell['neighbor'],
                                            payload   = self.pktToSend[numberPacketSentInThisTs]['payload'],
                                        )
                    
                                        # indicate that we're waiting for the TX operation to finish
                                                                 
                                        # log charge usage
                                        self._logChargeConsumed(self.CHARGE_TxDataRxAck_uC)
                                        numberPacketSentInThisTs=numberPacketSentInThisTs+1

                    self._tsch_schedule_activeCell()
    
    def _tsch_addCells(self,neighbor,cellList):
        ''' adds cell(s) to the schedule '''
        
        with self.dataLock:
            for cell in cellList:
                
                assert cell
                
                self.schedule[(cell[0],cell[1])] = {
                    'ts':                        cell[0],
                    'ch':                        cell[1],
                    'dir':                       cell[2],
                    'neighbor':                  neighbor,
                    'numTx':                     0,
                    'busy':                      0,
                    'numTxAck':                  0,
                    'broadCell_id':              None,
                    'numRx':                     0,
                    'history':                   [],
                    'waitingfor':                None,
                    'rxDetectedCollision':       False,
                    'debug_canbeInterfered':     [],                      # [debug] shows schedule collision that can be interfered with minRssi or larger level 
                    'debug_interference':        [],                      # [debug] shows an interference packet with minRssi or larger level 
                    'debug_lockInterference':    [],                      # [debug] shows locking on the interference packet
                    'debug_cellCreatedAsn':      self.engine.getAsn(),    # [debug]
                }
                
                # log
                self._log(
                    self.INFO,
                    "[tsch] add cell ts={0} ch={1} dir={2} with {3}",
                    (cell[0],cell[1],cell[2],neighbor.id),
                )

            self._tsch_schedule_activeCell()
            
            
    def _tsch_removeCells2(self,neighbor,tsList):
        ''' removes cell(s) from the schedule '''
       
        with self.dataLock:
            # log
            self._log(
                self.INFO,
                "[tsch] remove timeslots={0} with {1}",
                (tsList,neighbor.id),
            )

            for ts,ch in tsList:

                assert (ts,ch) in self.schedule.keys()
               	assert self.schedule[(ts,ch)]['dir']!=self.DIR_SHARED
                del self.schedule[(ts,ch)]
                
            self._tsch_schedule_activeCell()
    
    #===== radio
    
    def radio_txDone(self,isACKed,isNACKed):
        '''end of tx slot'''
        asn   = self.engine.getAsn()
        ts    = asn%self.settings.slotframeLength
        
        with self.dataLock:
            tss=[row[0] for row in self.schedule.keys()]
            assert ts in tss

                    
            i_ch=0
            for i_ch in range(self.settings.numChans):
                if (ts,i_ch) in self.schedule.keys():        
                        
                    if self.schedule[(ts,i_ch)]['waitingfor']==self.DIR_TX:

                        assert self.schedule[(ts,i_ch)]['dir']==self.DIR_TX
                        assert self.schedule[(ts,i_ch)]['waitingfor']==self.DIR_TX

                        if isACKed:

                            # update schedule stats
                            self.schedule[(ts,i_ch)]['numTxAck'] += 1
                            
                            # update history
                            self.schedule[(ts,i_ch)]['history'] += [1]
                            
                            # update queue stats
                            self._stats_logQueueDelay(asn-self.pktToSend[0]['asn'])
                            
                            # time correction
                            if self.schedule[(ts,i_ch)]['neighbor'] == self.preferredParent:
                                self.timeCorrectedSlot = asn
                            
                            # remove packet from queue
                            self.txQueue.remove(self.pktToSend[0])
                            self.pktToSend.remove(self.pktToSend[0])
                            

                        elif isNACKed:  #when fails in enqueue packet
                            
                            # NACK received
                            # update schedule stats as if it were successfully transmitted
                            self.schedule[(ts,i_ch)]['numTxAck'] += 1

                            # update history
                            self.schedule[(ts,i_ch)]['history'] += [1]
                            
                            # time correction
                            if self.schedule[(ts,i_ch)]['neighbor'] == self.preferredParent:
                                self.timeCorrectedSlot = asn

			    #remove this part because it is considered that a packet received is a good MAC tx even if the queue in the rx node is full
                            
                            # remove packet from queue
                            self.txQueue.remove(self.pktToSend[0])
                            self.pktToSend.remove(self.pktToSend[0])
                            
                        else:
                            # neither ACK nor NACK received
                            # update history
                            self.schedule[(ts,i_ch)]['history'] += [0]

                            # decrement 'retriesLeft' counter associated with that packet
                            i = self.txQueue.index(self.pktToSend[0])
                            if self.txQueue[i]['retriesLeft'] > 0:
                                self.txQueue[i]['retriesLeft'] -= 1
                            
                            
                            #debug problem with MAC drops                                  
                            # drop packet if retried too many time
                            if self.txQueue[i]['retriesLeft'] == 0:
                                self._stats_incrementMoteStats('droppedMacRetries')
                                                                
                                # remove packet from queue
                                self.txQueue.remove(self.pktToSend[0])
                                self.pktToSend.remove(self.pktToSend[0])

                        self.schedule[(ts,i_ch)]['waitingfor']=None
                        return
    
    def radio_rxDone(self,type=None,smac=None,dmac=None,payload=None,channel=None):
        '''end of RX radio activity'''
        
        asn   = self.engine.getAsn()
        ts    = asn%self.settings.slotframeLength
        with self.dataLock:
           
            if type=='SIXP_TYPE_MYSCHEDULE':

                if self.schedule.has_key((ts,channel)) and self.schedule[(ts,channel)]['waitingfor']==self.DIR_SHARED and self.schedule[(ts,channel)]['dir']==self.DIR_SHARED:
                  
                    if smac:
                        # I received a packet
                        
                        # log charge usage
                        self._logChargeConsumed(self.CHARGE_RxData_uC)
                        
                        
                        scheduleOfNeigbor=payload[2]

                        self._updateSchedule(scheduleOfNeigbor,smac)
                        
                        self.engine.bcstReceived+=1                        
                        
                        # update schedule stats

                        (isACKed, isNACKed) = (True, False)
                        self.schedule[(ts,channel)]['waitingfor']=None
                        return isACKed, isNACKed
                    else:
                        # this was an idle listen 
                        # log charge usage
                        self._logChargeConsumed(self.CHARGE_Idle_uC)
                                
                        (isACKed, isNACKed) = (False, False)


                        self.schedule[(ts,channel)]['waitingfor']=None
                        return isACKed, isNACKed
                            
            elif type=='TRAFFICOMIO':                
                for i_ch in range(0,self.settings.numChans):                
                    if (ts,i_ch) in self.schedule.keys() and self.schedule[(ts,channel)]['dir']!=self.DIR_SHARED:           
                        assert self.schedule[(ts,channel)]['dir']!=self.DIR_SHARED 
                        if self.schedule[(ts,i_ch)]['waitingfor']==self.DIR_RX:

                            assert self.schedule[(ts,i_ch)]['dir']==self.DIR_RX
                            assert self.schedule[(ts,i_ch)]['waitingfor']==self.DIR_RX
                            
                            if smac:
				self.numReceptions += 1
                                # I received a packet
                                # log charge usage
                                self._logChargeConsumed(self.CHARGE_RxDataTxAck_uC)
                                
                                # update schedule stats
                                self.schedule[(ts,i_ch)]['numRx'] += 1
                                
                                if self.dagRoot:
                                    # receiving packet (at DAG root)
                                    
                                    # update mote stats
                                    self._stats_incrementMoteStats('appReachesDagroot')
                                    
                                    #emunicio
				    #loging probing packets
                                    self.numPacketReceived=self.numPacketReceived+1 
				    if (self.engine.asn < (96*self.settings.slotframeLength)) and (self.engine.asn > (63*self.settings.slotframeLength)):
                                        self.probeNumPacketReceived=self.probeNumPacketReceived+1
                                    
                                    # calculate end-to-end latency
                                    self._stats_logLatencyStat(asn-payload[1])
                                    
                                    # log the number of hops
                                    self._stats_logHopsStat(payload[2])
                                    
                                    (isACKed, isNACKed) = (True, False)
   
                                    self.schedule[(ts,i_ch)]['waitingfor']=None
                                    return isACKed, isNACKed
                                else:
                                    # relaying packet
                                    # count incoming traffic for each node
                                    self._otf_incrementIncomingTraffic(smac)
                                    
                                    # update the number of hops
                                    newPayload     = copy.deepcopy(payload)
                                    newPayload[2] += 1
                                    
                                    # create packet
                                    relayPacket = {
                                        'asn':         asn,
                                        'type':        type,
                                        'payload':     newPayload,
                                        'retriesLeft': self.TSCH_MAXTXRETRIES
                                    }
                                    
                                    # enqueue packet in TSCH queue
                                    isEnqueued = self._tsch_enqueue(relayPacket)
                                    
                                    if isEnqueued:
                                        
                                        # update mote stats
                                        self._stats_incrementMoteStats('appRelayed')
                                        
                                        (isACKed, isNACKed) = (True, False)
                                        
                                        self.schedule[(ts,i_ch)]['waitingfor']=None                                
                                        return isACKed, isNACKed
                                    else:

                                        self._stats_incrementMoteStats('droppedAppFailedEnqueue')
                                        (isACKed, isNACKed) = (False, True)
                                        #if relayPacket['payload'][0]==24:
                                            #print "Sending NACK"
                                        self.schedule[(ts,i_ch)]['waitingfor']=None
                                        return isACKed, isNACKed
                            else:
                                # this was an idle listen
                                # log charge usage
                                self._logChargeConsumed(self.CHARGE_Idle_uC)
                                
                                (isACKed, isNACKed) = (False, False)
                    
                                self.schedule[(ts,i_ch)]['waitingfor']=None
                                return isACKed, isNACKed    
            
            else:
                 
		 #always coung charge
		 self._logChargeConsumed(self.CHARGE_Idle_uC)
               
                 (isACKed, isNACKed) = (False, False)

                 #if the broadcast packet has failed, we still can wait for a correct broadcast in other cell
                                 
                 self.schedule[(ts,channel)]['waitingfor']=None
                 return isACKed, isNACKed

    #===== wireless
    
    def setPDR(self,neighbor,pdr):
        ''' sets the pdr to that neighbor'''
        with self.dataLock:
            self.PDR[neighbor] = pdr
    
    def getPDR(self,neighbor):
        ''' returns the pdr to that neighbor'''
        with self.dataLock:
            return self.PDR[neighbor]
    
    def setRSSI(self,neighbor,rssi):
        ''' sets the RSSI to that neighbor'''
        with self.dataLock:
            self.RSSI[neighbor] = rssi
    
    def getRSSI(self,neighbor):
        ''' returns the RSSI to that neighbor'''
        with self.dataLock:
            #emunicio
            if neighbor==self:
                return self.minRssi
            else:
                return self.RSSI[neighbor]
    
    def _estimateETX(self,neighbor):
        
        with self.dataLock:
            
            # set initial values for numTx and numTxAck assuming PDR is exactly estimated
            pdr                   = self.getPDR(neighbor)
            numTx                 = self.NUM_SUFFICIENT_TX
            numTxAck              = math.floor(pdr*numTx)
            
            for (_,cell) in self.schedule.items():
                if (cell['neighbor'] == neighbor) and (cell['dir'] == self.DIR_TX):  #ok shared cell broadcast is not taken in account
                    numTx        += cell['numTx']
                    numTxAck     += cell['numTxAck']
            
            # abort if about to divide by 0
            if not numTxAck:
                return
            
            # calculate ETX
            
            etx = float(numTx)/float(numTxAck)

            return etx
    
    def _myNeigbors(self):
        return [n for n in self.PDR.keys() if self.PDR[n]>0]

    def _myInterferersNeigbors(self):	#mote.getRSSI(self)+(-97-(-105))  >= self.minRssi
        return [n for n in self.RSSI.keys() if (self.RSSI[n]+(-97-(-105)))>=self.minRssi]

    def _myGoodNeigbors(self):
        return [n for n in self.PDR.keys() if self.PDR[n]>0.5]
    
    #===== clock
    
    def clock_getOffsetToDagRoot(self):
        ''' calculate time offset compared to the DAGroot '''
        
        asn                  = self.engine.getAsn()
        offset               = 0.0
        child                = self
        parent               = self.preferredParent
            
        while True:
            secSinceSync     = (asn-child.timeCorrectedSlot)*self.settings.slotDuration  # sec
            # FIXME: for ppm, should we not /10^6?
            relDrift         = child.drift - parent.drift                                # ppm
            offset          += relDrift * secSinceSync    				 # us

            if parent.dagRoot:
                break
            else:
                child        = parent
                parent       = child.preferredParent

        return offset
        
    #emunicio  
     
    def recalculateNumHopsToRoot(self):
        ''' calculate time offset compared to the DAGroot '''
        child                = self
        parent               = self.preferredParent
        i=0
        while True:
            i=i+1
            if i>30:
                assert False # more than hops 30 is not allowed
            if parent.dagRoot:
                break
            else:
                child        = parent
                parent       = child.preferredParent
             
        return i
    #===== location
    
    def setLocation(self,x,y):
        with self.dataLock:
            self.x = x
            self.y = y
    
    def getLocation(self):
        with self.dataLock:
            return (self.x,self.y)
    
    #==== battery
    
    def boot(self):
        # start the stack layer by layer
        
        # app
        if not self.dagRoot:
            self._app_schedule_sendSinglePacket(firstPacket=True)
        # RPL
        self._rpl_schedule_sendDIO(firstDIO=True)
        # OTF
        self._otf_resetInboundTrafficCounters()

        # 6top
        if not self.settings.sixtopNoHousekeeping:
            self._sixtop_schedule_housekeeping()
	if self.settings.scheduler=='deBras':
            self._schedule_setInitialCell()

        # tsch
        self._tsch_schedule_activeCell()
                 
    def _logChargeConsumed(self,charge):
        with self.dataLock:
            self.chargeConsumed  += charge
	    
    
    #======================== private =========================================
    
    #===== getters
    
    def getChildrens(self,node):
        with self.dataLock:
            children=[]                                           
            for mote in self.engine.motes:
                if mote.preferredParent == node:
                    children.append(mote)  
            return children   
    
    #not used when OTF is present
    def getMyMaxCellDemand(self):
        with self.dataLock:
            alcanzables=[]

            alcanzables=self.getChildrens(self) 
            cellTh=len(alcanzables)+1  #+1 because I have to bear in mind my own traffic
            while len(alcanzables)!=0:
                hijo=alcanzables[0]
                alcanzables.remove(hijo)
                for hijodehijo in self.getChildrens(hijo):
                    cellTh+=1
                    alcanzables.append(hijodehijo)    
            cellTh=int((((1-self.getPDR(self.preferredParent))+1)*cellTh)+1)     
            return cellTh
    
    def getTxCells(self):
        with self.dataLock:
            return [(ts,c['ch'],c['neighbor']) for ((ts,ch),c) in self.schedule.items() if c['dir']==self.DIR_TX]
    
    def getRxCells(self):
        with self.dataLock:
            return [(ts,c['ch'],c['neighbor']) for ((ts,ch),c) in self.schedule.items() if c['dir']==self.DIR_RX]
    def getRxCellsToNeighbor(self,neighbor):
        with self.dataLock:
            return [(ts,c['ch'],c['neighbor']) for ((ts,ch),c) in self.schedule.items() if c['dir']==self.DIR_RX and c['neighbor']==neighbor]
    def getSharedCells(self):
        with self.dataLock:
            return [(ts,c['ch'],c['neighbor']) for ((ts,ch),c) in self.schedule.items() if c['dir']==self.DIR_SHARED]

    #===== stats
    
    # mote state  
    def getMoteStats(self):
                      
        # gather statistics
        with self.dataLock:
            returnVal = copy.deepcopy(self.motestats)
            returnVal['numTxCells']         = len(self.getTxCells())
            returnVal['numRxCells']         = len(self.getRxCells())
            returnVal['aveQueueDelay']      = self._stats_getAveQueueDelay()
            returnVal['aveLatency']         = self._stats_getAveLatency()
            returnVal['aveHopsPackets']     = self.hopsToRoot
            returnVal['aveHops']            = self._stats_getAveHops()
            returnVal['probableCollisions'] = self._stats_getRadioStats('probableCollisions')            
            returnVal['txQueueFill']        = len(self.txQueue)
            returnVal['PKTTX']              = self.numPacketSent
            returnVal['PKTRX']              = self.numPacketReceived
            returnVal['numReqCells']        = self.numReqCells
            returnVal['chargeConsumed']     = self.chargeConsumed
            returnVal['numTx']              =self.numTransmissions
            returnVal['numRx']              =self.numReceptions
            returnVal['thReqCells']         =self.threq
            returnVal['txBroadcast']     = self.engine.bcstTransmitted
            returnVal['rxBroadcast']     = self.engine.bcstReceived
	    returnVal['numRandomSelections']     = self.numRandomSelections
        # reset the statistics
        self._stats_resetMoteStats()
        self._stats_resetQueueStats()
        self._stats_resetLatencyStats()
        self._stats_resetHopsStats()
        self._stats_resetRadioStats()
        
        return returnVal
    
    
    def _stats_resetMoteStats(self):
        with self.dataLock:
            self.motestats = {
                # app
                'appGenerated':            0,   # number of packets app layer generated
                'appRelayed':              0,   # number of packets relayed
                'appReachesDagroot':       0,   # number of packets received at the DAGroot
                'droppedAppFailedEnqueue': 0,   # dropped packets because app failed enqueue them
                # queue
                'droppedQueueFull':        0,   # dropped packets because queue is full
                # rpl
                'rplTxDIO':                0,   # number of TX'ed DIOs
                'rplRxDIO':                0,   # number of RX'ed DIOs
                'rplChurnPrefParent':      0,   # number of time the mote changes preferred parent
                'rplChurnRank':            0,   # number of time the mote changes rank
                'rplChurnParentSet':       0,   # number of time the mote changes parent set
                'droppedNoRoute':          0,   # packets dropped because no route (no preferred parent)
                # otf
                'otfAdd':                  0,   # OTF adds some cells
                'otfRemove':               0,   # OTF removes some cells
                'droppedNoTxCells':        0,   # packets dropped because no TX cells
                # 6top
                'topTxRelocatedCells':     0,   # number of time tx-triggered 6top relocates a single cell
                'topTxRelocatedBundles':   0,   # number of time tx-triggered 6top relocates a bundle
                'topRxRelocatedCells':     0,   # number of time rx-triggered 6top relocates a single cell
                # tsch
                'droppedMacRetries':       0,   # packets dropped because more than TSCH_MAXTXRETRIES MAC retries
                'numReqCells':                   0,	
                'thReqCells':                   0,
                'cellsNotGiven':            0,
            }

    
    def _stats_incrementMoteStats(self,name):
        with self.dataLock:
            self.motestats[name] += 1
                    
    # cell stats
    
    def getCellStats(self,ts_p,ch_p):
        ''' retrieves cell stats '''
        
        returnVal = None
        with self.dataLock:
            for ((ts,ch),cell) in self.schedule.items():
                if ts==ts_p and cell['ch']==ch_p:
                    returnVal = {
                        'dir':            cell['dir'],
                        'neighbor':       cell['neighbor'].id,
                        'numTx':          cell['numTx'],
                        'numTxAck':       cell['numTxAck'],
                        'numRx':          cell['numRx'],
                    }
                    break
        return returnVal
    
    # queue stats
    
    def _stats_logQueueDelay(self,delay):
        with self.dataLock:
            self.queuestats['delay'] += [delay]
    
    def _stats_getAveQueueDelay(self):
        d = self.queuestats['delay']
        return float(sum(d))/len(d) if len(d)>0 else 0
    
    def _stats_resetQueueStats(self):
        with self.dataLock:
            self.queuestats = {
                'delay':               [],
            }
    
    # latency stats
    
    def _stats_logLatencyStat(self,latency):
        with self.dataLock:
            self.packetLatencies += [latency]
    
    def _stats_getAveLatency(self):
        with self.dataLock:
            d = self.packetLatencies
            return float(sum(d))/float(len(d)) if len(d)>0 else 0
    
    def _stats_resetLatencyStats(self):
        with self.dataLock:
            self.packetLatencies = []
    
    # hops stats
    
    def _stats_logHopsStat(self,hops):
        with self.dataLock:
            self.packetHops += [hops]
    
    def _stats_getAveHops(self):
        with self.dataLock:
            d = self.packetHops
            #print "Packet HOPS"+str(d)
            return float(sum(d))/float(len(d)) if len(d)>0 else 0
    
    def _stats_resetHopsStats(self):
        with self.dataLock:
            self.packetHops = []
    
    # radio stats
    
    def stats_incrementRadioStats(self,name):
        with self.dataLock:
            self.radiostats[name] += 1
    
    def _stats_getRadioStats(self,name):
        return self.radiostats[name]
    
    def _stats_resetRadioStats(self):
        with self.dataLock:
            self.radiostats = {
                'probableCollisions':      0,   # number of packets that can collide with another packets 
            }
    
    #===== log
    
    def _log(self,severity,template,params=()):
        
        if   severity==self.DEBUG:
            if not log.isEnabledFor(logging.DEBUG):
                return
            logfunc = log.debug
        elif severity==self.INFO:
            if not log.isEnabledFor(logging.INFO):
                return
            logfunc = log.info
        elif severity==self.WARNING:
            if not log.isEnabledFor(logging.WARNING):
                return
            logfunc = log.warning
        elif severity==self.ERROR:
            if not log.isEnabledFor(logging.ERROR):
                return
            logfunc = log.error
        else:
            raise NotImplementedError()
        
        output  = []
        output += ['[ASN={0:>6} id={1:>4}] '.format(self.engine.getAsn(),self.id)]
        output += [template.format(*params)]
        output  = ''.join(output)
        logfunc(output)
        
    def _log_printEndResults(self):
        with self.dataLock:
            self.engine.totalRx=self.engine.totalRx+self.numReceptions
            self.engine.totalTx=self.engine.totalTx+self.numTransmissions
		
	    self.engine.packetsSentToRoot=self.probePacketsGenerated+self.engine.packetsSentToRoot
	    self.engine.olGeneratedToRoot=(self.probePacketsGenerated/self.engine.timeElapsedFlow)+self.engine.olGeneratedToRoot
	    self.engine.packetReceivedInRoot=self.probeNumPacketReceived+self.engine.packetReceivedInRoot
	    self.engine.thReceivedInRoot=(self.probeNumPacketReceived/self.engine.timeElapsedFlow)+self.engine.thReceivedInRoot
	    
	    if self.settings.generateIndividualSummarys == True:

            	with open('{1}/mysummary{0}_{2}_cpu{3}.ods'.format(self.settings.numMotes,self.settings.simDataDir,self.settings.scheduler,self.settings.cpuID),'a') as f:
                	f.write("Mote "+str(self.id)+" TimeElapsed "+str(self.engine.timeElapsedFlow)+" PacketsGenerated "+str(self.probePacketsGenerated)+" AvgOLgenerated: "+str(self.probePacketsGenerated/self.engine.timeElapsedFlow)+" pk/s"+" PacketsReceived "+str(self.probeNumPacketReceived)+" AvgTHReceived: "+str(self.probeNumPacketReceived/self.engine.timeElapsedFlow)+" pk/s\n")
                	if self.id==0:
                    		print "Mote "+str(self.id)+" TimeElapsed "+str(self.engine.timeElapsedFlow)+" PacketsGenerated "+str(self.probePacketsGenerated)+" AvgOLgenerated: "+str(self.probePacketsGenerated/self.engine.timeElapsedFlow)+" pk/s"+" PacketsReceived "+str(self.probeNumPacketReceived)+" AvgTHReceived: "+str(self.probeNumPacketReceived/self.engine.timeElapsedFlow)+" pk/s\n"

    def _schedule_setInitialCell(self):
        
        with self.dataLock:

	    broadCell_id=0  
	    for neighbor in self._myInterferersNeigbors(): #initial neighbor selection
	        self.scheduleNeigborhood[neighbor]={}

            for j_ch in range(0,self.settings.numChans):

                ts_b=0
                for n in range(0,self.settings.numBroadcastCells):
                    cell = (ts_b,j_ch)
		    if broadCell_id < self.settings.numMotes:   #avoid allocate more cells per cycle than existing nodes

			    self.schedule[(ts_b,j_ch)] = {
			                'ts':                        ts_b,
			                'ch':                        j_ch,
			                'dir':                       self.DIR_SHARED,
			                'neighbor':                  self.BROAD,
			                'numTx':                     0,
			                'numTxAck':                  0,
			                'broadCell_id':              broadCell_id,
			                'numRx':                     0,
			                'busy':                      0,
			                'history':                   [],
			                'waitingfor':                None,
			                'rxDetectedCollision':       False,
			                'debug_canbeInterfered':     [],                      # [debug] shows schedule collision that can be interfered with minRssi or larger level 
			                'debug_interference':        [],                      # [debug] shows an interference packet with minRssi or larger level 
			                'debug_lockInterference':    [],                      # [debug] shows locking on the interference packet
			                'debug_cellCreatedAsn':      self.engine.getAsn(),    # [debug]
			            }

			    ts_b+=int(self.settings.slotframeLength/self.settings.numBroadcastCells)
			    broadCell_id+=1
      
            if self.settings.numBroadcastCells!=0:            
                
                
                self.maxWin=math.ceil((float(self.settings.numMotes)/(broadCell_id)))             
                self.numberOfWaitings= int((self.id/(broadCell_id)))

                value=[(ts,c['ch']) for ((ts,ch),c) in self.schedule.items() if c['broadCell_id']==(self.id % (broadCell_id))]
                self.myBrTs=value[0][0]
                self.myBrCh=value[0][1]

 
    def checkIfNeighborsInThisBroadcastCell(self, broadCell_id, order):
        
        neighbors=self._myNeigbors()
        candidates=[]

        for neigh in neighbors:  
            if self.DEBUG: print "neighbor "+str(neigh.id)+" is using this broadcast cell: C "+str(neigh.chosenBroadCell_id)+" and order "+str(neigh.numberOfWaitings)
            if neigh.chosenBroadCell_id==broadCell_id and neigh.numberOfWaitings==order:
                if self.DEBUG: print "probable Collision!"
                candidates.append(neigh)
        return candidates        

    def _updateSchedule(self,scheduleOfNeighbor,neighbor):

        with self.dataLock:
        
                if self.scheduleNeigborhood[neighbor]!=scheduleOfNeighbor:

                    self.scheduleNeigborhood[neighbor]=scheduleOfNeighbor

