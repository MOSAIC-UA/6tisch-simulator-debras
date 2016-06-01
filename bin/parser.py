import numpy as np
import matplotlib.pyplot as plt
import os
import collections
import operator
import subprocess
from pylab import *

import csv

def parse(filename):
	
    cycleInit=63
    cycleEnd=97
    maxCycles=100


    cycles=cycleEnd-cycleInit #end receiving - start receiving	
    command="find "
    args='{0} -name output* | sort -V'.format(filename)

    print str(command+args)
    tmp = os.popen(command+args).read()
    listOfFiles=tmp.split("\n")
    data_dict={}
     
    currentNumNodes=None 
	
    for filename in listOfFiles:
        i=0
        numRuns=None 	
	runParsed=None	
	
		
	if filename != "":
	    
	    print "Filtering: "+str(filename)
            nodes=filename.split("_")[10]
	    if currentNumNodes==None or nodes!=currentNumNodes:
		currentNumNodes=nodes
		
		OL=[]
		throughput=[]
		PER=[]#not used here
		TXpkt=[]
		RXpkt=[]
		collisionDrops=[]
	        propagationDrops=[]
		dropsMAC=[]
		dropsAPP=[]
		delay=[]
		battery=[]
		avgHops=[]
		rplParentChanges=[]
		avgEffectiveCollided=[]
		numTx=[]
		numRx=[]
		avgRTX=[]#not used here
		usedCells=[]
		reqCells=[]
		randomSelections=[]
		txbroad=[]
		rxbroad=[]
		PERBroad=[]   #not used here
		otf_messages=[]
	    

            infile = open(filename, 'r')

	    	
	    dropsMAC_values=None
            dropsAPP_values=None
	    delay_values=None
	    rpl_values=None

	    battery_values=[]
	    avgHops_values=None
	    avgEffectiveCollided_values=None
	    usedCells_values=0
            reqCells_values=0
	    randomSelections_values=None
	    txbroad_values=None
	    rxbroad_values=None
	    otf_messages_add=0
	    otf_messages_remove=0
	    otf_messages_values=None

	    for line in infile:
	        if i==5:
		    #print delay
		    numMotes=int(line.split(" ")[3])
		    
	        if i==24:
		    numRuns=int(line.split(" ")[3])
	            runParsed=1

	        if (numRuns!=None) and (runParsed<=numRuns):
	            if i==(29+(runParsed*(maxCycles+6))):			
			OL.append(float(line.split(" ")[7])*128*8)

			throughput.append(float(line.split(" ")[9])*128*8)

			numTx.append(float(line.split(" ")[13]))
			numRx.append(float(line.split(" ")[15]))
			TXpkt.append(int(line.split(" ")[3]))
			RXpkt.append(int(line.split(" ")[5]))
			
			collisionDrops.append(int(line.split(" ")[11]))
	    		propagationDrops.append(int(line.split(" ")[17]))


			runParsed+=1

		    if i>=((33+(runParsed*(maxCycles+6)))-(maxCycles+6)) and i<=((33+(runParsed*(maxCycles+6)))-7):	
			if rpl_values!=None:	
				rpl_values=int(line.split()[29])+int(rpl_values)
			else:
				rpl_values=int(line.split()[29])
			if dropsMAC_values!= None:
				dropsMAC_values=int(line.split()[14])+int(dropsMAC_values)
			else:
				dropsMAC_values=int(line.split()[14])
			if dropsAPP_values!= None:
				dropsAPP_values=int(line.split()[13])+int(dropsAPP_values)
			else:
				dropsAPP_values=int(line.split()[13])
			if txbroad_values!=None:
				txbroad_values=int(line.split()[40])+int(txbroad_values)
			else:
				txbroad_values=int(line.split()[40])
			if rxbroad_values!=None:
				rxbroad_values=int(line.split()[34])+int(rxbroad_values)
			else:
				rxbroad_values=int(line.split()[34])
			if otf_messages_values!=None:
				otf_messages_add=int(line.split()[25])+int(otf_messages_add)
				otf_messages_remove=int(line.split()[26])+int(otf_messages_remove)
				otf_messages_values=otf_messages_add+otf_messages_remove
			else:
				otf_messages_add=int(line.split()[25])
				otf_messages_remove=int(line.split()[26])
				otf_messages_values=otf_messages_add+otf_messages_remove
			if randomSelections_values!=None:
				randomSelections_values=int(line.split()[19])+int(randomSelections_values)
			else:
				randomSelections_values=int(line.split()[19])
			
			if i>=((33+cycleInit+(runParsed*(maxCycles+6)))-(maxCycles+6)) and i<=((33+(runParsed*(maxCycles+6)))-7-(maxCycles-cycleEnd)):
				if avgEffectiveCollided_values!=None:	
					avgEffectiveCollided_values=int(line.split()[18])+int(avgEffectiveCollided_values)
				else:
					avgEffectiveCollided_values=int(line.split()[18])
				if delay_values!=None:	
					delay_values=float(line.split()[7])+float(delay_values)
				else:
					delay_values=float(line.split()[7])
				if avgHops_values!=None:	
					avgHops_values=float(line.split()[5])+float(avgHops_values)
				else:
					avgHops_values=float(line.split()[5])
				usedCells_values=float(line.split()[24])+float(usedCells_values)
				reqCells_values=float(line.split()[20])+float(reqCells_values)
				#print "cycle "+str(line.split()[12]) + " hops "+str(line.split()[5])
			if i==((29+(runParsed*(maxCycles+6)))-3):
				battery_values.append(float(line.split()[10]))
		    else:
			if rpl_values!=None:

				rplParentChanges.append(float(rpl_values/numMotes))
				rpl_values=None
			if dropsMAC_values!=None:
				dropsMAC.append(int(dropsMAC_values))
				dropsMAC_values=None
			if dropsAPP_values!=None:	
				dropsAPP.append(int(dropsAPP_values))
				dropsAPP_values=None
			if delay_values!=None:				
				delay.append(float(0.01*delay_values/cycles))
				delay_values=None

			if battery_values!=[]:
				battery_values=[num for num in battery_values if num ]	
				battery.append(np.mean(battery_values)/numMotes)
				print "Battery "+str(battery)
				battery_values=[]
			if avgHops_values!=None:				
				avgHops.append(avgHops_values/cycles)		
				avgHops_values=None
			if reqCells_values!=0:
				reqCells.append(reqCells_values/cycles)		
				reqCells_values=0
			if usedCells_values!=0:
				usedCells.append(usedCells_values/cycles)		
				usedCells_values=0
			if txbroad_values!=None:	
				txbroad.append(int(txbroad_values))
				txbroad_values=None
			if rxbroad_values!=None:	
				rxbroad.append(int(rxbroad_values))
				rxbroad_values=None
			if avgEffectiveCollided_values!=None:	
				avgEffectiveCollided.append(int(avgEffectiveCollided_values/cycles))
				avgEffectiveCollided_values=None
			if randomSelections_values!=None:	
				randomSelections.append(int(randomSelections_values))
				randomSelections_values=None
			if otf_messages_values!=None:	 
				otf_messages.append(int(otf_messages_values))
				otf_messages_values=None
				otf_messages_add=0
				otf_messages_remove=0
				

	        i+=1
	    data_dict[int(nodes)]=(OL,throughput,PER,TXpkt,RXpkt,collisionDrops,propagationDrops,dropsMAC,dropsAPP,delay,battery,avgHops,rplParentChanges,avgEffectiveCollided,numTx,numRx,usedCells,reqCells,randomSelections,txbroad,rxbroad,otf_messages)    	    
    print "End parsing"

    return data_dict
    


