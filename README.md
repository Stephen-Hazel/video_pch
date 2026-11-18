# video_pch - pianocheetah demo video pipeline

Screen capture (OBS) + phone video of hands on the piano, synced off a
piano note, put in one frame with leveled audio.  Built 2026-11-12 for
the pianocheetah 60 sec demo (see zEtc in ~/web/pc).

## Setup

- Kubuntu 26.10, Wayland.  OBS Studio 33 Flatpak (`~/.bin/obs` wrapper).
- Monitors: HDMI-A-1 main 1920x1080 at 0,0.  DP-1 2nd, portrait
  1080x1920 at 1920,0.
- OBS records via PipeWire: config `vid` = main monitor (landscape),
  `vidp` = DP-1 (portrait).  Claude starts/stops OBS.
- Repo: github.com/Stephen-Hazel/video_pch (public).  Commits are
  Stephen's only - no Claude co-author / attribution, ever.
- Phone: Pixel 8a, landscape, HDR (HLG) is fine - mk.py tonemaps it to
  SDR.  Stabilization standard or off.  Vids get sftp'd over wifi to
  `~/_/t/DCIM/Camera/`.
- `.venv` has obsws-python n numpy (`.venv/bin/pip install ...`).
  ffmpeg 8.1 from apt (has zscale, tonemap, loudnorm, afftdn,
  sidechaincompress).

## Audio sources (decided 2026-11-14)

