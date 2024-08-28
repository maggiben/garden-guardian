from cgi import print_environ
import configparser
import json
import os
from datetime import datetime
from uuid import uuid4
from influxdb_client import Authorization, InfluxDBClient, Permission, PermissionResource, Point, WriteOptions
from influxdb_client.client.authorizations_api import AuthorizationsApi
from influxdb_client.client.bucket_api import BucketsApi
from influxdb_client.client.flux_table import FluxStructureEncoder
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.write_api import SYNCHRONOUS

from api.sensor import Sensor
from influxdb_client.domain.dialect import Dialect

config = configparser.ConfigParser()
config.read('config.ini')

def get_buckets():
    influxdb_client = InfluxDBClient(url=config.get('APP', 'INFLUX_URL'),
                                     token=os.environ.get('INFLUX_TOKEN'),
                                     org=os.environ.get('INFLUX_ORG'))

    buckets_api = influxdb_client.buckets_api()
    buckets = buckets_api.find_buckets()
    return buckets


def get_device(device_id=None) -> {}:
    influxdb_client = InfluxDBClient(url=config.get('APP', 'INFLUX_URL'),
                                     token=os.environ.get('INFLUX_TOKEN'),
                                     org=os.environ.get('INFLUX_ORG'))
    # Queries must be formatted with single and double quotes correctly
    query_api = QueryApi(influxdb_client)
    device_filter = ''
    if device_id:
        device_id = str(device_id)
        device_filter = f'r.deviceId == "{device_id}" and r._field != "token"'
    else:
        device_filter = f'r._field != "token"'

    flux_query = f'from(bucket: "{config.get("APP", "INFLUX_BUCKET_AUTH")}") ' \
                 f'|> range(start: 0) ' \
                 f'|> filter(fn: (r) => r._measurement == "deviceauth" and {device_filter}) ' \
                 f'|> last()'
    
    response = query_api.query(flux_query)
    result = []
    for table in response:
        for record in table.records:
            try:
                'updatedAt' in record
            except KeyError:
                record['updatedAt'] = record.get_time()
                record[record.get_field()] = record.get_value()
            result.append(record.values)
    return result


def create_device(device_id=None):
    influxdb_client = InfluxDBClient(url=config.get('APP', 'INFLUX_URL'),
                                     token=os.environ.get('INFLUX_TOKEN'),
                                     org=os.environ.get('INFLUX_ORG'))

    if device_id is None:
        device_id = str(uuid4())

    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

    point = Point('deviceauth') \
        .tag("deviceId", device_id) \
        .field('key', f'fake_auth_id_{device_id}') \
        .field('token', f'fake_auth_token_{device_id}')

    client_response = write_api.write(bucket=config.get('APP', 'INFLUX_BUCKET_AUTH'), record=point)

    # write() returns None on success
    if client_response is None:
        return device_id

    # Return None on failure
    return None

def write_measurements(device_ids):
    # Check if device_ids is a string and convert it to a list
    if isinstance(device_ids, str):
        device_ids = [device_ids]
    
    for device_id in device_ids:
        print(f"Writing measurements for: {device_id}")
        write_measurement(device_id)

def write_measurement2(device_id):
    influxdb_client = InfluxDBClient(url=config.get('APP', 'INFLUX_URL'),
                                     token=os.environ.get('INFLUX_TOKEN'),
                                     org=os.environ.get('INFLUX_ORG'))
    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
    virtual_device = Sensor()
    coord = virtual_device.geo()

    point = Point("environment") \
        .tag("device", device_id) \
        .tag("TemperatureSensor", "virtual_bme280") \
        .tag("HumiditySensor", "virtual_bme280") \
        .tag("PressureSensor", "virtual_bme280") \
        .field("Temperature", virtual_device.generate_measurement()) \
        .field("Humidity", virtual_device.generate_measurement()) \
        .field("Pressure", virtual_device.generate_measurement()) \
        .field("Lat", coord['latitude']) \
        .field("Lon", coord['latitude']) \
        .time(datetime.utcnow())

    print(f"Writing: {point.to_line_protocol()}")
    client_response = write_api.write(bucket=config.get('APP', 'INFLUX_BUCKET'), record=point)

    # write() returns None on success
    if client_response is None:
        # TODO Maybe also return the data that was written
        return device_id

    # Return None on failure
    return None

