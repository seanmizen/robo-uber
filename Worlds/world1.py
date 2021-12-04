import networld
import numpy
trafficOn = False


def fareProbMagnet(m): return numpy.random.random() > 0.98
# popular locations generate a fare about once every 2 hours
def fareProbPopular(p): return numpy.random.random() > 0.992
# semi-popular locations generate a fare approximately every 4 hours
def fareProbSemiPopular(s): return numpy.random.random() > 0.995
# normal locations generate a fare about once per day
def fareProbNormal(n): return numpy.random.random() > 0.999


# some traffic injectors and sinks for real-time simulation
trafficSrcMinor = 1 if trafficOn else 0
trafficSrcSignificant = 2 if trafficOn else 0
trafficSrcMajor = 3 if trafficOn else 0
trafficSrcHub = 4 if trafficOn else 0
trafficSinkMinor = 1 if trafficOn else 0
trafficSinkSignificant = 2 if trafficOn else 0
trafficSinkMajor = 3 if trafficOn else 0
trafficSinkDrain = 4 if trafficOn else 0


# some nodes - this can be automated
jct0 = networld.junctionDef(
    x=0, y=0, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor)
jct1 = networld.junctionDef(
    x=20, y=0, cap=2, canStop=True, src=trafficSrcSignificant, sink=trafficSinkMajor)
jct2 = networld.junctionDef(
    x=40, y=0, cap=2, canStop=True, src=trafficSrcMajor, sink=trafficSinkMajor)
jct3 = networld.junctionDef(
    x=49, y=0, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor)
jct4 = networld.junctionDef(
    x=0, y=10, cap=2, canStop=True, src=trafficSrcSignificant, sink=trafficSinkMinor)
jct5 = networld.junctionDef(
    x=10, y=10, cap=2, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12)
jct6 = networld.junctionDef(x=20, y=10, cap=2, canStop=True, maxTraffic=12)
jct7 = networld.junctionDef(
    x=24, y=15, cap=4, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12)
jct8 = networld.junctionDef(
    x=30, y=15, cap=4, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12)
jct9 = networld.junctionDef(
    x=40, y=15, cap=4, canStop=True, fareProb=fareProbPopular, maxTraffic=12)
jct10 = networld.junctionDef(x=49, y=15, cap=2, canStop=True,
                             src=trafficSrcSignificant, sink=trafficSinkSignificant)
jct11 = networld.junctionDef(x=10, y=20, cap=2, canStop=True)
jct12 = networld.junctionDef(
    x=20, y=20, cap=4, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12)
jct13 = networld.junctionDef(x=10, y=24, cap=2, canStop=True)
jct14 = networld.junctionDef(x=20, y=24, cap=4, canStop=True)
jct15 = networld.junctionDef(x=24, y=24, cap=8, canStop=True, fareProb=fareProbMagnet,
                             maxTraffic=16, src=trafficSrcHub, sink=trafficSinkMajor)
jct16 = networld.junctionDef(x=30, y=24, cap=4, canStop=True)
jct17 = networld.junctionDef(
    x=0, y=35, cap=2, canStop=True, src=trafficSrcSignificant, sink=trafficSinkMajor)
jct18 = networld.junctionDef(
    x=10, y=35, cap=4, canStop=True, fareProb=fareProbPopular, maxTraffic=12)
jct19 = networld.junctionDef(
    x=20, y=30, cap=4, canStop=True, fareProb=fareProbSemiPopular)
jct20 = networld.junctionDef(x=24, y=35, cap=4, canStop=True, fareProb=fareProbPopular,
                             maxTraffic=12, src=trafficSrcMajor, sink=trafficSinkDrain)
jct21 = networld.junctionDef(x=30, y=30, cap=4, canStop=True)
jct22 = networld.junctionDef(
    x=40, y=30, cap=4, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12)
jct23 = networld.junctionDef(
    x=49, y=30, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor)
jct24 = networld.junctionDef(x=10, y=40, cap=2, canStop=True)
jct25 = networld.junctionDef(
    x=15, y=40, cap=4, canStop=True, fareProb=fareProbPopular, maxTraffic=12)
jct26 = networld.junctionDef(
    x=30, y=40, cap=4, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12)
jct27 = networld.junctionDef(x=40, y=40, cap=2, canStop=True, maxTraffic=12)
jct28 = networld.junctionDef(
    x=0, y=49, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor)
jct29 = networld.junctionDef(
    x=15, y=49, cap=2, canStop=True, src=trafficSrcSignificant, sink=trafficSinkMajor)
jct30 = networld.junctionDef(
    x=30, y=49, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor)
jct31 = networld.junctionDef(
    x=49, y=49, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor)

junctions = [jct0, jct1, jct2, jct3, jct4, jct5, jct6, jct7, jct8, jct9, jct10, jct11, jct12, jct13, jct14, jct15,
             jct16, jct17, jct18, jct19, jct20, jct21, jct22, jct23, jct24, jct25, jct26, jct27, jct28, jct29, jct30, jct31]
junctionIdxs = [(node.x, node.y) for node in junctions]

