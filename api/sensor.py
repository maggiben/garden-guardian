import json
import random
import urllib3


http = urllib3.PoolManager()


# Helper function to fetch lat lon data
def fetch_json(url):
    """Fetch JSON from url."""
    response = http.request('GET', url)
    if not 200 <= response.status <= 299:
        raise Exception(f'[HTTP - {response.status}]: {response.reason}')
    config_fresh = json.loads(response.data.decode('utf-8'))
    return config_fresh


class Sensor:
    def __init__(self):
        self.id = ''
        self.temperature = None
        self.pressure = None
        self.humidity = None

    # def parse_measurement(self):
    #     lines = input_data.strip().split("\n")
    #     data = {}
    #     data["sensor"] = sensor_name
    #     current_section = None

    #     for line in lines:
    #         if line.startswith(f"[{sensor_name}:") and line.endswith("]"):
    #             current_section = line.strip("[").strip(f"{sensor_name}").strip(":").strip("]")
    #             data[current_section] = {}
    #         elif line.startswith("[") and line.endswith("]"):
    #             current_section = None
    #         else:
    #             if current_section:
    #                 try:
    #                     key, value = map(str.strip, line.split(":", 1))
    #                     data[current_section][key] = value
    #                 except ValueError:
    #                     continue

    #     return data

    def generate_measurement(self):
        return round(random.uniform(0, 100))

    def geo(self):
        """
        Get GEO location from https://freegeoip.app/json/'.
        :return: Returns a dictionary with `latitude` and `longitude` key.
        """
        try:
            return fetch_json('https://freegeoip.app/json/')
        except Exception:
            return {
                'latitude':  self.generate_measurement(),
                'longitude':  self.generate_measurement(),
            }