def plot_image(parsed_data,filenumber, column):


        print "There are sets: "+str(len(parsed_data))
        print "Ploting results of column "+str(column)

        print "There are sets: "+str(parsed_data[0][2])

        data_to_plot=[]
        yerr=[]


        parameter_translator={1: ['0','OL'], 2: ['1','Throughput'], 3: ['x','PER'], 4: ['3','TXpkts'],5: ['4','RXpkts'],6: ['5','dropsCollisions'],7: ['6','dropsPorpagation'],8: ['7','dropsMAC'],9: ['8','dropsAPP'],10: ['10','battery'],11: ['11','avgHops'],12: ['12','rplChanges'],13: ['13','effectiveCollided'],14: ['14','numTx'],15: ['15','numRx'],16: ['x','RTX'],17: ['16','usedCells'],18: ['17','ReqCells'],19: ['18','RandomSelection'],20: ['19','txbroad'],21: ['20','rxbroad'],22: ['x','PERBroad'],23: ['9','delay'], 24: ['21','otfMessages'], 25: ['x','PERDropColl'], 26: ['x','PERDropProp']}



    
    
	data_dict=parsed_data[filenumber]
	print "There are variables to plot: "+str(len(data_dict[2]))
	print "But I am going to display column: "+str(column)
	print "I am going to display column: "+str(parameter_translator[int(column)])

	data=[]


	for value in sorted(data_dict.keys()):
	    data.append((value,data_dict[value]))             
	
	x=[item[0] for item in data]

	if parameter_translator[int(column)][0]!='x':

		lenSets=[len(item3[1][1]) for item3 in data]	

		data_to_plot.append([np.mean(item[1][int(parameter_translator[int(column)][0])]) for item in data])
		print data_to_plot
		yerr.append([sqrt(np.var(item[1][int(parameter_translator[int(column)][0])])) for item in data])
		   

		return x, data_to_plot,yerr,parameter_translator[int(column)][1]
	else:
		if parameter_translator[int(column)][1]=='PER':
			per=[]
			for item in data:
				#data_to_plot.append(item[1][5]/item[1][4])
				tx=item[1][int(parameter_translator[int(4)][0])]
				rx=item[1][int(parameter_translator[int(5)][0])]	
				per.append([(1-float(a)/b) for a,b in zip(rx,tx)])


			data_to_plot.append([np.mean(item) for item in per])
			yerr.append([sqrt(np.var(item)) for item in per])
			print len(data_to_plot)
			return x, data_to_plot,yerr,parameter_translator[int(column)][1]
		elif parameter_translator[int(column)][1]=='RTX':
			rtx=[]
			print "RTX"
			for item in data:
				#data_to_plot.append(item[1][5]/item[1][4])
				tx=item[1][int(parameter_translator[int(14)][0])]				
				rx=item[1][int(parameter_translator[int(15)][0])]	
				rtx.append([float(a)/b for a,b in zip(tx,rx)])

				
			data_to_plot.append([np.mean(item) for item in rtx])
			print len(data_to_plot)
			yerr.append([sqrt(np.var(item)) for item in rtx])
			return x, data_to_plot,yerr,parameter_translator[int(column)][1]
		elif parameter_translator[int(column)][1]=='PERBroad':
			perbroad=[]

			for item in data:
				#data_to_plot.append(item[1][5]/item[1][4])
				tx=item[1][int(parameter_translator[int(20)][0])]				
				rx=item[1][int(parameter_translator[int(21)][0])]
				val=[]
				for i in range(len(rx)):
					if rx[i]!=0:
						val.append(rx[i]/tx[i])
					else:
						val.append(0)
				perbroad.append(val)
			
			data_to_plot.append([np.mean(item) for item in perbroad])
			
			yerr.append([sqrt(np.var(item)) for item in perbroad])
			return x, data_to_plot,yerr,parameter_translator[int(column)][1]

		elif parameter_translator[int(column)][1]=='PERDropColl':
			perbroad=[]

			for item in data:
				#data_to_plot.append(item[1][5]/item[1][4])
				tx=item[1][int(parameter_translator[int(14)][0])]				
				rx=item[1][int(parameter_translator[int(6)][0])]
				val=[]
				for i in range(len(rx)):
					if rx[i]!=0:
						val.append(rx[i]/tx[i])
					else:
						val.append(0)
				perbroad.append(val)
			
			data_to_plot.append([np.mean(item) for item in perbroad])
			
			yerr.append([sqrt(np.var(item)) for item in perbroad])
			return x, data_to_plot,yerr,parameter_translator[int(column)][1]
		elif parameter_translator[int(column)][1]=='PERDropProp':
			perbroad=[]

			for item in data:
				#data_to_plot.append(item[1][5]/item[1][4])
				tx=item[1][int(parameter_translator[int(14)][0])]				
				rx=item[1][int(parameter_translator[int(7)][0])]
				val=[]
				for i in range(len(rx)):
					if rx[i]!=0:
						val.append(rx[i]/tx[i])
						
					else:
						val.append(0)
					print val
				perbroad.append(val)
			
			data_to_plot.append([np.mean(item) for item in perbroad])
			
			yerr.append([sqrt(np.var(item)) for item in perbroad])
			return x, data_to_plot,yerr,parameter_translator[int(column)][1]

		else:
			assert False

