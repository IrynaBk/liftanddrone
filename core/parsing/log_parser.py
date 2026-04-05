"""Binary log parsing service."""

from __future__ import annotations

from typing import Dict, List, Optional

from pymavlink import mavutil

from core.constants import MESSAGE_TYPES


def parse_log(filepath: str) -> Dict[str, List[Dict]]:
    """Parse an ArduPilot Dataflash binary log file."""
    data = {msg_type: [] for msg_type in MESSAGE_TYPES}

    try:
        mlog = mavutil.mavlink_connection(filepath, dialect="ardupilotmega")
    except Exception as exc:
        raise RuntimeError(f"Cannot open log file '{filepath}': {exc}") from exc

    first_timestamp_us = None

    while True:
        msg = mlog.recv_match()
        if msg is None:
            break

        msg_type = msg.get_type()
        if msg_type not in MESSAGE_TYPES or not hasattr(msg, "TimeUS"):
            continue

        time_us = msg.TimeUS
        if first_timestamp_us is None:
            first_timestamp_us = time_us

        time_s = (time_us - first_timestamp_us) / 1_000_000.0
        msg_dict = msg.to_dict()
        msg_dict["TimeS"] = time_s
        data[msg_type].append(msg_dict)

    mlog.close()
    return data


def get_firmware_version(data: Dict) -> Optional[str]:
    """Extract firmware version string from MSG records, or None."""
    for msg in data.get("MSG", []):
        message = msg.get("Message", "")
        if "ArduCopter" in message or "ArduPlane" in message or "Rover" in message:
            return message
    return None
