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
from qgis.core import QgsMapLayerRegistry, QgsMessageLog
from PyQt4.QtCore import QObject, QThread, SIGNAL
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

    QgsMessageLog.logMessage("Access-Link: Read Access Link settings")

    transfer_dir = "C:\Users\Gebbert\Documents"
    input_file = "ImpAcc.txt"
    output_file = "ExpAcc.txt"
    lock_file = "lock.log"
    access_bin = "C:/Users/Gebbert/Documents/start_something.bat"
    access_db = "C:/Users/Gebbert/Documents/ImpAcc.txt"
    vector_layer = "Test_sie02_f_"
    attribute_column = "OBJID"
    poll_time = "0.5"

    if os.path.exists(CONFIG_FILE) is False:
        QMessageBox.critical(None, u"Access-Link: Fehler", u"Die Konfigurationsdatei <%s> "
                                                           u"wurde nicht gefunden. " % CONFIG_FILE)
        raise Exception("Konfigurationsdatei nicht gefunden.")

    config = configparser.ConfigParser()
    with open(CONFIG_FILE, 'r') as configfile:
        config.readfp(configfile)
        configfile.close()

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


def zoom_to_feature():

    QgsMessageLog.logMessage("Access-Link: versuche auf feature zu zoomen")

    # Read the settings from the config file
    settings = read_settings()

    input_file = os.path.join(settings["transfer_dir"], settings["input_file"])
    vector_layer = settings["vector_layer"]
    attribute_column = settings["attribute_column"]

    if os.path.exists(input_file) is False:
        QgsMessageLog.logMessage(u"Access-Link: Fehler: Die Input Datei <%s> wurde nicht gefunden." % input_file)
        # QMessageBox.warning(None, u"Access-Link: Warnung", u"Die Input Datei <%s> "
        #                                                   u"wurde nicht gefunden. " % self.input_file)
        return False

    if not vector_layer:
        return False

    layer = QgsMapLayerRegistry.instance().mapLayersByName(vector_layer)

    if not layer:
        QgsMessageLog.logMessage(u"Access-Link: Fehler: Der Vektorlayer <%s> wurde nicht gefunden." % vector_layer)
        return False

    if len(layer) > 0:
        layer = layer[0]

    fields = layer.fields()
    attr_list = []
    for field in fields:
        attr_list.append(field.name())
    if attribute_column not in attr_list:
        QMessageBox.critical(None, u"Access-Link: Fehler",
                             u"Der Vektorlayer <%s> hat keine Attributspalte <%s>." %
                             (vector_layer,
                              attribute_column))
        return False

    # Read the feature id and zoom to it
    feature_id = open(input_file, "r").read().strip()
    # Formulate the expression
    expr = "\"%s\" = '%s'" % (attribute_column, feature_id)
    QgsMessageLog.logMessage("Access-Link:  Expression: %s"%expr)

    layer.selectByExpression(expr)
    qgis.utils.iface.setActiveLayer(layer)
    # Zoom to the selected features
    qgis.utils.iface.actionZoomToSelected().trigger()

    QgsMessageLog.logMessage("Access-Link: zoom beendet")

def start_poll_worker(iface):
    """Start the thread that polls the ascii file for changes and zooms to the vector id
    """

    global worker_thread, worker_object

    if worker_thread:
        stop_poll_worker()

    worker_object = Worker()
    worker_thread = QThread()

    # Connect the
    QgsMessageLog.logMessage("Access-Link: verbinde worker thread signal mit zoom Funktion")
    iface.connect(worker_object, worker_object.signal, zoom_to_feature)

    worker_object.moveToThread(worker_thread)

    worker_thread.started.connect(worker_object.run)
    worker_thread.start()

    QgsMessageLog.logMessage("Access-Link: Worker thread gestartet")


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

        QgsMessageLog.logMessage("Worker thread stopped")


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
        self.poll_time = 1
        # The signal that is emitted when the file was modified
        self.signal = SIGNAL("File_modified")

        settings = read_settings()

        self.input_file = os.path.join(settings["transfer_dir"], settings["input_file"])
        self.lock_file = os.path.join(settings["transfer_dir"], settings["lock_file"])
        if settings["poll_time"]:
            self.poll_time = float(settings["poll_time"])

    def kill(self):
        self.killed = True

    def run(self):
        """The function that runs the infinite loop to poll the ascii file for changes. If the text file changes,
        then the a signal will be emitted to trigger the feature zoom.
        """
        QgsMessageLog.logMessage("Access-Link: starte Dateipolling auf <%s>"%self.input_file)
        lock_count = 0

        while True:

            # QgsMessageLog.logMessage("Access-Link: Polle Inputdatei")

            time.sleep(self.poll_time)

            if self.killed is True:
                QgsMessageLog.logMessage("Access-Link: worker thread beendet")
                break

            # Check the modification time
            if os.path.exists(self.input_file) is True:
                new_mtime = os.path.getmtime(self.input_file)

                if self.mtime == new_mtime:
                    continue
                else:
                    QgsMessageLog.logMessage(u"Access-Link: Datei hat sich geaendert: Zeitstempel alt %s neu %s"%(
                                             str(self.mtime), str(new_mtime)))
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
                    # Emit the vector zoom signal
                    self.mtime = new_mtime
                    QgsMessageLog.logMessage("Access-Link: versende zoom Signal")
                    self.emit(self.signal)
            else:
                pass
                # print("Waiting for QGIS to initialize")