def write_in_file(namefile,data_dict):

    data_to_write=[]
    
    print "There are sets: "+str(len(data_dict))
    print "Printing results in file: "+namefile

    data=[]

    for value in sorted(data_dict.keys()):
        data.append((value,data_dict[value]))

    numNodes=([item[0] for item in data]) 

    
       

    data_to_write.append([np.mean(item[1][0]) for item in data]) #OL    
    data_to_write.append([np.mean(item[1][1]) for item in data]) #throughput

    #print data_to_write
    data_to_write.append([(1-np.mean(item[1][4])/np.mean(item[1][3])) for item in data]) # PER
    data_to_write.append([np.mean(item[1][3]) for item in data]) # txpkt
    data_to_write.append([np.mean(item[1][4]) for item in data]) #rxpkt
    data_to_write.append([np.mean(item[1][5]) for item in data]) #drops collision
    data_to_write.append([np.mean(item[1][6]) for item in data]) #drops propagation
    data_to_write.append([np.mean(item[1][7]) for item in data]) # dropsmac
    data_to_write.append([np.mean(item[1][8]) for item in data]) #dropsapp
    data_to_write.append([np.mean(item[1][10]) for item in data]) # battery
    data_to_write.append([np.mean(item[1][11]) for item in data]) # avghops
    data_to_write.append([(np.mean(item[1][12])) for item in data]) # rplChanges
    data_to_write.append([np.mean(item[1][13]) for item in data]) # collided cells
    data_to_write.append([np.mean(item[1][14]) for item in data]) # numtx
    data_to_write.append([np.mean(item[1][15]) for item in data]) # numrx
    data_to_write.append([(np.mean(item[1][14])/np.mean(item[1][15])) for item in data]) # RTX
    data_to_write.append([np.mean(item[1][16]) for item in data]) # usedcells
    data_to_write.append([np.mean(item[1][17]) for item in data]) # reqcells
    data_to_write.append([np.mean(item[1][18]) for item in data]) # random selections
    data_to_write.append([np.mean(item[1][19]) for item in data]) # txbroad
    data_to_write.append([np.mean(item[1][20]) for item in data]) # rxbroad

    if np.mean(item[1][20])==0:
	data_to_write.append([np.mean(item[1][19]) for item in data])
    else:
    	data_to_write.append([(np.mean(item[1][20])/np.mean(item[1][19])) for item in data]) # PER broad

    data_to_write.append([np.mean(item[1][9]) for item in data]) # delay
    data_to_write.append([np.mean(item[1][9]) for item in data]) # otf messages

    with open(namefile,'a+') as csvfile:
	
	spamwriter = csv.writer(csvfile, delimiter=' ', quoting=csv.QUOTE_MINIMAL)
	content=["Nodes","OL","Throughput","PER","TX","RX","DropsCollisions","dropsPropagation","DropsMAC","DropsAPP","battery","avgHops","rplChanges","avgEffectiveCollided","numTx","numRx","avgRTX","usedCells","ReqCells","randomSelections","txbroad","rxbroad","PERBroad","delay","otfmessages"]
	



	spamwriter.writerow(content)
	for i in range(len(numNodes)):
		if data_to_write[2][i]<0:
			data_to_write[2][i]=0
		if data_to_write[15][i]<0:
			data_to_write[15][i]=0
		if data_to_write[20][i]<0:
			data_to_write[20][i]=0

		content=[numNodes[i],data_to_write[0][i],data_to_write[1][i],data_to_write[2][i],data_to_write[3][i],data_to_write[4][i],data_to_write[5][i],data_to_write[6][i],data_to_write[7][i],data_to_write[8][i],data_to_write[9][i],data_to_write[10][i],data_to_write[11][i],data_to_write[12][i],data_to_write[13][i],data_to_write[14][i],data_to_write[15][i],data_to_write[16][i],data_to_write[17][i],data_to_write[18][i],data_to_write[19][i],data_to_write[20][i],data_to_write[21][i],data_to_write[22][i],data_to_write[23][i]]
	
		spamwriter.writerow(content)
 
