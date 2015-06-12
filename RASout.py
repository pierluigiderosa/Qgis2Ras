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
                        QgsGeometry,QgsPoint,QgsRaster,QgsRectangle, QgsDataSourceURI, QgsVectorLayerImport, QgsMapLayerRegistry)
import datetime
from PyQt4.QtCore import QFileInfo
from osgeo import ogr,_ogr
from lengthalongline import pointInterpolate
from numpy import array,diff
from numpy import append as nappend
from os import linesep as LineSep  

from pyspatialite import dbapi2 as db

class spatialiteManager(object):
    def __init__(self, dbase):
        # get a connection, if a connect cannot be made an exception will be raised here
        self.conn = db.connect(dbase)
        self.cur = self.conn.cursor()

    def createDB(self):
        # initializing Spatial MetaData
        # using v.2.4.0 this will automatically create
        # GEOMETRY_COLUMNS and SPATIAL_REF_SYS
        sql = 'SELECT InitSpatialMetadata()'
        self.query(sql)

    def query(self, sql):
        self.cur.execute(sql)
        self.conn.commit()
        return self.cur
        
    def spatialIndex(self, table, geomCol):
        sql = """SELECT CreateSpatialIndex('{0}', '{1}')""".format(table, geomCol)
        self.cur.execute(sql)
        self.conn.commit()
        
    def removeSpatialIndex(self, table, geomCol):
        sql = """SELECT DisableSpatialIndex('{0}', '{1}')""".format(table, geomCol)
        self.cur.execute(sql)
        self.conn.commit()
        sql = """DROP TABLE idx_{}_{}""".format(table, geomCol)
        self.cur.execute(sql)
        self.conn.commit()       

    def dropTables(self,tables):
        for i in tables:
            sql = '''DROP TABLE IF EXISTS {}'''.format(i)
            self.cur.execute(sql)
            self.conn.commit()        
        self.cur.execute('VACUUM')
        self.conn.commit()
        
    def discardGeom(self, table, geomCol):
        sql = """SELECT DiscardGeometryColumn('{}', '{}')""".format(table, geomCol)
        self.cur.execute(sql)
        self.conn.commit()

    def __del__(self):
        print 'close db'
        self.conn.close() 

def output_headers(dbase, rlayer, outfile, units):
    """
    Prepare the output sdf file, and add header section
    """
    dbmgr = spatialiteManager(dbase)
    # Start header section
    dt = str(datetime.date.today())

    outfile.write("#QRAS geometry create on: " + dt + LineSep)
    outfile.write("BEGIN HEADER:\n")
    if units == 'feet':
        units = "US CUSTOMARY"
    else:
        units = 'METRIC'

    outfile.write("DTM TYPE: GRID\n")
    outfile.write("DTM: {}\n".format(rlayer.name()))
    outfile.write("STREAM LAYER: river\n")
    
    # write out how many reaches and cross sections
    sql = """SELECT COUNT(*) FROM river"""
    
    num_reaches = dbmgr.query(sql).fetchall()[0][0]
    outfile.write("NUMBER OF REACHES: {}\n".format(num_reaches))
    outfile.write("CROSS-SECTION LAYER: xs\n")
    sql = """SELECT COUNT(*) FROM xs"""
    num_xsects = dbmgr.query(sql).fetchall()[0][0]
    outfile.write("NUMBER OF CROSS-SECTIONS: {}\n".format(num_xsects))
    outfile.write("MAP PROJECTION: \nPROJECTION ZONE: \nDATUM: \nVERTICAL DATUM: \n")


    # write out the extents
    sql = """SELECT MbrMinX(the_geom),MbrmaxX(the_geom), MbrMinY(the_geom), MbrMaxY(the_geom)  from river"""
    xmin, xmax, ymin, ymax = dbmgr.query(sql).fetchall()[0]

    outfile.write("BEGIN SPATIAL EXTENT:\n")
    outfile.write("XMIN: {}\n".format(xmin))
    outfile.write("YMIN: {}\n".format(ymin))
    outfile.write("XMAX: {}\n".format(xmax))
    outfile.write("YMAX: {}\n".format(ymax))
    outfile.write("END SPATIAL EXTENT:\n")
    outfile.write("END HEADER:\n\n\n")




