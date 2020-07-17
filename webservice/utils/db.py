from influxdb import InfluxDBClient
import time
import os

INFLUXDB_IP = os.getenv("INFLUXDB_IP")
INFLUXDB_PORT = 8086
INFLUXDB_DATABASE = os.getenv("INFLUXDB_DATABASE")


class Database:
    """Database"""

    def __init__(self):
        self._client = InfluxDBClient(
            host=INFLUXDB_IP,
            port=8086,
            username='xxx',
            password='xxx',
            database=INFLUXDB_DATABASE)

    def insert(self, table, index_dict):
        data_points = [{"measurement": table, "fields": index_dict}]
        result = self._client.write_points(data_points)
        return result

    def query(self, query_stat):
        result = self._client.query(query_stat)
        return result