def autolabel(rects):
	for rect in rects:
		height = rect.get_height()
		ax.text(rect.get_x() + rect.get_width()/2., 1.05*height,
			'%d' % int(height),
			ha='center',            # vertical alignment
			va='bottom'             # horizontal alignment
			)
   

def print_help():
	print "This program needs arguments, ie:"
	print "To parse: parser.py parse dir1 dir2"
	print "To plot: parser.py plot parameter_to_plot dir1 dir2"
	print "To compare centralised-decentralised: parser.py otf-comparison dir1"
	print "To compare two parameter: parser.py comparison parameter1_to_plot parameter2_to_plot dir1"
	print "The parameters available are:"
	parameter_translator={1: ['0','OL'], 2: ['1','Throughput'], 3: ['x','PER'], 4: ['3','TXpkts'],5: ['4','RXpkts'],6: ['5','dropsCollisions'],7: ['6','dropsPorpagation'],8: ['7','dropsMAC'],9: ['8','dropsAPP'],10: ['10','battery'],11: ['11','avgHops'],12: ['12','rplChanges'],13: ['13','effectiveCollided'],14: ['14','numTx'],15: ['15','numRx'],16: ['x','RTX'],17: ['16','usedCells'],18: ['17','ReqCells'],19: ['18','RandomSelection'],20: ['19','txbroad'],21: ['20','rxbroad'],22: ['x','PERBroad'],23: ['9','delay'], 24: ['21','otfMessages'], 25: ['x','PERDropColl'], 26: ['x','PERDropProp']}
	for col in parameter_translator.items():
		print str(col[0])+" "+str(col[1][1])

