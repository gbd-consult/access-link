# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AccessLink
                                 A QGIS plugin
 Zeige spezifische Vektorobjekte eines Layers an die in einer Access Datenbank beschrieben werden.
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
import subprocess
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
import qgis
from qgis.gui import QgisInterface
from PyQt4.QtGui import QMessageBox
import resources
# Import the code for the dialog
from access_link_dialog import AccessLinkDialog
import os.path
from .file_poller import start_poll_worker, stop_poll_worker, read_settings


class AccessLink:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'AccessLink_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Access Link')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'AccessLink')
        self.toolbar.setObjectName(u'AccessLink')

        # Create the dialog (after translation) and keep reference
        self.dlg = AccessLinkDialog(parent=self.iface.mainWindow())
        # Call the initialization of the plugin when QGIS finished
        # its own initialization
        qgis.utils.iface.initializationCompleted.connect(self.init_plugin)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('AccessLink', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setToolTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/AccessLink/icon.png'
        icon_path = None
        self.add_action(
            icon_path,
            text=self.tr(u'Konfiguration'),
            status_tip=self.tr(u"Konfiguriere das Access Link Plugin"),
            whats_this=self.tr(u"Konfiguriere das Access Link Plugin"),
            add_to_menu=True,
            add_to_toolbar=False,
            callback=self.run,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Access Feature'),
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=self.tr(u"Zeige das aktuell selektierte Vektorfeature in MS-Access"),
            whats_this=self.tr(u"Zeige das aktuell selektierte Vektorfeature in MS-Access"),
            callback=self.open_access_for_feature,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Access Link'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

        # Stop the poll worker
        stop_poll_worker()

    def run(self):
        """Run method that performs all the real work"""

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def init_plugin(self):
        """This method must be called after QGIS is completely initialized, hence all projects
        and plugins are loaded

        :return:
        """
        # Start the poll worker thread
        start_poll_worker()
        self.dlg.load_settings()

    def open_access_for_feature(self):
        """Write the id into a text file and start MS-Access if its not running
        """
        settings = read_settings()

        output_file = os.path.join(settings["transfer_dir"], settings["output_file"])
        lock_file = os.path.join(settings["transfer_dir"], settings["lock_file"])
        access_bin = settings["access_bin"]
        access_db = settings["access_db"]
        # Extract lockfile
        filename, file_extension = os.path.splitext(access_db)

        access_db_lock_1 = "%s.laccdb"%filename
        access_db_lock_2 = "%s.ldb"%filename

        layer = self.iface.activeLayer()
        if not layer:
            return
        attr_col = settings["attribute_column"]
        features = layer.selectedFeatures()
        if layer and len(features) > 0:
            fields = layer.fields()
            attr_list = []
            for field in fields:
                attr_list.append(field.name())
            if attr_col not in attr_list:
                QMessageBox.critical(self.iface.mainWindow(),
                                     u"Access-Link: Fehler", u"Der Vektorlayer <%s> "
                                                             u"hat keine Attributspalte <%s>. " % (layer.name(),
                                                                                                          attr_col))
                return

            id = features[0][attr_col].strip()

            if os.path.exists(lock_file):
                QMessageBox.warning(self.iface.mainWindow(), u"Access-Link: Warnung",
                                    u"Kann Kataster ID nicht schreiben, da Lockdatei <%s> existiert."%lock_file)
                return

            try:
                # Write Lockfile
                lock = open(lock_file, "w")
                #print(u"Create lock file")
                lock.write("LOCK")
                lock.flush()
                lock.close()
                # Write data
                output = open(output_file, "w")
                output.write(id)
                output.write(os.linesep)
                output.flush()
                output.close()
            except Exception as e:
                QMessageBox.critical(self.iface.mainWindow(), u"Access-Link: Fehler",
                                     u"Kann Lockfile oder Ausgabedatei nicht schreiben. Fehler: str(e)")
                return
            finally:
                # Try to remove lock file
                try:
                    #print(u"Remove lock file")
                    os.remove(lock_file)
                except:
                    pass

            if os.path.exists(access_bin) is False:
                QMessageBox.critical(self.iface.mainWindow(), u"Access-Link: Fehler",
                                     u"MS-Access Programm nicht gefunden. Pfad: "
                                     u"<%s>" % access_bin)
            if os.path.isfile(access_db) is False:
                QMessageBox.critical(self.iface.mainWindow(), u"Access-Link: Fehler",
                                     u"MS-Access Datenbank nicht gefunden. Pfad: "
                                     u"<%s>" % access_db)

            if os.path.exists(access_db_lock_1) is True or os.path.exists(access_db_lock_2) is True:
                return

            # Start MS-Access
            print("Start", access_bin, access_db)
            proc = subprocess.Popen(args=[access_bin, access_db], shell=False)
