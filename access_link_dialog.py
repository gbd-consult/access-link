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
# from qgis.core import QgsProject
# from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QFileDialog
from .file_poller import start_poll_worker, stop_poll_worker, read_settings, write_settings

LOCK_FILE_NAME = "lock.log"
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'access_link_dialog_base.ui'))


class AccessLinkDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(AccessLinkDialog, self).__init__(parent)

        self.iface = iface
        self.setupUi(self)

        self.toolButtonTransferDir.released.connect(self.select_transfer_dir)
        self.toolButtonAccessBin.released.connect(self.select_access_bin)
        self.toolButtonAccessDB.released.connect(self.select_access_db)
        self.pushButtonSave.released.connect(self.save_settings)
        self.pushButtonRestartPolling.released.connect(self.start_poll_worker)
        self.pushButtonStopPolling.released.connect(self.stop_poll_worker)
        self.pushButtonReload.released.connect(self.load_settings)

        self.load_settings()

    def load_settings(self):
        """Load all settings from the project file"""

        settings = read_settings()

        self.lineEditTransferDir.setText(settings["transfer_dir"])
        self.lineEditInputFile.setText(settings["input_file"])
        self.lineEditOutputFile.setText(settings["output_file"])
        self.lineEditLockFile.setText(settings["lock_file"])
        self.lineEditAccessBin.setText(settings["access_bin"])
        self.lineEditAccessDB.setText(settings["access_db"])
        self.lineEditVectorLayer.setText(settings["vector_layer"])
        self.lineEditAttributeColumn.setText(settings["attribute_column"])
        self.lineEditPollTime.setText(settings["poll_time"])

    def select_transfer_dir(self):
        """Set the ASCII file path and the lock path derived from the ASCII file path"""

        file_name = QFileDialog.getExistingDirectory(self, u"Wähle das Transferverzeichnis")
        self.lineEditTransferDir.setText(file_name)

    def select_access_bin(self):
        file_name = QFileDialog.getOpenFileName(self, u"Wähle das MS-Access Executable")
        self.lineEditAccessBin.setText(file_name)

    def select_access_db(self):
        file_name = QFileDialog.getOpenFileName(self, u"Wähle die MS-Access Datenbank")
        self.lineEditAccessDB.setText(file_name)

    def save_settings(self):
        """Save all settings in the text config file
        """
        transfer_dir = self.lineEditTransferDir.text()
        input_file = self.lineEditInputFile.text()
        output_file = self.lineEditOutputFile.text()
        lock_file = self.lineEditLockFile.text()
        access_bin = self.lineEditAccessBin.text()
        access_db = self.lineEditAccessDB.text()
        vector_layer = self.lineEditVectorLayer.text()
        attribute_column = self.lineEditAttributeColumn.text()
        poll_time = self.lineEditPollTime.text()

        settings = dict(transfer_dir=transfer_dir,
                        input_file=input_file,
                        output_file=output_file,
                        lock_file=lock_file,
                        access_bin=access_bin,
                        access_db=access_db,
                        vector_layer=vector_layer,
                        attribute_column=attribute_column,
                        poll_time=poll_time)

        write_settings(settings)
        self.stop_poll_worker()
        self.start_poll_worker()

    def start_poll_worker(self):
        start_poll_worker(self.iface)

    def stop_poll_worker(self):
        stop_poll_worker()
