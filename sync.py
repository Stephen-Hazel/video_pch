#!/home/sh/web/video_pch/.venv/bin/python
# sync.py - line up phone vid with an obs recording off its audio
#   sync.py [-t N] [obs.mkv [phone.mp4]]
# defaults: last take in takes.log, newest vid in DCIM/Camera,
#   obs track 2 (mixer = what the speakers play, so what the phone hears)
# each CH secs chunk of phone audio is searched for over the whole obs
# take; the offset most chunks agree on wins.  first n last agreeing
# chunks are refined to the sample on their sharpest note -> drift
# writes out/<take>.sync.json  n  out/<take>.note1.jpg (n note2) to eyeball
# mapping:  phone time = a * obs time + b

import argparse, json, sys
import numpy as np
from vidlib import *

HOP   = 32                             # 2ms onset frames (fine)
EH    = 160                            # 10ms envelope frames (coarse)
CH    = 20.0                           # phone secs per coarse chunk
AGREE = 0.05                           # chunks agree within 50ms


def onsets (x):
   "how much each 2ms frame's level jumps over the prior 20ms max"
   n   = len (x) // HOP
   amp = np.sqrt ((x [:n*HOP].reshape (n, HOP) ** 2).mean (1))
   pad = np.concatenate ([np.zeros (10), amp])
   prv = np.lib.stride_tricks.sliding_window_view (pad, 10) [:n].max (1)
   return np.maximum (amp - prv, 0)


def coarse (x):
   "10ms log level jumps, normalized"
   n = len (x) // EH
   e = np.log10 (np.sqrt ((x [:n*EH].reshape (n, EH) ** 2).mean (1)) +
                 1e-6)
   d = np.maximum (np.diff (e, prepend=e [0]), 0)
   return (d - d.mean ()) / (d.std () + 1e-9)


def chunks (oa, o0, pa, p0):
   "(offset phone - obs, phone chunk start, peak ratio) per phone chunk"
   oc, pc = coarse (oa), coarse (pa)
   w, n   = int (CH * SR / EH), len (oc)
   if n <= w:
      return []
   fo = np.fft.rfft (oc, n)
   r  = []
   for i in range (0, len (pc) - w + 1, w):
      if np.sqrt ((pa [i*EH:(i+w)*EH] ** 2).mean ()) < 1e-3:
         continue                      # silent chunk
      c  = np.fft.irfft (fo * np.conj (np.fft.rfft (pc [i:i+w], n)), n)
      c  = c [:n-w+1]
      k  = int (np.argmax (c))
      rt = c [k] / max (np.partition (c, -200) [-200], 1e-9)
      pt = p0 + i * EH / SR
      r.append ((pt - (o0 + k * EH / SR), pt, float (rt)))
   return r


def agree (ch):
   "biggest group of chunks within AGREE of each other, in phone order"
   best = []
   for off, _, _ in ch:
      g = [c for c in ch if abs (c [0] - off) < AGREE]
      if (len (g), sum (c [2] for c in g)) > \
         (len (best), sum (c [2] for c in best)):
         best = g
   return best


def seg (x, x0, t0, t1):
   "samples of x (starting at time x0) for time t0..t1, n real start"
   i0 = max (0, int (round ((t0 - x0) * SR)))
   i1 = max (i0, int (round ((t1 - x0) * SR)))
   return x [i0:i1], x0 + i0 / SR


def env (x):
   x = np.convolve (np.abs (x), np.ones (16) / 16, "same")   # 1ms
   return x - x.mean ()


def refine (oa, o0, pa, p0, c):
   "sharpest obs note in chunk c n its offset refined to the sample"
   off, pt, _ = c
   a, at = seg (oa, o0, pt - off, pt - off + CH)
   oo = onsets (a)
   if not len (oo):
      return off, pt - off
   tn = at + int (np.argmax (oo)) * HOP / SR
