# Simple CWOP weather API and sender
# Copyright (C) 2023  Marco Trevisan

from enum import Enum

from typing import Optional, Union


class ConversionException(Exception):
    pass


def celsius_to_fahrenheit(c: Union[int, float]) -> float:
    """Converts celsius to fahrenheit"""
    return c * 9.0 / 5.0 + 32.0


def kph_to_mph(kph: Union[int, float]) -> float:
    """Converts km/h to mph"""
    return kph / 1.609344


def ms_to_kph(m: Union[int, float]) -> float:
    """Converts m/s to km/h"""
    return m * 3.6


def meters_to_feet(meters: Union[int, float]) -> float:
    """Converts meters to feet"""
    return meters * 3.28084


def mm_to_inch(mm: Union[int, float]) -> float:
    """Converts millimeters to inches"""
    return mm / 25.4


def lux_to_wm2(lux: Union[int, float]) -> float:
    "Approximate conversion from lux to solar radiation in W/m2"
    return lux * 0.0079


class Coordinate(Enum):
    LATITUDE = 1
    LONGITUDE = 2


def coordinates_loran(type, coord) -> str:
    """Converts decimal coordinates to LORAN format"""
    if type not in (Coordinate.LATITUDE, Coordinate.LONGITUDE):
        raise ConversionException(f"Invalid coordinate type {type}")

    decimals = abs(coord) % 1
    degrees = abs(int(coord))
    minutes = f"{decimals * 60:.2f}"

    if type == Coordinate.LATITUDE:
        direction = "N" if coord > 0 else "S"
    elif type == Coordinate.LONGITUDE:
        direction = "E" if coord > 0 else "W"
        degrees = f"{degrees:03d}"

    return f"{degrees}{minutes}{direction}"


def latitude_loran(coord: float) -> str:
    """Converts decimal latitude to LORAN format"""
    if not isinstance(coord, (int, float, complex)):
        raise ConversionException(f"Invalid latitude value {coord}")
    return coordinates_loran(Coordinate.LATITUDE, coord)


def longitude_loran(coord: float) -> str:
    """Converts decimal longitude to LORAN format"""
    if not isinstance(coord, (int, float, complex)):
        raise ConversionException(f"Invalid longitude value {coord}")
    return coordinates_loran(Coordinate.LONGITUDE, coord)


def number_to_max_length_int(
    input: Union[int, float, complex, None], max_length: int = 0, negative: bool = False
) -> Optional[int]:
    """Converts a number to an integer that has `max_length` maximum digits"""
    if input is None:
        return None
    if isinstance(input, (float, complex)):
        input = int(input)
    if not isinstance(input, int):
        raise ConversionException(f"Invalid value {input}")
    if input < 0:
        if not negative:
            return None
    if max_length > 0:
        if input < 0:
            max_length -= 1

        if abs(input) >= pow(10, max_length):
            return None
    return input
