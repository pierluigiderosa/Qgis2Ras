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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from RASout import main
from qgis.utils import showPluginHelp
from qras_dialog_base import Ui_Qgis2RasDialogBase




class Qgis2RasDialog(QDialog, Ui_Qgis2RasDialogBase):
    def __init__(self, iface): 
        """Constructor."""
        #~ super(Qgis2RasDialog, self).__init__(parent)
        QDialog.__init__(self)
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
        # noinspection PyArgumentList
        self.plugin_builder_path = os.path.dirname(__file__)
        
        #connections
        QObject.connect(self.browseBtn, SIGNAL( "clicked()" ), self.writeTxt)
        self.button_box.helpRequested.connect(self.show_help)
        self.button_box.accepted.connect(self.runProfile)
        
    def show_help(self):
        """Display application help to the user."""
        help_file = 'file:///%s/help/index.html' % self.plugin_builder_path
        # For testing path:
        #~ QMessageBox.information(None, 'Help File', help_file)
        # noinspection PyCallByClass,PyTypeChecker
        QDesktopServices.openUrl(QUrl(help_file))


    def Message(self,testo):
        str(testo)
        QMessageBox.information(self.iface.mainWindow(),"press OK", testo)
        
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
        #~ For raster
        DemIndex = self.rasterCombo.currentIndex()
        self.dem = self.rasterCombo.itemData(DemIndex)
        # I take the X Y resolution supposing its a square pixel
        resX = self.dem.rasterUnitsPerPixelX()
        resY = self.dem.rasterUnitsPerPixelY()
        resolution = (resX**2+resY**2)**0.5
        
        self.textfile = self.lineEdit.text()
        self.textfile = str(self.textfile)

        main(self.river,self.XSection,self.textfile,self.dem,resolution)

    def writeTxt(self):
        fileName = QFileDialog.getSaveFileName(self, 'Save RAS file', 
                                        "", "SDF (*.sdf);;All files (*)")
        fileName = os.path.splitext(str(fileName))[0]+'.sdf'
        self.lineEdit.setText(fileName)
        self.textfile = fileName
