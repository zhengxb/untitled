#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys, logging, argparse, json, re, wave, traceback
from tornado.ioloop import IOLoop
from tornado.httpclient import HTTPRequest
from tornado.websocket import websocket_connect
from time import time
from datetime import datetime
from functools import partial
from array import array

#-------------------------------------------------
# parse command line

parser = argparse.ArgumentParser(
             prog="krcli.py",
             usage="%(prog)s [-options] -action [iterations]",
             add_help=False,
             formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=45, width=100)
)
actions = parser.add_argument_group("specify one action").add_mutually_exclusive_group(required=True)
actions.add_argument("-i", "--getinfo", action="store_true", help="get server info")
actions.add_argument("-c", "--create", action="store_true", help="create/end session")
actions.add_argument("-d", "--detach", action="store_true", help="create detached session")
actions.add_argument("-e", "--end", metavar="sessionId", nargs="?", const="", help="end existing/indicated session")
actions.add_argument("-r", "--recognize", metavar="audioFile", help="recognize audio from wav/8kHz raw file")
actions.add_argument("-R", metavar="audioFile", help="recognize 16kHz raw audio from file")
actions.add_argument("-f", "--file", metavar="commandFile", help="execute protocol requests from file")
options = parser.add_argument_group("options")
options.add_argument("-h", "--help", action="help", help="show this help message and exit")
options.add_argument("-s", "--serverUrl", metavar="url", default="ws://192.168.1.167:8078/", help="server URL, default=ws://localhost:8078/")
options.add_argument("-p", "--protocol", metavar="pver", default="1.0", help="protocol version, default=1.0")
options.add_argument("-t", "--timeout", metavar="sec", type=float, default=2.0, help="server response timeout in seconds, default=2.0")
options.add_argument("-a", "--attach", action="store_true", help="attach to existing session (effective with -r, -f only)")
options.add_argument("-b", "--bufms", metavar="ms", type=int, default=20, help="audio buffer size in ms, default=20")
options.add_argument("-x", "--xrate", metavar="xr", type=float, default=1.0, help="audio rate factor: default=1.0 (realtime), fastest=+inf")
options.add_argument("--lang", metavar="langcode", default="cmn-CHN", help="language used for recognition, default=eng-USA")
options.add_argument("-l", "--loglevel", metavar="lvl", choices=["fatal","error","warn","info","debug"], default="info", help="fatal, error, warn, default=info, debug")
options.add_argument("-L", "--logfile", metavar="fn", nargs="?", const=True, help="log to file, default fn=krcli-{datetimestamp}.log")
options.add_argument("-q", "--quiet", action="store_true", help="disable console logging")
options.add_argument("-T", "--traceback", action="store_true", help="enable stack dump")
options.add_argument("iterations", nargs="?", type=int, const=1, help="iterations to run, default=1")
args = parser.parse_args()

# validate file/rate for -r/-R
try:
    args.rate = None
    if args.R:
        args.rate = 16000
        args.recognize = args.R
    if args.recognize:
        # verify readable
        with open(args.recognize, "r") as audio_file:
            pass
        if not args.rate:
            args.rate = 8000 # default
        fn = args.recognize
        if fn.lower().endswith(".wav"):
            wf = wave.open(fn, "r")
            rate = wf.getparams()[2]
            wf.close()
            if rate in [8000, 16000]:
                args.rate = rate
            else:
                raise RuntimeError("{0}: unsupported rate {1}".format(fn, rate))
except IOError as e:
    print "{0}: {1}".format(e.strerror, e.filename)
    sys.exit(1)

#-------------------------------------------------
# set up logging

logging.basicConfig(level=logging.WARN, format="%(asctime)s %(levelname)-5s: %(message)s")
if args.quiet:
    logging.getLogger().handlers[0] = logging.NullHandler()
log = logging.getLogger("com.nuance.coretech.kr.client")
logging.addLevelName(50, "FATAL")
log.setLevel(logging.getLevelName(args.loglevel.upper()))
def generate_log_file_name():
    return "krcli-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".log"

if args.logfile:
    logfile = args.logfile if type(args.logfile) is str else generate_log_file_name()
    fh = logging.FileHandler(logfile, mode="w")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s: %(message)s"))
    log.addHandler(fh)

#-------------------------------------------------
# audio conversion

# ulaw to linear PCM conversion
ulaw_exponents = [ 0, 132, 396, 924, 1980, 4092, 8316, 16764 ];
ulaw2linear = []
for ulaw in range(256):
    ulawByte = ~ulaw
    sign = ulawByte & 0x80
    exponent = (ulawByte >> 4) & 0x7
    mantissa = ulawByte & 0xf
    linear = ulaw_exponents[exponent] + (mantissa << (exponent+3))
    if sign: linear = -linear
    ulaw2linear.append(linear);

