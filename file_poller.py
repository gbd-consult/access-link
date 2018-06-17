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
import configparser
from qgis.core import QgsMapLayerRegistry
from PyQt4.QtCore import QObject, QThread
from PyQt4.QtGui import QMessageBox

worker_thread = None
worker_object = None

# The config file is always located in the plugin directory
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.txt")


def write_settings(settings):
    """Write the settings into the text config file

    :param settings:
    :return:
    """

    config = configparser.ConfigParser()

    config.add_section('AccessLink')

    config.set('AccessLink', 'transfer_dir', settings["transfer_dir"])
    config.set('AccessLink', 'input_file', settings["input_file"])
    config.set('AccessLink', 'output_file', settings["output_file"])
    config.set('AccessLink', 'lock_file', settings["lock_file"])
    config.set('AccessLink', 'access_bin', settings["access_bin"])
    config.set('AccessLink', 'access_db', settings["access_db"])
    config.set('AccessLink', 'vector_layer', settings["vector_layer"])
    config.set('AccessLink', 'attribute_column', settings["attribute_column"])
    config.set('AccessLink', 'poll_time', settings["poll_time"])

    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)


def read_settings():
    """Read the settings from the text config file

    :return: settings
    """
    transfer_dir = None
    input_file = None
    output_file = None
    lock_file = None
    access_bin = None
    access_db = None
    vector_layer = None
    attribute_column = None
    poll_time = None

    config = configparser.ConfigParser()
    with open(CONFIG_FILE, 'r') as configfile:
        config.read_file(configfile)

        if config.has_section("AccessLink"):
            if config.has_option("AccessLink", "transfer_dir"):
                transfer_dir = config.get("AccessLink", "transfer_dir")
            if config.has_option("AccessLink", "input_file"):
                input_file = config.get("AccessLink", "input_file")
            if config.has_option("AccessLink", "output_file"):
                output_file = config.get("AccessLink", "output_file")
            if config.has_option("AccessLink", "lock_file"):
                lock_file = config.get("AccessLink", "lock_file")
            if config.has_option("AccessLink", "access_bin"):
                access_bin = config.get("AccessLink", "access_bin")
            if config.has_option("AccessLink", "access_db"):
                access_db = config.get("AccessLink", "access_db")
            if config.has_option("AccessLink", "vector_layer"):
                vector_layer = config.get("AccessLink", "vector_layer")
            if config.has_option("AccessLink", "attribute_column"):
                attribute_column = config.get("AccessLink", "attribute_column")
            if config.has_option("AccessLink", "poll_time"):
                poll_time = config.get("AccessLink", "poll_time")

    settings = dict(transfer_dir=transfer_dir,
                    input_file=input_file,
                    output_file=output_file,
                    lock_file=lock_file,
                    access_bin=access_bin,
                    access_db=access_db,
                    vector_layer=vector_layer,
                    attribute_column=attribute_column,
                    poll_time=poll_time)

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

        self.layer_reg = QgsMapLayerRegistry.instance()

    def check_settings(self):

        print("Load settings in file poll thread")

        settings = read_settings()

        self.input_file = os.path.join(settings["transfer_dir"], settings["input_file"])
        self.lock_file = os.path.join(settings["transfer_dir"], settings["lock_file"])
        self.vector_layer = settings["vector_layer"]
        self.attribute_column = settings["attribute_column"]
        if settings["poll_time"]:
            self.poll_time = float(settings["poll_time"])

        if os.path.exists(self.input_file) is False:
            print(u"Access-Link: Fehler: Die Input Datei <%s> wurde nicht gefunden." % self.input_file)
            #QMessageBox.warning(None, u"Access-Link: Warnung", u"Die Input Datei <%s> "
            #                                                   u"wurde nicht gefunden. " % self.input_file)
            return False

        if not self.vector_layer:
            return False

        self.layer = self.layer_reg.mapLayersByName(self.vector_layer)
        if self.layer and len(self.layer) > 0:
            self.layer = self.layer[0]
        if not self.layer:
            print(u"Access-Link: Fehler: Der Vektorlayer <%s> wurde nicht gefunden." % self.vector_layer)
            #QMessageBox.critical(None, u"Access-Link: Fehler",
            #                     u"Der Vektorlayer <%s> wurde nicht gefunden. "
            #                     u"Breche Datei-Polling ab." % self.vector_layer)
            #self.killed = True
            return False

        if self.layer:
            fields = self.layer.fields()
            attr_list = []
            for field in fields:
                attr_list.append(field.name())
            if self.attribute_column not in attr_list:
                QMessageBox.critical(None, u"Access-Link: Fehler", u"Der Vektorlayer <%s> hat keine Attributspalte <%s>."%
                                     (self.vector_layer,
                                      self.attribute_column))
                return False


            self.field_index = attr_list.index(self.attribute_column)

        print("Successfully read settings")
        return True

    def kill(self):
        self.killed = True

    def run(self):
        """The function that runs the infinite loop to poll the ascii file for changes. If the text file changes,
        then the content will be read and zoom to a feature with the same id.
        """
        # print("Run infinite loop")
        lock_count = 0

        load_state = self.check_settings()
        count = 0

        while True:
            count += 1

            if self.poll_time is not None:
                time.sleep(self.poll_time)
            else:
                time.sleep(4)

            if self.killed is True:
                print("Worker thread got killed")
                break
            # Check for configuration reload
            if count % 20 is 0:
                print("Check for config", count)
                load_state = self.check_settings()

            # If the setting are incorrect, then wait for three seconds and check again
            if load_state is False:
                print("Load state was False")
                time.sleep(4)
                load_state = self.check_settings()
                if load_state is False:
                    continue

            # Check the modification time
            if os.path.exists(self.input_file) is True:
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
                            QMessageBox.critical(None, u"Access-Link: Fehler", u"Die Lock-Datei <%s> verhindert das "
                                                                               u"Einlesen der Kataster ID. "
                                                                               u"Bitte löschen." % self.lock_file)
                        continue
                    # Read the vector id
                    self.mtime = new_mtime
                    feature_id = open(self.input_file, "r").read().strip()

                    expr = "\"%s\" = '%s'" % (self.attribute_column, feature_id)
                    # print("Expression", expr)

                    if self.layer:
                        self.layer.selectByExpression(expr)
                        qgis.utils.iface.setActiveLayer(self.layer)
                        # Zoom to the selected features
                        qgis.utils.iface.actionZoomToSelected().trigger()
            else:
                pass
                # print("Waiting for QGIS to initialize")
