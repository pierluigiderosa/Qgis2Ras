# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2RasDialog
                                 A QGIS plugin
 Qgis 2 RAS preprocessor
                             -------------------
        begin                : 2014-12-18
        git sha              : $Format:%H$
        copyright            : (C) 2014 by Pierluigi De Rosa
        email                : pierluigi.derosa@gfosservices.it
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.core import (QgsVectorLayer,QgsRasterLayer,
                        QgsGeometry,QgsPoint,QgsRaster,QgsRectangle)
import datetime
from PyQt4.QtCore import QFileInfo
from osgeo import ogr,_ogr
from lengthalongline import pointInterpolate
from numpy import array
from os import linesep as LineSep




fileName = "/home/pierluigi/Scrivania/pluginQRAS/dem_torgiano.tif"
fileInfo = QFileInfo(fileName)
baseName = fileInfo.baseName()
rlayer = QgsRasterLayer(fileName, baseName)

def output_headers(river, xsections, outfile):
    """
    Prepare the output sdf file, and add header section
    """
    # Start header section
    dt = str(datetime.date.today())
    ver = '2.6'

    outfile.write("#QRAS geometry create on: " + dt + LineSep)
    outfile.write("BEGIN HEADER:")
    outfile.write(LineSep)
    units = "METRIC"

    outfile.write("DTM TYPE: TIN")
    outfile.write(LineSep)
    outfile.write("DTM: \\"+LineSep)
    outfile.write("STREAM LAYER: \\" + river.name() + LineSep)
    # write out how many reaches and cross sections
    num_reaches = int(river.featureCount())
    num_reaches = str(num_reaches)
    outfile.write("NUMBER OF REACHES: " + num_reaches + LineSep)
    outfile.write("CROSS-SECTION LAYER: \\" + xsections.name() + LineSep)
    num_xsects = int(xsections.featureCount())
    num_xsects = str(num_xsects)
    outfile.write("NUMBER OF CROSS-SECTIONS: " + num_xsects + LineSep)
    outfile.write("MAP PROJECTION: \nPROJECTION ZONE: \nDATUM: \nVERTICAL DATUM: ")
    outfile.write(LineSep)

    # write out the extents
    xmin = river.extent().xMinimum()
    xmin = str(xmin)
    xmax = river.extent().xMaximum()
    xmax = str(xmax)
    ymin = river.extent().yMinimum()
    ymin = str(ymin)
    ymax = river.extent().yMaximum()
    ymax = str(ymax)
    outfile.write("BEGIN SPATIAL EXTENT:"+LineSep)
    outfile.write("XMIN: " + xmin + LineSep)
    outfile.write("YMIN: " + ymin + LineSep)
    outfile.write("XMAX: " + xmax + LineSep)
    outfile.write("YMAX: " + ymax + LineSep)
    outfile.write("END SPATIAL EXTENT:"+LineSep)
    outfile.write("UNITS: " + units + LineSep)

    outfile.write("END HEADER:")
    outfile.write(LineSep+LineSep+LineSep)


def output_centerline(river, stations, outfile,rlayer):
    """
    Output the river network, including centerline for each reach
    and coordinates for all stations along each reach
    """
    outfile.write("BEGIN STREAM NETWORK:\t\t")
    outfile.write(LineSep)
    # TODO: multiple river feature in case of junction
    if int(river.featureCount() ) != 1:
        import sys

        sys.exit()    
    
    # Begin with the list of feature in reach
    iterFeature = river.getFeatures()





    for feature in iterFeature:
        points = getVertex(feature)
        # IT SHOUD LOOP thru the reach_cats again, and output a REACH: section for each reach,
        # with all points for that reach --- TODO
        riverName =  river.name().replace(" ", "")
        (Xs,Ys,Zs) = queryRaster(points[0],rlayer)
        (Xe,Ye,Ze) = queryRaster(points[-1],rlayer)
        #~ outfile.write("ENDPOINT: %.1f, %.1f, %.3f, 1\n" %(Xs,Ys,Zs) ) 
        #~ outfile.write("ENDPOINT: %.1f, %.1f, %.3f, 2\n" %(Xe,Ye,Ze) )
        outfile.write(LineSep)
        outfile.write("REACH:")
        outfile.write(LineSep)
        outfile.write("STREAM ID: %s" % (riverName) )
        outfile.write(LineSep)
        outfile.write("REACH ID: %s" % (riverName))
        outfile.write(LineSep)
        outfile.write("FROM POINT: 1")
        outfile.write(LineSep)
        outfile.write("TO POINT: 2")
        outfile.write(LineSep)
        outfile.write("CENTERLINE:")  # Now the actual points along centerline
        outfile.write(LineSep)
        for point in points:
            (X,Y,Z) = queryRaster(point,rlayer)
            p = QgsPoint(point[0],point[1])
            outfile.write( "\t%.4f, %.4f, %.6f, " %(X,Y,Z)) 
            outfile.write(LineSep)
    outfile.write("END:")
    outfile.write(LineSep)
    outfile.write(LineSep)
    outfile.write("END STREAM NETWORK:") 
    outfile.write(LineSep)
    outfile.write(LineSep)
    outfile.write(LineSep)	    

def queryRaster(point,raster):
    p = QgsPoint(point[0],point[1])
    if isInExtent(rlayer,point):
        provider=rlayer.dataProvider()		    			    
        identifyresult = provider.identify(p,QgsRaster.IdentifyFormatValue,QgsRectangle())
        results = identifyresult.results()
        val = results[1]
        return point[0],point[1],val

