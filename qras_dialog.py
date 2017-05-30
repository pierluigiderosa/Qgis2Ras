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
from PyQt4 import uic
from qgis.core import *
from RASout import main

from qgis.utils import showPluginHelp


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qras_dialog_base.ui'))




class Qgis2RasDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        """Constructor."""
        # ~ super(Qgis2RasDialog, self).__init__(parent)
        QDialog.__init__(self)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.iface = iface
        # ~ setup personal gui
        self.setup_gui()



        # general variables
        self.textfile = None
        self.XSection = None
        self.river = None
        self.dem = None
        # noinspection PyArgumentList
        self.plugin_builder_path = os.path.dirname(__file__)

        # connections
        self.browseBtn.clicked.connect(self.writeTxt)
        self.button_box.helpRequested.connect(self.show_help)
        self.button_box.accepted.connect(self.runProfile)
        self.vectorCombo.currentIndexChanged.connect(lambda: self.reloadFields())
        self.flowCombo.currentIndexChanged.connect(lambda: self.reloadFields())
        self.banksCombo.currentIndexChanged.connect(lambda: self.reloadFields())

    def trad(self, message):

        return QCoreApplication.translate('Qgis2Ras', message)

    def show_help(self):
        """Display application help to the user."""
        help_file = 'file:///%s/help/build/html/index.html' % self.plugin_builder_path
        # For testing path:
        # ~ QMessageBox.information(None, 'Help File', help_file)
        # noinspection PyCallByClass,PyTypeChecker
        QDesktopServices.openUrl(QUrl(help_file))

    def Message(self, testo):
        from qgis.gui import QgsMessageBar
        str(testo)

        self.iface.messageBar().pushMessage("QRAS", testo, level=QgsMessageBar.INFO)
        # QMessageBox.information(self.iface.mainWindow(), "press OK", testo)

    def setup_gui(self):
        """ Function to combos creation """
        self.vectorCombo.clear()
        self.XSCombo.clear()
        self.rasterCombo.clear()
        self.banksCombo.clear()
        for item in ['meters','feet', 'miles', 'kilometers']:
            self.stationCombo.addItem(item)
        #fill with null additional info
        self.banksCombo.addItem('not used',None)
        self.flowCombo.addItem('not used',None)
        for layer in self.iface.legendInterface().layers():
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QGis.Line:
                self.vectorCombo.addItem(layer.name(), layer)
                self.XSCombo.addItem(layer.name(), layer)
                self.flowCombo.addItem(layer.name(), layer)
                self.banksCombo.addItem(layer.name(), layer)
            if layer.type() == QgsMapLayer.RasterLayer:
                self.rasterCombo.addItem(layer.name(), layer)
        self.reloadFields()

    def reloadFields(self):
        '''
        reload fields attributes for river, reach and flowlines values
        '''
        def getFieldNames(layer):
            fields = layer.pendingFields()
            fieldNames = []
            for field in fields:
                if not field.name() in fieldNames:
                    fieldNames.append(unicode(field.name()))
            return fieldNames

        self.riverNameFieldCombo.clear()
        self.reachNameFieldCombo.clear()
        self.flowfieldsCombo.clear()
        self.bankfieldsCombo.clear()

        self.river = self.getLayer(self.vectorCombo)
        self.flowlines = self.getLayer(self.flowCombo)
        self.banks = self.getLayer(self.banksCombo)
        try:
            self.riverNameFieldCombo.addItems(getFieldNames(self.river))
            self.reachNameFieldCombo.addItems(getFieldNames(self.river))
            self.flowfieldsCombo.addItems(getFieldNames(self.flowlines))
            self.bankfieldsCombo.addItems(getFieldNames(self.banks))
        except:
            pass

    def getLayer(self, combo):
        idx = combo.currentIndex()
        layer = combo.itemData(idx)
        return layer

    def runProfile(self):
        # ~ get the layer from the combos:
        # ~ For XSection
        self.XSection = self.getLayer(self.XSCombo)
        # ~ For river
        self.river = self.getLayer(self.vectorCombo)
        # ~ For banks
        self.banks = self.getLayer(self.banksCombo)
         # ~ For flowlines
        self.flowlines = self.getLayer(self.flowCombo)
        # ~ For raster
        self.dem = self.getLayer(self.rasterCombo)
        # I take the X Y resolution supposing its a square pixel
        resX = self.dem.rasterUnitsPerPixelX()
        resY = self.dem.rasterUnitsPerPixelY()
        resolution = (resX ** 2 + resY ** 2) ** 0.5

        self.riverField = str(self.riverNameFieldCombo.currentText())
        self.reachField = str(self.reachNameFieldCombo.currentText())
        self.flowFields = str(self.flowfieldsCombo.currentText())
        self.bankFields = str(self.bankfieldsCombo.currentText())

        # generate conversion factor for river stationing
        units = str(self.stationCombo.currentText())
        if units == 'feet':
            convFactor = 1.0 * 3.2808
        elif units == 'miles':
            convFactor = 1.0 / 1609,34
        elif units == 'meters':
            convFactor = 1.0
        else:
            convFactor = 1.0 / 1000.0
        if self.rbFt.isChecked():
            convFactor = convFactor / 3.2808
        self.textfile = self.lineEdit.text()
        self.textfile = str(self.textfile)

        main(self.river, self.XSection, self.textfile, self.dem,
             resolution,units, self.banks,self.bankFields, self.flowlines, self.flowFields,convFactor)

        self.Message('elaborazione terminata')

    def writeTxt(self):
        fileName = QFileDialog.getSaveFileName(self, 'Save RAS file',
                                               "", "SDF (*.sdf);;All files (*)")
        fileName = os.path.splitext(str(fileName))[0] + '.sdf'
        self.lineEdit.setText(fileName)
        self.textfile = fileName
