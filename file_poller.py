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
import qgis
from qgis.core import QgsProject, QgsMapLayerRegistry
from PyQt4.QtCore import QObject, QThread
from PyQt4.QtGui import QMessageBox

worker_thread = None
worker_object = None


def load_settings():
    """Load all settings from the project file"""
    project = QgsProject.instance()
    if not project:
        QMessageBox.Critical(None, u"Fehler", u"Es existiert keine Projektdatei.")
        return None

    transfer_dir = project.readEntry("access_link", "transfer_dir")[0]
    input_file = project.readEntry("access_link", "input_file")[0]
    output_file = project.readEntry("access_link", "output_file")[0]
    lock_file = project.readEntry("access_link", "lock_file")[0]
    access_bin = project.readEntry("access_link", "access_bin")[0]
    access_db = project.readEntry("access_link", "access_db")[0]
    vector_layer = project.readEntry("access_link", "vector_layer")[0]
    attribute_column = project.readEntry("access_link", "attribute_column")[0]
    poll_time = project.readEntry("access_link", "poll_time")[0]
    enable_polling = project.readNumEntry("access_link", "enable_polling")[0]

    if True:
        transfer_dir = project.readEntry("access_link", "transfer_dir", "tmp")[0]
        input_file = project.readEntry("access_link", "input_file", "ExpAcc.txt")[0]
        output_file = project.readEntry("access_link", "output_file", "ImpAcc.txt")[0]
        lock_file = project.readEntry("access_link", "lock_file", "lock.log")[0]
        access_bin = project.readEntry("access_link", "access_bin", "/usr/bin/gedit")[0]
        access_db = project.readEntry("access_link", "access_db", "/tmp/access_db")[0]
        vector_layer = project.readEntry("access_link", "vector_layer", "ALKIS")[0]
        attribute_column = project.readEntry("access_link", "attribute_column", "id")[0]
        poll_time = project.readEntry("access_link", "poll_time", "0.5")[0]
        enable_polling = project.readNumEntry("access_link", "enable_polling", 1)[0]

    settings = dict(transfer_dir=transfer_dir,
                    input_file=input_file,
                    output_file=output_file,
                    lock_file=lock_file,
                    access_bin=access_bin,
                    access_db=access_db,
                    vector_layer=vector_layer,
                    attribute_column=attribute_column,
                    poll_time=poll_time,
                    enable_polling=enable_polling)

    return settings


def start_poll_worker():
    """Start the thread that polls the ascii file for changes and zooms to the vector id
    """
    global worker_thread, worker_object

    if worker_thread:
        stop_poll_worker()

    worker_object = Worker()
    worker_thread = QThread()

    worker_object.moveToThread(worker_thread)

    worker_thread.started.connect(worker_object.run)
    worker_thread.start()

    # print("Worker thread started")


def stop_poll_worker():
    """Stop the worker thread"""
    global worker_thread, worker_object
    if worker_thread:
        if worker_object:
            worker_object.kill()
            worker_object = None
        worker_thread.quit()
        worker_thread.wait()
        worker_thread.deleteLater()
        worker_thread = None

        # print("Worker thread stopped")


class Worker(QObject):
    """This is the class that polls the ascii file and triggers the zom to selected features"""

    def __init__(self):
        QObject.__init__(self)

        self.poll_time = None
        self.input_file = None
        self.vector_layer = None
        self.lock_file = None
        self.attribute_column = None
        self.killed = False
        self.mtime = None
        self.layer = None
        self.field_index = None
        self.layer_reg = None
        self.load()

    def load(self):

        # print("Load data for file poll thread")

        settings = load_settings()
        if settings is None:
            return

        self.layer_reg = QgsMapLayerRegistry.instance()

        self.input_file = os.path.join(settings["transfer_dir"], settings["input_file"])
        self.lock_file = os.path.join(settings["lock_file"], settings["input_file"])
        self.vector_layer = settings["vector_layer"]
        self.attribute_column = settings["attribute_column"]
        self.poll_time = float(settings["poll_time"])
        # print(settings)

        self.killed = False

        if os.path.isfile(self.input_file) is False:
            QMessageBox.Critical(None, u"Fehler", u"Die Input Datei <%s> wurde icht gefunden. "
                                                  u"Breche Datei-Polling ab." % self.input_file)
            self.killed = True
            return
        else:
            self.mtime = None

        self.layer = self.layer_reg.mapLayersByName(self.vector_layer)
        if self.layer and len(self.layer) > 0:
            self.layer = self.layer[0]
        if not self.layer:
            QMessageBox.Critical(None, u"Fehler",
                                 u"Der Vektorlayer <%s> wurde nicht gefunden. "
                                 u"Breche Datei-Polling ab." % self.vector_layer)
            self.killed = True
            return

        fields = self.layer.fields()
        attr_list = []
        for field in fields:
            attr_list.append(field.name())
        if self.attribute_column not in attr_list:
            QMessageBox.Critical(None, u"Fehler", u"Der Vektorlayer <%s> hat keine Attributspalte <%s>. "
                                                  u"Breche Datei-Polling ab." % (self.vector_layer,
                                                                                 self.attribute_column))
            self.killed = True
            return

        self.field_index = attr_list.index(self.attribute_column)

    def kill(self):
        self.killed = True

    def run(self):
        """The function that runs the infinite loop to poll the ascii file for changes. If the text file changes,
        then the content will be read and zoom to a feature with the same id.
        """
        # print("Run infinite loop")
        lock_count = 0

        while True:
            if self.poll_time is not None:
                time.sleep(self.poll_time)
            else:
                time.sleep(1)
                continue

            if self.killed is True:
                # print("Worker thread got killed")
                break

            # Check the modification time
            if os.path.isfile(self.input_file):
                new_mtime = os.path.getmtime(self.input_file)

                if self.mtime == new_mtime:
                    # print("Nothing to do")
                    continue
                else:
                    # print("File was changes", self.mtime, new_mtime)
                    # Wait until the lock file was removed
                    if os.path.isfile(self.lock_file):
                        lock_count += 1
                        # Show
                        if lock_count > 20:
                            lock_count = 0
                            QMessageBox.Critical(None, u"Fehler", u"Die Lock-Datei <%s> verhindert das "
                                                                  u"Einlesen der Kataster ID. "
                                                                  u"Bitte löschen." % self.lock_file)
                        continue
                    # Read the vector id
                    self.mtime = new_mtime
                    feature_id = open(self.input_file, "r").read().strip()

                    expr = "\"%s\" = '%s'" % (self.attribute_column, feature_id)
                    # print("Expression", expr)

                    self.layer.selectByExpression(expr)
                    qgis.utils.iface.setActiveLayer(self.layer)
                    # Zoom to the selected features
                    qgis.utils.iface.actionZoomToSelected().trigger()
            else:
                pass
                # print("Waiting for QGIS to initialize")
