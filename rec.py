#!/home/sh/web/video_pch/.venv/bin/python
# rec.py - drive obs over its websocket
#   rec.py check   show obs setup (output mode, tracks, inputs, video)
#   rec.py start   switch obs to the vid config, start recording
#   rec.py start -p   portrait: pianocheetah to 1080x1312 top left of
#                  the portrait monitor (kwin/portrait.js), obs vidp
#   rec.py stop    stop recording, log file path to takes.log
#   rec.py done    switch obs back to the config it had before start
#   rec.py status  is it recording n for how long

import json, logging, sys, time, pathlib, subprocess
import obsws_python as obs

logging.disable (logging.CRITICAL)     # obsws tracebacks - we say why

CFG = pathlib.Path.home () / (".var/app/com.obsproject.Studio/config/"
      "obs-studio/plugin_config/obs-websocket/config.json")
LOG = pathlib.Path (__file__).parent / "takes.log"
PREV = pathlib.Path (__file__).parent / "obs/prev.json"
PCH = pathlib.Path (__file__).parent / "kwin/portrait.js"
VID = "vid"                            # obs profile n scene collection
VIDP = "vidp"                          # same, portrait 1080x1920


def conn ():
   c = json.loads (CFG.read_text ())
   if not c ["server_enabled"]:
      sys.exit ("obs websocket off: Tools > WebSocket Server Settings")
   try:
      return obs.ReqClient (host="localhost", port=c ["server_port"],
                            password=c ["server_password"], timeout=5)
   except Exception as e:
      sys.exit (f"can't reach obs: {e}")


def parm (cl, cat, name):
   try:
      return cl.get_profile_parameter (cat, name).parameter_value
   except Exception:
      return "?"


def kwin (js):
   "run a kwin script, return its PCH|... print line"
   q = ["qdbus6", "org.kde.KWin"]
   jc = subprocess.run (["journalctl", "--user", "-n0", "--show-cursor"],
                        capture_output=True, text=True).stdout
   cur = jc.strip ().split ("cursor: ") [-1]
   sid = subprocess.run (q + ["/Scripting", "org.kde.kwin.Scripting."
                              "loadScript", str (js), "pch"],
                         capture_output=True, text=True).stdout.strip ()
   subprocess.run (q + [f"/Scripting/Script{sid}",
                        "org.kde.kwin.Script.run"], capture_output=True)
   time.sleep (.5)
   subprocess.run (q + ["/Scripting", "org.kde.kwin.Scripting."
                        "unloadScript", "pch"], capture_output=True)
   out = subprocess.run (["journalctl", "--user", "-o", "cat",
                          f"--after-cursor={cur}"],
                         capture_output=True, text=True).stdout
   ln = [l for l in out.splitlines () if "PCH|" in l]
   return ln [-1].split ("PCH|") [1] if ln else "err|no output from kwin"


def portrait ():
   "pianocheetah window to its portrait spot"
   for i in range (3):
      r = kwin (PCH)
      if r.startswith ("ok"):
         print ("pianocheetah:", r [3:])
         return
      if r.startswith ("err"):
         sys.exit ("pianocheetah: " + r [4:])
   sys.exit ("pianocheetah: didn't take - " + r)


def cur (cl):
   return (cl.get_profile_list ().current_profile_name,
           cl.get_scene_collection_list ().current_scene_collection_name)


def use (cl, prof, scn):
   if cur (cl) == (prof, scn):
      return
   for i in range (10):                # stop_record returns early
      if not cl.get_record_status ().output_active:
         break
      time.sleep (.5)
   else:
      sys.exit ("recording - can't switch obs config")
   if prof not in cl.get_profile_list ().profiles:
      sys.exit (f"no obs profile {prof}")
   if scn not in cl.get_scene_collection_list ().scene_collections:
      sys.exit (f"no obs scene collection {scn}")
   if cur (cl) [0] != prof:
      cl.set_current_profile (prof)
   if cur (cl) [1] != scn:
      cl.set_current_scene_collection (scn)
   for i in range (20):                # collection loads async
      if cur (cl) == (prof, scn):
         break
      time.sleep (.5)
   time.sleep (2)                      # let sources come up
   print (f"obs config: profile {prof}, scenes {scn}")


def fit (cl):
   "screen capture 1:1 at 0,0 - obs rescaled it once on a canvas change"
   sc = cl.get_current_program_scene ().current_program_scene_name
   for it in cl.get_scene_item_list (sc).scene_items:
      if it ["sourceName"].startswith ("Screen Capture"):
         cl.set_scene_item_transform (sc, it ["sceneItemId"],
            {"positionX": 0, "positionY": 0, "scaleX": 1, "scaleY": 1,
             "rotation": 0, "alignment": 5})


def check (cl):
   prof, scn = cur (cl)
   print (f"config:      profile {prof}, scenes {scn}" +
          ("" if (prof, scn) in ((VID, VID), (VIDP, VIDP))
              else f"  (NOT {VID} or {VIDP})"))
   mode = parm (cl, "Output", "Mode")
   print ("output mode:", mode)
   if mode == "Advanced":
      print ("rec format: ", parm (cl, "AdvOut", "RecFormat2"))
      trk = parm (cl, "AdvOut", "RecTracks")
      if trk != "?":
         trk = [i+1 for i in range (6) if int (trk) & (1 << i)]
      print ("rec tracks: ", trk)
   print ("rec dir:    ", cl.get_record_directory ().record_directory)
   v = cl.get_video_settings ()
   print (f"video:       {v.base_width}x{v.base_height} -> "
          f"{v.output_width}x{v.output_height} @ "
          f"{v.fps_numerator / v.fps_denominator:g}fps")
   for inp in cl.get_input_list ().inputs:
      nm = inp ["inputName"]
      ln = f"input: {nm}  ({inp ['inputKind']})"
      try:
         t = cl.get_input_audio_tracks (nm).input_audio_tracks
         on = [k for k in sorted (t) if t [k]]
         mute = cl.get_input_mute (nm).input_muted
         ln += f"  tracks {on}" + ("  MUTED" if mute else "")
      except Exception:
         pass                          # video only input
      print (ln)


def status (cl):
   s = cl.get_record_status ()
   if s.output_active:
      print (f"recording  {s.output_timecode}")
   else:
      print ("not recording")


def main ():
   arg = sys.argv [1] if len (sys.argv) > 1 else "status"
   cl = conn ()
   if   arg == "check":
      check (cl)
   elif arg == "start":
      if cl.get_record_status ().output_active:
         sys.exit ("already recording")
      cfg = VID
      if "-p" in sys.argv [2:]:
         cfg = VIDP
         portrait ()
      if not PREV.exists () and cur (cl) not in ((VID, VID),
                                                 (VIDP, VIDP)):
         PREV.write_text (json.dumps (cur (cl)))
      use (cl, cfg, cfg)
      fit (cl)
      cl.start_record ()
      time.sleep (1)
      status (cl)
   elif arg == "stop":
      if not cl.get_record_status ().output_active:
         sys.exit ("not recording")
      path = cl.stop_record ().output_path
      print (path)
      with LOG.open ("a") as f:
         f.write (f"{time.strftime ('%Y-%m-%d %H:%M:%S')}  {path}\n")
   elif arg == "done":
      if not PREV.exists ():
         sys.exit ("no saved obs config to go back to")
      use (cl, *json.loads (PREV.read_text ()))
      PREV.unlink ()
   elif arg == "status":
      status (cl)
   else:
      sys.exit ("rec.py check|start [-p]|stop|done|status")


main ()
