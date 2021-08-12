"""PySolarFrontier interacts as a library to communicate with
Solar Frontier inverters."""
from datetime import date

import aiohttp


class Sensor(object):
    """Sensor definition"""

    def __init__(self, key, name, unit='', per_day_basis=False,
                 per_total_basis=False):
        self.key = key
        self.name = name
        self.unit = unit
        self.value = None
        self.per_day_basis = per_day_basis
        self.per_total_basis = per_total_basis
        self.date = date.today()
        self.enabled = False


class Sensors(object):
    """Solar Frontier inverter sensors"""

    def __init__(self):
        self.__s = []
        self.add(
            (
                Sensor("day", "today_yield", "kWh", True),
                Sensor("month", "month_yield", "kWh", False),
                Sensor("year", "year_yield", "kWh", False),
                Sensor("total", "total_yield", "MWh", False, True)
            )
        )

    def __len__(self):
        """Length."""
        return len(self.__s)

    def __contains__(self, key):
        """Get a sensor using either the name or key."""
        try:
            if self[key]:
                return True
        except KeyError:
            return False

    def __getitem__(self, key):
        """Get a sensor using either the name or key."""
        for sen in self.__s:
            if sen.name == key or sen.key == key:
                return sen
        raise KeyError(key)

    def __iter__(self):
        """Iterator."""
        return self.__s.__iter__()

    def add(self, sensor):
        """Add a sensor, warning if it exists."""
        if isinstance(sensor, (list, tuple)):
            for sss in sensor:
                self.add(sss)
            return

        if not isinstance(sensor, Sensor):
            raise TypeError("pysolarfrontier.Sensor expected")

        if sensor.name in self:
            old = self[sensor.name]
            self.__s.remove(old)

        self.__s.append(sensor)


class SF(object):
    """Provides access to SF inverter data"""

    def __init__(self, host):
        self.host = host
        self.url = "http://{0}/".format(self.host)
        self.url_day = self.url + 'gen.yield.day.chart.js'
        self.url_month = self.url + 'gen.yield.month.chart.js'
        self.url_year = self.url + 'gen.yield.year.chart.js'
        self.url_total = self.url + 'gen.yield.total.chart.js'

    async def get_sensor_value(session, url, total_yield=False):
        """Get solar production values from SF inverter"""
        try:
            if total_yield:
                async with session.get(url) as response:
                    async for line in response.content:
                        if line:
                            line = line.decode()
                            if "innerHTML" in line:
                                line = line[53:-2].split(' ')
                                line = list(filter(None, line))
                                return line[0][:-4]
            else:
                async with session.get(url) as response:
                    async for line in response.content:
                        if line:
                            line = line.decode()
                            if "innerHTML" in line:
                                line = line[53:-2].split(' ')
                                line = list(filter(None, line))
                                return line[0][:-3]
        except aiohttp.client_exceptions.ServerDisconnectedError as err:
            raise UnexpectedResponseException(err)

    async def read(self, sensors):
        """Returns necessary sensors from SF inverter"""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout,
                                             raise_for_status=True) as session:
                url_day = self.url_day
                url_month = self.url_month
                url_year = self.url_year
                url_total = self.url_total
                at_least_one_enabled = False

                for sen in sensors:
                    if sen.key == 'day':
                        sen.value = await SF.get_sensor_value(session, url_day)
                        sen.date = date.today()
                        sen.enabled = True
                        at_least_one_enabled = True
                    elif sen.key == 'month':
                        sen.value = await SF.get_sensor_value(session,
                                                              url_month)
                        sen.date = date.today()
                        sen.enabled = True
                        at_least_one_enabled = True
                    elif sen.key == 'year':
                        sen.value = await SF.get_sensor_value(session,
                                                              url_year)
                        sen.date = date.today()
                        sen.enabled = True
                        at_least_one_enabled = True
                    elif sen.key == 'total':
                        sen.value = await SF.get_sensor_value(session,
                                                              url_total,
                                                              total_yield=True)
                        sen.date = date.today()
                        sen.enabled = True
                        at_least_one_enabled = True

                if not at_least_one_enabled:
                    raise NoSensorsEnabledException("No sensors enabled")
                return True

        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionErrorException(err)
        except aiohttp.client_exceptions.ClientResponseError as err:
            raise UnexpectedResponseException(err)


class ConnectionErrorException(Exception):
    """Exception for connection error."""
    def __init__(self, message):
        Exception.__init__(self, message)


class UnexpectedResponseException(Exception):
    """Exception for unexpected status code"""
    def __init__(self, message):
        Exception.__init__(self, message)


class NoSensorsEnabledException(Exception):
    """Exception for no sensors enabled"""
    def __init__(self, message):
        Exception.__init__(self, message)