def output_centerline(dbase, rlayer, outfile):
    """
    Output the river network, including centerline for each reach
    and coordinates for all stations along each reach
    """
    dbmgr = spatialiteManager(dbase)
    outfile.write("BEGIN STREAM NETWORK:\n")
#    # TODO: Add junctions
    
    # Begin with the list of feature in reach
    sql = """SELECT *, asWkt(the_geom) FROM river"""
    features = dbmgr.query(sql)
    for feature in features:
        riverName = feature[1]
        reachName = feature[2]
        us_junction = feature[3]
        ds_junction = feature[4]
        us_sa_2d = feature[5]
        ds_sa_2d = feature[6]
        the_geom = QgsGeometry.fromWkt(str(feature[-1]))
        points = getVertex(the_geom)

        outfile.write("\nREACH:\n")
        outfile.write("STREAM ID: {}\n" .format(riverName) )
        outfile.write("REACH ID: {}\n" .format(reachName))
        outfile.write("FROM POINT: 0\n")
        outfile.write("TO POINT: 1\n")
        outfile.write("CENTERLINE:\n")  # Now the actual points along centerlinep)
        for point in points:
            (X,Y,Z) = queryRaster(point,rlayer)
            outfile.write( "\t%.4f, %.4f, %.6f, " %(X,Y,Z)) 
            outfile.write(LineSep)
        outfile.write("END:\n\n")

    outfile.write("END STREAM NETWORK:\n\n\n") 
    

def queryRaster(point,raster):
    p = QgsPoint(point[0],point[1])
    if isInExtent(raster,point):
        provider=raster.dataProvider()		    			    
        identifyresult = provider.identify(p,QgsRaster.IdentifyFormatValue,QgsRectangle())
        results = identifyresult.results()
        val = results[1]
        return point[0],point[1],val

def getVertex(the_geom,distance=0):
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
    
def output_xsections(dbase, outfile, rlayer, res):
    """
    Output the river network, including centerline for each reach
    and coordinates for all stations along each reach
    """
    dbmgr = spatialiteManager(dbase)
    outfile.write("BEGIN CROSS-SECTIONS:\n\n")	

    
    sql = """SELECT *, AsWKT(the_geom) FROM xs ORDER BY river, river_station DESC"""
    features = dbmgr.query(sql)
    for feature in features:
        riverName = feature[1]
        reachName = feature[2]
        station = feature[3]
        lengthLOB = feature[4]
        lengthChannel = feature[5]
        lengthROB = feature[6]
        lBank = feature[9]
        rBank = feature[10]   
        lLevee = feature[11] 
        lLeveeElev = feature[12] 
        rLevee = feature[13]
        rLeveeElev = feature[14] 
        the_geom = QgsGeometry.fromWkt(str(feature[-1]))
        
        outfile.write("CROSS-SECTION:\n")
        outfile.write("STREAM ID: %s\n" % (riverName))
        outfile.write("REACH ID: %s\n" % (reachName))
        outfile.write("STATION: %s\n" % (station))
        if lBank and rBank:
            outfile.write("BANK POSITIONS: {}, {}\n".format(lBank,rBank))
        outfile.write(LineSep)
        outfile.write("REACH LENGTHS: {0:.4f} ,{1:.4f}, {2:.4f}\n".format (lengthROB,lengthChannel,lengthLOB)) 
        
        outfile.write("CUT LINE:\n")
        points = getVertex(the_geom)
        for point in points:
            outfile.write("\t%.4f, %.4f\n" %(point[0],point[1]))
        outfile.write("SURFACE LINE:\n")
        points = getVertex(the_geom,res)
        for point in points:
            (X,Y,Z) = queryRaster(point,rlayer)
            outfile.write( "\t{0:.4f}, {1:.4f}, {2:.4f}\n" .format(X,Y,Z)) 
        outfile.write("END:\n\n")

    outfile.write("END CROSS-SECTIONS:\n\n\n")


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

