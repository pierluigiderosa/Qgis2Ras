# -*- coding: utf-8 -*-
#
# Copyright © 2012 Giovanni Allegri (Gis3W s.a.s.)
# Licensed under the terms of the LGPLv2 License

from qgis.core import *
import math

def pointInterpolate(geom,point):
    geomType = geom.wkbType ()
    if geomType <> QGis.WKBLineString:
        return None
    linegeom = geom.asPolyline()
    segStop = nearestSegToPoint(linegeom,point)
    segPoints = (linegeom[segStop],linegeom[segStop+1])
    length = 0.0
    seg = 0
    while seg < segStop:
        p1 = linegeom[seg]
        p2 = linegeom[seg+1]
        length += distToPoint(p1,p2)
        seg += 1
    
    pointProj = closesPointToSeg(segPoints[0],segPoints[1],point)
    partSegLength = distToPoint(segPoints[0],pointProj)
    partSegLength += distToPoint(pointProj,point)
    length += partSegLength
    return length
        
    
def nearestSegToPoint(linegeom,point):
    nearestseg = 0
    mindist = -1
    nsegs = len(linegeom)-1
    for seg in range(nsegs):
        lpt1 = linegeom[seg]
        lpt2 = linegeom[seg+1]
        dist = distToSeg(lpt1,lpt2,point)
        if seg == 0 or dist<mindist:
            nearestseg = seg
            mindist = dist
        if mindist==float(0):
            nearestseg = seg
            break
        seg = seg+1
    return nearestseg

def closesPointToSeg(lpt1,lpt2,point):
    lpt1x = lpt1.x()
    lpt1y = lpt1.y()
    lpt2x = lpt2.x()
    lpt2y = lpt2.y()
    pointx = point.x()
    pointy = point.y()
    
    if (lpt1x == lpt2x) and (lpt1y == lpt2y):
        return lpt1
    
    r = (((pointx-lpt1x) * (lpt2x-lpt1x)) + ((pointy-lpt1y) * (lpt2y-lpt1y))) / (((lpt2x-lpt1x) * (lpt2x-lpt1x)) + ((lpt2y-lpt1y) * (lpt2y-lpt1y)))
    
    if r<0:
        return lpt1
    
    if r>1:
        return lpt2
    
    x = lpt1x + ((lpt2x-lpt1x)*r)
    y = lpt1y + ((lpt2y-lpt1y)*r)
    return QgsPoint(x,y)

        
def distToPoint(p1,p2):
    h = p2.x()-p1.x()
    v = p2.y()-p1.y()
    return math.sqrt((h*h)+(v*v))
        
def distToSeg(lpt1,lpt2,point):
    
    lpt1x = lpt1.x()
    lpt1y = lpt1.y()
    lpt2x = lpt2.x()
    lpt2y = lpt2.y()
    pointx = point.x()
    pointy = point.y()
    
    if (lpt1x == lpt2x) and (lpt1y == lpt2y):
        return distToPoint(lpt1,point)
  
    r = (((pointx-lpt1x) * (lpt2x-lpt1x)) + ((pointy-lpt1y) * (lpt2y-lpt1y))) / (((lpt2x-lpt1x) * (lpt2x-lpt1x)) + ((lpt2y-lpt1y) * (lpt2y-lpt1y)))
    
    if r<0:
        return distToPoint(lpt1,point)
    if r>0:
        return distToPoint(lpt2,point)
        
    s = (((lpt1y-pointy) * (lpt2x-lpt1x)) - ((lpt1x-pointx) * (lpt2y-lpt1y))) / (((lpt2x-lpt1x) * (lpt2x-lpt1x)) + ((lpt2y-lpt1y) * (lpt2y-lpt1y)))

    return math.fabs(s) * math.sqrt(math.fabs(((lpt2x-lpt1x) * (lpt2x-lpt1x)) - ((lpt2y-lpt1y) * (lpt2y-lpt1y))))