# 1ms envelopes, +-10ms
   ea, eat = seg (oa, o0, tn - 0.05, tn + 0.30)
   eb, ebt = seg (pa, p0, tn + off - 0.06, tn + off + 0.31)
   if len (ea) and len (eb) > len (ea):
      k   = np.correlate (env (eb), env (ea), "valid")
      off = ebt + int (np.argmax (k)) / SR - eat
   return off, tn


def still (obs, oi, phone, pi, to, tp, path):
   tm = (TONEMAP + ",") if isHdr (pi) else ""
   run (["ffmpeg", "-y", "-v", "error",
         "-ss", f"{to - fstart (oi):.4f}", "-i", str (obs),
         "-ss", f"{tp - fstart (pi):.4f}", "-i", str (phone),
         "-filter_complex",
         f"[0:v]scale=-2:540[a];[1:v]{tm}scale=-2:540[b];[a][b]hstack",
         "-frames:v", "1", str (path)])


def main ():
   ap = argparse.ArgumentParser ()
   ap.add_argument ("obs",   nargs="?")
   ap.add_argument ("phone", nargs="?")
   ap.add_argument ("-t", type=int, default=2, help="obs track to match")
   o = ap.parse_args ()
   obs   = pathlib.Path (o.obs)   if o.obs   else newestObs ()
   phone = pathlib.Path (o.phone) if o.phone else newestPhone ()
   oi, pi = probe (obs), probe (phone)
   trk = o.t if o.t <= len (streams (oi, "audio")) else 1
   print (f"obs:   {obs}  (track {trk})\nphone: {phone}")
   oa, o0 = audio (obs, oi, trk - 1)
   pa, p0 = audio (phone, pi, 0)
   oEnd, pEnd = o0 + len (oa) / SR, p0 + len (pa) / SR

   ch = chunks (oa, o0, pa, p0)
   if not ch:
      sys.exit ("recordings too short (or phone silent)")
   g = agree (ch)
   print (f"{len (g)} of {len (ch)} phone chunks agree:  "
          f"phone = obs {g [0][0]:+.3f}s")
   if len (g) < 2:
      print ("  weak match - check the still")

   off1, tn1 = refine (oa, o0, pa, p0, g [0])
   print (f"note 1 at obs {tn1:.3f}s  phone = obs {off1:+.4f}s")
   a, b, notes, conf = 1.0, off1, [tn1], [g [0][2]]
   off2, tn2 = refine (oa, o0, pa, p0, g [-1]) if len (g) > 1 \
               else (off1, tn1)
   if tn2 - tn1 > 20:
      drift = (off2 - off1) / (tn2 - tn1)
      print (f"note 2 at obs {tn2:.3f}s  phone = obs {off2:+.4f}s  "
             f"drift {drift * 1e6:+.0f}ppm")
      if abs (off2 - off1) < 0.1 and abs (drift) < 500e-6:
         a, b = 1 + drift, off1 - drift * tn1
         notes.append (tn2)
         conf.append (g [-1][2])
      else:
         print ("  doesn't agree with note 1 - ignoring drift")
   else:
      print ("too short to measure drift (fine for short takes)")

   OUT.mkdir (exist_ok=True)
   sf = syncFile (obs)
   sf.write_text (json.dumps ({
      "obs": str (obs), "phone": str (phone), "a": a, "b": b,
      "notes": notes, "conf": conf, "agree": [len (g), len (ch)],
      "obsFps": fps (oi), "obsTracks": len (streams (oi, "audio")),
      "obsStart": fstart (oi), "phoneStart": fstart (pi),
      "phoneHdr": isHdr (pi),
      "from": max (o0, (p0 - b) / a), "to": min (oEnd, (pEnd - b) / a)
   }, indent=1))
   print (f"wrote {sf}")
   for i, t in enumerate (notes, 1):
      jp = OUT / f"{obs.stem}.note{i}.jpg"
      still (obs, oi, phone, pi, t, a * t + b, jp)
      print (f"wrote {jp}")


main ()