def getKey(item):
    return item[0]
    
def loadVectorsIntoDB(layers, dbase, customCRSFlag, srid):
    #database import options
    options = {}
    options['overwrite'] = True
    options['forceSinglePartGeometryType'] = True
    uri = QgsDataSourceURI()
    uri.setDatabase(dbase)
    for layer in layers:
        uri.setDataSource('',layer.name(),'the_geom')
        ret, errMsg = QgsVectorLayerImport.importLayer(layer, uri.uri(), 'spatialite', layer.crs(), False, False, options)
        print uri.uri()
        print errMsg
    if customCRSFlag:
        pass
#        dbmgr = spatialiteManager(dbase)
#        sql = """UPDATE geometry_columns SET srid = {}""".format(srid)
#        dbmgr.query(sql)

#def loadVectorsFromDB(layerName, dbase):
#    uri = QgsDataSourceURI()
#    uri.setDatabase(dbase)
#    uri.setDataSource('', layerName, 'the_geom')
#    vlayer = QgsVectorLayer(uri.uri(), layerName, 'spatialite')
#    QgsMapLayerRegistry.instance().addMapLayer(vlayer)
#    return vlayer


def createDB(layer, dbase, srid):
    # setup spatilite manager
    dbmgr = spatialiteManager(dbase)
    # create database
    dbmgr.createDB()
    
    # check if projection doesn't exist in spatialite database
    sql = """SELECT COUNT(*) FROM spatial_ref_sys WHERE srid = {}""".format(srid)
    count = dbmgr.query(sql).fetchall()[0][0]
    if count == 0: # add def. if needed
        #not needed...doesn't seem to be supported in spatilite
#        sql = """INSERT INTO spatial_ref_sys(srid, auth_name, auth_srid, ref_sys_name, proj4text, srtext) VALUES({0}, '', '', '{3}', '{1}', '{2}')""".format(srid, layer.crs().toProj4(), layer.crs().toWkt(), layer.crs().description())
#        dbmgr.query(sql)
        customCRSFlag = True  
    else:
        customCRSFlag = False
    return customCRSFlag

def attributeRiver(riverLayer, riverField, reachField, dbase, srid):
    dbmgr = spatialiteManager(dbase)
    # create table
    sql = """CREATE TABLE river (id INTEGER PRIMARY KEY, river TEXT, reach TEXT, us_junction TEXT, ds_junction TEXT, "us_sa-2d" TEXT, "ds_sa-2d" TEXT, mergedGeom NULL)"""
    dbmgr.query(sql)
    # add geom column
    sql = """SELECT AddGeometryColumn('river', 'the_geom', {}, 'LINESTRING', 'XY')""".format(srid)
    dbmgr.query(sql)
    sql = """INSERT INTO river SELECT NULL as id, {0} as river, {1} as reach, NULL as us_junction, NULL as ds_junction, NULL as "us_sa-2d", NULL as "ds_sa-2d", the_geom, the_geom FROM {2}""".format(riverField, reachField, riverLayer)
    dbmgr.query(sql)
    dbmgr.spatialIndex('river','the_geom')
    sql = """select river, count(*), asWkt(st_lineMerge(st_union(the_geom))) FROM river GROUP By river"""
    result = dbmgr.query(sql).fetchall()
    for river, count, mergedGeom in result:
        if count>1:
            sql = """UPDATE river SET mergedGeom = st_lineMerge(ST_GeomFromText('{}')) WHERE river LIKE '{}'""".format(mergedGeom, river)
            dbmgr.query(sql)
    dbmgr.discardGeom(riverLayer, 'the_geom')
    dbmgr.dropTables([riverLayer])
#    slRiverLayer = loadVectorsFromDB('river', dbase)
#    return slRiverLayer

