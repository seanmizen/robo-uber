import worldselector
import pygame
import threading
import time
import math
import numpy
# the 3 Python modules containing the RoboUber objects
import networld
import taxi
import dispatcher
import time
import datetime
import json
import copy
import matplotlib.pyplot as plt
import numpy as np
import curses
import os
# drawing on pygame
# import matplotlib.backends.backend_agg as agg

tloc = threading.local()


# import matplotlib
# Note: plt.savefig('foo.png', bbox_inches='tight')
# https://stackoverflow.com/questions/9622163/save-plot-to-image-file-instead-of-displaying-it-using-matplotlib

# create objects for RoboUber

# TODO
# experiment with parameter settings. worldX and worldY should not need to be
# changed, but others are fair game!
# basic parameters
worldX = 50
worldY = 50
runTime = 1440 * 2
# displayedTextArea will use displaySize[1] for height - only specify a width here
displayedTextAreaWidth = 400
boldFontSize = 16
normalFontSize = 15
displaySize = (1024, 768)
# trafficOn = True
# if displayUI set to true, view the map and use ticks.
# if displayUI set to false, set ticks = 0 and run x number of threads
displayUI = True
# only used if displayUI == False:
threadsToUse = 10

world = worldselector.export()

#    'junctions': junctions,
#    'junctionIdxs
#    'streets': streets,
#    'fareProbMagnet': fareProbMagnet,
#    'fareProbPopular': fareProbPopular,
#    'fareProbSemiPopular': fareProbSemiPopular,
#    'fareProbNormal': fareProbNormal,

outputValuesTemplate = {'time': [], 'fares': {}, 'taxis': {},
                        'completedFares': 0, 'cancelledFares': 0, 'dispatcherRevenue': 0, 'taxiPaths': [], 'historicPathLengths': []}
outputValues = copy.deepcopy(outputValuesTemplate)
outputValuesArray = [outputValues]

# RoboUber itself will be run as a separate thread for performance, so that screen
# redraws aren't interfering with model updates.


def runRoboUber(worldX, worldY, runTime, stop, junctions=None, streets=None, interpolate=False, outputValues=None, **args):

    if 'fareProbNormal' not in args:
        args['fareProbNormal'] = lambda x: numpy.random.random() > 0.999
    # create the NetWorld - the service area
    svcArea = networld.NetWorld(x=worldX, y=worldY, runtime=runTime,
                                fareprob=args['fareProbNormal'], jctNodes=junctions, edges=streets, interpolateNodes=interpolate)
    svcMap = svcArea.exportMap()
    if 'serviceMap' in args:
        args['serviceMap'] = svcMap

    # create some taxis
    taxi0 = taxi.Taxi(world=svcArea, taxi_num=100,
                      service_area=svcMap, start_point=(20, 0))
    taxi1 = taxi.Taxi(world=svcArea, taxi_num=101,
                      service_area=svcMap, start_point=(49, 15))
    taxi2 = taxi.Taxi(world=svcArea, taxi_num=102,
                      service_area=svcMap, start_point=(15, 49))
    taxi3 = taxi.Taxi(world=svcArea, taxi_num=103,
                      service_area=svcMap, start_point=(0, 35))

    taxis = [taxi0, taxi1, taxi2, taxi3]

    # and a dispatcher
    dispatcher0 = dispatcher.Dispatcher(parent=svcArea, taxis=taxis)

    # who should be on duty
    svcArea.addDispatcher(dispatcher0)

    # bring the taxis on duty
    for onDutyTaxi in taxis:
        onDutyTaxi.comeOnDuty()

    threadRunTime = runTime
    threadTime = 0
    while threadTime < threadRunTime:
        # cheeky debug info area:
        # live fare dictionary: svcArea._dispatcher._fareBoard
        # all fares ever: outputValues['fares']
        # print("fares: " + str(len(outputValues['fares'])))

        # if threadTime == 50:
        #    print(json.dumps(dict((str(k), v)
        #                          for k, v in outputValues['fares'].items()), indent=2))

        # exit if 'q' has been pressed
        if 'ticks' in args:
            tickSetting = args['ticks']
        else:
            tickSetting = 1

        if stop.is_set():
            threadRunTime = 0
        else:
            svcArea.runWorld(
                ticks=tickSetting, outputs=outputValuesArray[args['threadIdentifier']])
            # if (outputValues['time'][-1] % 5 == 0):
            #    print("Time: {0}, Fares: {1}, Taxis: {2}".format(
            #        outputValues['time'][-1], len(outputValues['fares']), len(outputValues['taxis'])))
            if threadTime != svcArea.simTime:
                threadTime += 1
            time.sleep(0.01)  # !! was 1

    # print(str(round(svcArea._dispatcherRevenue * 10, 2)))

    # 2021-11-19: Batch statistics
    # -last tick with taxis
    # -total revenue
    # -mean revenue per taxi
    # -taxi revenue standard deviation
    # -Coefficient of variation


