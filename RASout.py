# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2RasDialog
                                 A QGIS plugin
 Qgis 2 RAS preprocessor
                             -------------------
        begin                : 2014-12-18
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Pierluigi De Rosa
                                & M. Weier - North Dakota State Water Commission
        email                : pierluigi.derosa@gfosservices.it
                                mweier@nd.gov
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
from psycopg2.extensions import NoneAdapter
from qgis.core import (QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsExpression,
                       QgsGeometry, QgsPoint, QgsRaster, QgsRectangle)
import datetime
from PyQt4.QtCore import QFileInfo
from osgeo import ogr, _ogr
from lengthalongline import pointInterpolate
from numpy import array, diff
from numpy import append as nappend
from os import linesep as LineSep


def output_headers(river, xsections, outfile, units):
    """
    Prepare the output sdf file, and add header section
    """
    # Start header section
    tStemp = datetime.datetime.now()
    day = str(tStemp.year) + '/' + str(tStemp.month) + '/' + str(tStemp.day) + '/ '
    ver = '2.6'
    ora = str(tStemp.hour) + ':' + str(tStemp.minute) + ':' + str(tStemp.second)

    outfile.write("#QRAS create on " + day + ora + LineSep)
    outfile.write("BEGIN HEADER:\n")
    if units == 'feet':
        units = "US CUSTOMARY"
    else:
        units = 'METRIC'

    outfile.write("DTM TYPE: GRID\n")
    outfile.write("DTM: \\" + LineSep)
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
    outfile.write("BEGIN SPATIAL EXTENT:" + LineSep)
    outfile.write("XMIN: " + xmin + LineSep)
    outfile.write("YMIN: " + ymin + LineSep)
    outfile.write("XMAX: " + xmax + LineSep)
    outfile.write("YMAX: " + ymax + LineSep)
    outfile.write("END SPATIAL EXTENT:" + LineSep)
    outfile.write("UNITS: " + units + LineSep)

    outfile.write("END HEADER:")
    outfile.write(LineSep + LineSep + LineSep)


def output_centerline(river, stations, outfile, rlayer):
    """
    Output the river network, including centerline for each reach
    and coordinates for all stations along each reach
    """
    outfile.write("BEGIN STREAM NETWORK:\t\t")
    outfile.write(LineSep)
    # TODO: multiple river feature in case of junction
    if int(river.featureCount()) != 1:
        import sys

        sys.exit()

        # Begin with the list of feature in reach
    iterFeature = river.getFeatures()

    for feature in iterFeature:
        points = getVertex(feature)
        # IT SHOUD LOOP thru the reach_cats again, and output a REACH: section for each reach,
        # with all points for that reach --- TODO
        riverName = river.name().replace(" ", "")

        outfile.write(LineSep)
        outfile.write("REACH:")
        outfile.write(LineSep)
        outfile.write("STREAM ID: {}\n".format(riverName))
        outfile.write("REACH ID: {}\n".format(riverName))
        outfile.write("FROM POINT: 0\n")
        outfile.write("TO POINT: 1\n")
        outfile.write("CENTERLINE:\n")  # Now the actual points along centerlinep)
        for point in points:
            (X, Y, Z) = queryRaster(point, rlayer)
            p = QgsPoint(point[0], point[1])
            outfile.write("\t%.4f, %.4f, %.6f, " % (X, Y, Z))
            outfile.write(LineSep)
    outfile.write("END:")
    outfile.write(LineSep)
    outfile.write(LineSep)
    outfile.write("END STREAM NETWORK:")
    outfile.write(LineSep)
    outfile.write(LineSep)
    outfile.write(LineSep)


def queryRaster(point, raster):
    p = QgsPoint(point[0], point[1])
    if isInExtent(raster, point):
        provider = raster.dataProvider()
        identifyresult = provider.identify(p, QgsRaster.IdentifyFormatValue, QgsRectangle())
        results = identifyresult.results()
        val = results[1]
        return point[0], point[1], val