# alaw to linear PCM conversion
alaw2linear = []
for alaw in range(256):
    alaw ^= 0x55
    i = ((alaw & 0xf) << 4) + 8
    seg = (alaw & 0x70) >> 4
    if seg:
        i = (i + 0x100) << (seg - 1)
    alaw2linear.append(i if alaw & 0x80 else -i);

#-------------------------------------------------
# define client implementation

methods = [
    "CreateSession", "EndSession", "Load", "Recognize", "StartRecognitionTimers", "Stop",
    "AudioText", "EndOfInput", "Ping", "GetInfo",
    "@Audio", # convert file to binary dataframes
    "@Pause"  # synchronous delay
]

overlap_allowed = {
    None : methods,
    "Load": [ "Stop", "Ping", "GetInfo", "@Pause" ],
    "Recognize":  [ "StartRecognitionTimers", "AudioText", "EndOfInput", "Stop", "Ping", "GetInfo", "@Audio", "@Pause" ]
}

def pretty_json(msg):
    return json.dumps(msg, indent=4, separators=(',', ': '))

def packetize(fn, bufms, rate, encoding, sample_bytes):
    samples = None
    if fn.lower().endswith(".wav"):
        wf = wave.open(fn, "r")
        wf_params = wf.getparams()[0:5]
        if wf_params == (1, 2, rate, wf.getnframes(), "NONE"):
            samples = wf.readframes(wf.getnframes())
        elif wf_params == (1, 1, rate, wf.getnframes(), "ULAW"):
            samples = array('h', [ ulaw2linear[ord(ulaw)] for ulaw in wf.readframes(wf.getnframes()) ]).tostring()
        elif wf_params == (1, 1, rate, wf.getnframes(), "ALAW"):
            samples = array('h', [ alaw2linear[ord(alaw)] for alaw in wf.readframes(wf.getnframes()) ]).tostring()
        else:
            raise RuntimeError("{0}: unsupported audio format {1}".format(fn, wf.getparams()))
        wf.close()
    else:
        samples = open(fn, "rb").read() # assume headerless
    packet_size = min(rate * bufms * sample_bytes / 1000, len(samples))
    packet_ms = int(float(packet_size) / sample_bytes / rate * 1000)
    packets = [ samples[x:x+packet_size] for x in xrange(0, len(samples), packet_size) ]
    num_packets = len(packets)-1 + float(len(packets[-1])) / packet_size if len(packets) > 1 else 1
    fnum_packets = ("%.1f" % num_packets).rstrip("0").rstrip(".")
    log.info("converted {0} bytes {1:g}kHz {2} to {3} {4:g}ms packet{5}".format(
        len(samples), rate/1000.0, encoding, fnum_packets, packet_ms, num_packets>1 and "s" or ""))
    packets.reverse() # so .pop() yields the next packet from list end
    return packets

def dig(start, *keys):
    child = start
    for key in keys:
        if type(child) is dict and key in child:
            child = child[key]
        else:
            return None
    return child

