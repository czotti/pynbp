# -*- coding: utf-8 -*-
"""
Python Numeric Broadcast Protocol

This module implements HP Tuners / Track Addict Numeric Broadcast Protocol

WiFI Implementation
"""

import time
from collections import namedtuple
import logging
import threading
from pathlib import Path
import socket

import serial

__version__ = "0.0.10"
HOME = str(Path.home())

NbpKPI = namedtuple("NbpKPI", "name, unit, value")
NbpPayload = namedtuple("NbpPayload", "timestamp, packettype, nbpkpilist")

LOGGER = logging.getLogger("pynbp")
FH = logging.FileHandler("{0}/pynbp.log".format(HOME))
FH.setLevel(logging.INFO)
FH.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s\n%(message)s"))
LOGGER.addHandler(FH)


class BasePyNBP(threading.Thread):
    """
    Base class taht define package creation for Wifi and Bluetooth
    """

    def __init__(self, nbpqueue, device_name="PyNBP",
                 protocol_version="NBP1", min_update_interval=0.2):
        self.device_name = device_name
        self.protocol_version = protocol_version
        self.last_update_time = 0
        self.packettime = 0
        self.kpis = {}
        self.nbpqueue = nbpqueue
        self.updatelist = []
        self.min_update_interval = min_update_interval
        threading.Thread.__init__(self)

    def run(self):
        raise NotImplementedError

    def metadata(self):
        """
        Get metadata for the device, device_name
        """
        return str.encode("@NAME:{0}\n\n".format(self.device_name))

    def _genpacket(self, ptype='ALL'):
        if ptype not in ["ALL", "UPDATE", "METADATA"]:
            raise ValueError("Unrecognize ptype: {}".format(ptype))
        if ptype == "METADATA":
            return self.metadata()

        packet = "*{0},{1},{2:.6f}\n".format(
            self.protocol_version, ptype, self.packettime)

        if self.updatelist and ptype != "ALL":
            kpis = [self.kpis[k] for k in self.updatelist]
        else:
            kpis = self.kpis.values()

        for kpi in kpis:
            if kpi.unit:
                packet += '"{0}","{1}":{2}\n'.format(
                    kpi.name, kpi.unit, kpi.value)
            else:
                packet += '"{0}":{1}\n'.format(kpi.name, kpi.value)

        packet += "#\n\n"

        return str.encode(packet)


class PyNBP(BasePyNBP):
    """
    Defines Bluetooth communication of the NBP protocol.
    """

    def __init__(self, nbpqueue, device="/dev/rfcomm0", device_name="PyNBP",
                 protocol_version="NBP1", min_update_interval=0.2):
        super().__init__(
            nbpqueue,
            device_name=device_name,
            protocol_version=protocol_version,
            min_update_interval=min_update_interval)
        self.device = device

    def run(self):
        connected = False
        serport = None

        while True:
            nbppayload = self.nbpqueue.get()

            self.packettime = nbppayload.timestamp

            for kpi in nbppayload.nbpkpilist:
                if kpi.name not in self.updatelist:
                    self.updatelist.append(kpi.name)
                self.kpis[kpi.name] = kpi

            if not connected:
                try:
                    serport = serial.serial_for_url(self.device)
                    connected = True
                except serial.SerialException as _:
                    logging.info(
                        "Comm Port conection not open - waiting for connection")

            if not connected and not serport.is_open:
                continue
            try:
                if serport.in_waiting > 0:
                    LOGGER.info(serport.read(serport.in_waiting).decode())

                if time.time() - self.last_update_time < self.min_update_interval:
                    continue

                nbppacket = self._genpacket(nbppayload.packettype)

                LOGGER.warning(nbppacket.decode())

                serport.write(nbppacket)
                self.updatelist = []
                self.last_update_time = time.time()

            except serial.SerialTimeoutException as _:
                logging.exception("Serial Write timeout. Closing port.")
                serport.close()
                connected = False


class WifiPyNBP(BasePyNBP):
    """
    Defines the Wifi communication of NBP protocol.
    """

    def __init__(self, nbpqueue, ip="127.0.0.1", port=35000, device_name="PyNBP",
                 protocol_version="NBP1", min_update_interval=0.2):
        super().__init__(
            nbpqueue,
            device_name=device_name,
            protocol_version=protocol_version,
            min_update_interval=min_update_interval)
        self._ip = ip
        self._port = port

    def run(self):
        connected = False
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        logging.warning("Binding to {}:{}".format(self._ip, self._port))
        sock.bind((self._ip, self._port))
        sock.listen(1)

        while True:
            nbppayload = self.nbpqueue.get()

            self.packettime = nbppayload.timestamp

            for kpi in nbppayload.nbpkpilist:
                if kpi.name not in self.updatelist:
                    self.updatelist.append(kpi.name)
                self.kpis[kpi.name] = kpi

            if not connected:
                try:
                    conn, client_address = sock.accept()
                    conn.setblocking(0)
                    connected = True
                    logging.warning(
                        "Connection from {0} open".format(client_address))
                except socket.timeout as _:
                    logging.info(
                        "Socket conection not open - waiting for connection")

            if not connected:
                continue
            try:
                data = conn.recv(1024)
                if data:
                    text = data.decode().strip()
                    LOGGER.info(text)
                    if text == "!ALL":
                        logging.warning("ALL Packet Requested. Sending")
                        conn.sendall(self._genpacket('ALL'))
            except BlockingIOError as _:
                # nothing received from the client to send 'ALL'
                pass
            try:

                if time.time() - self.last_update_time < self.min_update_interval:
                    continue

                nbppacket = self._genpacket(nbppayload.packettype)

                LOGGER.warning(nbppacket.decode())

                conn.sendall(nbppacket)
                self.updatelist = []
                self.last_update_time = time.time()

            except Exception as _:  # TODO: Find the good one.
                logging.exception("Wifi Write Failed. Closing port.")
                conn.close()
                connected = False
