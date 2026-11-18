// portrait.js - pianocheetah 1080x1312 (titlebar n frame incl) top left
// of the portrait monitor (phone video goes under it in 1080x1920),
// obs main window in the rest of the monitor under it (not in the vid)
// loaded n run by rec.py start -p, twice: kwin applies the geometry
// later so 1st run says set, 2nd says ok if it took (or err).
// rec.py swaps TAG for a unique one per run to find it in the journal

const W = 1080, H = 1312, TAG = "PCH";
function say (s)  { print (TAG + "|" + s); }
let scr = null, win = null, obs = null;
for (const s of workspace.screens)
   if (s.geometry.height > s.geometry.width)  scr = s;
for (const w of workspace.windowList ())
   if (w.resourceClass == "app.shaz.pianocheetah")  win = w;
   else if (w.resourceClass == "com.obsproject.Studio" && w.normalWindow &&
            w.caption.startsWith ("OBS "))  obs = w;
if      (! scr)  say ("err|no portrait monitor");
else if (! win)  say ("err|pianocheetah not running");
else if (! obs)  say ("err|obs main window not found");
else {
   const g = scr.geometry, f = win.frameGeometry, o = obs.frameGeometry;
   const og = {x: g.x, y: g.y + H, width: W, height: g.height - H};
   if (f.x == g.x && f.y == g.y && f.width == W && f.height == H &&
       ! win.noBorder && ! win.minimized &&
       o.x == og.x && o.y == og.y && o.width == og.width &&
       o.height == og.height && ! obs.minimized)
      say ("ok|" + scr.name + "|" + W + "x" + H + ", obs under it " +
           og.width + "x" + og.height);
   else {
      win.minimized = false;
      win.noBorder = false;
      win.frameGeometry = {x: g.x, y: g.y, width: W, height: H};
      obs.minimized = false;
      obs.setMaximize (false, false);
      obs.frameGeometry = og;
      workspace.activeWindow = win;
      say ("set|" + scr.name + "|was " + f.width + "x" + f.height);
   }
}