def attributeXS(xsLayer, dbase, srid, convFactor):
    dbmgr = spatialiteManager(dbase)
    # create table
    sql = """CREATE TABLE xs (id INTEGER PRIMARY KEY, river TEXT, reach TEXT, river_station REAL, lengthLOB NULL, lengthChannel NULL, lengthROB NULL, contractionCoeff NULL, expansionCoeff NULL, lBank NULL, rBank NULL, lLevee NULL, lLeveeElev NULL, rLevee NULL, rLeveeElev NULL)"""
    dbmgr.query(sql)
    # add geom column
    sql = """SELECT AddGeometryColumn('xs', 'the_geom', {}, 'LINESTRING', 'XY')""".format(srid)
    dbmgr.query(sql)
    #add spatial index before spaitial query
    dbmgr.spatialIndex('{}'.format(xsLayer),'the_geom')
    # add in stationing, reach names etc....
    sql = """INSERT INTO xs SELECT null as id, r.river, r.reach, ST_line_locate_point(st_reverse(r.mergedGeom), st_intersection(r.mergedGeom, xs.the_geom))*ST_length(r.mergedGeom) as river_station, null as lengthLOB, null as lengthChannel, null as lengthROB, null as contractionCoeff, null as expansionCoeff, null as lBank, null as rBank, null as lLevee, null as lLeveeElev, null as rLevee, null as rLeveeElev, xs.the_geom
    FROM river r, {} xs 
    WHERE ST_Intersects(r.the_geom, xs.the_geom)""".format(xsLayer)
    dbmgr.query(sql)
    dbmgr.spatialIndex('xs','the_geom')
    #remove spatial index and drop table
    dbmgr.removeSpatialIndex('{}'.format(xsLayer),'the_geom')
    dbmgr.discardGeom(xsLayer, 'the_geom')
    dbmgr.dropTables([xsLayer])
    
    # update xs lengths
    sql = """SELECT q.id, q.river, q.reach, q.river_station, q.river_station - coalesce((select r.river_station FROM xs as r where r.river = q.river and r.river_station < q.river_station order by r.river_station DESC limit 1), q.river_station) as length FROM xs as q"""
    result = dbmgr.query(sql).fetchall()
    for pkid, riverName, reachName, river_station, length in result:
        sql = """UPDATE xs SET lengthChannel = {0}, lengthROB = {0}, lengthLOB = {0} WHERE id = {1} AND river LIKE '{2}' and reach LIKE '{3}'""".format(length, pkid, riverName, reachName)
        dbmgr.query(sql)
        
    # update last row for each river
    dbmgr.query("""UPDATE xs SET lengthChannel = river_station, lengthROB = river_station, lengthLOB = river_station WHERE lengthChannel = 0""")
    dbmgr.query("""UPDATE xs SET river_station = cast(round(river_station*{}, 4) as text)""".format(convFactor))
    
#    slXSLayer = loadVectorsFromDB('xs', dbase)
#    return slXSLayer
     
    
                

def main(river,xsections,file_strin_path,rlayer,res, dbase, riverField, reachField, units, convFactor):
    srid = river.crs().authid()[5:]
    customCRSFlag = createDB(river, dbase, srid)
    # add to fix customCRS issues...doesn't seem to be supported in spatilite
    if customCRSFlag:
        srid = 0
    loadVectorsIntoDB([river, xsections], dbase, customCRSFlag, srid)
    attributeRiver(str(river.name()), riverField, reachField, dbase, srid)
    attributeXS(str(xsections.name()), dbase, srid, convFactor)
    
    
    outfile = open(file_strin_path, 'w')
    output_headers(dbase, rlayer, outfile, units)
    output_centerline(dbase, rlayer, outfile)
    output_xsections(dbase, outfile, rlayer, res)
    outfile.close()
    # test line endings
    f = open(file_strin_path, 'U')
    f.readline()
    if f.newlines == '\n':
        line_endings(file_strin_path)