if __name__ == '__main__':

    maxYvalue=0
    colors_dic={0: 'bo-', 1: 'r^-',2: 'ks-',3: 'y^-',4: 'b*-',5: 'ro-',6: 'ko-',7: 'y*-'}

    legend_dic={0: 'v0', 1: 'v1',2: 'v2',3: 'v3',4: 'v4',5: 'v5',6: 'v6',7: 'v7'} #4 # 5


    if len(sys.argv) >= 2:

	if sys.argv[1] == 'parse': 
		print "Starting to parse..."
		y_values=[e for number in xrange(len(sys.argv)-2)]
   		yerr_values=[e for number in xrange(len(sys.argv)-2)]
		parsed_data=[]
	
		for i in range(len(sys.argv)-2):
			print "Searching in dir: "+sys.argv[i+2];
			if sys.argv[i+2][len(sys.argv[i+2])-1]=='/':  #check no / is in the name
				sys.argv[i+2]=sys.argv[i+2][:-1]
			print "Searching in dir: "+sys.argv[i+2];
		
			parsed_data.append(parse(sys.argv[i+2]))
		i=0
		for data_dict in parsed_data:
			write_in_file("./results.ods",data_dict)
			i+=1



	elif sys.argv[1] == 'plot': 
		print "Starting to plot..."
		y_values=[e for number in xrange(len(sys.argv)-2)]
   		yerr_values=[e for number in xrange(len(sys.argv)-2)]

		print "There are files: "+str(len(sys.argv)-2)
		if len(sys.argv) < 4:
			print_help()
		elif int(sys.argv[2]) == 0 or int(sys.argv[2]) > 26:
			print "Parameter "+str(sys.argv[2])+" not available"
			print_help()
		else:	
			parsed_data=[]
		        fig=plt.figure()
			ax=plt.subplot(111)

			for i in range(len(sys.argv)-3):
				print "Reading file: "+sys.argv[i+3];
				print i
				parsed_data.append(parse(sys.argv[i+3]))
			nodes=[keys for keys in parsed_data[0].keys()]
			print "Parse done. There are nodes: "+str(max(nodes))	
			for i in range(len(sys.argv)-3):	
				[x,y_values[i],yerr_values[i],title]=plot_image(parsed_data,i, sys.argv[2] )		
				print "adding ..."+str(y_values[i])				
	    			plt.errorbar(x, y_values[i][0], yerr=yerr_values[i][0],fmt=colors_dic[i],label=legend_dic[i],markersize=10)
				if maxYvalue<float(max(y_values[i][0])):
					maxYvalue=float(max(y_values[i][0]))

			plt.xlabel('# nodes',fontsize=13)
			plt.ylabel('MAC Retransmissions (RTX)',fontsize=15)
			
			ax.legend(loc='center', bbox_to_anchor=(0.5, 1.02),ncol=1, fancybox=True, shadow=True)

			if maxYvalue==0:
				plt.ylim(0, 1)
			else:
				plt.ylim(0, float(maxYvalue)*1.1)
			plt.xlim(0, max(nodes))
			plt.grid(True)
			plt.show()

	elif sys.argv[1] == 'otf-comparison': 
		y_values=[e for number in xrange(len(sys.argv)-1)]
  		yerr_values=[e for number in xrange(len(sys.argv)-1)]

		parsed_data=[]
		plt.figure()
		ax=plt.subplot(111)
		for i in range(len(sys.argv)-2):
			print "Reading file: "+sys.argv[i+2];
			parsed_data.append(parse(sys.argv[i+2]))
		print "Parse done"
		nodes=[keys for keys in parsed_data[0].keys()]
	
		[x,y_values[0],yerr_values[0],title]=plot_image(parsed_data,0, 24 )	
		plt.errorbar(x, y_values[0][0], yerr=yerr_values[0][0],fmt=colors_dic[0],label=legend_dic[0])

		[x,y_values[1],yerr_values[1],title]=plot_image(parsed_data,0, 11 ) # number of hops

		aveHops=np.mean(y_values[1])
	
		y_cen_values=[]
		yerr_cen_values=[]
		y_cen_values = [val * aveHops * 2 for val in y_values[0][0]]
		yerr_cen_values=[val * aveHops * 2 for val in yerr_values[0][0]]
		if maxYvalue<float(max(y_cen_values)):
			maxYvalue=float(max(y_cen_values))

		plt.errorbar(x, y_cen_values, yerr=yerr_cen_values,fmt=colors_dic[1],label=legend_dic[1])
		ax.legend(loc='center', bbox_to_anchor=(0.5, 1.02),ncol=1, fancybox=True, shadow=True)
		plt.xlabel('# nodes')
		plt.ylabel('Number of control messages')
	    	plt.ylim(0, float(maxYvalue)*1.1)
		plt.xlim(0, max(nodes))
		plt.grid(True)
		plt.show()

	elif sys.argv[1] == 'comparison': 
		print len(sys.argv)
		if len(sys.argv) == 5:
			y_values=[e for number in xrange(len(sys.argv)-1)]
	  		yerr_values=[e for number in xrange(len(sys.argv)-1)]

			parsed_data=[]
			fig=plt.figure()
			ax=plt.subplot(111)
			print "Reading file: "+sys.argv[4];
			parsed_data.append(parse(sys.argv[4]))
			print "Parse done"
			nodes=[keys for keys in parsed_data[0].keys()]
	
			[x,y_values[0],yerr_values[0],title]=plot_image(parsed_data,0, sys.argv[2] )	
			plt.errorbar(x, y_values[0][0], yerr=yerr_values[0][0],fmt=colors_dic[0],label=legend_dic[0],markersize=10)

			[x,y_values[1],yerr_values[1],title]=plot_image(parsed_data,0, sys.argv[3] ) # number of hops
	
			if maxYvalue<float(max(y_values[1][0])):
				maxYvalue=float(max(y_values[1][0]))
			if maxYvalue<float(max(y_values[0][0])):
				maxYvalue=float(max(y_values[0][0]))

			plt.errorbar(x, y_values[1][0], yerr=yerr_values[1][0],fmt=colors_dic[1],label=legend_dic[1],markersize=10)
		
			#plt.legend( loc=2, borderaxespad=0.)
			ax.legend(loc='center', bbox_to_anchor=(0.5, 1.02),ncol=1, fancybox=True, shadow=True)
			plt.xlabel('# nodes',fontsize=13)
			plt.ylabel('Drops to TXs ratio (%)',fontsize=15)
		    	plt.ylim(0, float(maxYvalue)*1.1)
			plt.xlim(0, max(nodes))
			
			plt.grid(True)
			plt.show()
		else:
			print_help()
	elif sys.argv[1] == 'plot-bars': 
		print "Starting to plot some bars..."
		y_values=[e for number in xrange(len(sys.argv)-2)]
   		yerr_values=[e for number in xrange(len(sys.argv)-2)]

		listOfYValues=[]
		listOfYErrValues=[]

		print "There are files: "+str(len(sys.argv)-2)
		if len(sys.argv) < 4:
			print_help()
		elif int(sys.argv[2]) == 0 or int(sys.argv[2]) > 25:
			print "Parameter "+str(sys.argv[2])+" not available"
			print_help()
		else:
			parsed_data=[]
		        plt.subplots()
			for i in range(len(sys.argv)-3):
				print "Reading file: "+sys.argv[i+3];
				print i
				parsed_data.append(parse(sys.argv[i+3]))
			nodes=[keys for keys in parsed_data[0].keys()]
			print "Parse done. There are nodes: "+str(max(nodes))	
			#print parsed_data[0][32]
			val=0

			for i in range(len(sys.argv)-3):	
				[x,y_values[i],yerr_values[i],title]=plot_image(parsed_data,i, sys.argv[2] )		
				print "adding ..."+str(y_values[i])
				val=np.mean(y_values[i][0])
				errval=np.mean(yerr_values[i][0])
				listOfYValues.append(val)
				listOfYErrValues.append(errval)				
	    			#plt.errorbar(x, y_values[i][0], yerr=yerr_values[i][0],fmt=colors_dic[i],label=legend_dic[i])

			
			print listOfYValues
			print listOfYErrValues
			print "There are files: "+str(len(sys.argv)-2)
			plt.bar(range(len(sys.argv)-3), listOfYValues, yerr=listOfYErrValues, alpha=0.5, color=['red', 'green', 'blue', 'cyan', 'magenta'],error_kw=dict(ecolor='gray', lw=2, capsize=5, capthick=2), align='center')
				
			plt.margins(0.02)

			plt.ylabel('# of drops (pkts)')
			plt.legend( loc=1, borderaxespad=0.)
			plt.xticks([0,1,2,3,4,5,6,7,8,9,10,11,12], ['none', 'Broad1', 'Broad2', 'Broad4','Broad6','Broad8','Broad10','Broad12','Broad14','Broad16','Broad18','Broad20','opt2'])
			plt.ylim(0, 0.1)
			plt.show()

			
	else:
	
		print_help()
	

    else:
       print_help()
	