def getVertex(feature, distance=0):
    '''
    Crete a point along line
    :param feature: la linea da cui dedurre la linea
    :param distance: la distance whee get the line
    :return: list of points or single point
    '''
    the_geom = feature.geometry()
    if distance == 0:
        wkbgeom = the_geom.asWkb()
        ogrgeom = ogr.CreateGeometryFromWkb(wkbgeom)
        if ogrgeom.GetGeometryName() == 'LINESTRING':
            points = ogrgeom.GetPoints()
        return points
    else:
        length = the_geom.length()
        currentdistance = distance
        points = []

        wkbgeom = the_geom.asWkb()
        ogrgeom = ogr.CreateGeometryFromWkb(wkbgeom)
        if ogrgeom.GetGeometryName() == 'LINESTRING':
            pointsL = ogrgeom.GetPoints()
        points.append(pointsL[0])

        while currentdistance < length:
            # Get a point along the line at the current distance
            point = the_geom.interpolate(currentdistance)
            # Create a new tuple and get XY from the geometry
            Qpoint = point.asPoint()
            points.append((Qpoint.x(), Qpoint.y()))
            # Increase the distance
            currentdistance = currentdistance + distance

        points.append(pointsL[-1])
        return points


def output_xsections(xsects, outfile, elev, res, river,
                     banks, bankFields, flowlines, flowfield, conv):
    """
    Output the river network, including centerline for each reach
    and coordinates for all stations along each reach
    :rtype: convFact is units conversion factor
    """
    outfile.write("BEGIN CROSS-SECTIONS:")
    outfile.write(LineSep)
    outfile.write(LineSep)
    riverName = river.name().replace(" ", "")

    nXS = xsects.featureCount()
    nXS = int(nXS)

    # ~ loop for detecting reach length

    # ~ modify to keep distance from US and order on this attribute
    if int(river.featureCount()) == 1:
        XSstation = list()
        for riv_feat in river.getFeatures():
            riv_geom = riv_feat.geometry()
            riverLen = riv_geom.length()
            #TODO flowlines
            # get data for flowlines
            if flowlines is not None:
                LeftFeature = getGeomByAtt(flowlines, flowfield,"left")
                RightFeature = getGeomByAtt(flowlines, flowfield,"right")
                Lflow=LeftFeature.geometry()
                Rflow = RightFeature.geometry()

            if banks is not None:
                bankR = getGeomByAtt(banks, bankFields, "right")
                bankL = getGeomByAtt(banks, bankFields, "left")
                bankRgeom = bankR.geometry()
                bankLgeom = bankL.geometry()


            for XSfeature in xsects.getFeatures():
                XS_geom = XSfeature.geometry()
                pt_int = riv_geom.intersection(XS_geom)
                if banks is not None:
                    Lpt = bankLgeom.intersection(XS_geom)
                    Rpt = bankRgeom.intersection(XS_geom)
                else:
                    Lpt = 0
                    Rpt = 1

                distSP = pointInterpolate(riv_geom, pt_int.asPoint())

                if flowlines is not None:
                    Ldist = pointInterpolate(Lflow, Lpt.asPoint())
                    Rdist = pointInterpolate(Rflow, Rpt.asPoint())
                else:
                    Ldist = 0
                    Rdist = 1

                XSstation.append((distSP, XSfeature, Ldist, Rdist))

        # sorting tuple according to the distance US
        XSstationASC = sorted(XSstation, key=getKey)
        stationUS = [(i[0]) for i in XSstationASC]

        reachLen = riverLen - array(stationUS)
        reachLenUP = diff(array(stationUS))
        reachLenUP = nappend(reachLenUP, reachLen[-1])

        # flowlines
        if flowlines is not None:
            Lstation = [(i[2]) for i in XSstationASC]
            Rstation = [(i[3]) for i in XSstationASC]
            LreachLen = Lflow.length() - array(Lstation)
            RreachLen = Rflow.length() - array(Rstation)
            LreachLenUP = diff(array(Lstation))
            RreachLenUP = diff(array(Rstation))
            LreachLenUP = nappend(LreachLenUP,LreachLen[-1])
            RreachLenUP = nappend(RreachLenUP,RreachLen[-1])

    idXS = 0
    for XSfeature in [(i[1]) for i in XSstationASC]:
        outfile.write("CROSS-SECTION:")
        outfile.write(LineSep)
        outfile.write("STREAM ID: %s" % (riverName))
        outfile.write(LineSep)
        outfile.write("REACH ID: %s" % (riverName))
        outfile.write(LineSep)
        outfile.write("STATION: %.2f" % (reachLen[idXS] * conv))
        outfile.write(LineSep)
        outfile.write("NODE NAME: ")
        outfile.write(LineSep)
        # stationing of banks
        if banks is not None:
            bankList= list()
            for bank_feat in banks.getFeatures():
                bank_geom=bank_feat.geometry()
                XS_geom = XSfeature.geometry()
                pt_bnk=XS_geom.intersection(bank_geom)
                distBnk = pointInterpolate(XS_geom, pt_bnk.asPoint())
                bankList.append(distBnk / XS_geom.length() )

            outfile.write("BANK POSITIONS: {0:2f}, {1:2f}".format(min(bankList),max(bankList)))
            outfile.write(LineSep)
        if flowlines is not None:
            outfile.write("REACH LENGTHS: %.4f ,%.4f, %.4f " % (LreachLenUP[idXS] * conv, reachLenUP[idXS] * conv, RreachLenUP[idXS] * conv))
        else:
            outfile.write("REACH LENGTHS: %.4f ,%.4f, %.4f " % (reachLenUP[idXS]*conv, reachLenUP[idXS]*conv, reachLenUP[idXS]*conv))
            outfile.write(LineSep)
        outfile.write(
            "NVALUES:" + LineSep + "LEVEE POSITIONS:" + LineSep + "INEFFECTIVE POSITIONS: " + LineSep + "BLOCKED POSITIONS: " + LineSep)
        idXS += 1
        outfile.write("CUT LINE:")
        outfile.write(LineSep)
        points = getVertex(XSfeature)
        for point in points:
            outfile.write("\t%.4f, %.4f" % (point[0], point[1]))
            outfile.write(LineSep)
        outfile.write("SURFACE LINE:")
        outfile.write(LineSep)
        points = getVertex(XSfeature, res)
        for point in points:
            (X, Y, Z) = queryRaster(point, elev)
            p = QgsPoint(point[0], point[1])
            outfile.write("\t%.4f, %.4f, %.4f" % (X, Y, Z))
            outfile.write(LineSep)
        outfile.write("END:")
        outfile.write(LineSep)
        outfile.write(LineSep)

    outfile.write("END CROSS-SECTIONS:")
    outfile.write(LineSep)
    outfile.write(LineSep)
    outfile.write(LineSep)


