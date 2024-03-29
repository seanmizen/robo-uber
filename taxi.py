import math
# from typing_extensions import TypeVarTuple
import numpy as np
import heapq
import bisect
from numpy.random.mtrand import random

# a data container object for the taxi's internal list of fares. This
# tells the taxi what fares are available to what destinations at
# what price, and whether they have been bid upon or allocated. The
# origin is notably missing: that's because the Taxi will keep this
# in a dictionary indexed by fare origin, so we don't need to duplicate that
# here.


class FareInfo:

    def __init__(self, destination, price):

        self.destination = destination
        self.price = price
        # bid is a ternary value: -1 = no, 0 = undecided, 1 = yes indicating whether this
        # taxi has bid for this fare.
        self.bid = 0
        self.allocated = False


''' A Taxi is an agent that can move about the world it's in and collect fares. All taxis have a
    number that identifies them uniquely to the dispatcher. Taxis have a certain amount of 'idle'
    time they're willing to absorb, but beyond that, they go off duty since it seems to be a waste
    of time to stick around. Eventually, they might come back on duty, but it usually won't be for
    several hours. A Taxi also expects a map of the service area which forms part of its knowledge
    base. Taxis origin from some fixed location in the world. Note that they can't just 'appear' there:
    any real Node in the world may have traffic (or other taxis!) there, and if its origin node is
    unavailable, the taxi won't enter the world until it is. Taxis collect revenue for fares, and
    each minute of active time, whether driving, idle, or conducting a fare, likewise costs them £1.
'''


