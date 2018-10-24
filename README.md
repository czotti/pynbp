# pynbp - Python Numeric Broadcast Protocol

Python Numeric Broadcast Protocol

This module implements HP Tuners / Track Addict Numeric Broadcast Protocol

http://racerender.com/TrackAddict/docs/NBP%20Specification%20V1.pdf

Example:
        $ python examples/example1.py

Attributes:
    nbpqueue - queue.Queue() for sending pauloads into the class
        - Format: tuple-> ([list of NbpKPIs], 'PACKETTYPE')
            - Packet types 'UPDATE', 'ALL' and 'METADATA' supported
    device: Bluetooth Serial device for comms
    device_name: Device name sent via metadata packet to host
    protocol_version: NBP1 as defined. 
    max_update_interval: Minimum interval to send packets. If using this with high rate senders, send 'ALL' packets as updates will miss updates. 

    See racerender docs for unit types.

Todo:
    * None at this time
