import networld
import numpy
scenario = 2
trafficOn = True

n = 0
ne = 1
e = 2
se = 3
s = 4
sw = 5
w = 6
nw = 7


def fareProbMagnet(m): return numpy.random.random() > 0.98
# popular locations generate a fare about once every 2 hours
def fareProbPopular(p): return numpy.random.random() > 0.992
# semi-popular locations generate a fare approximately every 4 hours
def fareProbSemiPopular(s): return numpy.random.random() > 0.995
# normal locations generate a fare about once per day
def fareProbNormal(n): return numpy.random.random() > 0.999
# ensure most points have 0 traffic
def fareProbZero(z): return False


# some traffic injectors and sinks for real-time simulation
trafficSrcMinor = 1 if trafficOn else 0
trafficSrcSignificant = 2 if trafficOn else 0
trafficSrcMajor = 3 if trafficOn else 0
trafficSrcHub = 4 if trafficOn else 0
trafficSinkMinor = 1 if trafficOn else 0
trafficSinkSignificant = 2 if trafficOn else 0
trafficSinkMajor = 3 if trafficOn else 0
trafficSinkDrain = 4 if trafficOn else 0

jct0 = networld.junctionDef(
    x=0, y=30, cap=1, canStop=True, fareProb=fareProbZero)
jct1 = networld.junctionDef(
    x=10, y=30, cap=1, canStop=False, fareProb=fareProbZero)
jct2 = networld.junctionDef(
    x=20, y=30, cap=1, canStop=False, fareProb=fareProbZero)
jct3a = networld.junctionDef(
    x=23, y=30, cap=1, canStop=False, fareProb=fareProbZero)
jct3b = networld.junctionDef(
    x=27, y=30, cap=1, canStop=False, fareProb=fareProbZero)
jct4 = networld.junctionDef(
    x=30, y=30, cap=1, canStop=False, fareProb=fareProbZero)
jct5 = networld.junctionDef(
    x=40, y=30, cap=1, canStop=False, fareProb=fareProbZero)
jct6 = networld.junctionDef(
    x=49, y=30, cap=1, canStop=True, fareProb=fareProbNormal)
jct7 = networld.junctionDef(
    x=22, y=25, cap=1, canStop=False, fareProb=fareProbZero)
jct8 = networld.junctionDef(
    x=28, y=25, cap=1, canStop=False, fareProb=fareProbZero)
jct9 = networld.junctionDef(
    x=10, y=20, cap=1, canStop=False, fareProb=fareProbZero)
jct10 = networld.junctionDef(
    x=40, y=20, cap=1, canStop=False, fareProb=fareProbZero)

# Scenario 1: No traffic
# taxi will take a straight line route across the map
if scenario == 1:
    pass

# Scenario 2: (minor traffic avoidance)
# jct 3 major traffic, minor sink
if scenario == 2:
    jct3a = networld.junctionDef(
        x=23, y=30, cap=2, canStop=False, src=trafficSrcMajor, sink=trafficSinkMinor)
    jct3b = networld.junctionDef(
        x=27, y=30, cap=2, canStop=False, src=trafficSrcMajor, sink=trafficSinkMinor)

# Scenario 3: (Major traffic avoidance)
# jct 3 major traffic, minor sink
# jct 7 major traffic, minor sink
if scenario == 3:
    jct3a = networld.junctionDef(
        x=23, y=30, cap=2, canStop=False, src=trafficSrcMajor, sink=trafficSinkMinor)
    jct3b = networld.junctionDef(
        x=27, y=30, cap=2, canStop=False, src=trafficSrcMajor, sink=trafficSinkMinor)
    jct7 = networld.junctionDef(
        x=22, y=25, cap=2, canStop=False, src=trafficSrcMajor, sink=trafficSrcMinor)

# Scenario 4: Gridlock avoidance
# jct 3 hub traffic, minor sink
# jct 7 hub traffic, minor sink
if scenario == 4:
    jct3a = networld.junctionDef(
        x=23, y=30, cap=2, canStop=True, src=trafficSrcHub, sink=trafficSinkMinor)
    jct7 = networld.junctionDef(
        x=22, y=30, cap=2, canStop=True, src=trafficSrcHub, sink=trafficSinkMinor)

junctions = [jct0, jct1, jct2, jct3a, jct3b,
             jct4, jct5, jct6, jct7, jct8, jct9, jct10]
junctionIdxs = [(node.x, node.y) for node in junctions]

# straight line network:
strt0 = networld.streetDef(
    (jct0.x, jct0.y), (jct1.x, jct1.y), e, w, biDirectional=True)
strt1 = networld.streetDef(
    (jct1.x, jct1.y), (jct2.x, jct2.y), e, w, biDirectional=True)
strt2 = networld.streetDef(
    (jct2.x, jct2.y), (jct3a.x, jct3a.y), e, w, biDirectional=True)
strt3a = networld.streetDef(
    (jct3a.x, jct3a.y), (jct3b.x, jct3b.y), e, w, biDirectional=True)
strt3b = networld.streetDef(
    (jct3b.x, jct3b.y), (jct4.x, jct4.y), e, w, biDirectional=True)
strt4 = networld.streetDef(
    (jct4.x, jct4.y), (jct5.x, jct5.y), e, w, biDirectional=True)
strt5 = networld.streetDef(
    (jct5.x, jct5.y), (jct6.x, jct6.y), e, w, biDirectional=True)

# The slight diversion:
strt6 = networld.streetDef(
    (jct2.x, jct2.y), (jct7.x, jct7.y), ne, sw, biDirectional=True)
strt7 = networld.streetDef(
    (jct7.x, jct7.y), (jct8.x, jct8.y), e, w, biDirectional=True)
strt8 = networld.streetDef(
    (jct8.x, jct8.y), (jct4.x, jct4.y), se, nw, biDirectional=True)

# The major diversion:
strt9 = networld.streetDef(
    (jct1.x, jct1.y), (jct9.x, jct9.y), n, s, biDirectional=True)
strt10 = networld.streetDef(
    (jct9.x, jct9.y), (jct10.x, jct10.y), e, w, biDirectional=True)
strt11 = networld.streetDef(
    (jct10.x, jct10.y), (jct5.x, jct5.y), s, n, biDirectional=True)

streets = [strt0, strt1, strt2, strt3a, strt3b, strt4, strt5,
           strt6, strt7, strt8, strt9, strt10, strt11]

# only one taxi, expressed as tuple (int id, (int x, int y))
taxis = [(100, (0, 30))]
if scenario == 5:
    taxis.append((101, (49, 30)))


def export():
    return {
        'junctions': junctions,
        'junctionIdxs': junctionIdxs,
        'streets': streets,
        'fareProbMagnet': fareProbMagnet,
        'fareProbPopular': fareProbPopular,
        'fareProbSemiPopular': fareProbSemiPopular,
        'fareProbNormal': fareProbNormal,
        'taxis': taxis}
