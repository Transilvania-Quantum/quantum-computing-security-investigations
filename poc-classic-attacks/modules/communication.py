"""
Handle the communication to the simulated c2 server.

Provides a wrapper over the functionality for c2 connection and message dispatching.
"""
import json
import http.client
import socket


class C2Communication:
    """A class to handle the logic for connecting and sending message to a server."""

    def __init__(self, ip, port):
        """
        Initialize the C2Communication instance.

        This class is responsible for establishing a connection to a given ednpoint.
        The endpoint is clasically identified by (ip, port) pair. It establishes
        a connection which can later be used.

        Parameters
        ----------
        ip : str
            Represents the IP to connect to.
        port : str
            Represents the port to connect to.
        """
        self._ip = ip
        self._port = port
        self._connection = None

        self._connect()

    def _connect(self):
        """
        Establish a HTTP connection to the specifified endpoint.

        All traffic will not be encrypted, as this is just for simulating and
        testing PoC like application.

        Returns
        -------
        None
        """
        print("[*] Attempting to connect to c2: %s %d" % (self._ip, self._port))

        self._connection = http.client.HTTPConnection(self._ip, self._port)
        self._connection.request("GET", "/")
        self._response = self._connection.getresponse()

    @staticmethod
    def get_ip():
        """
        Find the ip of the current machine.

        Connects to 8.8.8.8 and then uses the getsockname()
        to find the ip of the current machine.

        Returns
        -------
        The ip of the local machine.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()

        return ip

    def send(self, api, data):
        """
        Send a post request to the active connection.

        It will use the application/json content type hardcoded.
        No response will be returned, as we'll just log it and move on.

        Parameters
        ----------
        api : str
            Represents the url of the request.
        data : str
             A dictionary, list of tuples, bytes or a file object to send to the specified url.

        Returns
        -------
        None
        """
        headers = {"Content-type": "application/json"}
        jdata = json.dumps(data)

        print("[*] Sending data to c2: %s" % (jdata))
        self._connection.request("POST", api, jdata, headers)

        response = self._connection.getresponse()
        print("[*] Received response: %s" % (response.read().decode("utf-8")))
