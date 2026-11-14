#!/usr/bin/env python3
"""Serve the built site locally with the response headers from _site/_headers applied.

For checking pages under the production Content-Security-Policy (Netlify
applies _headers in production; plain `python3 -m http.server` does not).

    python3 web/serve.py [--dir _site] [--port 8000] [--bind 127.0.0.1]
"""
import argparse
import functools
import http.server
import os
import re


def parse_headers(path):
    """Netlify _headers file -> [(compiled path pattern, [(name, value), ...])]."""
    rules = []
    if not os.path.isfile(path):
        return rules
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line[0].isspace():
                pattern = "^" + re.escape(line.strip()).replace(r"\*", ".*") + "$"
                rules.append((re.compile(pattern), []))
            elif rules and ":" in line:
                name, value = line.strip().split(":", 1)
                rules[-1][1].append((name.strip(), value.strip()))
    return rules


class Handler(http.server.SimpleHTTPRequestHandler):
    rules = []

    def _rule_headers(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        out = {}
        for pattern, headers in self.rules:
            if pattern.match(path):
                for name, value in headers:
                    out[name.lower()] = (name, value)
        return out

    def send_header(self, keyword, value):
        # A Content-Type from _headers replaces the guessed one.
        if keyword.lower() == "content-type" and "content-type" in self._rule_headers():
            return
        super().send_header(keyword, value)

    def end_headers(self):
        for name, value in self._rule_headers().values():
            super().send_header(name, value)
        super().end_headers()

    def send_error(self, code, message=None, explain=None):
        page = os.path.join(self.directory, "404.html")
        if code == 404 and os.path.isfile(page):
            with open(page, "rb") as f:
                body = f.read()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return
        super().send_error(code, message, explain)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=os.path.join(root, "_site"))
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--bind", default="127.0.0.1",
                    help="address to listen on; 0.0.0.0 lets other devices on the network reach it")
    args = ap.parse_args()
    Handler.rules = parse_headers(os.path.join(args.dir, "_headers"))
    handler = functools.partial(Handler, directory=args.dir)
    with http.server.ThreadingHTTPServer((args.bind, args.port), handler) as httpd:
        print(f"serving {args.dir} at http://{args.bind}:{args.port}/ with {len(Handler.rules)} header rules")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