def write_measurements(device_id, device_data):
    influxdb_client = InfluxDBClient(url=config.get('APP', 'INFLUX_URL'),
                                     token=os.environ.get('INFLUX_TOKEN'),
                                     org=os.environ.get('INFLUX_ORG'))
    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
    
    # Write a point for each relevant section in the device data
    sections = ['sensors', 'network', 'cpu', 'hdd', 'ram', 'flow']
    success = True

    for section in sections:
        section_data = device_data.get(section)
        if section_data:
            point = Point(section) \
                .tag("device", device_id)

            # Add fields for each key-value pair in the section
            for key, value in section_data.items():
                try:
                    # Convert to a float if possible
                    value = float(value.replace("'", "").replace("C", "").replace("MB", "").replace("G", "").replace("%", "").replace("ms", "").replace(",", "").strip())
                except ValueError:
                    pass  # Keep the original value if conversion fails
                point.field(key, value)

            point.time(datetime.utcnow())
            print(f"Writing: {point.to_line_protocol()}")
            client_response = write_api.write(bucket=config.get('APP', 'INFLUX_BUCKET'), record=point)

            # Check for write success
            if client_response is not None:
                success = False

    # Return the device_id if all writes were successful
    return device_id if success else None


def get_measurements2(query):
    influxdb_client = InfluxDBClient(url=config.get('APP', 'INFLUX_URL'),
                                     token=os.environ.get('INFLUX_TOKEN'),
                                     org=os.environ.get('INFLUX_ORG'))

    # Queries must be formatted with single and double quotes correctly
    query_api = QueryApi(influxdb_client)
    result = query_api.query_csv(query,
                                   dialect=Dialect(
                                       header=True,
                                       delimiter=",",
                                       comment_prefix="#",
                                       annotations=['group', 'datatype', 'default'],
                                       date_time_format="RFC3339"))
    
    response = ''
    for row in result:
        response += (',').join(row) + ('\n')
    return response

def get_measurements(device_id):
    influxdb_client = InfluxDBClient(
        url=config.get('APP', 'INFLUX_URL'),
        token=os.environ.get('INFLUX_TOKEN'),
        org=os.environ.get('INFLUX_ORG')
    )

    query_api = QueryApi(influxdb_client)

    # Construct a proper Flux query
    # flux_query = f'from(bucket: "{config.get("APP", "INFLUX_BUCKET_AUTH")}") ' \
    #             f'|> range(start: 0) ' \
    #             f'|> filter(fn: (r) => r["_measurement"] == "temperature")' \
    #             f'|> filter(fn: (r) => r["device"] == "{device_id}"' 

    # Api token: ILox_M3uZJXu9g8v8L-v1QgW0PHZlWqu4mVir_-d0eDj-gC4YzhNBuYuKuoyqAeFpg3odTi_e4mUQIejbiqcJg==

    try:
        query = f'''
            from(bucket: "{config.get("APP", "INFLUX_BUCKET")}")
            |> range(start: 0)
            '''

        response = query_api.query(query)
        result = []
        for table in response:
            for record in table.records:
                result.append(record)
        return result

    except Exception as e:
        print(f"Error executing query: {e}")
        return None


# TODO
# Function should return a response code
# Creates an authorization for a supplied deviceId
def create_authorization(device_id) -> Authorization:
    influxdb_client = InfluxDBClient(url=config.get('APP', 'INFLUX_URL'),
                                     token=os.environ.get('INFLUX_TOKEN'),
                                     org=os.environ.get('INFLUX_ORG'))

    authorization_api = AuthorizationsApi(influxdb_client)
    # get bucket_id from bucket
    buckets_api = BucketsApi(influxdb_client)
    buckets = buckets_api.find_bucket_by_name(config.get('APP', 'INFLUX_BUCKET'))  # function returns only 1 bucket
    bucket_id = buckets.id
    org_id = buckets.org_id
    desc_prefix = f'IoTCenterDevice: {device_id}'
    org_resource = PermissionResource(org_id=org_id, id=bucket_id, type="buckets")
    read = Permission(action="read", resource=org_resource)
    write = Permission(action="write", resource=org_resource)
    permissions = [read, write]
    authorization = Authorization(org_id=org_id, permissions=permissions, description=desc_prefix)
    request = authorization_api.create_authorization(authorization)
    return request




