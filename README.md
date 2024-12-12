# Pilot CSV Importer Plugin for RotorHazard

This plugin allows you to import pilots and generate heats from a CSV file in RotorHazard.

## Features

- Import pilots from a CSV file locally, from a website address or from IFPV
- Automatically create a race class
- Generate heats based on the imported data
- Assign pilots to appropriate heats

## Installation

- ### Manually

1. Clone this repository or download the source code.
2. Place the `pilot_csv_importer` folder in your RotorHazard plugins directory `~/RotorHazard/src/server/plugins`.
3. Restart your RotorHazard server.

- ### Commandline

```bash
cd ~
sudo rm -r RotorHazard/src/server/plugins/pilot_csv_importer
wget https://github.com/l1cardo/RH-Pilot-CSV-Importer/releases/latest/download/pilot_csv_importer.zip
unzip pilot_csv_importer.zip -d pilot_csv_importer
cp -r pilot_csv_importer RotorHazard/src/server/plugins/
rm -r pilot_csv_importer
rm pilot_csv_importer.zip
sudo systemctl restart rotorhazard.service
```

## Usage

1. Navigate to the "Pilot CSV Importer" panel in the Format page.
2. Set the desired class name (default is `Imported Class`).
3. Select the type of import (From File, From ifpv.co.uk, from URL)
4. Specify the path to your CSV file (default is `~/RotorHazard/src/server/static/user/pilots.csv`) or website address or IFPV event ID (found in IFPV URL).
5. Click the "Import" button to start the import process.

## CSV File Format

Your CSV file **MUST** contain the following columns:

- `name`: Pilot name
- `callsign`: Pilot callsign
- `heat`: Heat name #The pilots will be put into same Heat if they have the same `heat`

CSV File example

```scv
name,callsign,heat
Licardo,Licardo,A
Tom,Tom,A
Jack,Jack,A
John,John,B
Tim,Tim,C
```

## License

[MIT](LICENSE)