- Softsynth (pianocheetah) - PipeWire.
- Piano n drums - line ins on the mixer, Behringer Xenyx Q1202USB.
  Piano on stereo ch 7/8 (no gain knob - level knob up past U to get
  the 0 led flickering; piano's own volume at max).  Its USB audio is
  a PCM2902 ("Burr-Brown USB Audio CODEC"), card 3.
- Voice - Logi USB Headset mic (48k mono).  Mixer mic stays down.
- Phone (Pixel 8a) audio - sync only, not used as voice (hears
  speakers ~20 dB louder than voice n clips).  Turn speakers (Ctrl
  Room) down while talking so the headset doesn't hear them.
- PC front jack is a TRRS combo (headset icon): a 3 pole plug = stereo
  headphone OUT only, no usable input.

### Q1202USB gotchas (measured)

- Main meters are just clip / 6 / 0 / 20.  Aim 0 flickering on loud
  bits, 6 rare, never clip.  -20 only = USB send ~50 dB too quiet.
- 2-TR/USB to Ctrl Room/Phones REPLACES the main mix in the speakers
  (you hear only the computer).
- 2-TR/USB to Main adds the computer into main BUT MUTES THE USB SEND
  to the computer (USB drops to bare -85 dB hiss).  So the synth can't
  come back over the 2-TR/USB return while recording.
- Ctrl Room / Phones knob = speaker volume only, doesn't touch USB.
- FX knobs only feed FX SEND jack (nothing plugged in) - keep at 0,
  FX to Ctrl Room off.

### Routing (wired n gain staged 2026-11-15)

    softsynth -> PC front headphone out -> RCA -> 1/4" mono x2 -> ch 5/6
              \-> OBS track 1 (clean synth copy, sync n backup)
    ch 5/6 synth + ch 7/8 piano + drums -> MAIN -> USB -> OBS track 2
                                              \-> Ctrl Room -> speakers
    headset -> OBS track 3 (voice)
    2-TR/USB to Main OFF, to Ctrl Room OFF

Track 2 = the full music mix (balanced by ear on the mixer).  Never mix
track 1 n 2 together (synth doubled = phasey).

## OBS one time setup (done 2026-11-14)

1. Tools > WebSocket Server Settings > Enable (port 4455, auth on).
   rec.py reads port/password from OBS's own config:
   `~/.var/app/com.obsproject.Studio/config/obs-studio/plugin_config/
   obs-websocket/config.json`
2. Settings > Output > Advanced > Recording: format MKV,
   audio tracks 1, 2 n 3 checked.  Rec path is still /home/sh.
3. Settings > Audio: Mic/Aux disabled.  Sources (Edit > Advanced Audio
   Properties), monitoring off on all:
   - Desktop Audio -> track 1 only (synth)
   - `mixer` (Audio Input Capture, PCM2902 input) -> track 2 only
   - `headset` (Audio Input Capture, Logi USB Headset Mono) -> track 3
   DON'T mute in OBS - muted means it's gone.
4. Source: Screen Capture (PipeWire), main monitor.
5. `./rec.py check` - all of the above verified 2026-11-14.
6. PCM2902 capture in PipeWire set to 100% (was 50%).

## OBS configs (2026-11-18)

All of the above lives in OBS profile `vid` + scene collection `vid`
(copied from Untitled).  Untitled is yours for everyday use - change
it freely.

- `rec.py start` saves the current profile / scene collection to
  `obs/prev.json`, switches to vid (if not already), starts recording.
- `rec.py done` switches back to what was in prev.json.  Do it after
  the last take, not between takes (switching reloads all sources).
- `rec.py check` shows which config is on (says NOT vid if not).
- `rec.py start -p` = portrait: kwin/portrait.js puts pianocheetah
  at 1080x1312 (titlebar n frame on, included in that) at the top
  left of DP-1, OBS main window under it (10 px gap, 540x598, recorded
  but mk.py only uses the top 1312), then OBS goes to `vidp` (profile
  1080x1920 canvas, scene collection screen capture = DP-1, no V4L2),
  then records.  Both windows stay put after.
- Backup: `obs/{vid,vidp}/basic.ini` n `scenes.json` (copied
  2026-11-18).  Restore in OBS: Profile > Import (the dir), Scene
  Collection > Import (its scenes.json).
- vid scenes also has a Video Capture Device (V4L2) under the screen
  capture (hidden behind it) - was in Untitled, left as is.

## Each take

1. `./rec.py start`  (OBS to vid, main monitor), or
   `./rec.py start -p` (portrait: pianocheetah to DP-1 top, OBS vidp)
2. start phone recording
3. Ctrl Room up so the phone hears the speakers (sync is off them)
4. do the demo (Ctrl Room down while you talk on the headset)
5. a sharp note or two near the start n end helps but isn't needed
6. stop phone, `./rec.py stop` (logs file path to takes.log)
7. wait for the phone vid to land in ~/_/t/DCIM/Camera/
8. after the last take: `./rec.py done` (back to everyday config)

## Make the video

    ./sync.py                  # last take + newest phone vid
    ./sync.py obs.mkv phone.mp4
    ./sync.py -t 1 ...         # match obs track 1 (default 2)

Prints how many 20s phone chunks agree on the offset (want >= 2,
more is better), offset n drift, writes
`out/<take>.sync.json` n `out/<take>.note1.jpg` (n note2) - obs frame
left, phone frame right at the note.  Eyeball em: the key press should
match.

    ./mk.py -p 20              # 20 sec previews of everything
    ./mk.py -l stackv -v mic   # full length, one combo

- `-l` layout (default all):
  - `stackv` 1080x1920, screen 1080x1312 on top, whole phone frame
    (1080x608, 16:9) under it.  Portrait take: top 1312 rows of DP-1
    1:1 (--sy 0).  Landscape take: crop from the left (--sx 0).
  - `stack`  1920x1080, screen band 1920x540 on top, phone band below
  - `pip`    1920x1080, full screen, phone 960x540 fills bottom right
    quarter
- `-v` voice (default all): `none`, `mic` (obs track 3 headset).
  Silent mic is skipped.
- `--from T --to T` obs secs to keep (default whole overlap - use this
  to cut off the sync notes)
- `--nudge MS` phone video later (or earlier if -) if sync looks off
- `--noise T` obs secs where 5s of bare mixer hiss starts (default:
  quietest 5s of track 2 - needs a gap w no playing somewhere)
- `--sx --sy --px --py` crop centre 0..1 for screen / phone
  (eg `--py .7` keeps lower part of the phone frame)

Output: `out/<take>[-prev]-<layout>-<voice>.mp4`, H.264 crf 18,
AAC 192k, faststart.

## How it works

- **sync.py**: phone audio cut in 20s chunks (silent ones skipped);
  each one's 10ms log level jumps cross correlated over the whole obs
  track (default 2 = mixer = what the speakers play).  The offset most
  chunks agree on (within 50ms) wins.  First n last agreeing chunks
  refined to the sample on 1ms envelopes around their sharpest note
  -> drift.  Mapping saved as `phone time = a * obs time + b`.
  Drift ignored if the 2 disagree (> 100ms or > 500ppm).
- **mk.py audio**: music (track 2, mixer) dehissed (afftdn nr 12 dB,
  noise profile learnt off 5s of bare hiss from the same take) n set
  to -18 LUFS, voice (track 3 headset: highpass, afftdn denoise,
  compressor) set to -16 LUFS, music ducked under voice
  (sidechaincompress), mixed, then straight gain to -14 LUFS w
  alimiter at -2 dB (~-1.7 dBTP); gain re-measured after the limiter
  til within 0.2 LU.  No loudnorm dynamic mode = no lifted hiss.
- **mk.py video**: phone tonemapped if HDR, setpts for drift,
  both forced to obs fps, scale+crop to fill each pane.
- Tune: MUSIC / VOICE / FINAL / PEAK / NR / NOISE / VCHN / DUCK at
  top of mk.py.

## Status / next

- 2026-11-12: scripts written n tested on synthetic takes (4.3s offset,
  +100ppm drift, echo + noise on "phone"): sync within ~0.5ms, all 9
  previews render at -14 LUFS, layouts n stills checked.
- NOT yet run against real OBS (websocket was off) or real phone vids.
- 2026-11-14: OBS set up (3 tracks), 2 real test takes
  (`/home/sh/2026-11-14 09-26-57.mkv`, `09-27-48.mkv` + phone
  PXL_20261114_172702950 / 172802331).  Take 2 findings:
  - track 2 (mixer) dead - turned out to be "to Main" muting USB +
    piano level way low.  Fixed level: piano now ~-18 rms / -2 pk on
    USB (back ch 7/8 off a bit, aim ~-6 pk to leave room for drums).
  - synth clips: +1.3 dB, 8k clipped samples -> turn pianocheetah
    down ~6 dB.
  - phone vs obs: obs = phone + 12.6s, no drift.  sync.py got it
    WRONG (38.6s) - only searches obs first 60s of track 1 n synth
    started at 0:29.  tmp/xc.py (whole take, any track) got it right.
- 2026-11-15: synth wired front jack -> ch 5/6, gain staged.
  - PipeWire default sink = Built-in Audio Analog Stereo (front jack,
    "Headphones" port), sink vol 100%.  OBS Desktop Audio = "default"
    so it follows.  Noise floor on USB w ch 5/6 open: -84 dB rms.
    Jack -> ch 5/6 at U -> USB loses ~12.5 dB.
  - pianocheetah stream "syn" (float32) set to 79% = -6 dB in
    PipeWire - its drums n busy parts hit 0 dBFS at 100%.  Ch 5/6
    then ~4.5 dB above U.  Drums now come from pianocheetah (syn),
    also a DTX drum kit on the mixer.
  - Each alone peaks ~-8..-10 on USB; all together -5 pk / -23 rms.
  - Headset mic hw gain was +11 dB (max) -> voice clipped.  Now
    +5 dB: `amixer -c 6 sset 'USB Audio' capture 5dB`.
  - Test take `/home/sh/2026-11-15 13-14-51.mkv` (no phone): track 2
    good, track 3 voice clipped (fixed above) n speaker bleed only
    ~15 dB under voice.  Listen clip out/2026-11-15-track2-100s.mp3.
  - pianocheetah runs at 64 frame quantum; parecord w default
    latency caused xruns (synth slowed) - use --latency-msec=200.
    OBS attached caused none.
  - Voice take `/home/sh/2026-11-15 13-22-49.mkv` (at +1 dB): voice
    pk -11.6, no clip; Ctrl Room down -> bleed 25-30 dB under voice;
    headset floor -72.  Raised to +5 dB after.
- Next:
  1. Always Ctrl Room down (or phones) while talking.
  2. Balance check by ear of track 2 (drum kit vs synth).
  3. Real take w phone to test the new sync.py n mk.py (below).
- 2026-11-15 pipeline changes: mk.py music = track 2, voice = track 3
  only (no phone voice); sync.py chunk agreement over whole take,
  `-t` track (default 2); rec.py no obsws tracebacks.  sync.py on
  11-14 take 2 (`-t 1`, files now in trash): 5 of 13 chunks agree,
  phone = obs -12.60s, +39ppm - right.  mk.py not yet run on a real
  3 track take.
- 2026-11-17: first real take w phone, `/home/sh/2026-11-17 07-55-46.mkv`
  + `~/_/t/DCIM/Camera/PXL_20261117_155557852.mp4` (Clair de Lune on
  the piano, pianocheetah on screen).  Headset was unplugged n synth
  not playing -> only track 2 has sound.  Sync note 0:16, music
  0:31-2:35, hit 2:39.
  - sync.py: 4 of 8 chunks agree, phone = obs -9.44s, note1 still
    matches.  Notes disagree 35ms -> drift ignored.
  - Layouts picked: landscape = pip (phone fills bottom right 1/4) -
    user says great.  Portrait = stackv 3/4 screen (left side, sx 0
    now default) over 1/4 phone.
  - Rendered full length, no voice:
    `out/2026-11-17 07-55-46-{pip,stackv}-none.mp4` (--from 30 --to
    156).  Old mk.py in /tmp scratchpad (gone after reboot).
  - "Hum": none in the file (60/120/180 Hz ~-100 dB raw, -77 in the
    render).  Low drone heard = piano B♭2 116 Hz / E♭2 78 Hz notes.
    User didn't say where they heard it - ask.
  - HISS (open): raw floor clean (-86 dB > 6k) but render quiet bits
    ~-61 dB.  Cause: track 2 only -31.6 LUFS / -12.6 pk so +17.6 dB
    gain to -14, AND loudnorm goes dynamic (compresses, lifts quiet
    bits).  FINAL LRA 11->20 did NOT help: linear gain would put
    peaks at ~+5 dBTP > -1, so loudnorm still goes dynamic (out LRA
    9.2 vs 15 in).
- Next (2026-11-17):
  1. mk.py: alimiter (~-1..-3 dB, fast) on music before loudnorm so
     linear mode works; check normalization_type = linear n hiss
     drop.  Maybe gentle afftdn on music if still hissy (watch
     piano decays).
  2. Next take: piano ch 7/8 hotter, peaks ~-6 on USB (0 led
     flickering) = ~6 dB less hiss.
  3. Plug in headset (`amixer -c 6 sset 'USB Audio' capture 5dB`
     after), start pianocheetah synth (syn 79%) -> full 3 track take.
  4. Phone: aim so hands are centred (portrait crops phone centre).
- 2026-11-18: OBS profile n scene collection `vid` made (copies of
  Untitled), rec.py start/done switch to n back, backup in obs/.
  Tested: Untitled -> start -> 3 track mkv w screen -> stop ->
  done -> Untitled.  No PipeWire screen picker came up on switch.
  Then Untitled put back to everyday: output Simple (mp4 to
  ~/^/midi2), mixer n headset sources removed, Desktop Audio on all
  tracks, Mic/Aux off, V4L2 kept.  Filenames yymmdd_hhmmss
  (`%YY%MM%DD_%hh%mm%ss`, Untitled only - vid unchanged).  Pre-revert
  copy in obs/untitled-before-revert/.
- 2026-11-18: portrait.  Dir renamed web/vid -> web/video_pch, git n
  private github repo.  stackv now 1080x1312 screen over whole 16:9
  phone (tested on 11-17 take).  `rec.py start -p` + kwin/portrait.js
  + OBS vidp (1080x1920, DP-1).  pianocheetah = class
  app.shaz.pianocheetah, min size 583x196, takes 1080x1312 fine.
  Then: titlebar n frame left on (in the video).  rec.py finds the
  kwin script's output in the journal by a unique tag per run (the
  journal cursor way failed intermittently).  Repo made public.
