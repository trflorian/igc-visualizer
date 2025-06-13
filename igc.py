import logging
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import pandas as pd

logger = logging.getLogger(__name__)


class PositionRecord(NamedTuple):
    """
    Represents a position record in an IGC file.
    """

    timestamp: datetime
    latitude: float  # in degrees, north is positive, south is negative
    longitude: float  # in degrees, east is positive, west is negative
    av_flag: bool
    pressure_altitude: float  # in meters
    gps_altitude: float  # in meters


class IGCParser:
    """
    Parse IGC files according to the IGC_FORMAT_2008 specification.
    https://xp-soaring.github.io/igc_file_format/igc_format_2008.html
    """

    flight_date: datetime
    gps_datum: str = ""
    pilot_name: str = ""
    manufacturer_id: str = ""
    logger_id: str = ""
    additional_info: str = ""
    position_records: list[PositionRecord]

    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)

        self._validate_file_path()

        self.position_records = []
        self._parse()

    def _validate_file_path(self) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f"File {self.file_path} does not exist")
        if not self.file_path.suffix == ".igc":
            raise ValueError("File must have a .igc extension")

    def _parse(self) -> None:
        """
        Parse the IGC file and extract records, reading the file line by line.
        """
        with open(self.file_path, "r") as file:
            self.lines = file.readlines()

        for line in self.lines:
            line = line.strip()
            self._parse_record(line)

    def _check_all_data_parsed(self) -> None:
        """
        Check if all expected data has been parsed.
        This can be expanded to include more checks as needed.
        """
        if not self.flight_date:
            logger.warning("Flight date not parsed.")
        if not self.gps_datum:
            logger.warning("GPS datum not parsed.")
        if not self.pilot_name:
            logger.warning("Pilot name not parsed.")
        if not self.manufacturer_id:
            logger.warning("Manufacturer ID not parsed.")
        if not self.logger_id:
            logger.warning("Logger ID not parsed.")
        if not self.additional_info:
            logger.warning("Additional info not parsed.")

        logger.info("All expected data parsed successfully.")

    def _parse_record(self, line: str) -> None:
        """
        Parse a single IGC record line. The first few characters determine the record type.
        """
        if line.startswith("A"):
            self._parse_manufacturer(line)
        elif line.startswith("H"):
            # metadata record
            self._parse_metadata(line)
        elif line.startswith("B"):
            self._parse_position(line)
        elif line.startswith("L"):
            # This is a comment line, we can ignore it for now
            logger.debug(f"Comment line: {line}")
        elif line.startswith("G"):
            # Security key calculated by the logger from the content above
            logger.debug(f"Security key line: {line}")
        else:
            logger.warning(f"Unknown record type: {line[:1]} in line: {line}")

    def _parse_manufacturer(self, line: str) -> None:
        """
        Parse the manufacturer record in the following format:
        A XXX ABC FLIGHT:1
        e.g. AXBM001 BURNAIR V1.0.0 ID:00000001
        """

        self.manufacturer_id = line[1:4].strip()
        self.logger_id = line[4:7].strip()
        self.additional_info = line[7:].strip()

    def _parse_metadata(self, line: str) -> None:
        """
        Parse the metadata record in the following format:
        HFPLTPILOT:Florian Trautweiler
        HFDTM100GPSDATUM:WGS-84
        HFDTEDATE:100525
        """
        if line.startswith("HFPLTPILOT"):
            self.pilot_name = line[11:].strip()
        elif line.startswith("HFDTM100GPSDATUM"):
            self.gps_datum = line[17:].strip()
        elif line.startswith("HFDTEDATE"):
            flight_date_str = line[10:].strip()
            if len(flight_date_str) == 6:
                # Convert from DDMMYY
                self.flight_date = datetime.strptime(flight_date_str, "%d%m%y")
            else:
                raise ValueError(f"Invalid flight date format: {flight_date_str}")

    def _parse_position(self, line: str) -> None:
        """
        Parse the position record in the following format:
        B160240 5407121N 00249342W A 00280 00421 205 09 950

        Great, we've finally got to the log points we are interested in. The format is "B-timestamp-latitude-longitude-AVflag-pressure alt-GPS alt-extensions".
        As mentioned above, the first 35 bytes of the B record have a fixed definition, then after that the fields are determined by the I record. This B record
        has timestamp 16:02:40, lat 54 degrees 7.121 mins North, long 2 deg 49.342 mins West, AVflag (3D validity) A, 280m altitude from pressure sensor,
        421m altitude from GPS, and FXA (accuracy) 205m, SIU (satellite count) 09 and ENL (engine noise) 950 (suggesting the engine is running...).

        e.g.

        B
        095532
        4650345N
        00824866E
        A
        00000
        01909
        """

        if len(line) < 35:
            raise ValueError(f"Position record line too short: {line}")

        timestamp_str = line[1:7].strip()
        latitude_str = line[7:15].strip()
        longitude_str = line[15:24].strip()
        av_flag_str = line[24:25].strip()
        pressure_altitude_str = line[25:30].strip()
        gps_altitude_str = line[30:35].strip()

        # Parse timestamp
        timestamp = datetime.strptime(timestamp_str, "%H%M%S")
        timestamp = timestamp.replace(
            year=self.flight_date.year,
            month=self.flight_date.month,
            day=self.flight_date.day,
        )

        # Parse latitude
        latitude = float(latitude_str[:2]) + float(latitude_str[2:-1]) / 60.0
        if latitude_str[-1] == "S":
            latitude = -latitude

        # Parse longitude
        longitude = float(longitude_str[:3]) + float(longitude_str[3:-1]) / 60.0
        if longitude_str[-1] == "W":
            longitude = -longitude

        # Parse AV flag
        av_flag = av_flag_str == "A"

        # Parse pressure altitude
        pressure_altitude = float(pressure_altitude_str)

        # Parse GPS altitude
        gps_altitude = float(gps_altitude_str)

        # Create a PositionRecord and add it to the list
        position_record = PositionRecord(
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            av_flag=av_flag,
            pressure_altitude=pressure_altitude,
            gps_altitude=gps_altitude,
        )

        self.position_records.append(position_record)

    def to_pandas(self) -> pd.DataFrame:
        """
        Convert the parsed position records to a pandas DataFrame.
        """

        data = {
            "timestamp": [record.timestamp for record in self.position_records],
            "latitude": [record.latitude for record in self.position_records],
            "longitude": [record.longitude for record in self.position_records],
            "av_flag": [record.av_flag for record in self.position_records],
            "pressure_altitude": [
                record.pressure_altitude for record in self.position_records
            ],
            "gps_altitude": [record.gps_altitude for record in self.position_records],
        }

        return pd.DataFrame(data)
