# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AccessLink
                                 A QGIS plugin
 Zeigespezifische Vektorobjekte eines Layers an die in einer Access Datenbank beschrieben werden.
                             -------------------
        begin                : 2018-04-04
        copyright            : (C) 2018 by GBD GmbH
        email                : gebbert@gbd-consult.de
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
    """Load AccessLink class from file AccessLink.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .access_link import AccessLink
    return AccessLink(iface)
