import hashlib
import json
import subprocess
from configparser import ConfigParser
from uuid import uuid4

from netaddr import EUI, mac_eui48

from kafka_test.models.config import Settings, get_settings

settings: Settings = get_settings()

def get_process(process_name):
    try:
        # Run pgrep and count the number of matching process IDs
        output = subprocess.check_output(["pgrep", "-f", process_name])
        process_count = len(output.splitlines())
        new_instance = settings.default_worker + str(process_count)
        return new_instance
    except subprocess.CalledProcessError:
        return f"{settings.default_worker}1"

def decode_hexastr(hexa_str) -> str:
    prefix_remove = hexa_str.replace("0x", "")
    try:
        if len(prefix_remove) == 12:
            mac_address = ":".join(
                prefix_remove[i : i + 2] for i in range(0, len(prefix_remove), 2)
            )
            return mac_address
        if len(prefix_remove) > 12:
            decoded_string = "".join(
                chr(int(prefix_remove[i : i + 2], 16))
                for i in range(0, len(prefix_remove), 2)
            )
            return decoded_string
        else:
            return prefix_remove
    except ValueError:
        return hexa_str

def mac2EUI(mac: str):
    eui_mac = str(EUI(mac, dialect=mac_eui48))
    return eui_mac

def parse_properties(file_path):
    config = ConfigParser()
    config.read(file_path)

    parsed_config = {}
    for key, value in config["kafka-config"].items():
        try:
            parsed_value = eval(value)
        except (NameError, SyntaxError):
            parsed_value = value

        parsed_config[key] = parsed_value

    return parsed_config

def compute_hash(payload):
    encoded_payload = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(encoded_payload).hexdigest()

def generate_uuid4():
    session_id = str(uuid4())
    return session_id

