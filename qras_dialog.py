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

import os

from PyQt4 import  uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from tools.RASout import main



FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qras_dialog_base.ui'))


class Qgis2RasDialog(QDialog, FORM_CLASS):
    def __init__(self, iface,parent=None):
        """Constructor."""
        super(Qgis2RasDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        self.iface = iface
        #~ setup personal gui
        self.setup_gui()
        
        #general variables
        self.textfile = None
        self.XSection = None
        self.river = None
        self.dem = None
        
        #connections
        QObject.connect(self.execute, SIGNAL( "clicked()" ), self.runProfile)
        QObject.connect(self.browseBtn, SIGNAL( "clicked()" ), self.writeTxt)
        
        
    def setup_gui(self):
        """ Function to combos creation """
        self.vectorCombo.clear()
        self.XSCombo.clear()
        self.rasterCombo.clear()
        for layer in self.iface.legendInterface().layers():
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QGis.Line:
                self.vectorCombo.addItem( layer.name(), layer )
                self.XSCombo.addItem( layer.name(), layer )
            if layer.type() == QgsMapLayer.RasterLayer:
                self.rasterCombo.addItem( layer.name(), layer )


        

    def runProfile(self):
        #~ get the layer from the combos:
        #~ For XSection
        XSindex = self.XSCombo.currentIndex()
        self.index = XSindex
        self.XSection = self.XSCombo.itemData(XSindex)
        #~ For river
        RivIndex = self.vectorCombo.currentIndex()
        self.river = self.vectorCombo.itemData(RivIndex)
        #~ For grraster
        DemIndex = self.rasterCombo.currentIndex()
        self.dem = self.rasterCombo.itemData(DemIndex)
        
        self.textfile = self.lineEdit.text()
        self.textfile = str(self.textfile)

        main(self.river,self.XSection,self.textfile)

    def writeTxt(self):
        fileName = QFileDialog.getSaveFileName(self, 'Save RAS file', 
                                        "", "SDF (*.sdf);;All files (*)")
        fileName = os.path.splitext(str(fileName))[0]+'.sdf'
        self.lineEdit.setText(fileName)
        self.textfile = fileName