def dateStamp():
    return str(datetime.datetime.now()).split('.')[0]


# curTime is the time point currently displayed
curTime = 0

# event to manage a user exit, invoked by pressing 'q' on the keyboard
userExit = threading.Event()

roboUber = threading.Thread(target=runRoboUber,
                            name='RoboUberThread',
                            kwargs={'worldX': worldX,
                                    'worldY': worldY,
                                    'runTime': runTime,
                                    'stop': userExit,
                                    'junctions': world['junctions'],
                                    'streets': world['streets'],
                                    'interpolate': True,
                                    'outputValues': outputValues,
                                    'fareProbMagnet': world['fareProbMagnet'],
                                    'fareProbPopular': world['fareProbPopular'],
                                    'fareProbSemiPopular': world['fareProbSemiPopular'],
                                    'fareProbNormal': world['fareProbNormal'],
                                    'threadIdentifier': 0,
                                    'ticks': int(displayUI)})
# ticks: int(displayUI) -- if UI, use ticks. otherwise, don't wait.

roboUberThreads = [roboUber]
# index 0 reserved for default thread
for i in range(1, threadsToUse):
    outputValuesArray.append(copy.deepcopy(outputValuesTemplate))
    roboUberThreads.append(threading.Thread(target=runRoboUber,
                                            name='RoboUberThread',
                                            kwargs={'worldX': worldX,
                                                    'worldY': worldY,
                                                    'runTime': runTime,
                                                    'stop': userExit,
                                                    'junctions': world['junctions'],
                                                    'streets': world['streets'],
                                                    'interpolate': True,
                                                    'outputValues': outputValuesArray[i],
                                                    'fareProbMagnet': world['fareProbMagnet'],
                                                    'fareProbPopular': world['fareProbPopular'],
                                                    'fareProbSemiPopular': world['fareProbSemiPopular'],
                                                    'fareProbNormal': world['fareProbNormal'],
                                                    'threadIdentifier': i,
                                                    'ticks': 0}))


