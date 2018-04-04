# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AccessLinkDialog
                                 A QGIS plugin
 Zeigespezifische Vektorobjekte eines Layers an die in einer Access Datenbank beschrieben werden.
                             -------------------
        begin                : 2018-04-04
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

from PyQt4 import QtGui, uic
from qgis.core import QgsProject
from PyQt4.QtCore import QFileInfo
from PyQt4.QtGui import QFileDialog
from .file_poller import start_poll_worker, stop_poll_worker

LOCK_FILE_NAME = "LOCK.log"
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'access_link_dialog_base.ui'))


class AccessLinkDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(AccessLinkDialog, self).__init__(parent)

        self.setupUi(self)
        self.project = None

        self.toolButtonIdFile.released.connect(self.select_ascii_id_file)
        self.toolButtonLockFile.released.connect(self.select_lock_file)
        self.toolButtonBatchFile.released.connect(self.select_batch_file)
        self.toolButtonBatchFile.released.connect(self.select_batch_file)
        self.pushButtonSave.released.connect(self.save_settings)
        self.pushButtonRestartPolling.released.connect(self.start_poll_worker)
        self.pushButtonStopPolling.released.connect(self.stop_poll_worker)
        self.pushButtonReload.released.connect(self.load_settings)

    def load_settings(self):
        """Load all settings from the project file"""

        self.project = QgsProject.instance()
        ascii_file = self.project.readEntry("access_link", "ascii_file", "/tmp/ascii.txt")[0]
        self.lineEditIdFile.setText(ascii_file)
        lock_file = self.project.readEntry("access_link", "lock_file", "/tmp/lock.log")[0]
        self.lineEditLockFile.setText(lock_file)
        batch_file = self.project.readEntry("access_link", "batch_file", "/tmp/script.vba")[0]
        self.lineEditBatchFile.setText(batch_file)
        vector_layer = self.project.readEntry("access_link", "vector_layer", "ALKIS")[0]
        self.lineEditVectorLayer.setText(vector_layer)
        attribute_column = self.project.readEntry("access_link", "attribute_column", "id")[0]
        self.lineEditAttributeColumn.setText(attribute_column)
        poll_time = self.project.readEntry("access_link", "poll_time", "0.5")[0]
        self.lineEditPollTime.setText(poll_time)

    def select_ascii_id_file(self):
        """Set the ASCII file path and the lock path derived from the ASCII file path"""

        file_name = QFileDialog.getOpenFileName(self, "Wähle ASCII Datei die die Vektor-Id enthält")
        self.lineEditIdFile.setText(file_name)
        # Extract the directory path from the ascii file path, since this should be the directory in which
        # the lock file is located
        dir_path = os.path.dirname(file_name)
        lock_path = os.path.join(dir_path, LOCK_FILE_NAME)
        self.lineEditLockFile.setText(lock_path)

    def select_lock_file(self):
        file_name = QFileDialog.getOpenFileName(self, "Wähle Lock Datei.")
        self.lineEditLockFile.setText(file_name)

    def select_batch_file(self):
        file_name = QFileDialog.getOpenFileName(self, "Wähle das Visual Basic Script")
        self.lineEditBatchFile.setText(file_name)

    def save_settings(self):
        """Save all settings in the project file
        """
        self.project.writeEntry("access_link", "ascii_file", self.lineEditIdFile.text())
        self.project.writeEntry("access_link", "lock_file", self.lineEditLockFile.text())
        self.project.writeEntry("access_link", "batch_file", self.lineEditBatchFile.text())
        self.project.writeEntry("access_link", "vector_layer", self.lineEditVectorLayer.text())
        self.project.writeEntry("access_link", "attribute_column", self.lineEditAttributeColumn.text())
        self.project.writeEntry("access_link", "poll_time", self.lineEditPollTime.text())

    def start_poll_worker(self):
        start_poll_worker()

    def stop_poll_worker(self):
        stop_poll_worker()
