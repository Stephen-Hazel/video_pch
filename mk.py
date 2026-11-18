#!/home/sh/web/vid/.venv/bin/python
# mk.py - render synced obs + phone vid in some layouts / voice sources
#   mk.py [obs.mkv | x.sync.json] [opts]   (default: last take)
#   -l stackv|stack|pip|all   layout (default all)
#        stackv  1080x1920  screen 1080x1312 top, whole phone 1080x608
#                under it.  portrait take (rec.py start -p) = top
#                1312 rows of the monitor, 1:1
#        stack   1920x1080  screen band on top, phone band below
#        pip     1920x1080  full screen, phone fills bottom right 1/4
#   -v none|mic|all           voiceover (default all)
#   -p SECS    just render a preview this long
#   --from T --to T     obs secs to keep (default whole overlap)
#   --nudge MS          phone video later by MS (earlier if -)
#   --sx --sy --px --py crop centre 0..1 of screen / phone (default .5,
#                       stackv --sx 0 = left side of screen, portrait
#                       take --sy 0 = top)
# music = obs track 2 (mixer), mic = obs track 3 (headset)
# writes out/<take>-<layout>-<voice>.mp4

import argparse, json, re
from vidlib import *

MUSIC = -18                            # LUFS each source is set to
VOICE = -16
FINAL = "I=-14:TP=-1:LRA=20"           # youtube'ish; LRA > input's
                                       # or loudnorm goes dynamic
AFMT  = "aformat=sample_rates=48000:channel_layouts=stereo"
VCHN  = ("highpass=f={hp},afftdn=nf=-25,"
         "acompressor=threshold=-24dB:ratio=3:attack=5:release=120")
DUCK  = "sidechaincompress=threshold=0.05:ratio=4:attack=20:release=300"


def fill (w, h, cx, cy):
   return (f"scale={w}:{h}:force_original_aspect_ratio=increase:"
           f"flags=lanczos,crop={w}:{h}:(iw-{w})*{cx}:(ih-{h})*{cy},"
           "setsar=1")


def video (lay, s, o):
   "filter_complex video part ending in [v]"
   f   = s ["obsFps"]
   ph  = (TONEMAP + ",") if s ["phoneHdr"] else ""
   if abs (s ["a"] - 1) > 20e-6:
      ph += f"setpts=PTS/{s ['a']:.8f},"
   scr = f"[0:v]fps={f},"
   ph  = f"[1:v]{ph}fps={f},"
   sx  = o.sx if o.sx is not None else 0 if lay == "stackv" else 0.5
   sy  = o.sy if o.sy is not None else 0 if s ["obsPortrait"] else 0.5
   if lay == "stackv":
      return (scr + fill (1080, 1312, sx, sy) + "[t];" +
              ph + fill (1080, 608, o.px, o.py) + "[b];[t][b]vstack[v]")
   if lay == "stack":
      return (scr + fill (1920, 540, sx, o.sy) + "[t];" +
              ph + fill (1920, 540, o.px, o.py) + "[b];[t][b]vstack[v]")
   return (scr + fill (1920, 1080, sx, o.sy) + "[t];" +
           ph + fill (960, 540, o.px, o.py) + "[b];"
           "[t][b]overlay=W-w:H-h[v]")


def loud (args):
   "loudnorm's measurement json for an ffmpeg arg list ending in a filter"
   r = run (["ffmpeg", "-hide_banner", "-nostats"] + args +
            ["-f", "null", "-"])
   m = re.findall (r"\{[^{}]*\}", r.stderr.decode (errors="replace"))
   return json.loads (m [-1])


def voiceSrc ():
   "filter chain for the raw voice"
   return "[0:a:2]" + VCHN.format (hp=80)