class KrClient:
    
    def __init__(self, actions, completion_callback):
        self._ws = None
        self._connection_start_time = None
        self._actions = list(reversed(actions))
        self._action = None
        self._in_progress_action = None
        self._session_id = None
        self._next_request_id = 1
        self._bufms = None
        self._xrate = None
        self._sample_rate = 8000      #
        self._sample_encoding = "pcm" # defaults
        self._sample_bytes = 2        #
        self._packets = None
        self._first_packet_time = None
        self._last_packet_time = None
        self._timeout_futures = {}
        self._completion_callback = completion_callback
        IOLoop.instance().add_callback(self._connect)

    def _connect(self):
        request = HTTPRequest(args.serverUrl, validate_cert=False)
        log.debug("connecting to " + request.url)
        IOLoop.instance().add_future(websocket_connect(request), self._ws_connected)

    def _ws_connected(self, conn_future):
        self._connection_start_time = time()
        log.debug("websocket connected")
        try:
            self._ws = conn_future.result()
            self._ws.read_message(callback=self._ws_message)
            self._next_action()
        except Exception as e:
            log.fatal("{0} {1}".format(args.serverUrl, e))
            self._close(True)

    def _next_action(self):
        self._action = None
        if self._actions:
            self._action = self._actions[-1]
            method = self._action["method"]
            if method not in methods:
                raise RuntimeError("invalid method: {0}".format(method))
            if method == "EndSession" and args.end is not None and not self._session_id:
                log.info("no active session found")
                self._close()
            elif method in overlap_allowed[dig(self._in_progress_action, "method")]:
                self._actions.pop()
                if method == "@Pause":
                    delay = max(float(self._action.get("seconds") or 1.0), 0)
                    log.info("pause {0} seconds".format(delay))
                    self._timeout_futures["pause"] = IOLoop.instance().call_later(delay, self._pause_complete)
                elif method == "@Audio":
                    self._bufms = int(self._action.get("bufms") or args.bufms)
                    self._xrate = float(self._action.get("xrate") or args.xrate)
                    self._packets = packetize(self._action["audioFile"],
                                              self._bufms,
                                              self._sample_rate,
                                              self._sample_encoding,
                                              self._sample_bytes)
                    if self._packets:
                        self._packets_sent = 0
                        self._first_packet_time = time()
                        self._send_packet()
                    else:
                        log.warn("no audio from {0}".format(self._action["audioFile"]))
                        IOLoop.instance().add_callback(self._next_action)
                else:
                    self._send_request(self._action)
        else:
            self._close()

    def _close(self, failed=False):
        for future in self._timeout_futures.itervalues():
            IOLoop.instance().remove_timeout(future)
        self._ws and self._ws.close()
        IOLoop.instance().add_callback(self._completion_callback, failed)
    
    def _pause_complete(self):
        log.info("pause complete")
        del self._timeout_futures["pause"]
        self._next_action()

    def _next_packet_time(self):
        realtime_offset = self._packets_sent * self._bufms / 1000.0
        return max(self._first_packet_time + realtime_offset / self._xrate, time())

    def _send_packet(self):
        if self._packets:
            packet = self._packets.pop()
            log.debug("send audio packet {0}, {1} bytes".format(self._packets_sent+1, len(packet)))
            self._ws.write_message(packet, True)
            self._packets_sent += 1
            self._last_packet_time = time()
        if self._packets:
            self._timeout_futures["packet"] = IOLoop.instance().call_at(self._next_packet_time(), self._send_packet)
        else:
            log.info("sent {0} packets".format(self._packets_sent))
            self._timeout_futures.pop("packet", None)
            IOLoop.instance().add_callback(self._next_action)

    def _send_request(self, req):
        request_id = str(self._next_request_id)
        self._next_request_id += 1
        if self._session_id:
            req["sessionId"] = self._session_id
        req["requestId"] = request_id
        req["version"] = args.protocol
        msg = json.dumps(req)
        log.debug("request: {0}".format(msg))
        self._ws.write_message(msg)
        self._timeout_futures[request_id] = IOLoop.instance().call_later(args.timeout, partial(self._request_timeout, req))

    def _request_timeout(self, req):
        log.fatal("request timeout: {0}".format(json.dumps(req)))
        self._close(True)

    def _ws_message(self, message_future):
        message = message_future.result()
        if message is None:
            if self._timeout_futures or self._in_progress_action:
                log.error("websocket closed")
            else:
                log.debug("websocket closed")
            return

        try:
            message = message.encode("utf-8")
            msg = json.loads(message)
            method = msg.get("method")
            log.debug("message: {0}".format(message))
            if msg.get("responseTo") == "Audio":
                pass # ignore
            elif method == "Response":
                self._handle_response(msg)
            elif method == "Event":
                self._handle_event(msg)
            else:
                raise IOError("invalid method: " + method)
            self._ws.read_message(callback=self._ws_message) # rearm reader if possible
        except Exception as e:
            # oops
            log.fatal(e)
            args.traceback and traceback.print_exc()
            self._close(True)

    def _handle_response(self, rsp):
        log.info("{1}: {2}".format(rsp["method"], rsp["responseTo"], rsp["status"]))
        if rsp["status"] == "failed":
            raise IOError(pretty_json(rsp["errors"]))
        request_id = rsp["requestId"]

        if rsp["responseTo"] == "GetInfo" and not self._actions:
            log.info(pretty_json(rsp))

        # clear handler timeout, if any
        if request_id in self._timeout_futures:
            IOLoop.instance().remove_timeout(self._timeout_futures[request_id])
            del self._timeout_futures[request_id]

        # update state
        if request_id == dig(self._action, "requestId"):
            if rsp["status"] == "in-progress":
                if self._in_progress_action:
                    raise IOError("multiple in-progress status")
                log.debug("setting in progress action: {0}".format(self._action))
                self._in_progress_action = self._action
            elif rsp["status"] not in ["complete", "no-action"]:
                raise IOError("unexpected status")
        elif request_id == dig(self._in_progress_action, "requestId"):
            if rsp["status"] != "complete":
                raise IOError("unexpected status")
            self._in_progress_action = None
            if "packet" in self._timeout_futures:
                IOLoop.instance().remove_timeout(self._timeout_futures["packet"])
                del self._timeout_futures["packet"]
        else:
            raise IOError("unexpected request id: {0}".format(request_id))

        if rsp["responseTo"] == "CreateSession":
            self._session_id = rsp["sessionId"]
            audio_format = dig(self._action, "sessionParameters", "audioFormat") or "rate=8000"
            self._sample_rate = int(re.search("rate=(\d+)", audio_format).group(1))
            self._sample_encoding = "pcm" # L16 only
            self._sample_bytes = 2
            log.info("session language={0} rate={1}".format(dig(self._action, "languagePack", "language"), self._sample_rate))
        elif not self._session_id and rsp["responseTo"] == "GetInfo" and rsp["activeSessions"]:
            self._session_id = rsp["activeSessions"][0]
        
        self._next_action()

    def _handle_event(self, evt):
        if evt["event"] == "PartialResult" or evt["event"] == "FinalResult":
            cause = dig(evt, "data", "completion_cause")
            nbest = dig(evt, "data", "nBest") or []
            top = nbest and nbest[0]["formattedText"].encode("utf-8") or ""
            final = evt["event"] == "FinalResult"
            log.info("{0}: {1} {2:.2f} [{3}] {4}".format(evt["event"], cause, self._latency(final), len(nbest), top))
            #print top
        else:
            log.info("{0}".format(evt["event"]))
        log.debug("{0}".format(pretty_json(evt)))
        if evt["event"] == "EndOfSession":
            self._close()

    def _latency(self, final):
        if final and self._last_packet_time:
            return time() - self._last_packet_time
        elif not final and self._first_packet_time:
            return time() - self._first_packet_time
        else:
            return float("nan")

