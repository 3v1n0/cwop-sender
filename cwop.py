# Simple CWOP weather API and sender
# Copyright (C) 2023  Marco Trevisan

# Simple python implementation of CWOP protocol, based on
#  ftp://ftp.tapr.org/aprssig/aprsspec/spec/aprs101/APRS101.pdf
#  http://www.aprs.org/aprs11/spec-wx.txt

from typing import Callable, NamedTuple, Optional, Union

import conversions
import datetime
import logging
import socket

logger = logging.getLogger(__name__)


class CWOPValue(object):
    def __init__(
        self,
        value: Union[int, float, None],
        converter: Callable = None,
        max_digits: int = -1,
        negative: bool = False,
        use_float: bool = False,
        prefix: str = "",
    ):
        super().__init__()
        self.value = value
        self._max_digits = max_digits
        self._converted = converter(value) if converter and value is not None else value
        self._int_value = conversions.number_to_max_length_int(
            self._converted, self._max_digits, negative=negative
        )
        if (
            use_float
            and self._converted
            and (
                self._int_value
                and abs(self._int_value) < pow(10, max_digits)
                or self._converted < 1
            )
        ):
            cut = str(self._converted)[:max_digits]
            self._int_value = float(cut) if "." in cut else int(cut)

        self.prefix = prefix if prefix and len(prefix) == 1 else ""

    def __bool__(self):
        return self._int_value is not None

    def __repr__(self) -> str:
        if self.value is None:
            return str(None)

        extra_infos = {}
        if self._converted != self.value:
            extra_infos["converted to"] = self._converted
        if self._int_value != self._converted:
            extra_infos["int as"] = self._int_value
        if self.prefix:
            extra_infos["prefix"] = self.prefix
        if self._max_digits > 0:
            extra_infos["max digits"] = self._max_digits

        return f"{int(self.value)}{f' ({extra_infos})' if extra_infos else ''}"

    def __str__(self) -> str:
        if self._max_digits <= 0:
            return f"{self.prefix}{self._int_value}" if self else ""

        if not self:
            return f"{self.prefix}{self._max_digits * '.'}"

        return f"{self.prefix}{self._int_value:>0{self._max_digits}}"


class CWOPReport(NamedTuple):
    designator: str
    timestamp: Optional[datetime.datetime]
    latitude: str
    longitude: str
    altitude: CWOPValue
    temperature: CWOPValue
    humidity: CWOPValue
    pressure: CWOPValue
    wind: CWOPValue
    wind_dir: CWOPValue
    wind_gust: CWOPValue
    rain_1h: CWOPValue
    rain_24h: CWOPValue
    rain_day: CWOPValue
    illuminance: CWOPValue
    snow_24h: CWOPValue
    comment: str

    def to_cwop_packet(self):
        use_aprs_messaging = True

        packet = f"{self.designator:s}>APRS,TCPIP*:"

        if self.timestamp:
            packet += f"{'@' if use_aprs_messaging else '/':s}"
            packet += f"{self.timestamp:%d%H%M}z"
        else:
            packet += f"{'=' if use_aprs_messaging else '!':s}"

        packet += f"{self.latitude}/{self.longitude}"
        packet += f"{self.wind_dir}{self.wind}{self.wind_gust}{self.temperature}"

        if self.rain_1h:
            packet += str(self.rain_1h)

        packet += f"{self.rain_24h}{self.rain_day}{self.humidity}{self.pressure}"

        if self.illuminance:
            packet += str(self.illuminance)

        if self.snow_24h:
            packet += str(self.snow_24h)

        comment_data = []

        if self.altitude:
            comment_data.append(f"/A={self.altitude}")

        if self.comment:
            comment_data.append(self.comment)

        comment_data.append("- cwop-sender.py")

        packet += " ".join(comment_data)

        return packet