def mix (v, s, ins, stem):
   "render the leveled audio mix to a wav, None if no voice there"
   lvl = lambda ch: float (loud (ins + ["-filter_complex",
            ch + f",{AFMT},loudnorm=print_format=json[o]",
            "-map", "[o]"]) ["input_i"])
   mus = f"[0:a:1]{AFMT}"
   gm  = MUSIC - lvl (mus)
   g   = f"{mus},volume={gm:.2f}dB"
   if v != "none":
      vi = lvl (voiceSrc ())
      if vi < -60:
         print (f"  {v}: no voice on it - skipping")
         return None
      g = (f"{g}[m];{voiceSrc ()},{AFMT},volume={VOICE - vi:.2f}dB,"
           f"asplit=2[vo][sc];[m][sc]{DUCK}[md];"
           "[md][vo]amix=2:normalize=0:duration=first")
   wav = OUT / f"{stem}-{v}.wav"
   run (["ffmpeg", "-y", "-v", "error"] + ins +
        ["-filter_complex", g + "[o]", "-map", "[o]",
         "-c:a", "pcm_s24le", str (wav)])
   return wav


def main ():
   ap = argparse.ArgumentParser ()
   ap.add_argument ("take", nargs="?")
   ap.add_argument ("-l", default="all")
   ap.add_argument ("-v", default="all")
   ap.add_argument ("-p", type=float)
   ap.add_argument ("--from", dest="t0", type=float)
   ap.add_argument ("--to", dest="t1", type=float)
   ap.add_argument ("--nudge", type=float, default=0)
   ap.add_argument ("--sx", type=float)
   ap.add_argument ("--sy", type=float)
   for c in ("px", "py"):
      ap.add_argument ("--" + c, type=float, default=0.5)
   o = ap.parse_args ()

   t  = pathlib.Path (o.take) if o.take else newestObs ()
   sf = t if t.suffix == ".json" else syncFile (t)
   if not sf.exists ():
      sys.exit (f"no {sf} - run sync.py first")
   s    = json.loads (sf.read_text ())
   stem = pathlib.Path (s ["obs"]).stem
   ov   = streams (probe (s ["obs"]), "video") [0]
   s ["obsPortrait"] = ov ["height"] > ov ["width"]
   t0   = s ["from"] if o.t0 is None else o.t0
   t1   = s ["to"]   if o.t1 is None else o.t1
   dur  = min (t1 - t0, o.p) if o.p else t1 - t0
   pss  = max (0, s ["a"] * t0 + s ["b"] - s ["phoneStart"]
                  - o.nudge / 1000)
   ins  = ["-ss", f"{t0 - s ['obsStart']:.4f}", "-t", f"{dur:.4f}",
           "-i", s ["obs"],
           "-ss", f"{pss:.4f}", "-t", f"{dur * s ['a'] + 0.5:.4f}",
           "-i", s ["phone"]]
   lays = ["stackv", "stack", "pip"] if o.l == "all" else [o.l]
   vos  = ["none", "mic"]            if o.v == "all" else [o.v]
   if s ["obsTracks"] < 2:
      sys.exit ("obs file has no track 2 (music)")
   if s ["obsTracks"] < 3 and "mic" in vos:
      print ("obs file has no track 3 (mic) - skipping mic")
      vos.remove ("mic")
   tag = "-prev" if o.p else ""

   for v in vos:
      print (f"audio: {v}")
      wav = mix (v, s, ins, stem + tag)
      if not wav:
         continue
      m  = loud (["-i", str (wav), "-af",
                  f"loudnorm={FINAL}:print_format=json"])
      ln = (f"loudnorm={FINAL}:measured_I={m ['input_i']}:"
            f"measured_TP={m ['input_tp']}:"
            f"measured_LRA={m ['input_lra']}:"
            f"measured_thresh={m ['input_thresh']}:"
            f"offset={m ['target_offset']}:linear=true,aresample=48000")
      for lay in lays:
         mp4 = OUT / f"{stem}{tag}-{lay}-{v}.mp4"
         print (f"  {mp4.name}")
         run (["ffmpeg", "-y", "-v", "error"] + ins + ["-i", str (wav),
               "-filter_complex", video (lay, s, o) + f";[2:a]{ln}[a]",
               "-map", "[v]", "-map", "[a]", "-t", f"{dur:.4f}",
               "-c:v", "libx264", "-crf", "18",
               "-preset", "veryfast" if o.p else "medium",
               "-pix_fmt", "yuv420p", "-colorspace", "bt709",
               "-color_primaries", "bt709", "-color_trc", "bt709",
               "-c:a", "aac", "-b:a", "192k",
               "-movflags", "+faststart", str (mp4)])
      wav.unlink ()


main ()
