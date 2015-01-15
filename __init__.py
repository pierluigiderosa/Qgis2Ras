# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2Ras
                                 A QGIS plugin
 Qgis 2 RAS preprocessor
                             -------------------
        begin                : 2014-12-18
        copyright            : (C) 2014 by Pierluigi De Rosa
        email                : pierluigi.derosa@gfosservices.it
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load Qgis2Ras class from file Qgis2Ras.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .qras import Qgis2Ras
    return Qgis2Ras(iface)