class CWOP:
    def __init__(
        self,
        designator: str,
        latitude: float,
        longitude: float,
        server: Optional[str] = None,
        port: Optional[int] = None,
        altitude: Optional[int] = None,
        passcode: Optional[int] = None,
    ):
        self._server = server
        self._port = port
        self._designator = designator
        self._latitude = conversions.latitude_loran(latitude)
        self._longitude = conversions.longitude_loran(longitude)
        self._altitude = conversions.meters_to_feet(altitude) if altitude else None
        self._passcode = passcode

        if not self._server:
            self._server = "rotate.aprs.net" if self._passcode else "cwop.aprs.net"

    def prepare_report(
        self,
        timestamp=Optional[datetime.datetime],
        wind: Optional[float] = None,
        wind_dir: Optional[int] = None,
        gust: Optional[float] = None,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        pressure: Optional[float] = None,
        rain_1h: Optional[float] = None,
        rain_24h: Optional[float] = None,
        rain_day: Optional[float] = None,
        snow_24h: Optional[float] = None,
        illuminance: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> CWOPReport:
        timestamp = (
            timestamp.astimezone(datetime.timezone.utc)
            if timestamp
            else datetime.datetime.utcnow()
        )

        if comment:
            if "~" in comment:
                comment = comment.replace("~", "-")
            if "|" in comment:
                comment = comment.replace("|", "/")

        return CWOPReport(
            designator=self._designator,
            timestamp=timestamp,
            latitude=self._latitude,
            longitude=self._longitude,
            altitude=self._altitude,
            temperature=CWOPValue(
                temperature,
                conversions.celsius_to_fahrenheit,
                prefix="t",
                max_digits=3,
                negative=True,
            ),
            humidity=CWOPValue(
                humidity, lambda h: int(h % 100), prefix="h", max_digits=2
            ),
            pressure=CWOPValue(
                pressure,
                lambda p: conversions.number_to_max_length_int(p / 10.0),
                prefix="b",
                max_digits=5,
            ),
            wind=CWOPValue(
                wind,
                lambda w: conversions.kph_to_mph(conversions.ms_to_kph(w)),
                prefix="/",
                max_digits=3,
            ),
            wind_dir=CWOPValue(wind_dir, max_digits=3, prefix="_"),
            wind_gust=CWOPValue(
                gust,
                lambda w: conversions.kph_to_mph(conversions.ms_to_kph(w)),
                prefix="g",
                max_digits=3,
            ),
            rain_1h=CWOPValue(
                rain_1h,
                lambda r: 100 * conversions.mm_to_inch(r),
                prefix="r",
                max_digits=3,
            ),
            rain_24h=CWOPValue(
                rain_24h,
                lambda r: 100 * conversions.mm_to_inch(r),
                prefix="p",
                max_digits=3,
            ),
            rain_day=CWOPValue(
                rain_day,
                lambda r: 100 * conversions.mm_to_inch(r),
                prefix="P",
                max_digits=3,
            ),
            snow_24h=CWOPValue(
                snow_24h,
                lambda r: conversions.mm_to_inch(r),
                prefix="s",
                max_digits=3,
                use_float=True,
            ),
            illuminance=CWOPValue(
                illuminance if illuminance < 1000 else illuminance - 1000,
                prefix="L" if illuminance < 1000 else "l",
                max_digits=3,
            )
            if illuminance
            else None,
            comment=comment,
        )

    def _open_socket(self):
        try:
            sock = socket.socket()
            sock.settimeout(5)
            logger.debug(f"Connecting to {self._server}:{self._port}")
            sock.connect((self._server, self._port))
            sock.settimeout(30)

        except Exception:
            sock.close()
            raise

        return sock

    def send_report(self, report):
        if not isinstance(report, CWOPReport):
            raise Exception("Not a valid CWOPReport instance")

        try:
            sock = self._open_socket()
            response = sock.recv(4096).decode("ASCII")
            logger.debug("server software: %s", response.strip())

            passcode = self._passcode or -1
            login = f"user {self._designator} pass {passcode} vers cwop-sender.py 0.5\n"
            login = login.encode("ASCII")
            logger.debug(f'login: "{login}"')

            sock.sendall(login)
            response = sock.recv(4096).decode("ASCII")
            logger.debug("server login ack: %s", response.strip())

            packet = report.to_cwop_packet()
            logger.debug(
                f"Sending CWOP packet '{packet}' to {self._server}:{self._port}"
            )

            sock.sendall(packet.encode("ASCII") + b"\n")
            sock.shutdown(socket.SHUT_RDWR)

        finally:
            sock.close()
