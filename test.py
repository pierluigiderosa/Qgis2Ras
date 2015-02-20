# -*- coding: utf-8 -*-
#
from numpy import  array
from numpy import  diff
from numpy import  append as nappend
def getKey(item):
    return item[0]


XSstation = list()
for riv_feat in river.getFeatures():
    riv_geom = riv_feat.geometry()
    riverLen = riv_geom.length()
    for XSfeature in xsects.getFeatures():
        XS_geom = XSfeature.geometry()
        pt_int = riv_geom.intersection(XS_geom)
        distSP = pointInterpolate(riv_geom,pt_int.asPoint())
        XSstation.append((distSP,XSfeature))
#sorting tuple according to the distance US
XSstationASC = sorted(XSstation,key=getKey)
stationUS = [(i[0]) for i in XSstationASC]

reachLen = riverLen - array(stationUS)
reachLenUP=diff(array(stationUS))
reachLenUP = nappend(reachLenUP,reachLen[-1])