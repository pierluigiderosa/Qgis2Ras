# -*- coding: utf-8 -*-
from qgis.core import *
import qgis.utils
from pyspatialite import dbapi2 as db
import timeit

start = timeit.default_timer()

dbase='/home/pierluigi/Scrivania/db.sqlite'
conn = db.connect(dbase)
cur = conn.cursor()

sql = 'SELECT InitSpatialMetadata(1)'
cur.execute(sql)
conn.commit()

stop = timeit.default_timer()

print stop - start 
