// portrait.js - pianocheetah borderless 1080x1312 top left of the
// portrait monitor (phone video goes under it in the 1080x1920 frame)
// loaded n run by rec.py start -p, twice: kwin applies the geometry
// later so 1st run says PCH|set, 2nd says PCH|ok if it took (or err)

const W = 1080, H = 1312;
let scr = null, win = null;
for (const s of workspace.screens)
   if (s.geometry.height > s.geometry.width)  scr = s;
for (const w of workspace.windowList ())
   if (w.resourceClass == "app.shaz.pianocheetah")  win = w;
if      (! scr)  print ("PCH|err|no portrait monitor");
else if (! win)  print ("PCH|err|pianocheetah not running");
else {
   const g = scr.geometry, f = win.frameGeometry;
   if (f.x == g.x && f.y == g.y && f.width == W && f.height == H &&
       win.noBorder && ! win.minimized)
      print ("PCH|ok|" + scr.name + "|" + W + "x" + H);
   else {
      win.minimized = false;
      win.noBorder = true;
      win.frameGeometry = {x: g.x, y: g.y, width: W, height: H};
      workspace.activeWindow = win;
      print ("PCH|set|" + scr.name + "|was " + f.width + "x" + f.height);
   }
}
