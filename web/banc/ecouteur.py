"""Écouteur local des mesures (127.0.0.1:8765) : ajoute chaque POST, horodaté, à un fichier JSONL."""

import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

SORTIE = sys.argv[1]


class H(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        corps = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        with open(SORTIE, "a") as f:
            f.write(json.dumps({"recu": time.time() * 1000, "corps": json.loads(corps)}) + "\n")
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def log_message(self, *a):
        pass


HTTPServer(("127.0.0.1", 8765), H).serve_forever()