def getVertex(feature,distance=0):
    the_geom = feature.geometry()
    if distance ==0:
        wkbgeom = the_geom.asWkb()
        ogrgeom = ogr.CreateGeometryFromWkb(wkbgeom)
        if ogrgeom.GetGeometryName() == 'LINESTRING' :
            points = ogrgeom.GetPoints()
        return points
    else:
        length = the_geom.length()
        currentdistance = distance
        points = []
        
        wkbgeom = the_geom.asWkb()
        ogrgeom = ogr.CreateGeometryFromWkb(wkbgeom)
        if ogrgeom.GetGeometryName() == 'LINESTRING' :
            pointsL = ogrgeom.GetPoints()
        points.append(pointsL[0]) 
               
        while currentdistance < length:
            # Get a point along the line at the current distance
            point = the_geom.interpolate(currentdistance)
            # Create a new tuple and get XY from the geometry
            Qpoint = point.asPoint()
            points.append((Qpoint.x(),Qpoint.y()))
            # Increase the distance
            currentdistance = currentdistance + distance
        
        points.append(pointsL[-1]) 
        return points
    
def output_xsections(xsects, outfile, elev, res, river):
    """
    Output the river network, including centerline for each reach
    and coordinates for all stations along each reach
    """
    outfile.write("BEGIN CROSS-SECTIONS:")	
    outfile.write(LineSep)
    outfile.write(LineSep)
    riverName =  river.name().replace(" ", "") 
    
    nXS = xsects.featureCount()
    nXS = int(nXS)
    
    #~ loop for detecting reach length
    if int(river.featureCount() ) == 1:
        reachLen = list()
        for riv_feat in river.getFeatures():
            riv_geom = riv_feat.geometry()
            riverLen = riv_geom.length()
            for XSfeature in xsects.getFeatures():
                XS_geom = XSfeature.geometry()
                pt_int = riv_geom.intersection(XS_geom)
                distSP = pointInterpolate(riv_geom,pt_int.asPoint())
                reachLen.append(distSP)
                
        #~ invert orded reachLen          
        #~ reachLen=reachLen[::-1]
        
        
                        
        reachLenUP=list()
        for i in range(len(reachLen)):
            if i < len(reachLen)-1:
                reachLenUP.append( reachLen[i+1]-reachLen[i] )
            else:
                reachLenUP.append (riverLen - reachLen[i] )
        
        #store distance from end stream as RAS required
        reachLen = riverLen - array(reachLen)

        
    idXS=0
    for XSfeature in xsects.getFeatures():
        outfile.write("CROSS-SECTION:")
        outfile.write(LineSep)
        outfile.write("STREAM ID: %s" % (riverName))
        outfile.write(LineSep)
        outfile.write("REACH ID: %s" % (riverName))
        outfile.write(LineSep)
        outfile.write("STATION: %.2f" % (reachLen[idXS]))
        outfile.write(LineSep)
        outfile.write("NODE NAME: ")
        outfile.write(LineSep)
        outfile.write("BANK POSITIONS: 0, 1")
        outfile.write(LineSep)
        outfile.write("REACH LENGTHS: %.4f ,%.4f, %.4f " % (reachLenUP[idXS],reachLenUP[idXS],reachLenUP[idXS])) 
        outfile.write(LineSep)       
        outfile.write("NVALUES:"+LineSep+"LEVEE POSITIONS:"+LineSep+"INEFFECTIVE POSITIONS: "+LineSep+"BLOCKED POSITIONS: "+LineSep)
        idXS+=1
        outfile.write("CUT LINE:")
        outfile.write(LineSep)
        points = getVertex(XSfeature)
        for point in points:
            outfile.write("\t%.4f, %.4f" %(point[0],point[1]))
            outfile.write(LineSep)
        outfile.write("SURFACE LINE:")
        outfile.write(LineSep)
        points = getVertex(XSfeature,res)
        for point in points:
            (X,Y,Z) = queryRaster(point,elev)
            p = QgsPoint(point[0],point[1])
            outfile.write( "\t%.4f, %.4f, %.4f" %(X,Y,Z)) 
            outfile.write(LineSep)
        outfile.write("END:")
        outfile.write(LineSep)
        outfile.write(LineSep)
        
    outfile.write("END CROSS-SECTIONS:")
    outfile.write(LineSep)
    outfile.write(LineSep)
    outfile.write(LineSep)



def isInExtent(raster,point):
	rextent = raster.extent()
	xMin = rextent.xMinimum()
	yMin = rextent.yMinimum()
	xMax = rextent.xMaximum()
	yMax = rextent.yMaximum()
    
	if (xMin<point[0]<xMax) and (yMin<point[1]<yMax):
	    return True
	return False

def line_endings(text_file):
    import re
    data = open(text_file, 'rb').read()
    newdata = re.sub("\r(?!\n)|(?<!\r)\n", "\r\n", data)
    if newdata != data:
        f = open(text_file, "wb")
        f.write(newdata)
        f.close()


def main(river,xsections,file_strin_path,res=1):
    #~ rimuovi i commenti se tutto ok
    river = QgsVectorLayer('/home/pierluigi/Scrivania/pluginQRAS/asse_tevere_OK.shp', 'asse_tevere_OK', 'ogr')
    #~ xsections = QgsVectorLayer('/home/pierluigi/Scrivania/pluginQRAS/XSections1.shp', 'XSections1', 'ogr')
    #~ file_strin_path='/tmp/test.sdf'
    #~ res=1
    outfile = open(file_strin_path, 'w')
    output_headers(river, xsections, outfile)
    output_centerline(river,xsections, outfile,rlayer)
    output_xsections(xsections, outfile, rlayer, res, river)
    outfile.close()
    #~ test line endings
    f = open(file_strin_path, 'U')
    f.readline()
    if f.newlines == '\n':
        line_endings(file_strin_path)