- 2026-11-18: 1st portrait take `/home/sh/2026-11-18 08-59-37.mkv`
  (6:06, no voice, no synth audio - piano on track 2 only, pk -11.7)
  + phone `PXL_20261118_170317245.mp4` (4K SDR, 2:27, started 3:39
  in; `PXL_20261118_165908459.mp4` 15 MB = stray clip).  sync.py: 6
  of 7 chunks agree, phone = obs -219.15s, +179ppm (applied).  No
  sync note needed - song itself syncs fine.
  - obs 0:49-0:54 n 3:50-4:02 = same intro, no hands (pianocheetah
    playing it?).  User plays 4:18-6:06.
  - Rendered `out/2026-11-18 08-59-37-stackv-none.mp4` --from 255
    --to 346 (cut before last loud note at 346.2): 91s, -13.8 LUFS.
  - Phone aimed too high: hands at bottom edge, fingertips cut (no
    crop room in stackv now).  pianocheetah track list columns cut
    at 1080 wide.
- 2026-11-18: hiss fix + tiktok cut.  mk.py: afftdn on music w
  learnt noise profile, loudnorm replaced by gain + alimiter.
  Rendered `out/2026-11-18 08-59-37-stackv-none.mp4` --from 258
  --to 314.8 (1st note 258.64, phrase break ~314.5): 56.8s,
  -14.1 LUFS, -1.66 dBTP.  Quiet floor -51.4 -> -65.5 dB (old vs new
  chain, same cut), music level same.  Listen: out/...-hiss-{old,new}
  .mp3 (1st 15s).  Tiktok: 9:16 1080x1920 h264/aac, <= 60s.
  User to judge by ear: piano decays not watery?
- Next: aim phone lower (hands centred), piano ch 7/8 hotter (~-6
  pk) = less hiss to start with.
- Watch for: speaker bleed into headset n phone (lower Ctrl Room
  while talking).  Synth/speaker latency may need a small `--nudge`.

## Files

- `rec.py`    OBS start [-p]/stop/done/status/check over websocket
- `kwin/portrait.js` pianocheetah to its portrait spot (rec.py runs it)
- `obs/`      vid n vidp profile + scene collection backups,
              untitled-before-revert/, prev.json (not in git)
- `sync.py`   find phone <-> obs offset n drift
- `mk.py`     render layouts x voice sources
- `vidlib.py` shared bits (ffprobe, audio decode, tonemap, paths)
- `takes.log` obs recordings, one per line (from rec.py stop)
- `out/`      sync json, stills, rendered mp4s
- `tmp/lev.py` per second rms/peak of obs tracks 1-3 (throwaway)
- `tmp/xc.py`  `<mkv> <phone> <track>` phone offset per 20s chunk