# start the simulation (which will automatically stop at the end of the run time)
if displayUI:
    roboUber.start()
    print(
        "{0} - Main thread started".format(dateStamp()))
    pygame.init()

    # New:
    # initialize font; must be called after 'pygame.init()' to avoid 'Font not Initialized' error
    boldFont = pygame.font.Font("./Fonts/SourceCodePro-Bold.ttf", boldFontSize)
    normalFont = pygame.font.Font(
        "./Fonts/SourceCodePro-SemiBold.ttf", boldFontSize)
    # boldFont.bold = True

    # |pygame.SCALED arrgh...new in pygame 2.0, but pip install installs 1.9.6 on Ubuntu 16.04 LTS
    displaySurface = pygame.display.set_mode(
        size=(displaySize[0] + displayedTextAreaWidth, displaySize[1]), flags=pygame.RESIZABLE)
    backgroundRect = None
    aspectRatio = worldX/worldY
    if aspectRatio > 4/3:
        activeSize = (displaySize[0]-100, (displaySize[0]-100)/aspectRatio)
    else:
        # activeSize = (aspectRatio*(displaySize[1]-100), displaySize[1]-100)
        activeSize = (aspectRatio*(displaySize[1]-100), displaySize[1]-100)
    # new: text area on the left of the screen

    displayedTextArea = pygame.Surface(
        (displayedTextAreaWidth, displaySize[1] - 100))
    displayedTextArea.fill(pygame.Color(33, 33, 33))
    displayedBackground = pygame.Surface(activeSize)
    displayedBackground.fill(pygame.Color(210, 210, 210))
    # activeRect = pygame.Rect(X position, not size. hmm., round(
    textRect = pygame.Rect(round((displaySize[0]-activeSize[0]) / 2), round(
        (displaySize[1]-activeSize[1])/2), displayedTextAreaWidth, activeSize[1])
    activeRect = pygame.Rect(round((displaySize[0]-activeSize[0]) / 2) + displayedTextAreaWidth, round(
        (displaySize[1]-activeSize[1])/2), activeSize[0], activeSize[1])

    meshSize = ((activeSize[0]/worldX), round(activeSize[1]/worldY))

    # create a mesh of possible drawing positions
    positions = [[pygame.Rect(round(x*meshSize[0]),
                              round(y*meshSize[1]),
                              round(meshSize[0]),
                              round(meshSize[1]))
                  for y in range(worldY)]
                 for x in range(worldX)]
    drawPositions = [[displayedBackground.subsurface(
        positions[x][y]) for y in range(worldY)] for x in range(worldX)]

    # junctions exist only at labelled locations; it's convenient to create subsurfaces for them
    jctRect = pygame.Rect(round(meshSize[0]/4),
                          round(meshSize[1]/4),
                          round(meshSize[0]/2),
                          round(meshSize[1]/2))
    jctSquares = [drawPositions[jct[0]][jct[1]].subsurface(
        jctRect) for jct in world['junctionIdxs']]

    # initialise the network edge drawings (as grey lines)
    for street in world['streets']:
        pygame.draw.aaline(displayedBackground,
                           pygame.Color(128, 128, 128),
                           (round(street.nodeA[0]*meshSize[0]+meshSize[0]/2),
                            round(street.nodeA[1]*meshSize[1]+meshSize[1]/2)),
                           (round(street.nodeB[0]*meshSize[0]+meshSize[0]/2), round(street.nodeB[1]*meshSize[1]+meshSize[1]/2)))

    # initialise the junction drawings (as grey boxes)
    for jct in range(len(world['junctionIdxs'])):
        jctSquares[jct].fill(pygame.Color(192, 192, 192))
        # note that the rectangle target in draw.rect refers to a Rect relative to the source surface, not an
        # absolute-coordinates Rect.
        pygame.draw.rect(jctSquares[jct], pygame.Color(128, 128, 128), pygame.Rect(
            0, 0, round(meshSize[0]/2), round(meshSize[1]/2)), 5)

    # redraw the entire image
    displaySurface.blit(displayedBackground, activeRect)
    displaySurface.blit(displayedTextArea, textRect)
    pygame.display.flip()

    # which taxi is associated with which colour
    taxiColours = {}
    # possible colours for taxis: black, blue, green, red, magenta, cyan, yellow, white
    taxiPalette = [pygame.Color(0, 0, 0),
                   pygame.Color(255, 0, 0),
                   pygame.Color(0, 255, 0),
                   pygame.Color(0, 0, 255),
                   pygame.Color(255, 0, 255),
                   pygame.Color(0, 255, 255),
                   pygame.Color(255, 255, 0),
                   pygame.Color(255, 255, 255)]

    # relative positions of taxi and fare markers in a mesh point
    taxiRect = pygame.Rect(round(meshSize[0]/3),
                           round(meshSize[1]/3),
                           round(meshSize[0]/3),
                           round(meshSize[1]/3))

    fareRect = pygame.Rect(round(3*meshSize[0]/8),
                           round(3*meshSize[1]/8),
                           round(meshSize[0]/4),
                           round(meshSize[1]/4))

    # this is the display loop which updates the on-screen output.
    while curTime < runTime:
        # you can end the simulation by pressing 'q'. This triggers an event which is also passed into the world loop
        try:
            quitevent = next(evt for evt in pygame.event.get(
            ) if evt.type == pygame.KEYDOWN and evt.key == pygame.K_q)
            userExit.set()
            pygame.quit()
            # sys.exit()
        # event queue had no 'q' keyboard events. Continue.
        except StopIteration:
            pygame.event.get()
            values = copy.copy(outputValues)
            if 'time' in values and len(values['time']) > 0 and curTime != values['time'][-1]:
                # try:
                # print("curTime: {0}, world.time: {1}".format(
                #    curTime, values['time'][-1]))

                # naive: redraw the entire map each time step. This could be improved by saving a list of squares
                # to redraw and being incremental, but there is a fair amount of bookkeeping involved.
                displayedBackground.fill(pygame.Color(255, 255, 255))

                for street in world['streets']:
                    pygame.draw.aaline(displayedBackground,
                                       pygame.Color(128, 128, 128),
                                       (round(street.nodeA[0]*meshSize[0]+meshSize[0]/2),
                                        round(street.nodeA[1]*meshSize[1]+meshSize[1]/2)),
                                       (round(street.nodeB[0]*meshSize[0]+meshSize[0]/2), round(street.nodeB[1]*meshSize[1]+meshSize[1]/2)))

                for jct in range(len(world['junctionIdxs'])):
                    jctSquares[jct].fill(pygame.Color(192, 192, 192))
                    pygame.draw.rect(jctSquares[jct], pygame.Color(128, 128, 128), pygame.Rect(
                        0, 0, round(meshSize[0]/2), round(meshSize[1]/2)), 5)

                # draw any custom objects for debug purposes
                if False:
                    customDrawAddress1 = (40, 0)
                    customDrawAddress2 = (49, 15)

                    pygame.draw.circle(drawPositions[customDrawAddress1[0]][customDrawAddress1[1]],
                                       pygame.Color(100, 100, 0),
                                       (round(meshSize[0]/2),
                                        round(meshSize[1]/2)),
                                       round(meshSize[0]/2), 3)
                    pygame.draw.circle(drawPositions[customDrawAddress2[0]][customDrawAddress2[1]],
                                       pygame.Color(100, 100, 0),
                                       (round(meshSize[0]/2),
                                        round(meshSize[1]/2)),
                                       round(meshSize[0]/2), 3)

                # get fares and taxis that need to be redrawn. We find these by checking the recording dicts
                # for time points in advance of our current display timepoint. The nested comprehensions
                # look formidable, but are simply extracting members with a time stamp ahead of our
                # most recent display time. The odd indexing fare[1].keys()[-1] gets the last element
                # in the time sequence dictionary for a fare (or taxi), which, because of the way this
                # is recorded, is guaranteed to be the most recent entry.
                faresToRedraw = dict([(fare[0], dict([(time[0], time[1])
                                                      for time in fare[1].items()
                                                      if time[0] > curTime]))
                                      for fare in values['fares'].items()
                                      if sorted(list(fare[1].keys()))[-1] > curTime])

                taxisToRedraw = dict([(taxi[0], dict([(taxiPos[0], taxiPos[1])
                                                      for taxiPos in taxi[1].items()
                                                      if taxiPos[0] > curTime]))
                                      for taxi in values['taxis'].items()
                                      if sorted(list(taxi[1].keys()))[-1] > curTime])

                # some taxis are on duty?
                if len(taxisToRedraw) > 0:
                    for taxi in taxisToRedraw.items():
                        # new ones should be assigned a colour
                        if taxi[0] not in taxiColours and len(taxiPalette) > 0:
                            taxiColours[taxi[0]] = taxiPalette.pop(0)
                        # but only plot taxis up to the palette limit (which can be easily extended)
                        if taxi[0] in taxiColours:
                            newestTime = sorted(list(taxi[1].keys()))[-1]
                            # a taxi shows up as a circle in its colour
                            pygame.draw.circle(drawPositions[taxi[1][newestTime][0]][taxi[1][newestTime][1]],
                                               taxiColours[taxi[0]],
                                               (round(meshSize[0]/2),
                                                round(meshSize[1]/2)),
                                               round(meshSize[0]/3))
                        if taxi[0] in values['taxiPaths']:
                            # 2021-11-15: draw current path
                            path = values['taxiPaths'][taxi[0]]
                            for node, nextNode in zip(path, path[1:]):
                                pygame.draw.line(displayedBackground,
                                                 taxiColours[taxi[0]],
                                                 (round(node[0]*meshSize[0]+meshSize[0]/2),
                                                  round(node[1]*meshSize[1]+meshSize[1]/2)),
                                                 (round(nextNode[0]*meshSize[0]+meshSize[0]/2),
                                                  round(nextNode[1]*meshSize[1]+meshSize[1]/2)), width=3)
                else:
                    # no taxis out!
                    print("No taxis out at time {0}".format(curTime))

                # some fares still awaiting a taxi?
                if len(faresToRedraw) > 0:
                    for fare in faresToRedraw.items():
                        newestFareTime = sorted(list(fare[1].keys()))[-1]
                        # fares are plotted as orange triangles (using pygame's points representation which
                        # is relative to the rectangular surface on which you are drawing)
                        pygame.draw.polygon(drawPositions[fare[0][0]][fare[0][1]],
                                            pygame.Color(255, 128, 0),
                                            [(meshSize[0]/2, meshSize[1]/4),
                                            (meshSize[0]/2-math.cos(math.pi/6)*meshSize[1]/4,
                                                meshSize[1]/2+math.sin(math.pi/6)*meshSize[1]/4),
                                            (meshSize[0]/2+math.cos(math.pi/6)*meshSize[1]/4, meshSize[1]/2+math.sin(math.pi/6)*meshSize[1]/4)])
                # new: render text onto the screen.
                # Debug and useful info will be printed onto the screen each update.
                displayedTextArea.fill(pygame.Color(40, 40, 40))

                whiteText = (210, 210, 210)
                redText = (210, 50, 30)
                greenText = (50, 210, 30)
                lineSpacing = boldFontSize + 1
                dataLabelXOffset = 185
                labels = []

                def addLabel(label="", datum="", labelColor=whiteText, datumColor=greenText):
                    # doesn't need to be a function, but it will enforce line spacings :)
                    labelImg = boldFont.render(label, 1, labelColor)
                    datumImg = normalFont.render(datum, 1, datumColor)
                    labels.append((labelImg, datumImg))
                    return None

                ts = time.time()
                dateStamp = datetime.datetime.fromtimestamp(
                    ts).strftime('%Y-%m-%d %H:%M:%S')

                addLabel("RoboUber")
                addLabel("IRL time: ", "{0}".format(dateStamp))
                addLabel("Game time: ", "{0}".format(curTime))
                addLabel("Taxis on duty: ", "{0}".format(len(taxisToRedraw)))
                addLabel("Fares to pickup: ", "{0}".format(len(faresToRedraw)))
                addLabel("Fares completed: ", "{0}".format(
                    values['completedFares']))
                addLabel("Fares cancelled: ", "{0}".format(
                    values['cancelledFares']))
                addLabel("Dispatch revenue: ", "£{0}".format(
                    round(values['dispatcherRevenue'], 2)))
                addLabel()
                addLabel("Map Details:")
                addLabel("Streets: ", "{0}".format(
                    len(world['streets'])), whiteText, whiteText)
                addLabel("Junctions: ", "{0}".format(
                    len(world['junctionIdxs'])), whiteText, whiteText)

                labelsDrawn = 0
                for label in labels:
                    displayedTextArea.blit(
                        label[0], (10, 10 + (lineSpacing * labelsDrawn)))
                    displayedTextArea.blit(
                        label[1], (dataLabelXOffset, 10 + (lineSpacing * labelsDrawn)))
                    labelsDrawn += 1

                #  redraw the whole map
                displaySurface.blit(displayedBackground, activeRect)
                displaySurface.blit(displayedTextArea, textRect)
                pygame.display.flip()

                # reactivate to save images. Will need fiddling with in Linux.
                if curTime % 100 == 0 and False:
                    if os.name == 'nt':
                        # If system is Windows
                        pygame.image.save(displayedBackground,
                                          "D:\Temp\img\{0}.png".format(str(curTime)))
                    else:
                        pygame.image.save(displayedBackground,
                                          "img/{0}.png".format(str(curTime)))
                if curTime % 100 == 0 and False:
                    # with plt.xkcd():
                    # plt.axis([40, 160, 0, 0.03])
                    # plt.grid(True)
                    hist = plt.hist(values['historicPathLengths'])
                    if curTime == 0:
                        plt.xlabel('Steps')
                        plt.ylabel('Frequency')
                        plt.title(
                            'Frequency of travel distances (deepening ply)')
                        plt.ion()
                        # plt.show()
                    else:
                        pass
                        # plt.draw()

                    canvas = agg.FigureCanvasAgg(hist)
                    canvas.draw()
                    renderer = canvas.get_renderer()
                    raw_data = renderer.tostring_rgb()

                if curTime == 100:
                    print("========================================")
                    print("========================================")
                    print("")
                    print("Time: {0}".format(curTime))
                    print("Calls: {0}".format(values['calls']))
                    print("Steps: {0}".format(values['steps']))
                    print("")
                    print("========================================")
                    print("========================================")

                # advance the time
                # except RuntimeError:
                #    print(
                #       "Screen Printing error - skipping time {0}".format(curTime))
                curTime += 1
            # elif len(values['time']) > 0 and curTime == values['time'][-1]:
            #    curTime += 1
