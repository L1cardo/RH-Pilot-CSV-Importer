import csv
import os
import logging
import urllib.request
from eventmanager import Evt
from RHUI import UIField, UIFieldType, UIFieldSelectOption
from Database import ProgramMethod
from collections import defaultdict

class PilotCSVImporter:
    default_class_name = "Imported Class"
    default_file_path = "./static/user/pilots.csv"

    def __init__(self, rhapi):
        self.logger = logging.getLogger(__name__)
        self._rhapi = rhapi

    def init_plugin(self, args):
        self.logger.info("Starting Pilot CSV Importer plugin")
        self.init_ui(args)

    def init_ui(self, args):
        ui = self._rhapi.ui
        ui.register_panel("pilot-csv-importer", self._rhapi.__("Pilot CSV Importer"), "format")
        ui.register_quickbutton("pilot-csv-importer", "pilot-csv-import-button", self._rhapi.__("Import"), self.import_pilot)
        pilot_csv_importer_class_name = UIField(
            name="pilot-csv-importer-class-name",
            label=self._rhapi.__("Class Name"),
            field_type=UIFieldType.TEXT,
            value=self.default_class_name,
            placeholder=self.default_class_name,
        )
        pilot_csv_importer_type = UIField(
            name="pilot-csv-importer-type",
            label=self._rhapi.__("Type of Import"),
            field_type=UIFieldType.SELECT,
            value="from_file",
            options=[
                UIFieldSelectOption("from_file", "From File"),
                UIFieldSelectOption("from_ifpv", "From ifpv.co.uk"),
                UIFieldSelectOption("from_ulr", "From URL"),
            ],
        )
        pilot_csv_importer_location = UIField(
            name="pilot-csv-importer-location",
            label=self._rhapi.__("CSV File Path / Event ID / URL"),
            field_type=UIFieldType.TEXT,
            desc=self._rhapi.__("Source file MUST contain [name], [callsign] and [heat] fields."),
            value=self.default_file_path,
            placeholder=self.default_file_path,
        )
        fields = self._rhapi.fields
        fields.register_option(pilot_csv_importer_class_name, "pilot-csv-importer")
        fields.register_option(pilot_csv_importer_type, "pilot-csv-importer")
        fields.register_option(pilot_csv_importer_location, "pilot-csv-importer")


    def ifpv_download(self, event_id):
        self.download_csv("https://www.ifpv.co.uk/events/" + event_id + "/rh")
    
    def download_csv(self, url):
        download_location = "./plugins/pilot_csv_importer/downloaded/pilots.csv"

        if os.path.isfile(download_location):
            os.remove(download_location)
            self.logger.info("Deleted: " + download_location)

        self.logger.info("Attempting to download: " + url)
        download_result = urllib.request.urlretrieve(url, download_location)
        self.logger.info("Downloaded: " + str(download_result))

    def import_pilot(self, args):
        if self._rhapi.db.option("pilot-csv-importer-type") == "1": # ifpv
            self.ifpv_download(self._rhapi.db.option("pilot-csv-importer-location"))
            file_path = "./plugins/pilot_csv_importer/downloaded/pilots.csv"
        elif self._rhapi.db.option("pilot-csv-importer-type") == "2": # url
            self.download_csv(self._rhapi.db.option("pilot-csv-importer-location"))
            file_path = "./plugins/pilot_csv_importer/downloaded/pilots.csv"
        else:
            file_path = os.path.abspath(self._rhapi.db.option("pilot-csv-importer-location"))
        if os.path.isfile(file_path):
            heats = defaultdict(list)
            with open(file_path, mode="r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    pilot_name = row.get("name")
                    pilot_callsign = row.get("callsign")
                    pilot_heat = row.get("heat")
                    pilot = {"name": pilot_name, "callsign": pilot_callsign}
                    existing_pilot = self.check_existing_pilot(pilot)
                    if not existing_pilot:
                        self.logger.info(f"Pilot added: {pilot['name']} - {pilot['callsign']}")
                        self._rhapi.db.pilot_add(name=pilot["name"], callsign=pilot["callsign"])
                    else:
                        self.logger.info(f"Pilot alredy exists: {pilot['name']} - {pilot['callsign']}")

                    pilot_id = self.get_pilot_id(pilot)
                    heats[pilot_heat].append(pilot_id)
                        
            self._rhapi.ui.broadcast_pilots()
            self.logger.info("Import complete, generating heats...")

            # Generate heats
            self.generate_heats(heats)

        else:
            self._rhapi.ui.message_alert(self._rhapi.__("Cannot find CSV file") + ": " + file_path)
            self.logger.warning(f"Cannot find CSV file: {file_path}")

    def generate_heats(self, heats):
        # First, create a race class if it doesn't exist
        class_name = self._rhapi.db.option("pilot-csv-importer-class-name")
        existing_class = self.check_existing_class(class_name)
        if not existing_class:
            race_class = self._rhapi.db.raceclass_add(name=self._rhapi.db.option("pilot-csv-importer-class-name"))

            # Create heats and associate them with the race class and format
            for heat, pilot_ids in heats.items():
                heat_name = self._rhapi.__("Heat ") + heat
                new_heat = self._rhapi.db.heat_add(name=heat_name)
                
                # Associate the heat with the race class and format
                self._rhapi.db.heat_alter(new_heat.id, raceclass=race_class.id)
                
                # Get all slots for this heat
                slots = self._rhapi.db.slots_by_heat(new_heat.id)
                
                for index, pilot_id in enumerate(pilot_ids):
                    slot_id = slots[index].id
                    self._rhapi.db.slot_alter(
                        slot_id,
                        method=ProgramMethod.ASSIGN,
                        pilot=pilot_id
                    )
            self._rhapi.ui.message_notify(self._rhapi.__("Pilot imported, Race class and heats generated successfully"))
            self.logger.info("Race class, format, and heats generated successfully")

        else:
            self._rhapi.ui.message_alert(self._rhapi.__("Race class name exists, please change to another name"))
            self.logger.warning("Race class name exists, please change to another name")

        self._rhapi.ui.broadcast_raceclasses()
        self._rhapi.ui.broadcast_heats()
        

    def check_existing_pilot(self, pilot):
        existing_pilots = self._rhapi.db.pilots
        existing = False
        for existing_pilot in existing_pilots:
            if (existing_pilot.name == pilot["name"] and existing_pilot.callsign == pilot["callsign"]):
                existing = True
        return existing
    
    def check_existing_class(self, class_name):
        existing_classes = self._rhapi.db.raceclasses
        existing = False
        for existing_class in existing_classes:
            if (existing_class.name == class_name):
                existing = True
        return existing
    
    def get_pilot_id(self, pilot):
        db_pilots = self._rhapi.db.pilots
        for db_pilot in db_pilots:
            if db_pilot.name == pilot['name'] and db_pilot.callsign == pilot['callsign']:
                return db_pilot.id
        return None
    
def initialize(rhapi):
    pilot_csv_importer = PilotCSVImporter(rhapi)
    rhapi.events.on(Evt.STARTUP, pilot_csv_importer.init_plugin)