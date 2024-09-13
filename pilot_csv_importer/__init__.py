import csv
import os
import logging
from eventmanager import Evt
from RHUI import UIField, UIFieldType
from Database import ProgramMethod
from collections import defaultdict

class PilotCSVImporter:
    default_class_name = "Imported Class"
    default_file_path = "/static/user/pilots.csv"

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
        pilot_csv_importer_csv_file_path = UIField(
            name="pilot-csv-importer-csv-file-path",
            label=self._rhapi.__("CSV File Path"),
            field_type=UIFieldType.TEXT,
            desc=self._rhapi.__("CSV file MUST contain [name], [callsign], [group] and [heat] fields. Recommend to place the CSV file here") + ": " + self.default_file_path,
            value=self.default_file_path,
            placeholder=self.default_file_path,
        )
        fields = self._rhapi.fields
        fields.register_option(pilot_csv_importer_class_name, "pilot-csv-importer")
        fields.register_option(pilot_csv_importer_csv_file_path, "pilot-csv-importer")

    def import_pilot(self, args):
        file_path = "." + os.path.abspath(self._rhapi.db.option("pilot-csv-importer-csv-file-path"))
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
                heat_name = self._rhapi.__("Heat") + heat
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