#-------------------------------------------------
# initialize actions

def handle_attach(actions):
    if args.attach and actions:
        if actions[0].get("method") == "CreateSession":
            actions[0] = {"method":"GetInfo"}
        else:
            actions.insert(0, {"method":"GetInfo"})

actions = None
create_session = {
    "method": "CreateSession",
    "languagePack": {"language":args.lang},
    "sessionParameters": { "detachedTimeout": "60s" },
    "clientData": {
        "companyName": "Nuance",
        "applicationName": "krtest",
        "applicationVersion": "0.0",
    }
}
if args.rate:
    create_session["sessionParameters"]["audioFormat"] = "audio/L16;rate={0}".format(args.rate)

if args.getinfo:
    actions = [ { "method": "GetInfo" } ]
elif args.create:
    actions = [ create_session, { "method": "EndSession" } ]
elif args.detach:
    create_session_detach = dict(create_session)
    create_session_detach["attach"] = False
    actions = [ create_session_detach ]
elif args.end is not None:
    if args.end == "":
        actions = [ { "method": "GetInfo" }, { "method": "EndSession" } ]
    else:
        actions = [ { "method": "EndSession", "sessionId": args.end } ]
elif args.recognize is not None:
    actions = [
        create_session,
        { "method": "Recognize" },
        { "method": "@Audio", "audioFile": args.recognize },
        { "method": "EndOfInput" },
        { "method": "EndSession" },
    ]
    handle_attach(actions)
else:
    assert args.file is not None
    try:
        with open(args.file, "rb") as command_file:
            commands = command_file.read()
            actions = json.loads(re.sub(r"^\s*#[^\n]*\n", "", commands, flags=re.M))
            handle_attach(actions)
    except IOError as e:
        print "{0}: {1}".format(e.strerror, e.filename)
        sys.exit(1)

#-------------------------------------------------
# run iterations

iters_completed = 0
def completion(failed):
    global iters_completed
    iters_completed += 1
    if failed:
        log.fatal("iteration {0} failed".format(iters_completed))
        IOLoop.instance().stop()
        sys.exit(1)
    elif iters_completed < args.iterations:
        log.info("{0}/{1} iterations completed".format(iters_completed, args.iterations))
        KrClient(actions, completion)
    else:
        if iters_completed > 1:
            log.info("{0} iterations completed".format(iters_completed))
        IOLoop.instance().stop()

# catch ^C to suppress ugly exception message
try:
    KrClient(actions, completion)
    IOLoop.instance().start()
except KeyboardInterrupt:
    print; sys.exit(1)