else:
    # assume this is a batch run. run multiple threads, start a curses session.
    for i, thread in enumerate(roboUberThreads, start=1):
        thread.start()
        print(
            "{0} - Thread {1} started.".format(dateStamp(), i))

    # threads will now be running. set up a curses terminal session.
    stdscr = curses.initscr()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(1)

    beginX = 20
    beginY = 7
    height = 9
    maxLines = height - 1
    width = 40
    win = curses.newwin(height, width, beginY, beginX)

    def threadsAlive(threads):
        isAlive = False
        for thread in threads:
            isAlive = isAlive or thread.is_alive()
        return isAlive

    while threadsAlive(roboUberThreads):
        linesUsed = 0
        threadCount = 0
        for i, thread in enumerate(roboUberThreads):
            if i > maxLines:
                next
            progressCounter = 0
            if len(outputValuesArray[i]['time']) > 0:
                progressCounter = int(
                    100 * (outputValuesArray[i]['time'][-1] / runTime))

            # width 100 progress bar
            completeString = ("#" * progressCounter) + \
                (" " * (100 - progressCounter))

            stdscr.addstr(
                linesUsed + 1, 0, "|", curses.color_pair(1))
            if progressCounter < 99:
                stdscr.addstr(
                    linesUsed + 1, 1, completeString, curses.color_pair(2))
            else:
                stdscr.addstr(
                    linesUsed + 1, 1, completeString, curses.color_pair(3))
            stdscr.addstr(
                linesUsed + 1, len(completeString), "| $", curses.color_pair(1))
            stdscr.addstr(
                linesUsed + 1, len(completeString + "| $"), str(int(outputValuesArray[i]['dispatcherRevenue'])), curses.color_pair(3))

            if thread.is_alive:
                threadCount += 1
            linesUsed += 1

        #
        #
        #
        #

        stdscr.addstr(
            0, 0, "{0} - {1} threads running.".format(dateStamp(), threadCount))

        stdscr.refresh()
        # print("Alive!")

    # (currently redundant) wait for the main thread to finish
    roboUber.join()
    # end curses
    curses.nocbreak()
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()
    # rejoin batch threads
    for i, thread in enumerate(roboUberThreads, start=1):
        thread.join()
        print("{0} - Thread {1} rejoined.".format(
            dateStamp(), i))
