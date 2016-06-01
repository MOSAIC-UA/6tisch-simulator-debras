Changes performed in the 6Tisch simulator
====================

By:

added changes by Esteban Municio <esteban.municio@uantwerpen.be>

Scope
-----

See README_initVersion.md 
Some functionalities have been added:

- Multi-channel full duplex communication

- Possibility to use an ideal phy

- Fix some assumptions for interference

- Fix some bugs when adding/removing cells

- Otf enable/disable. When disabled, an ideal scheduler calculate the number of cells per node. For this perform:
	- Calculation of children nodes 
	- Calculation of theoretical demand

- Schedulers:
	- none(otf-sf0): Randomly selects the demanding cells
	- cen: Theoretically avoid collisions by having complete real information in all nodes
	- opt2: Theoretically avoid collisions by having complete real information in all nodes. Optimizes and allow overlapping when no collisions will occur
	- BeBraS: Send EB Broadcast messages in order to locally spread scheduling information. Used cells in the neighborhood are avoided.

- Switch between star and mesh topology

- New Parser file


Running
-------
* Run a simulation: `python runSimAllCPUs.py $nodes $scheduler $numBr $numOverlap $rpl $otf $sixtop`

$nodes = number of nodes
$scheduler = cen | opt2 | none | deBras
$numBr = number of broadcast cells per channel
$numOverlap = 0
$rpl = RPL DIO period
$otf = OTF HouseKeeping Period
$sixtop = 6Top HouseKeeping Period


Code Organization
-----------------

* `bin/`: the script for you to run
* `SimEngine/`: the simulator
    * `Mote.py`: Models a 6TiSCH mote running the different standards listed above.
    * `Propagation.py`: Wireless propagation model.
    * `SimEngine.py`: Event-driven simulation engine at the core of this simulator.
    * `SimSettings.py`: Data store for all simulation settings.
    * `SimStats.py`: Periodically collects statistics and writes those to a file.
    * `Topology.py`: creates a topology of the motes in the network.
* `SimGui/`: the graphical user interface to the simulator
