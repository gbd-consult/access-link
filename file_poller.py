# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AccessLinkFilePoller
                                 A QGIS plugin
 Zeige spezifische Vektorobjekte eines Layers an die in einer Access Datenbank beschrieben werden.
                             -------------------
        begin                : 2018-04-01
        git sha              : $Format:%H$
        copyright            : (C) 2018 by GBD GmbH
        email                : gebbert@gbd-consult.de
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
import time
from qgis.gui import QgisInterface
from qgis.core import QgsProject, QgsMapLayerRegistry, QgsVectorLayer
from PyQt4.QtCore import QObject, QThread
from PyQt4.QtGui import QMessageBox

worker_thread = None
worker_object = None


def load_settings(project):
    """Load all settings from the project file"""
    ascii_file = project.readEntry("access_link", "ascii_file", "/tmp/ascii.txt")[0]
    lock_file = project.readEntry("access_link", "lock_file", "/tmp/lock.log")[0]
    batch_file = project.readEntry("access_link", "batch_file", "/tmp/script.vba")[0]
    vector_layer = project.readEntry("access_link", "vector_layer", "ALKIS")[0]
    attribute_column = project.readEntry("access_link", "attribute_column", "id")[0]
    poll_time = project.readEntry("access_link", "poll_time", "0.5")[0]
    enable_polling = project.readNumEntry("access_link", "enable_polling", 1)[0]

    settings = dict(ascii_file=ascii_file,
                    lock_file=lock_file,
                    batch_file=batch_file,
                    vector_layer=vector_layer,
                    attribute_column=attribute_column,
                    poll_time=poll_time,
                    enable_polling=enable_polling)

    return settings


def start_poll_worker(project, iface):
    """Start the thread that polls the ascii file for changes and zooms to the vector id

    :param project: The project file that contains the settings for file polling
    :param iface:
    :return:
    """
    global worker_thread, worker_object

    if worker_thread:
        stop_poll_worker()

    worker_object = Worker(project=project, iface=iface)
    worker_thread = QThread()

    worker_object.moveToThread(worker_thread)

    worker_thread.started.connect(worker_object.run)
    worker_thread.start()
    print("Worker thread started")


def stop_poll_worker():
    """Stop the worker thread"""
    global worker_thread, worker_object
    if worker_thread:
        if worker_object:
            worker_object.kill()
        worker_thread.quit()
        worker_thread.wait()
        worker_thread.deleteLater()
        worker_thread = None

        print("Worker thread stopped")


class Worker(QObject):
    """This is the class that polls the ascii file and updates the zoom of the canvas"""

    def __init__(self, project, iface):
        """The function that runs the infinite loop to poll a file for changes. If the text file changes,
        then the content will be read and zoom to a feature with the same id.

        :param project:
        :param iface:
        :return:
        """
        QObject.__init__(self)
        settings = load_settings(project)
        self.layer_reg = QgsMapLayerRegistry.instance()
        self.iface = iface

        self.mtime = None

        print("Settings", settings)

        self.ascii_file = settings["ascii_file"]
        self.vector_layer = settings["vector_layer"]
        self.lock_file = settings["lock_file"]
        self.attribute_column = settings["attribute_column"]
        self.poll_time = float(settings["poll_time"])
        print("Poll time", self.poll_time)

        self.killed = False

        if os.path.isfile(self.ascii_file) is False:
            QMessageBox.warning(None, u"Error", u"Die ASCII Datei wurde icht gefunden. Breche Datei-Polling ab.")
            self.killed = True
            return
        else:
            self.mtime = os.path.getmtime(self.ascii_file)

        self.layer = self.layer_reg.mapLayersByName(self.vector_layer)
        if self.layer and len(self.layer) > 0:
            self.layer = self.layer[0]
        if not self.layer:
            QMessageBox.warning(None, u"Error", u"Der Vektorlayer <%s> wurde nicht gefunden. Breche Datei-Polling ab."%self.vector_layer)
            self.killed = True
            return

        fields = self.layer.fields()
        attr_list = []
        for field in fields:
            attr_list.append(field.name())
        print(attr_list)
        if self.attribute_column not in attr_list:
            QMessageBox.warning(None, u"Error", u"Der Vektorlayer <%s> hat keine Attributspalte <%s>. "
                                        u"Breche Datei-Polling ab."%(self.vector_layer, self.attribute_column))
            self.killed = True
            return

        self.field_index = attr_list.index(self.attribute_column)

    def kill(self):
        self.killed = True

    def run(self):
        """The infinite loop that does all the polling and zooming

        :return:
        """
        while True:

            time.sleep(self.poll_time)

            if self.killed is True:
                print("Worker thread got killed")
                break

            # Check the modification time
            new_mtime = os.path.getmtime(self.ascii_file)

            if self.mtime == new_mtime:
                print("Nothing changed")
                continue
            else:
                print("File was changes", self.mtime, new_mtime)
                self.mtime = new_mtime
