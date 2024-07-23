# Purpose

This repository includes basic proof-of-concept emulation scripts for traditional attacks aimed at Quantum providers.
It assumes a threat model where the attacker has compromised the victim's machine and is operating with the same user-level privileges.
To ensure no python package is damaged, we recommend running these scripts in a virtual machine, and installing the qiskit-related libraries in a virtual environment.

# Structure
> `quantum_daemon.py` acts as the attacker's script, quietly operating on the victim's machine.
    To see the usage, and all arguments description run with `--help` argument.
    Upon termination, cleanup will be performed to ensure no artefacts are left on the machine.

> `quantum_c2.py` serves as a simulated "command and control" (C2) server. The daemon connects to this server and tries to exfiltrate data.
    This receives circuits from the daemon, and also connection tokens. Upon receiving a token, it is utilized to inquire about the job history of circuits that were executed previously.

Each script has comments explaining the function and the logic inside the current module.
