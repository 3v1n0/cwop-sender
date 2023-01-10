#!/usr/bin/env python3
# Simple CWOP weather API and sender
# Copyright (C) 2023  Marco Trevisan

import argparse
import datetime
import logging
import sys

from cwop import CWOP

logger = logging.getLogger(__name__)


def typed_range(type, min, max):
    def range_checker(arg):
        try:
            f = type(arg)
        except ValueError:
            raise argparse.ArgumentTypeError(f"must be a {type} typed number")
        if f < min or f > max:
            raise argparse.ArgumentTypeError(
                "must be in range [" + str(min) + " .. " + str(max) + "]"
            )
        return f

    return range_checker


def float_range(min=sys.float_info.min, max=sys.float_info.max):
    return typed_range(type=float, min=min, max=max)


def int_range(min=-sys.maxsize - 1, max=sys.maxsize):
    return typed_range(type=int, min=min, max=max)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send Weather data to CWOP")
    parser.add_argument("designator", help="Designator ID")
    parser.add_argument(
        "--server",
        type=str,
        metavar="cwop.aprs.net",
        help="CWOP server to use",
    )
    parser.add_argument(
        "--port",
        type=int,
        metavar="23",
        default=14580,
        help="CWOP port to use, normally 14580 or 23",
    )
    parser.add_argument(
        "--lat",
        required=True,
        type=float_range(min=-90, max=90),
        metavar="LATITUDE",
        help="latitude in decimal degrees format",
    )
    parser.add_argument(
        "--lon",
        required=True,
        type=float_range(min=-180, max=180),
        metavar="LONGITUDE",
        help="latitude in decimal degrees format",
    )
    parser.add_argument(
        "--alt",
        required=False,
        type=int_range(min=0),
        metavar="ALTITUDE",
        help="altitude in meters",
    )
    parser.add_argument(
        "--passcode", type=int, help="optional passcode for radio operators"
    )

    parser.add_argument("--timestamp", type=datetime.datetime.fromisoformat,
                        help="timestamp as ISO format")
    parser.add_argument("--temperature", type=float, help="Temperature in °C")
    parser.add_argument(
        "--humidity", type=float_range(min=0, max=100), help="Humidity in %%"
    )
    parser.add_argument("--pressure", type=float_range(min=0), help="Pressure in Pa")
    parser.add_argument("--wind", type=float_range(min=0), help="Wind speed in m/s")
    parser.add_argument(
        "--wind-dir", type=int_range(min=0, max=360), help="Wind direction in degrees"
    )
    parser.add_argument(
        "--wind-gust", type=float_range(min=0), help="Wind gust speed in m/s"
    )
    parser.add_argument(
        "--rain-1h", type=float_range(min=0), help="Rain fallen in the last hour in mm"
    )
    parser.add_argument(
        "--rain-24h",
        type=float_range(min=0),
        help="Rain fallen in the last 24 hours in mm",
    )
    parser.add_argument(
        "--rain-day",
        type=float_range(min=0),
        help="Rain fallen in the current day in mm",
    )
    parser.add_argument(
        "--snow-24h",
        type=float_range(min=0),
        help="Snow fallen in the last 24 hours in mm",
    )
    parser.add_argument(
        "--illuminance", type=float_range(min=0), help="Illuminance in W/m²"
    )
    parser.add_argument(
        "--comment", type=str, help="Comment to include in the report"
    )

    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    cwop = CWOP(
        args.designator,
        passcode=args.passcode,
        server=args.server,
        port=args.port,
        latitude=args.lat,
        longitude=args.lon,
        altitude=args.alt,
    )

    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    report = cwop.prepare_report(
        timestamp=args.timestamp,
        temperature=args.temperature,
        humidity=args.humidity,
        pressure=args.pressure,
        wind=args.wind,
        wind_dir=args.wind_dir,
        gust=args.wind_gust,
        rain_1h=args.rain_1h,
        rain_24h=args.rain_24h,
        rain_day=args.rain_day,
        snow_24h=args.snow_24h,
        illuminance=args.illuminance,
        comment=args.comment,
    )

    logger.debug(f"Report prepared as {report}")

    if args.dry_run:
        logger.debug(f"Dry run: CWOP packet '{report.to_cwop_packet()}'")
        sys.exit(0)

    cwop.send_report(report)
