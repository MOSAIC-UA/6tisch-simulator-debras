#!/usr/bin/python
'''
\brief Wireless propagation model.

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
log = logging.getLogger('Propagation')
log.setLevel(logging.DEBUG)
log.addHandler(NullHandler())

#============================ imports =========================================

import threading
import random
import math
#emunicio
import operator

import Topology
import SimSettings
import SimEngine

#============================ defines =========================================

#============================ body ============================================

class Propagation(object):
    
    #===== start singleton
    _instance      = None
    _init          = False
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Propagation,cls).__new__(cls, *args, **kwargs)
        return cls._instance
    #===== end singleton
    
    def __init__(self):
        
        #===== start singleton
        # don't re-initialize an instance (needed because singleton)
        if self._init:
            return
        self._init = True
        #===== end singleton
        
        # store params
        self.settings                  = SimSettings.SimSettings()
        self.engine                    = SimEngine.SimEngine()
        
        # variables
        self.dataLock                  = threading.Lock()
        self.receivers                 = [] # motes with radios currently listening
        self.transmissions             = [] # ongoing transmissions
        random.seed(5)
        # schedule propagation task
        self._schedule_propagate()
    
    def destroy(self):
        self._instance                 = None
        self._init                     = False
    
    #======================== public ==========================================
    
    #===== communication
    
    def startRx(self,mote,channel):
        ''' add a mote as listener on a channel'''
        with self.dataLock:
            self.receivers += [{
                'mote':                mote,
                'channel':             channel,
            }]
    
    def startTx(self,channel,type,smac,dmac,payload):
        ''' add a mote as using a channel for tx'''
        with self.dataLock:
            self.transmissions  += [{
                'channel':             channel,
                'type':                type,
                'smac':                smac,
                'dmac':                dmac,
                'payload':             payload,
            }]
    
    def propagate(self):
        ''' Simulate the propagation of pkts in a slot. '''
        
        with self.dataLock:
            
            asn   = self.engine.getAsn()
            ts    = asn%self.settings.slotframeLength
            
            arrivalTime = {}
                       
            # store arrival times of transmitted packets 
            for transmission in self.transmissions:
                if transmission['smac'].id != 0:
                    arrivalTime[transmission['smac']] = transmission['smac'].clock_getOffsetToDagRoot()
                else:
                    arrivalTime[transmission['smac']] = self.engine.getAsn()
                                   
            sortedTransmissionByChannel=[]
            for i in range(0,self.settings.numChans):
                for transmission in self.transmissions:
                   
                    if transmission['channel']==i:
                        sortedTransmissionByChannel.append(transmission)
         
            for transmission in sortedTransmissionByChannel:
                
                i           = 0 # index of a receiver
                isACKed     = False
                isNACKed    = False

                if 'SIXP_TYPE_MYSCHEDULE' == transmission['type']:
                    
                    while i<len(self.receivers):
                        if self.receivers[i]['channel']==transmission['channel']:
                            interferers = [t['smac'] for t in self.transmissions if (t!=transmission) and (t['channel']==transmission['channel'])]
                            
                            interferenceFlag = 0
                            for itfr in interferers:
                               
                                if self.receivers[i]['mote'].getRSSI(itfr) >self.receivers[i]['mote'].minRssi:
                                    interferenceFlag = 1
                                                        
                            if interferenceFlag:
                                transmission['smac'].stats_incrementRadioStats('probableCollisions') 
                            
                            lockOn = transmission['smac']
                            for itfr in interferers:
                                if arrivalTime[itfr] < arrivalTime[lockOn] and self.receivers[i]['mote'].getRSSI(itfr)>self.receivers[i]['mote'].minRssi:
                                    # lock on interference
                                    lockOn = itfr
                            
                            if lockOn == transmission['smac']:
                                # mote locked in the current signal
                                transmission['smac'].schedule[(ts,transmission['channel'])]['debug_lockInterference'] += [0] # debug only
                                
                                # calculate pdr, including interference
                                sinr  = self._computeSINR(transmission['smac'],self.receivers[i]['mote'],interferers,True)
                                pdr   = self._computePdrFromSINR(sinr, self.receivers[i]['mote'])
                                                                                                 
                                
                                # pick a random number
                                failure = random.random() 

                                if pdr>=failure:
        
                                    isACKed, isNACKed = self.receivers[i]['mote'].radio_rxDone(
                                        type       = transmission['type'],
                                        smac       = transmission['smac'],
                                        dmac       = self.receivers[i]['mote'],
                                        payload    = transmission['payload'],
                                        channel    = transmission['channel']
                                    )                                        
                                    # this mote stops listening
                                    #EB Broadcast message received correctly
                                del self.receivers[i]
                                  
                            else:
				#EB Broadcast message not received correctly
                                #not including broadcast collisions in the stats                                                                                                   
                                self.receivers[i]['mote'].radio_rxDone(None,None,None,None,transmission['channel'])
                                del self.receivers[i]

                        i += 1                                                
                else:    
                    #normal cell
                    while i<len(self.receivers):
                        
                        if self.receivers[i]['channel']==transmission['channel']:
                            # this receiver is listening on the right channel
                            
                            if self.receivers[i]['mote']==transmission['dmac']:
                                # this packet is destined for this mote
                                                                                       
                                if not self.settings.noInterference:
      
                                    #================ with interference ===========
                                     
                                    # other transmissions on the same channel?
                                    interferers = [t['smac'] for t in self.transmissions if (t!=transmission) and (t['channel']==transmission['channel'])]
                                                                        
                                    interferenceFlag = 0
                                    for itfr in interferers:
                                        if transmission['dmac'].getRSSI(itfr)+(-97-(-105))>transmission['dmac'].minRssi:
					    # here we are considering that several non interfererers can create a collisions. 
					    # we add a margin of (-97-(-105)) when considering interference
                                            interferenceFlag = 1
                                            
                                    
                                    transmission['smac'].schedule[(ts,transmission['channel'])]['debug_interference'] += [interferenceFlag] # debug only
                                                                                                          
                                    if interferenceFlag:
                                        transmission['smac'].stats_incrementRadioStats('probableCollisions') 
                                    
                                    lockOn = transmission['smac']
                                    for itfr in interferers:
                                        if arrivalTime[itfr] < arrivalTime[lockOn] and transmission['dmac'].getRSSI(itfr)>transmission['dmac'].minRssi:
                                            # lock on interference                                            
                                            lockOn = itfr
                                    
                                    if lockOn == transmission['smac']:
                                        # mote locked in the current signal
                                        
                                        transmission['smac'].schedule[(ts,transmission['channel'])]['debug_lockInterference'] += [0] # debug only
                                        
                                        # calculate pdr, including interference
                                        sinr  = self._computeSINR(transmission['smac'],transmission['dmac'],interferers,False)
                                        pdr   = self._computePdrFromSINR(sinr, transmission['dmac'])

                                        # pick a random number
                                        failure = random.random() 

                                        if pdr>=failure:
                                           
                                            isACKed, isNACKed = self.receivers[i]['mote'].radio_rxDone(
                                                type       = transmission['type'],
                                                smac       = transmission['smac'],
                                                dmac       = transmission['dmac'],
                                                payload    = transmission['payload'],
                                                channel    = transmission['channel']
                                            )  
                                            #message received correctly
                                            # this mote stops listening
                                            del self.receivers[i]
                                            
                                        else: 
					    #here does not mean there is a collision. Only means a packet that have a possible interference has failed. 
					    #it is not known yet if the error is due to collision                                           
                                            if interferenceFlag: #due to collision						
                                                self.engine.incrementStatDropByCollision()
							
					    else: #due to propagation
						self.engine.incrementStatDropByPropagation()
                                            self.receivers[i]['mote'].radio_rxDone(None,None,None,None,transmission['channel'])
                                            del self.receivers[i]
                                        
                                    else:
                                        # mote locked in an interfering signal

                                        # for debug
                                        transmission['smac'].schedule[(ts,transmission['channel'])]['debug_lockInterference'] += [1]
                                        
                                        # receive the interference as if it's a desired packet
                                        interferers.remove(lockOn)
                                        pseudo_interferers = interferers + [transmission['smac']]
                                        
                                        # calculate SINR where locked interference and other signals are considered S and I+N respectively
                                        pseudo_sinr  = self._computeSINR(lockOn,transmission['dmac'],pseudo_interferers,False)
                                        pseudo_pdr   = self._computePdrFromSINR(pseudo_sinr, transmission['dmac'])
                                        
                                        # pick a random number
                                        failure = random.random()
                                        if pseudo_pdr>=failure:
                                            # success to receive the interference and realize collision
                                            
                                            transmission['dmac'].schedule[(ts,transmission['channel'])]['rxDetectedCollision'] = True
                                            
                                        # desired packet is not received
                                        self.engine.incrementStatDropByCollision()
                                        self.receivers[i]['mote'].radio_rxDone(None,None,None,None,transmission['channel'])
                                        del self.receivers[i]
                                    
                                else:
                                    
                                    #================ without interference ========
                                    assert False #only interference model
                        i += 1
                    # indicate to source packet was sent
                    transmission['smac'].radio_txDone(isACKed, isNACKed)
            
            
            # remaining receivers that does not receive a desired packet
            for r in self.receivers:
                
                if not self.settings.noInterference:
                    
                    #================ with interference ===========
                   
                    interferers = [t['smac'] for t in self.transmissions if t['dmac']!=r['mote'] and t['channel']==r['channel']]
                    
                    lockOn = None
                    for itfr in interferers:
                        
                        if not lockOn:
                            if r['mote'].getRSSI(itfr)>r['mote'].minRssi:
                                lockOn = itfr
                        else:
                            if r['mote'].getRSSI(itfr)>r['mote'].minRssi and arrivalTime[itfr]<arrivalTime[lockOn]:
                                lockOn = itfr
                    
                    if lockOn:
                        # pdr calculation
                        
                        # receive the interference as if it's a desired packet
                        interferers.remove(lockOn)
    
                        # calculate SINR where locked interference and other signals are considered S and I+N respectively
                        pseudo_sinr  = self._computeSINR(lockOn,r['mote'],interferers,False)
                        pseudo_pdr   = self._computePdrFromSINR(pseudo_sinr,r['mote'])
                        
                        # pick a random number
                        failure = random.random()

                        if pseudo_pdr>=failure:
                            for cell in lockOn.schedule.keys():
                                if cell in r['mote'].schedule.keys():
                                    if cell[0] == ts:
                                        # success to receive the interference and realize collision
                                         
                                        r['mote'].schedule[(ts,cell[1])]['rxDetectedCollision'] = True

                    # desired packet is not received                   
                    r['mote'].radio_rxDone(None,None,None,None,r['channel'])
                else: #only model with interference
                    assert False
            # clear all outstanding transmissions
            self.transmissions              = []
            self.receivers                  = []
        #assert False
        self._schedule_propagate()
    
    #======================== private =========================================
    
    def _schedule_propagate(self):
        with self.dataLock:
            self.engine.scheduleAtAsn(
                asn         = self.engine.getAsn()+1,# so propagation happens in next slot
                cb          = self.propagate,
                uniqueTag   = (None,'propagation'),
                priority    = 1,
            )
    
    def _computeSINR(self,source,destination,interferers,broadcast):
        ''' compute SINR  '''
       
#        #maximize interference effects in order to check ideal cases
#        if broadcast==False:
#            for interferer in interferers:   
#                if (destination.getRSSI(interferer)+(-97-(-105)) >= destination.minRssi):
#                    return -10.0
                         
        noise = self._dBmTomW(destination.noisepower)

        signal = self._dBmTomW(source.getRSSI(destination)) - noise

        if signal < 0.0:
            # RSSI has not to be below noise level. If this happens, return very low SINR (-10.0dB)
            return -10.0
          
        totalInterference = 0.0
        for interferer in interferers:
            # I = RSSI - N            
            interference = self._dBmTomW(interferer.getRSSI(destination)) - noise

            if interference < 0.0:
                # RSSI has not to be below noise level. If this happens, set interference 0.0
                interference = 0.0
            totalInterference += interference

        sinr = signal/(totalInterference + noise)

        return self._mWTodBm(sinr)
    
    def _computePdrFromSINR(self, sinr, destination):
        ''' compute PDR from SINR '''

        
	 #for remove propagation errors in order to check ideal cases (if it is in range, PDR=1)       
#        if sinr > 10:
#            return 1
#        else:
#            return 0
        
        
        equivalentRSSI  = self._mWTodBm(
            self._dBmTomW(sinr+destination.noisepower) + self._dBmTomW(destination.noisepower)
        )
        

        pdr             = Topology.Topology.rssiToPdr(equivalentRSSI)

        
        return pdr
    
    def _dBmTomW(self, dBm):
        ''' translate dBm to mW '''
        return math.pow(10.0, dBm/10.0)
    
    def _mWTodBm(self, mW):
        ''' translate dBm to mW '''
        return 10*math.log10(mW)
