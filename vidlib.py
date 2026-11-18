# vidlib.py - bits shared by sync.py n mk.py

import json, subprocess, sys, pathlib
import numpy as np

HERE = pathlib.Path (__file__).parent
OUT  = HERE / "out"
LOG  = HERE / "takes.log"
CAM  = pathlib.Path.home () / "_/t/DCIM/Camera"
SR   = 16000                           # analysis sample rate

# hlg/pq phone video -> sdr bt709
TONEMAP = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
           "tonemap=tonemap=hable:desat=0,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def run (cmd, **kw):
   r = subprocess.run (cmd, capture_output=True, **kw)
   if r.returncode:
      sys.exit (f"failed: {' '.join (map (str, cmd))}\n"
                f"{r.stderr.decode (errors='replace') [-2000:]}")
   return r


def probe (path):
   r = run (["ffprobe", "-v", "error", "-show_streams", "-show_format",
             "-of", "json", str (path)])
   return json.loads (r.stdout)


def streams (info, kind):
   return [s for s in info ["streams"] if s ["codec_type"] == kind]


def start (s):
   return float (s.get ("start_time", 0) or 0)


def isHdr (info):
   v = streams (info, "video") [0]
   return v.get ("color_transfer") in ("arib-std-b67", "smpte2084")


def fps (info):
   n, d = streams (info, "video") [0] ["avg_frame_rate"].split ("/")
   return float (n) / float (d) if float (d) else 30.0


def audio (path, info, idx=0):
   "mono SR float32 of audio stream idx, n its container start time"
   r = run (["ffmpeg", "-v", "error", "-i", str (path),
             "-map", f"0:a:{idx}", "-ac", "1", "-ar", str (SR),
             "-f", "f32le", "-"])
   return (np.frombuffer (r.stdout, np.float32),
           start (streams (info, "audio") [idx]))


def newestObs ():
   if LOG.exists ():
      ln = LOG.read_text ().strip ().splitlines ()
      if ln:
         return pathlib.Path (ln [-1].split ("  ", 1) [1])
   sys.exit ("no takes.log yet - pass the obs file")


def newestPhone ():
   vids = sorted (CAM.glob ("*.mp4"), key=lambda p: p.stat ().st_mtime)
   if not vids:
      sys.exit (f"no phone vids in {CAM}")
   return vids [-1]


def syncFile (obsPath):
   return OUT / (pathlib.Path (obsPath).stem + ".sync.json")


def fstart (info):
   "ffmpeg's -ss is relative to this"
   return float (info ["format"].get ("start_time", 0) or 0)
