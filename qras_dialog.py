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

from qgis._gui import QgsMapLayerProxyModel

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

    def trad(self, message):

        return QCoreApplication.translate('Qgis2Ras', message)

    def show_help(self):
        """Display application help to the user."""
        help_file = 'file:///%s/help/build/html/index.html' % self.plugin_builder_path
        # For testing path:
        # ~ QMessageBox.information(None, 'Help File', help_file)
        # noinspection PyCallByClass,PyTypeChecker
        QDesktopServices.openUrl(QUrl(help_file))

    def Message(self, text):
        from qgis.gui import QgsMessageBar
        str(text)

        self.iface.messageBar().pushMessage("QRAS", text, level=QgsMessageBar.INFO)
        # QMessageBox.information(self.iface.mainWindow(), "press OK", testo)

    def setup_gui(self):
        """ Function to combos creation """
        self.vectorComboQgs.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.XSComboQgs.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.rasterComboQgs.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.banksComboQgs.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.banksComboQgs.hide()
        self.flowComboQgs.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.flowComboQgs.hide()
        for item in ['meters','feet', 'miles', 'kilometers']:
            self.stationCombo.addItem(item)
        #fill with null additional info
        self.banksComboQgs.hide()
        self.flowComboQgs.hide()
        self.flowfieldsComboQgs.hide()
        self.bankfieldsComboQgs.hide()



    def runProfile(self):
        # ~ get the layer from the combos:
        # ~ For XSection
        self.XSection = self.XSComboQgs.currentLayer()
        # ~ For river
        self.river = self.vectorComboQgs.currentLayer()
        # ~ For banks
        if self.banksComboQgs.isHidden:
            self.banks = None
        else:
            self.banks = self.banksComboQgs.currentLayer()
         # ~ For flowlines
        if self.flowComboQgs.isHidden:
            self.flowlines = None
        else:
            self.flowlines = self.flowComboQgs.currentLayer()
        # ~ For raster
        self.dem = self.rasterComboQgs.currentLayer()
        # I take the X Y resolution supposing its a square pixel
        resX = self.dem.rasterUnitsPerPixelX()
        resY = self.dem.rasterUnitsPerPixelY()
        resolution = (resX ** 2 + resY ** 2) ** 0.5

        self.riverField = self.riverNameFieldComboQgs.currentField()
        self.reachField = self.reachNameFieldComboQgs.currentText()
        self.flowFields = self.flowfieldsComboQgs.currentText()
        self.bankFields = self.bankfieldsComboQgs.currentText()


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
             resolution, units, self.banks, self.bankFields, self.flowlines,
             self.flowFields, convFactor)

        self.Message('elaborazione terminata')

    def writeTxt(self):
        fileName = QFileDialog.getSaveFileName(self, 'Save RAS file',
                                               "", "SDF (*.sdf);;All files (*)")
        fileName = os.path.splitext(str(fileName))[0] + '.sdf'
        self.lineEdit.setText(fileName)
        self.textfile = fileName