class Taxi:

    # message type constants
    FARE_ADVICE = 1
    FARE_ALLOC = 2
    FARE_PAY = 3
    FARE_CANCEL = 4
    # lastKnownTaxiCount is used to keep track of whether to recompute K-centres.
    _lastKnownTaxiCount = 0
    _kCentres = []
    KCENTRES = True

    '''constructor. The only required arguments are the world the taxi operates in and the taxi's number.
         optional arguments are:
         idle_loss - how much cost the taxi is prepared to absorb before going off duty. 256 gives about 4
         hours of life given nothing happening. Loss is cumulative, so if a taxi was idle for 120 minutes,
         conducted a fare over 20 minutes for a net gain to it of 40, then went idle for another 120 minutes,
         it would have lost 200, leaving it with only £56 to be able to absorb before going off-duty.
         max_wait - this is a heuristic the taxi can use to decide whether a fare is even worth bidding on.
         It is an estimate of how many minutes, on average, a fare is likely to wait to be collected.
         on_duty_time - this says at what time the taxi comes on duty (default is 0, at the origin of the
         simulation)
         off_duty_time - this gives the number of minutes the taxi will wait before returning to duty if
         it goes off (default is 0, never return)
         service_area - the world can optionally populate the taxi's map at creation time.
         start_point - this gives the location in the network where the taxi will origin. It should be an (x,y) tuple.
         default is None which means the world will randomly place the Taxi somewhere on the edge of the service area.
      '''

    def __init__(self, world, taxi_num, idle_loss=256, max_wait=50, on_duty_time=0, off_duty_time=0, service_area=None, start_point=None):

        self._world = world
        self.number = taxi_num
        self.onDuty = False
        self.historicPathLengths = []
        self.calls = 0
        self.steps = 0
        self._onDutyTime = on_duty_time
        self._offDutyTime = off_duty_time
        self._onDutyPos = start_point
        self._dailyLoss = idle_loss
        self._maxFareWait = max_wait
        self._account = 0
        self._loc = None
        self._direction = -1
        self._nextLoc = None
        self._nextDirection = -1
        self._timeAtBankruptcy = -1
        # this contains a Fare (object) that the taxi has picked up. You use the functions pickupFare()
        # and dropOffFare() in a given Node to collect and deliver a fare
        self._passenger = None
        # the map is a dictionary of nodes indexed by (x,y) pair. Each entry is a dictionary of (x,y) nodes that indexes a
        # direction and distance. such a structure allows rapid lookups of any node from any other.
        self._map = service_area
        if self._map is None:
            self._map = self._world.exportMap()
        # path is a list of nodes to be traversed on the way from one point to another. The list is
        # in order of traversal, and does NOT have to include every node passed through, if these
        # are incidental (i.e. involve no turns or stops or any other remarkable feature)
        self._path = []
        # for part 1C - keep a traffic history.
        # COMMENTED OUT FOR CODE STABILITY
        # self._trafficHistory = {}
        # for node in self._world._net:
        #    self._trafficHistory[node] = []
        # pick the first available entry point starting from the top left corner if we don't have a
        # preferred choice when coming on duty
        if self._onDutyPos is None:
            x = 0
            y = 0
            while (x, y) not in self._map and x < self._world.xSize:
                y += 1
                if y >= self._world.ySize:
                    y = 0
                    x += self._world.xSize - 1
            if x >= self._world.xSize:
                raise ValueError(
                    "This taxi's world has a map which is a closed loop: no way in!")
            self._onDutyPos = (x, y)
        # this dict maintains which fares the Dispatcher has broadcast as available. After a certain
        # period of time, fares should be removed  given that the dispatcher doesn't inform the taxis
        # explicitly that their bid has not been successful. The dictionary is indexed by
        # a tuple of (time, originx, originy) to be unique, and the expiry can be implemented using a heap queue
        # for priority management. You would do this by initialising a self._fareQ object as:
        # self._fareQ = heapq.heapify(self._fares.keys()) (once you have some fares to consider)

        # the dictionary items, meanwhile, contain a FareInfo object with the price, the destination, and whether
        # or not this taxi has been allocated the fare (and thus should proceed to collect them ASAP from the origin)
        self._availableFares = {}
        # Utility rankings for fare bidding
        self._fareUtilityRankings = []
        self._fareDensityRankings = []
        # streetmap for easy node / streedID lookups
        # streetFareCount is where we will store a count of each fare.
        self._streetMap, self._streetAdjacencies = self._generateStreetMap()
        self._streetFareCount = {}
        streetIDs = set(value for value in self._streetMap.values())
        for streetID in streetIDs:
            self._streetFareCount[streetID] = 0
        self._kCentrePath = []

    # This property allows the dispatcher to query the taxi's location directly. It's like having a GPS transponder
    # in each taxi.

    @property
    def currentLocation(self):
        if self._loc is None:
            return (-1, -1)
        return self._loc.index

    # ___________________________________________________________________________________________________________________________
    # methods to populate the taxi's knowledge base

    # get a map if none was provided at the outset
    def importMap(self, newMap):
        # a fresh map can just be inserted
        if self._map is None:
            self._map = newMap
        # but importing a new map where one exists implies adding to the
        # existing one. (Check that this puts in the right values!)
        else:
            for node in newMap.items():
                neighbours = [(neighbour[1][0], neighbour[0][0], neighbour[0][1])
                              for neighbour in node[1].items()]
                self.addMapNode(node[0], neighbours)

    # incrementally add to the map. This can be useful if, e.g. the world itself has a set of
    # nodes incrementally added. It can then call this function on the existing taxis to update
    # their maps.
    def addMapNode(self, coords, neighbours):
        if self._world is None:
            return AttributeError("This Taxi does not exist in any world")
        node = self._world.getNode(coords[0], coords[1])
        if node is None:
            return KeyError("No such node: {0} in this Taxi's service area".format(coords))
        # build up the neighbour dictionary incrementally so we can check for invalid nodes.
        neighbourDict = {}
        for neighbour in neighbours:
            neighbourCoords = (neighbour[1], neighbour[2])
            neighbourNode = self._world.getNode(neighbour[1], neighbour[2])
            if neighbourNode is None:
                return KeyError("Node {0} expects neighbour {1} which is not in this Taxi's service area".format(coords, neighbour))
            neighbourDict[neighbourCoords] = (
                neighbour[0], self._world.distance2Node(node, neighbourNode))
        self._map[coords] = neighbourDict

    # ---------------------------------------------------------------------------------------------------------------------------
    # automated methods to handle the taxi's interaction with the world. You should not need to change these.

    # comeOnDuty is called whenever the taxi is off duty to bring it into service if desired. Since the relevant
    # behaviour is completely controlled by the _account, _onDutyTime, _offDutyTime and _onDutyPos properties of
    # the Taxi, you should not need to modify this: all functionality can be achieved in clockTick by changing
    # the desired properties.
    def comeOnDuty(self, time=0):
        if self._world is None:
            return AttributeError("This Taxi does not exist in any world")
        if self._offDutyTime == 0 or (time >= self._onDutyTime and time < self._offDutyTime):
            if self._account <= 0:
                self._account = self._dailyLoss
            self.onDuty = True
            # print(
            #     "Taxi {0} is coming on-duty".format(self.number))
            onDutyPose = self._world.addTaxi(self, self._onDutyPos)
            self._nextLoc = onDutyPose[0]
            self._nextDirection = onDutyPose[1]

    # clockTick should handle all the non-driving behaviour, turn selection, stopping, etc. Drive automatically
    # stops once it reaches its next location so that if continuing on is desired, clockTick has to select
    # that action explicitly. This can be done using the turn and continueThrough methods of the node. Taxis
    # can collect fares using pickupFare, drop them off using dropoffFare, bid for fares issued by the Dispatcher
    # using transmitFareBid, and any other internal activity seen as potentially useful.
    def clockTick(self, world):
        # automatically go off duty if we have absorbed as much loss as we can in a day

        # Getting probabilistic - update the traffic history map.
        # for part 1C (commented out when not necessary)
        # Do not worry about maxTraffic / Gridlock here - the path planner can do gridlock checks.
        # for node in self._map:
        #    self._trafficHistory[node].append(world._net[node].traffic)

        # Tangential to part 3: build a k-centres list if necessary.
        if self.KCENTRES:
            taxisOut = sum(
                1 if taxi[0].onDuty else 0 for taxi in world._taxis.items())
            if taxisOut != self._lastKnownTaxiCount:
                self.updateKCentre(self._calculateKCentres(world, taxisOut))
                self.updateLastKnownTaxiCount(taxisOut)

        # sum(1 if meets_condition(x) else 0 for x in my_list)
        if self._account == 0:
            # Only update bankruptcy time when taxi hits 0
            # this allows a fare to save a taxi from bankruptcy
            # but only if the fare payout gets account > 0 again.
            # Register bankruptcy before the fare is dropped off
            self._timeAtBankruptcy = world.simTime

        if self._account <= 0 and self._passenger is None:
            # print(
            #     "Loss too high. Taxi {0} is going off-duty".format(self.number))
            self.onDuty = False
            self._offDutyTime = world.simTime
        # have we reached our last known destination? Decide what to do now.
        if len(self._path) == 0:
            # obviously, if we have a fare aboard, we expect to have reached their destination,
            # so drop them off.
            if self._passenger is not None:
                # update rankings - delete them all. this can be done on pickup, but doesn't hurt to do it on dropoff either.
                self._fareUtilityRankings = []
                self._fareDensityRankings = []
                if self._loc.dropoffFare(self._passenger, self._direction):
                    self._passenger = None
                # failure to drop off means probably we're not at the destination. But check
                # anyway, and replan if this is the case.
                elif self._passenger.destination != self._loc.index:
                    self._path = self._planPath(
                        self._loc.index, self._passenger.destination)
            else:
                if self.KCENTRES:
                    # no path, no passenger. Calculate your best k-centre.
                    bestKCentre = self._findBestKCentre(world)
                    if bestKCentre is not None:
                        self._kCentrePath = self._planPath(
                            self._loc.index, bestKCentre)
                        a = 1

            # decide what to do about available fares. This can be done whenever, but should be done
            # after we have dropped off fares so that they don't complicate decisions.
            faresToRemove = []
            for fare in self._availableFares.items():
                # remember that availableFares is a dict indexed by (time, originx, originy). A location,
                # meanwhile, is an (x, y) tuple. So fare[0][0] is the time the fare called, fare[0][1]
                # is the fare's originx, and fare[0][2] is the fare's originy, which we can use to
                # build the location tuple.
                origin = (fare[0][1], fare[0][2])
                destination = fare[1].destination

                # much more intelligent things could be done here. This simply naively takes the first
                # allocated fare we have and plans a basic path to get us from where we are to where
                # they are waiting.
                if fare[1].allocated and self._passenger is None:
                    # at the collection point for our next passenger?
                    if self._loc.index[0] == origin[0] and self._loc.index[1] == origin[1]:
                        self._passenger = self._loc.pickupFare(self._direction)
                        # if a fare was collected, we can origin to drive to their destination. If they
                        # were not collected, that probably means the fare abandoned.
                        if self._passenger is not None:
                            self._path = self._planPath(
                                self._loc.index, self._passenger.destination)
                        faresToRemove.append(fare[0])
                    # not at collection point, so determine how to get there
                    elif len(self._path) == 0:
                        self._path = self._planPath(self._loc.index, origin)
                # get rid of any unallocated fares that are too stale to be likely customers
                elif world.simTime-fare[0][0] > self._maxFareWait:
                    faresToRemove.append(fare[0])
                # may want to bid on available fares. This could be done at any point here, it
                # doesn't need to be a particularly early or late decision amongst the things to do.
                elif fare[1].bid == 0:
                    if self._bidOnFare(fare[0][0], origin, destination, fare[1].price):
                        world.transmitFareBid(origin, self)
                        fare[1].bid = 1
                    else:
                        fare[1].bid = -1

                    # register fares first, we will make a second pass through availableFares to make our bids.
                    # self._bidSystemRegisterFare(
                    #    fare[0][0], origin, destination, fare[1].price)
            for expired in faresToRemove:
                del self._availableFares[expired]
            if False:
                # second pass to now act on valid bids.
                for fare in self._availableFares.items():
                    origin = (fare[0][1], fare[0][2])
                    destination = fare[1].destination
                    if self._bidOnFare(fare[0][0], origin, destination, fare[1].price):
                        world.transmitFareBid(origin, self)
                        fare[1].bid = 1
                    else:
                        fare[1].bid = -1

                # may want to do something active whilst enroute - this simple default version does
                # nothing, but that is probably not particularly 'intelligent' behaviour.
        else:
            pass
        # the last thing to do is decrement the account - the fixed 'time penalty'. This is always done at
        # the end so that the last possible time tick isn't wasted e.g. if that was just enough time to
        # drop off a fare.
        self._account -= 1

    # Calculate the ideal "idle" spots for all k taxis.
    def _calculateKCentres(self, world, k):
        # uses a modified Gon algorithm to find ourselves k centres to gravitate the taxis to.
        # our variation: while calculating new centres, treat the map edges as an infinite wall of centres.
        # https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=8792058
        # pick a random first centre
        centres = [list(world._net.items())[
            np.random.randint(len(world._net))][0]]
        while len(centres) < k:
            nextNodeToPick = -1  # will eventually be the index of the best node
            biggestDistance = 0
            for node in world._net:
                if node not in centres:
                    smallestDistance = math.inf
                    for centroid in centres:
                        # find the smallest distance from C[n...] to this node.
                        # do this for every node, pick the maximal smallest distance
                        distance = self._euclideanDistance(node, centroid)
                        if distance < smallestDistance:
                            smallestDistance = distance

                    # also calculate the smallest edge distance
                    topDistance = self._euclideanDistance((node[0], 0), node)
                    bottomDistance = self._euclideanDistance(
                        (node[0], 50), node)
                    leftDistance = self._euclideanDistance((0, node[1]), node)
                    rightDistance = self._euclideanDistance(
                        (50, node[1]), node)
                    edgeDistance = min(
                        [topDistance, bottomDistance, leftDistance, rightDistance])
                    if edgeDistance < smallestDistance:
                        smallestDistance = edgeDistance

                    if smallestDistance > biggestDistance:
                        biggestDistance = smallestDistance
                        nextNodeToPick = node

            centres.append(nextNodeToPick)

        return centres

    def _findBestKCentre(self, world):
        bestKCentre = None

        def taxiKCentreList(taxi):
            taxiDistanceTuples = []
            for centre in self._kCentres:
                taxiDistanceTuples.append(
                    (self._euclideanDistance(taxi.currentLocation, centre), taxi.number, centre))
            return taxiDistanceTuples
        distanceTuples = []
        for taxi in world._taxis:
            distanceTuples.extend(taxiKCentreList(taxi))

        distanceTuples.sort()

        # greedyMatch k-Centres to taxis.
        assignedTaxis = []
        assignedKCentres = []
        assignments = {}
        for taxiKCentreMatching in distanceTuples:
            _, taxi, kCentre = taxiKCentreMatching
            if taxi not in assignedTaxis and kCentre not in assignedKCentres:
                assignments[taxi] = kCentre
                assignedTaxis.append(taxi)
                assignedKCentres.append(kCentre)
            if len(assignedKCentres) == len(self._kCentres):
                break
        if self.number in assignments:
            bestKCentre = assignments[self.number]
        else:
            bestKCentre = None

        return bestKCentre

    @classmethod
    def updateKCentre(cls, kCentres):
        cls._kCentres += kCentres

    @classmethod
    def updateLastKnownTaxiCount(cls, kCentres):
        cls._lastKnownTaxiCount += kCentres

    # called automatically by the taxi's world to update its position. If the taxi has indicated a
    # turn or that it is going straight through (i.e., it's not stopping here), drive will
    # move the taxi on to the next Node once it gets the green light.

    def drive(self, newPose):
        # as long as we are not stopping here,

        if self._nextLoc is not None:
            # and we have the green light to proceed,
            if newPose[0] == self._nextLoc and newPose[1] == self._nextDirection:
                nextPose = (None, -1)
                # vacate our old position and occupy our new node.
                if self._loc is None:
                    nextPose = newPose[0].occupy(newPose[1], self)
                else:
                    nextPose = self._loc.vacate(self._direction, newPose[1])
                if nextPose[0] == newPose[0] and nextPose[1] == newPose[1]:
                    self._loc = self._nextLoc
                    self._direction = self._nextDirection
                    self._nextLoc = None
                    self._nextDirection = -1
                    # not yet at the destination?

                    if len(self._kCentrePath) > 0:
                        if self._kCentrePath[0][0] == self._loc.index[0] and self._kCentrePath[0][1] == self._loc.index[1]:
                            self._kCentrePath.pop(0)

                    if len(self._path) > 0:
                        #  if we have reached the next path waypoint, pop it.
                        if self._path[0][0] == self._loc.index[0] and self._path[0][1] == self._loc.index[1]:
                            self._path.pop(0)
                        # otherwise continue straight ahead (as long as this is feasible)
                        else:
                            nextNode = self._loc.continueThrough(
                                self._direction)
                            self._nextLoc = nextNode[0]
                            self._nextDirection = nextNode[1]
                            return
        elif self._nextLoc is None and len(self._path) == 0 and len(self._kCentrePath) > 0:
            # No fare to service. Idly travel towards the closest k-centre.
            if self._kCentrePath[0] == self._loc.index:
                self._kCentrePath.pop(0)
            if len(self._kCentrePath) > 0:
                if self._kCentrePath[0] in self._map[self._loc.index]:
                    nextNode = self._loc.turn(
                        self._direction, self._map[self._loc.index][self._kCentrePath[0]][0])
                    self._nextLoc = nextNode[0]
                    self._nextDirection = nextNode[1]
                    if self._nextLoc is not None:
                        self.drive((self._nextLoc, self._nextDirection))

        # Either get underway or move from an intermediate waypoint. Both of these could be
        # a change of direction
        if self._nextLoc is None and len(self._path) > 0:
            #  if we are resuming from a previous path point, just pop the path
            if self._path[0][0] == self._loc.index[0] and self._path[0][1] == self._loc.index[1]:
                self._path.pop(0)
            elif len(self._kCentrePath) > 0:
                if self._kCentrePath[0][0] == self._loc.index[0] and self._kCentrePath[0][1] == self._loc.index[1]:
                    self._kCentrePath.pop(0)

            # we had better be in a known position!
            if self._loc.index not in self._map:
                raise IndexError("Fell of the edge of the world! Index ({0},{1}) is not in this taxi's map".format(
                    self._loc.index[0], self._loc.index[1]))
            # and we need to be going to a reachable location
            if self._path[0] not in self._map[self._loc.index]:
                raise IndexError("Can't get there from here! Map doesn't have a path to ({0},{1}) from ({2},{3})".format(
                                 self._path[0][0], self._path[0][1], self._loc.index[0], self._loc.index[1]))
            # look up the next place to go from the map
            nextNode = self._loc.turn(
                self._direction, self._map[self._loc.index][self._path[0]][0])
            # update our next locations appropriately. If we're at the destination, or
            # can't move as expected, the next location will be None, meaning we will stop
            # here and will have to plan our path again.
            self._nextLoc = nextNode[0]
            self._nextDirection = nextNode[1]

    # recvMsg handles various dispatcher messages.
    def recvMsg(self, msg, **args):
        timeOfMsg = self._world.simTime
        # A new fare has requested service: add it to the list of availables
        if msg == self.FARE_ADVICE:
            callTime = self._world.simTime
            self._availableFares[callTime, args['origin'][0], args['origin'][1]] = FareInfo(
                args['destination'], args['price'])
            # Add to the fare density map. This will not need to be removed.
            self._streetFareCount[self._streetMap[args['origin']]] += 1
            return True
        # the dispatcher has approved our bid: mark the fare as ours
        elif msg == self.FARE_ALLOC:
            for fare in self._availableFares.items():
                if fare[0][1] == args['origin'][0] and fare[0][2] == args['origin'][1]:
                    if fare[1].destination[0] == args['destination'][0] and fare[1].destination[1] == args['destination'][1]:
                        fare[1].allocated = True
                        return True
        # we just dropped off a fare and received payment, add it to the account
        elif msg == self.FARE_PAY:
            self._account += args['amount']
            return True
        # a fare cancelled before being collected, remove it from the list
        elif msg == self.FARE_CANCEL:
            for fare in self._availableFares.items():
                # and fare[1].allocated:
                if fare[0][1] == args['origin'][0] and fare[0][2] == args['origin'][1]:
                    del self._availableFares[fare[0]]
                    return True
        # if we didn't get the result we wanted, return false.
        # hopefully this solves our issue.
        return False
    # _____________________________________________________________________________________________________________________

    ''' HERE IS THE PART THAT YOU NEED TO MODIFY
      '''

    # _planPath is now the selector method which chooses the pathfinder algorithm.
    def _planPath(self, origin, destination, **args):
        returnVal = []

        if False:
            returnVal = self._planPath_original(origin, destination, **args)
        if False:
            returnVal = self._depthFirstSearch(
                200, origin, destination, **args)
        if False:
            returnVal = self._iterativeDeepeningSearch(
                origin, destination, 1, True, ** args)
        if False:
            returnVal = self._aStarSearch(
                origin, destination, self._euclideanDistance, **args)
        if True:
            returnVal = self._aStarSearch(
                origin, destination, self._trafficInclusiveEuclidean, **args)
        if False:
            returnVal = self._aStarSearch(
                origin, destination, self._trafficPredictingEuclidean, **args)

        return returnVal

    def _iterativeDeepeningSearch(self, origin, destination, step=1, corridor=False, **args):
        # probabilistic depth-first search discounting traffic, etc
        self.calls += 1
        maxPly = 150
        ply = 1
        path = []
        while ply <= maxPly and destination not in path:
            path = [origin]
            args['explored'] = {}
            args['explored'][origin] = None
            if corridor:
                path = self._depthFirstSearchCorridor(
                    ply, origin, destination, **args)
            else:
                path = self._depthFirstSearch(ply, origin, destination, **args)
            ply += step

        self.historicPathLengths.append(ply)
        return path

    def _depthFirstSearch(self, ply, origin, destination, **args):
        self.calls += 1
        if 'explored' not in args:
            args['explored'] = {}
        args['explored'][origin] = None

        path = [origin]
        if destination in path:
            # bug fix for frontier nodes
            # exit early if this is the destination
            return path

        if origin in self._map and ply > 0:
            # the frontier of unexplored paths (from this Node)
            frontier = [node for node in self._map[origin].keys()
                        if node not in args['explored']]
            # recurse down to the next node. This will automatically create a depth-first
            # approach because the recursion won't bottom out until no more frontier nodes
            # can be generated

            for nextNode in frontier:
                self.steps += 1
                path = path + \
                    self._depthFirstSearch(ply - 1, nextNode, destination,
                                           explored=args['explored'])
                # stop early as soon as the destination has been found by any route.
                if destination in path:
                    # print("Found - path length {0}".format(len(path)))
                    return path
        # didn't reach the destination from any reachable node
        # no need, therefore, to expand the path for the higher-level call, this is a dead end.
        return []

    def _depthFirstSearchCorridor(self, ply, origin, destination, **args):
        self.calls += 1
        if 'explored' not in args:
            args['explored'] = {}
        args['explored'][origin] = None

        path = [origin]
        if destination in path:
            # bug fix for frontier nodes
            # exit early if this is the destination
            return path

        if origin in self._map and ply > 0:
            frontier = [node for node in self._map[origin].keys()
                        if node not in args['explored']]
            # loop down a corridor (being careful to check for the goal!)
            while len(frontier) == 1:
                path = path + frontier
                args['explored'][frontier[-1]] = None
                if destination in path:
                    return path
                frontier = [node for node in self._map[frontier[-1]].keys()
                            if node not in args['explored']]

            for nextNode in frontier:
                self.steps += 1
                path = path + \
                    self._depthFirstSearchCorridor(ply - 1, nextNode, destination,
                                                   explored=args['explored'])
                # stop early as soon as the destination has been found by any route.
                if destination in path:
                    return path
        return []

    def _euclideanDistance(self, a, b):
        return math.sqrt(
            (a[0]-b[0])**2+(a[1]-b[1])**2)

    # Calculate euclidean distance + the current node's traffic estimate.
    # the traffic encountered should be equal to the time delay incurred - so this can be added as "distance"
    # If traffic increases while the taxi is en-route, it is possible the taxi will re-calculate
    # especially if gridlock occurs while en-route.
    def _trafficInclusiveEuclidean(self, a, b):
        expectedTraffic = self._world._net[a].traffic
        if expectedTraffic == self._world._net[a].maxTraffic:
            expectedTraffic = math.inf
        return expectedTraffic + self._euclideanDistance(a, b)

    # The same as TIE, but calculate the probable traffic given a history of all traffic.
    # configurable: either all traffic data points, or the last N traffic points
    def _trafficPredictingEuclidean(self, a, b):
        maxHistory = 20
        allTrafficPoints = self._trafficHistory[a]
        if len(allTrafficPoints) != 0:
            if maxHistory > len(allTrafficPoints):
                maxHistory = len(allTrafficPoints)
            allTrafficPoints = allTrafficPoints[-(
                len(allTrafficPoints) - maxHistory):]
            meanTraffic = sum(allTrafficPoints) / len(allTrafficPoints)
            expectedTraffic = meanTraffic
            # If expectedTraffic approaches maxTraffic (within 1), assume gridlock
            if expectedTraffic >= self._world._net[a].maxTraffic - 1:
                expectedTraffic = math.inf
        else:
            expectedTraffic = 0
        return expectedTraffic + self._euclideanDistance(a, b)

    def _aStarSearch(self, origin, destination, heuristic, **args):
        self.calls += 1
        if 'explored' not in args:
            args['explored'] = {}

        if origin == destination:
            # exit early if this is the destination
            return [origin]

        # Addition for probabilistic dispatcher
        # return the distance (or rather, time) to target
        if 'travelTime' in args:
            args['travelTime'].append(-1)

        # adapted from gridagents_solution.py
        expanded = {heuristic(origin, destination): {origin: [origin]}}
        while len(expanded) > 0:
            self.steps += 1
            # index by heuristic distance
            # search from the next shortest expansion
            bestTravelTime = min(expanded.keys())
            nextExpansion = expanded[bestTravelTime]
            if destination in nextExpansion:
                if 'travelTime' in args:
                    args['travelTime'][0] = bestTravelTime
                return nextExpansion[destination]
            nextNode = nextExpansion.popitem()
            while len(nextExpansion) > 0 and nextNode[0] in args['explored']:
                # Ignore explored nodes, pop next item
                nextNode = nextExpansion.popitem()
            if len(nextExpansion) == 0:
                del expanded[bestTravelTime]
            if nextNode[0] not in args['explored']:
                args['explored'][nextNode[0]] = None
                expansionTargets = [
                    node for node in self._map[nextNode[0]].items() if node[0] not in args['explored']]
                while len(expansionTargets) > 0:
                    self.steps += 1
                    expTgt = expansionTargets.pop()
                    estimatedDistance = bestTravelTime - \
                        heuristic(nextNode[0], destination) + \
                        expTgt[1][1] + heuristic(expTgt[0], destination)
                    if estimatedDistance in expanded:
                        expanded[estimatedDistance][expTgt[0]
                                                    ] = nextNode[1]+[expTgt[0]]
                    else:
                        expanded[estimatedDistance] = {
                            expTgt[0]: nextNode[1]+[expTgt[0]]}
        return []

    def _planPath_original(self, origin, destination, **args):
        self.calls += 1
        # the list of explored paths. Recursive invocations pass in explored as a parameter
        if 'explored' not in args:
            args['explored'] = {}
        # add this origin to the explored list
        # explored is a dict purely so we can hash its index for fast lookup, so its value doesn't matter
        args['explored'][origin] = None
        # the actual path we are going to generate
        path = [origin]
        if destination in path:
            # bug fix for frontier nodes
            # exit early if this is the destination
            return path

        # take the next node in the frontier, and expand it depth-wise
        if origin in self._map:
            # the frontier of unexplored paths (from this Node
            frontier = [node for node in self._map[origin].keys()
                        if node not in args['explored']]
            # recurse down to the next node. This will automatically create a depth-first
            # approach because the recursion won't bottom out until no more frontier nodes
            # can be generated
            for nextNode in frontier:
                self.steps += 1
                path = path + \
                    self._planPath_original(nextNode, destination,
                                            explored=args['explored'])
                # stop early as soon as the destination has been found by any route.
                if destination in path:
                    return path
        # didn't reach the destination from any reachable node
        # no need, therefore, to expand the path for the higher-level call, this is a dead end.
        return []

    # _____________________________________________________________________________________________________________________

    def _fareUtility1(self, time, origin, destination, price):
        # DUPLICATE OF DISPATCHER FAREUTILITY1 - minor adjustments
        # return farePayout / (how long will it take to get the payout)
        # make use of the taxi's routefinder. It is a private method, but it's very useful.
        # fareJourneyTime = the actual fare's itineary time
        # travelToFareTime = how long it will take to reach the fare
        fareJourneyTime = -1
        travelToFareTime = -1
        args = {'travelTime': []}
        fareJourneyPath = self._planPath(
            origin, destination, **args)
        fareJourneyTime = args['travelTime'][0]
        fareTravelPath = self._planPath(
            self.currentLocation, origin, **args)
        travelToFareTime = args['travelTime'][0]
        returnVal = 0
        if fareJourneyTime > -1 and travelToFareTime > -1:
            returnVal = price / \
                (fareJourneyTime + travelToFareTime)
        return returnVal

    def _generateStreetMap(self):
        # generateStreepMap is called once at the beginning of the simulation.
        # We will use the resulting dictionary of streets to help categorise fare density zones.
        def getNode(myTup):
            # getNode: convert (dir, x, y) tuple into ((x, y), nodeObject) tuple
            return ((myTup[1], myTup[2]), self._world._net[(myTup[1], myTup[2])])
        # create dict of (location): streetID mappings - this will be how we group our fare densities.
        nodeAdjacencies = {}
        origin = getNode((0, 0, 0))
        nextNode = getNode(origin[1].neighbours[0])
        explored = [origin[0]]
        streetID = 0
        nodeStreetMap = {}
        nodeStreetMap[origin[0]] = streetID
        streetsToStart = []
        while len(nodeStreetMap.keys()) < self._world.size:

            nodeStreetMap[nextNode[0]] = streetID
            explored.append(nextNode[0])
            if len(nextNode[1].neighbours) == 2:
                # corridor node - continue down the street
                neighbourSelected = False
                for neighbour in nextNode[1].neighbours:
                    if (neighbour[1], neighbour[2]) not in explored:
                        nextNode = getNode(neighbour)
                        neighbourSelected = True
                        break
                if not neighbourSelected:
                    nextNode = getNode(streetsToStart.pop())
                    streetID += 1
            elif len(nextNode[1].neighbours) == 1:
                # nothing to do - the node is already assigned a street.
                # get our nextNode out of the streetsToStart list.
                nextNode = getNode(streetsToStart.pop())
                streetID += 1
                pass
            else:
                if nextNode[0] not in nodeAdjacencies:
                    nodeAdjacencies[nextNode[0]] = {}
                # if here, implied neighbours > 2
                streetID += 1
                for neighbour in nextNode[1].neighbours:
                    nodeAdjacencies[nextNode[0]][(
                        neighbour[1], neighbour[2])] = None
                    if (neighbour[1], neighbour[2]) not in explored:
                        streetsToStart.append(neighbour)
                if len(streetsToStart) > 0:
                    nextNode = getNode(streetsToStart.pop())
                else:
                    break

        streetAdjacencies = {}
        streetIDs = set(value for value in nodeStreetMap.values())
        for streetID in streetIDs:
            streetAdjacencies[streetID] = []

        for nodeAdjacency in nodeAdjacencies.items():
            origin = nodeAdjacency[0]
            originStreet = nodeStreetMap[origin]
            for destination in nodeAdjacency[1].keys():
                destStreet = nodeStreetMap[destination]
                if originStreet != destStreet:
                    streetAdjacencies[originStreet].append(destStreet)
                    streetAdjacencies[destStreet].append(originStreet)

        return (nodeStreetMap, streetAdjacencies)

    def _fareDensity(self, destination):
        # streetMap contains our street IDs indexed by node
        # streetFareCount is our count of total fares - TODO make this smarter!
        # TODO turn this into a Naive Bayes model!
        fareDensity = self._streetFareCount[self._streetMap[destination]]
        for neighbourStreet in self._streetAdjacencies[self._streetMap[destination]]:
            fareDensity += self._streetFareCount[neighbourStreet]/2

        return self._streetFareCount[self._streetMap[destination]]

    def _bidSystemRegisterFare(self, time, origin, destination, price):
        fareUtility = self._fareUtility1(
            time, origin, destination, price)
        fareDensity = self._fareDensity(destination)
        bisect.insort(self._fareUtilityRankings,
                      (fareUtility, (origin, destination)))
        bisect.insort(self._fareDensityRankings,
                      (fareDensity, (origin, destination)))

    def _bidSystem1(self, time, origin, destination, price):
        try:
            utilityRank = [i for i, fareDetail in enumerate(
                self._fareUtilityRankings) if fareDetail[1] == (origin, destination)][0]
            densityRank = [i for i, fareDetail in enumerate(
                self._fareDensityRankings) if fareDetail[1] == (origin, destination)][0]
        except:
            # fare doesn't exist anymore
            return False

        # If utilityRank is higher than densityRank, we know this fare will be prioritised
        # by the dispatcher even though we don't want it to be prioritised. Block its bid.
        if utilityRank > densityRank:
            return False
        else:
            return True

    def _bidSystem2(self, time, origin, destination, price):
        return False

    # TODO
    # this function decides whether to offer a bid for a fare. In general you can consider your current position, time,
    # financial state, the collection and dropoff points, the time the fare called - or indeed any other variable that
    # may seem relevant to decide whether to bid. The (crude) constraint-satisfaction method below is only intended as
    # a hint that maybe some form of CSP solver with automated reasoning might be a good way of implementing this. But
    # other methodologies could work well. For best results you will almost certainly need to use probabilistic reasoning.

    def _bidOnFare_new(self, time, origin, destination, price):

        # bidSystem1: "Is this fare's FU ranking equal or worse than it's FD ranking? If so, accept it."
        bidSystemAccepted = self._bidSystem1(time, origin, destination, price)

        NoCurrentPassengers = self._passenger is None
        NoAllocatedFares = len(
            [fare for fare in self._availableFares.values() if fare.allocated]) == 0
        TimeToOrigin = self._world.travelTime(
            self._loc, self._world.getNode(origin[0], origin[1]))
        TimeToDestination = self._world.travelTime(self._world.getNode(origin[0], origin[1]),
                                                   self._world.getNode(destination[1], destination[1]))
        FiniteTimeToOrigin = TimeToOrigin > 0
        FiniteTimeToDestination = TimeToDestination > 0
        CanAffordToDrive = self._account > TimeToOrigin
        FairPriceToDestination = price > TimeToDestination
        PriceBetterThanCost = FairPriceToDestination and FiniteTimeToDestination
        FareExpiryInFuture = self._maxFareWait > self._world.simTime-time
        EnoughTimeToReachFare = self._maxFareWait - \
            self._world.simTime+time > TimeToOrigin
        SufficientDrivingTime = FiniteTimeToOrigin and EnoughTimeToReachFare
        WillArriveOnTime = FareExpiryInFuture and SufficientDrivingTime
        NotCurrentlyBooked = NoCurrentPassengers and NoAllocatedFares
        CloseEnough = CanAffordToDrive and WillArriveOnTime
        Worthwhile = PriceBetterThanCost and NotCurrentlyBooked
        Bid = CloseEnough and Worthwhile
        Bid = Bid and bidSystemAccepted
        return Bid

    def _bidOnFare(self, time, origin, destination, price):
        NoCurrentPassengers = self._passenger is None
        NoAllocatedFares = len(
            [fare for fare in self._availableFares.values() if fare.allocated]) == 0
        TimeToOrigin = self._world.travelTime(
            self._loc, self._world.getNode(origin[0], origin[1]))
        TimeToDestination = self._world.travelTime(self._world.getNode(origin[0], origin[1]),
                                                   self._world.getNode(destination[1], destination[1]))
        FiniteTimeToOrigin = TimeToOrigin > 0
        FiniteTimeToDestination = TimeToDestination > 0
        CanAffordToDrive = self._account > TimeToOrigin
        FairPriceToDestination = price > TimeToDestination
        PriceBetterThanCost = FairPriceToDestination and FiniteTimeToDestination
        FareExpiryInFuture = self._maxFareWait > self._world.simTime-time
        EnoughTimeToReachFare = self._maxFareWait - \
            self._world.simTime+time > TimeToOrigin
        SufficientDrivingTime = FiniteTimeToOrigin and EnoughTimeToReachFare
        WillArriveOnTime = FareExpiryInFuture and SufficientDrivingTime
        NotCurrentlyBooked = NoCurrentPassengers and NoAllocatedFares
        CloseEnough = CanAffordToDrive and WillArriveOnTime
        Worthwhile = PriceBetterThanCost and NotCurrentlyBooked
        Bid = CloseEnough and Worthwhile
        return Bid