def isInExtent(raster, point):
    rextent = raster.extent()
    xMin = rextent.xMinimum()
    yMin = rextent.yMinimum()
    xMax = rextent.xMaximum()
    yMax = rextent.yMaximum()

    if (xMin < point[0] < xMax) and (yMin < point[1] < yMax):
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


def getKey(item):
    return item[0]


def main(river, xsections, file_strin_path, rlayer, res, units, banks,bankFields,
         flowlines, flowfield,convFactor):
    # ~ res=1
    outfile = open(file_strin_path, 'w')
    output_headers(river, xsections, outfile,units)
    output_centerline(river, xsections, outfile, rlayer)
    output_xsections(xsections, outfile, rlayer, res, river,
                     banks,bankFields, flowlines, flowfield,convFactor)
    outfile.close()
    # test line endings
    f = open(file_strin_path, 'U')
    f.readline()
    if f.newlines == '\n':
        line_endings(file_strin_path)


def getGeomByAtt(vector, attribute,side='left'):
    request = QgsExpression(u'"{}" = \'{}\''.format(attribute, side) ) #outfile.write("STREAM ID: {}\n".format(riverName))
    vector_iter = vector.getFeatures( QgsFeatureRequest( request ) )
    feature_list = []
    for f in vector_iter:
        feature_list.append(f)
    if len(feature_list) == 1:
        return feature_list[0]
    else:
        return None




def uniqueAtt(layer,attribute):
    idx = layer.fieldNameIndex(attribute)
    values = layer.uniqueValues( idx )
    return values