# and some streets between them; likewise, this can be automated
strt0 = networld.streetDef((0, 0), (10, 10), 3, 7, biDirectional=True)
strt1 = networld.streetDef((0, 10), (10, 10), 2, 6, biDirectional=True)
strt2 = networld.streetDef((0, 35), (10, 35), 2, 6, biDirectional=True)
strt3 = networld.streetDef((0, 49), (10, 40), 1, 5, biDirectional=True)
strt4 = networld.streetDef((10, 10), (10, 20), 4, 0, biDirectional=True)
strt5 = networld.streetDef((10, 20), (10, 24), 4, 0, biDirectional=True)
strt6 = networld.streetDef((10, 24), (10, 35), 4, 0, biDirectional=True)
strt7 = networld.streetDef((10, 35), (10, 40), 4, 0, biDirectional=True)
strt8 = networld.streetDef((10, 10), (20, 10), 2, 6, biDirectional=True)
strt9 = networld.streetDef((10, 20), (20, 20), 2, 6, biDirectional=True)
strt10 = networld.streetDef((10, 24), (20, 24), 2, 6, biDirectional=True)
strt11 = networld.streetDef((10, 35), (20, 30), 1, 5, biDirectional=True)
strt12 = networld.streetDef((10, 35), (15, 40), 3, 7, biDirectional=True)
strt13 = networld.streetDef((10, 40), (15, 40), 2, 6, biDirectional=True)
strt14 = networld.streetDef((20, 0), (20, 10), 4, 0, biDirectional=True)
strt15 = networld.streetDef((20, 10), (20, 20), 4, 0, biDirectional=True)
strt16 = networld.streetDef((20, 20), (20, 24), 4, 0, biDirectional=True)
strt17 = networld.streetDef((20, 24), (20, 30), 4, 0, biDirectional=True)
strt18 = networld.streetDef((15, 40), (15, 49), 4, 0, biDirectional=True)
strt19 = networld.streetDef((20, 10), (24, 15), 3, 7, biDirectional=True)
strt20 = networld.streetDef((20, 20), (24, 15), 1, 5, biDirectional=True)
strt21 = networld.streetDef((20, 20), (24, 24), 3, 7, biDirectional=True)
strt22 = networld.streetDef((20, 24), (24, 24), 2, 6, biDirectional=True)
strt23 = networld.streetDef((20, 30), (24, 24), 1, 5, biDirectional=True)
strt24 = networld.streetDef((20, 30), (24, 35), 3, 7, biDirectional=True)
strt25 = networld.streetDef((15, 40), (24, 35), 1, 5, biDirectional=True)
strt26 = networld.streetDef((15, 40), (30, 40), 2, 6, biDirectional=True)
strt27 = networld.streetDef((24, 15), (24, 24), 4, 0, biDirectional=True)
strt28 = networld.streetDef((24, 24), (24, 35), 4, 0, biDirectional=True)
strt29 = networld.streetDef((24, 15), (30, 15), 2, 6, biDirectional=True)
strt30 = networld.streetDef((24, 24), (30, 15), 1, 5, biDirectional=True)
strt31 = networld.streetDef((24, 24), (30, 24), 2, 6, biDirectional=True)
strt32 = networld.streetDef((24, 24), (30, 30), 3, 7, biDirectional=True)
strt33 = networld.streetDef((24, 35), (30, 30), 1, 5, biDirectional=True)
strt34 = networld.streetDef((24, 35), (30, 40), 3, 7, biDirectional=True)
strt35 = networld.streetDef((30, 15), (30, 24), 4, 0, biDirectional=True)
strt36 = networld.streetDef((30, 24), (30, 30), 4, 0, biDirectional=True)
strt37 = networld.streetDef((30, 40), (30, 49), 4, 0, biDirectional=True)
strt38 = networld.streetDef((30, 15), (40, 15), 2, 6, biDirectional=True)
strt39 = networld.streetDef((30, 15), (40, 30), 3, 7, biDirectional=True)
strt40 = networld.streetDef((30, 40), (40, 40), 2, 6, biDirectional=True)
strt41 = networld.streetDef((40, 0), (40, 15), 4, 0, biDirectional=True)
strt42 = networld.streetDef((40, 15), (40, 30), 4, 0, biDirectional=True)
strt43 = networld.streetDef((40, 30), (40, 40), 4, 0, biDirectional=True)
strt44 = networld.streetDef((40, 15), (49, 0), 1, 5, biDirectional=True)
strt45 = networld.streetDef((40, 15), (49, 15), 2, 6, biDirectional=True)
strt46 = networld.streetDef((40, 30), (49, 30), 2, 6, biDirectional=True)
strt47 = networld.streetDef((40, 40), (49, 49), 3, 7, biDirectional=True)

streets = [strt0, strt1, strt2, strt3, strt4, strt5, strt6, strt7, strt8, strt9, strt10, strt11, strt12, strt13, strt14, strt15,
           strt16, strt17, strt18, strt19, strt20, strt21, strt22, strt23, strt24, strt25, strt26, strt27, strt28, strt29, strt30, strt31,
           strt32, strt33, strt34, strt35, strt36, strt37, strt38, strt39, strt40, strt41, strt42, strt43, strt44, strt45, strt46, strt47]


def export():
    return {
        'junctions': junctions,
        'junctionIdxs': junctionIdxs,
        'streets': streets,
        'fareProbMagnet': fareProbMagnet,
        'fareProbPopular': fareProbPopular,
        'fareProbSemiPopular': fareProbSemiPopular,
        'fareProbNormal': fareProbNormal}
