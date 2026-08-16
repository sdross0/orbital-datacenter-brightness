"""
A sky you can drag, built out of one panorama and a fragment shader.

The problem this solves: a server render takes about a third of a second, and
drag has to answer in sixteen milliseconds. No amount of tuning closes that
gap, so the panning cannot happen on the server at all. Instead the whole dome
goes to the browser once, as an equirectangular image, and a shader cuts a
correct gnomonic window out of it at whatever heading the pointer asks for.
That is the same projection frame.py renders, computed per pixel on the GPU,
so dragging is free and the geometry still matches the stills.

The same viewer plays orbital motion. Successive panoramas differ only in
where the satellites are, so handing it a stack of them and swapping the
texture each tick shows the constellation moving while the sky holds still.

Counts are done here too, from a subsample of the visible satellites carried
along as plain numbers. Otherwise the figure beside the picture would freeze
the moment the user dragged away from the view the server rendered.
"""

import base64
import io

import numpy as np
from PIL import Image

_HTML = r"""
<style>
  .wrap { position:relative; width:100%; background:#05070c; border-radius:8px;
          overflow:hidden; font-family:-apple-system,BlinkMacSystemFont,
          "Segoe UI",Helvetica,Arial,sans-serif; }
  .wrap canvas { display:block; width:100%; height:__CH__px; cursor:grab; }
  .wrap canvas.drag { cursor:grabbing; }
  #ov { position:absolute; left:0; top:0; pointer-events:none; }
  .bar { display:flex; align-items:center; gap:10px; padding:8px 10px;
         color:#c3cddd; font-size:12.5px; background:#0a0e16; flex-wrap:wrap; }
  .bar button { background:#1b2433; color:#dbe4f2; border:1px solid #2b3648;
                border-radius:5px; padding:4px 11px; font-size:12.5px;
                cursor:pointer; }
  .bar button:hover { background:#243046; }
  .bar select { background:#1b2433; color:#dbe4f2; border:1px solid #2b3648;
                border-radius:5px; padding:3px 6px; font-size:12.5px; }
  .rd { color:#8b97a8; }
  .rd b { color:#dbe4f2; font-weight:600; }
  .cnt { margin-left:auto; text-align:right; line-height:1.25; }
  .cnt .s { color:__SATC__; font-weight:600; font-size:15px; }
  .cnt .t { color:#cfd8e8; font-weight:600; font-size:15px; }
  .hint { padding:0 10px 8px; color:#66707f; font-size:11.5px; }
</style>

<div class="wrap">
  <canvas id="sky"></canvas>
  <canvas id="ov"></canvas>
  <div class="bar">
    <button id="play" __PLAYHIDE__>__PLAYLABEL__</button>
    <select id="spd" __PLAYHIDE__>__SPEEDS__</select>
    <span class="rd">Facing <b id="rAz"></b> &nbsp;&middot;&nbsp; elevation
      <b id="rEl"></b> &nbsp;&middot;&nbsp; <b id="rFov"></b> wide</span>
    <button id="reset">Reset view</button>
    <button id="full">Fullscreen</button>
    <span class="cnt"><span class="s" id="cSat"></span>
      <span class="rd">satellites</span> &nbsp;
      <span class="t" id="cStar"></span> <span class="rd">stars</span>
      <span class="rd">in view</span></span>
  </div>
  <div class="hint">Drag to look around. Scroll or pinch to zoom. The counts
    follow the view.</div>
</div>

<script>
(function () {
  var FRAMES = __FRAMES__;
  var ALTMAX = __ALTMAX__ * Math.PI / 180.0;
  var SAT = __SATS__, STAR = __STARS__;
  var SAT_SCALE = __SATSCALE__, STAR_SCALE = __STARSCALE__;
  var YAW0 = __YAW__ * Math.PI / 180.0;
  var PIT0 = __PITCH__ * Math.PI / 180.0;
  var FOV0 = __FOV__ * Math.PI / 180.0;

  var cv = document.getElementById('sky');
  var ov = document.getElementById('ov');
  var octx = ov.getContext('2d');
  var gl = cv.getContext('webgl') || cv.getContext('experimental-webgl');

  var yaw = YAW0, pitch = PIT0, fov = FOV0;
  var dragging = false, lx = 0, ly = 0, moved = false;
  var playing = false, cur = 0, timer = null;

  // Where you were looking survives a rerun.
  //
  // Streamlit rebuilds this whole frame whenever any control changes, so
  // without this the view snapped back to the sidebar's heading every time the
  // clock moved, which makes comparing two times almost impossible. VIEWKEY
  // encodes the sidebar's starting view: if you change that deliberately the
  // key changes and the saved position is discarded, but if you only change
  // the time or the model the key is the same and you stay where you were.
  var VIEWKEY = '__VIEWKEY__', STORE = 'odc_sky_view';
  function saveView() {
    try {
      window.localStorage.setItem(STORE, JSON.stringify(
        { k: VIEWKEY, yaw: yaw, pitch: pitch, fov: fov }));
    } catch (e) { /* storage blocked; the view simply will not persist */ }
  }
  function loadView() {
    try {
      var s = JSON.parse(window.localStorage.getItem(STORE) || 'null');
      if (s && s.k === VIEWKEY && isFinite(s.yaw)) {
        yaw = s.yaw; pitch = s.pitch; fov = s.fov;
      }
    } catch (e) { /* same */ }
  }
  function clearView() {
    try { window.localStorage.removeItem(STORE); } catch (e) {}
  }
  loadView();

  var VS = 'attribute vec2 p; void main(){ gl_Position = vec4(p,0.0,1.0); }';
  var FS = [
    'precision highp float;',
    'uniform vec2 uRes; uniform float uYaw,uPitch,uFov,uAltMax;',
    'uniform sampler2D uTex;',
    'const float PI = 3.14159265358979;',
    'void main(){',
    '  vec2 uv = (gl_FragCoord.xy / uRes) * 2.0 - 1.0;',
    '  float sx = tan(uFov*0.5);',
    '  float sy = sx * uRes.y / uRes.x;',
    '  float ce = cos(uPitch), se = sin(uPitch);',
    '  vec3 fwd = vec3(sin(uYaw)*ce, cos(uYaw)*ce, se);',
    '  vec3 rgt = vec3(cos(uYaw), -sin(uYaw), 0.0);',
    '  vec3 up  = cross(rgt, fwd);',
    '  vec3 d = normalize(fwd + uv.x*sx*rgt + uv.y*sy*up);',
    '  float alt = asin(clamp(d.z,-1.0,1.0));',
    '  if (alt < 0.0) {',
    '    float g = 0.020 + 0.012 * exp(alt*14.0);',
    '    gl_FragColor = vec4(g, g*0.95, g*0.88, 1.0); return; }',
    '  if (alt > uAltMax) { gl_FragColor = vec4(0.004,0.005,0.010,1.0); return; }',
    '  float az = atan(d.x, d.y); if (az < 0.0) az += 2.0*PI;',
    '  gl_FragColor = texture2D(uTex, vec2(az/(2.0*PI), 1.0 - alt/uAltMax));',
    '}'
  ].join('\n');

  function sh(t, s) {
    var o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o);
    if (!gl.getShaderParameter(o, gl.COMPILE_STATUS))
      console.error(gl.getShaderInfoLog(o));
    return o;
  }

  var prog, tex, uni = {};
  if (gl) {
    prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS));
    gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog); gl.useProgram(prog);
    var buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER,
      new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
    var loc = gl.getAttribLocation(prog, 'p');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    ['uRes','uYaw','uPitch','uFov','uAltMax','uTex'].forEach(function (n) {
      uni[n] = gl.getUniformLocation(prog, n); });
    tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  }

  var imgs = [], ready = 0;
  FRAMES.forEach(function (src, i) {
    var im = new Image();
    im.onload = function () {
      ready++;
      if (ready === 1) { upload(0); draw(); }
      if (FRAMES.length > 1) {
        var hint = document.querySelector('.hint');
        if (ready < FRAMES.length) {
          hint.textContent = 'Loading motion, ' + ready + ' of '
            + FRAMES.length + ' frames...';
        } else {
          hint.textContent = 'Drag to look around. Scroll or pinch to zoom. '
            + 'The counts follow the view.';
          // Start on its own. Asking someone to hunt for a play button after
          // they already waited for a render is one step too many.
          if (!playing) { playing = true; playBtn.textContent = 'Pause'; tick(); }
        }
      }
    };
    im.src = src; imgs[i] = im;
  });

  function upload(i) {
    if (!gl || !imgs[i] || !imgs[i].complete) return;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, imgs[i]);
  }

  function size() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = cv.clientWidth, h = cv.clientHeight;
    cv.width = Math.round(w*dpr); cv.height = Math.round(h*dpr);
    ov.width = cv.width; ov.height = cv.height;
    ov.style.width = w + 'px'; ov.style.height = h + 'px';
    if (gl) gl.viewport(0, 0, cv.width, cv.height);
  }

  var PTS = ['N','NNE','NE','ENE','E','ESE','SE','SSE',
             'S','SSW','SW','WSW','W','WNW','NW','NNW'];

  function draw() {
    if (!gl) return;
    gl.useProgram(prog);
    gl.uniform2f(uni.uRes, cv.width, cv.height);
    gl.uniform1f(uni.uYaw, yaw);
    gl.uniform1f(uni.uPitch, pitch);
    gl.uniform1f(uni.uFov, fov);
    gl.uniform1f(uni.uAltMax, ALTMAX);
    gl.uniform1i(uni.uTex, 0);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    overlay();
    readout();
  }

  function cam() {
    var ce = Math.cos(pitch), se = Math.sin(pitch);
    return { f: [Math.sin(yaw)*ce, Math.cos(yaw)*ce, se],
             r: [Math.cos(yaw), -Math.sin(yaw), 0],
             u: [-Math.sin(yaw)*se, -Math.cos(yaw)*se, ce] };
  }
  function dot(a, b) { return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]; }

  function project(alt, az) {
    var c = cam();
    var d = [Math.cos(alt)*Math.sin(az), Math.cos(alt)*Math.cos(az),
             Math.sin(alt)];
    var z = dot(d, c.f);
    if (z <= 1e-6) return null;
    var foc = (cv.width/2) / Math.tan(fov/2);
    return [cv.width/2 + foc*dot(d, c.r)/z, cv.height/2 - foc*dot(d, c.u)/z];
  }

  function inView(alt, az) {
    var p = project(alt, az);
    return p && p[0] >= 0 && p[0] < cv.width && p[1] >= 0 && p[1] < cv.height;
  }

  function almucantars(dpr) {
    // Curves of constant altitude. In this projection they are not straight,
    // so they are drawn by projecting the curve rather than ruling a line.
    var levels = [15, 30, 45, 60, 75];
    octx.font = '500 ' + Math.round(11.5*dpr) + 'px -apple-system,Helvetica,Arial';
    for (var li = 0; li < levels.length; li++) {
      var alt = levels[li] * Math.PI / 180;
      var started = false, label = null;
      octx.beginPath();
      for (var k = -90; k <= 90; k += 1.5) {
        var p = project(alt, yaw + k * Math.PI / 180);
        if (!p) { started = false; continue; }
        if (p[0] < -2e4 || p[0] > 2e4) { started = false; continue; }
        if (!started) { octx.moveTo(p[0], p[1]); started = true; }
        else octx.lineTo(p[0], p[1]);
        if (label === null && p[0] > 6*dpr && p[1] > 12*dpr
            && p[1] < ov.height - 6*dpr) label = p;
      }
      octx.strokeStyle = 'rgba(150,170,200,0.20)';
      octx.lineWidth = 1*dpr;
      octx.stroke();
      if (label) {
        octx.textAlign = 'left';
        octx.lineWidth = 3*dpr;
        octx.strokeStyle = 'rgba(5,7,12,0.8)';
        octx.strokeText(levels[li] + '°', 6*dpr, label[1] - 4*dpr);
        octx.fillStyle = 'rgba(168,184,208,0.85)';
        octx.fillText(levels[li] + '°', 6*dpr, label[1] - 4*dpr);
      }
    }
    // The zenith itself, since satellites do pass through it.
    var z = project(Math.PI/2 - 1e-6, yaw);
    if (z && z[0] > 0 && z[0] < ov.width && z[1] > 0 && z[1] < ov.height) {
      octx.strokeStyle = 'rgba(150,170,200,0.45)';
      octx.lineWidth = 1*dpr;
      octx.beginPath();
      octx.moveTo(z[0]-6*dpr, z[1]); octx.lineTo(z[0]+6*dpr, z[1]);
      octx.moveTo(z[0], z[1]-6*dpr); octx.lineTo(z[0], z[1]+6*dpr);
      octx.stroke();
      octx.textAlign = 'left';
      octx.fillStyle = 'rgba(168,184,208,0.8)';
      octx.fillText('zenith', z[0] + 9*dpr, z[1] + 4*dpr);
    }
  }

  function overlay() {
    var dpr = cv.width / cv.clientWidth;
    octx.setTransform(1, 0, 0, 1, 0, 0);
    octx.clearRect(0, 0, ov.width, ov.height);
    almucantars(dpr);
    octx.font = '600 ' + Math.round(13*dpr) + 'px -apple-system,Helvetica,Arial';
    octx.textAlign = 'center';
    octx.lineWidth = 3*dpr;
    octx.strokeStyle = 'rgba(5,7,12,0.85)';
    for (var i = 0; i < 16; i++) {
      var az = i * Math.PI / 8;
      var p = project(0.0, az);
      if (!p) continue;
      if (p[0] < 14*dpr || p[0] > ov.width - 14*dpr) continue;
      var y = Math.max(20*dpr, Math.min(p[1], ov.height - 8*dpr));
      var major = (i % 2 === 0);
      octx.beginPath();
      octx.moveTo(p[0], y - (24*dpr));
      octx.lineTo(p[0], y - (17*dpr));
      octx.strokeStyle = major ? 'rgba(214,226,244,0.85)' : 'rgba(190,202,222,0.5)';
      octx.lineWidth = (major ? 2 : 1) * dpr;
      octx.stroke();
      octx.lineWidth = 3*dpr;
      octx.strokeStyle = 'rgba(5,7,12,0.85)';
      octx.strokeText(PTS[i], p[0], y);
      octx.fillStyle = major ? 'rgba(226,235,250,0.96)' : 'rgba(198,210,230,0.8)';
      octx.fillText(PTS[i], p[0], y);
    }
  }

  function count(arr) {
    var n = 0;
    for (var i = 0; i < arr.length; i += 2)
      if (inView(arr[i], arr[i+1])) n++;
    return n;
  }

  function fmt(n) { return n.toLocaleString(); }

  function readout() {
    var a = ((yaw*180/Math.PI) % 360 + 360) % 360;
    document.getElementById('rAz').textContent =
      Math.round(a) + '° ' + PTS[Math.round(a/22.5) % 16];
    document.getElementById('rEl').textContent =
      Math.round(pitch*180/Math.PI) + '°';
    document.getElementById('rFov').textContent =
      Math.round(fov*180/Math.PI) + '°';
    document.getElementById('cSat').textContent =
      fmt(Math.round(count(SAT) * SAT_SCALE));
    document.getElementById('cStar').textContent =
      fmt(Math.round(count(STAR) * STAR_SCALE));
  }

  cv.addEventListener('pointerdown', function (e) {
    dragging = true; moved = false; lx = e.clientX; ly = e.clientY;
    cv.classList.add('drag'); cv.setPointerCapture(e.pointerId);
  });
  cv.addEventListener('pointermove', function (e) {
    if (!dragging) return;
    var dx = e.clientX - lx, dy = e.clientY - ly;
    lx = e.clientX; ly = e.clientY;
    if (Math.abs(dx) + Math.abs(dy) > 2) moved = true;
    // One screen pixel moves the sky by the angle that pixel subtends, so the
    // point under the cursor stays under the cursor.
    var perPx = 2 * Math.tan(fov/2) / cv.clientWidth;
    yaw -= dx * perPx / Math.max(Math.cos(pitch), 0.35);
    pitch = Math.max(-Math.PI/9, Math.min(ALTMAX - 0.02,
                                          pitch + dy * perPx));
    draw();
  });
  function endDrag(e) {
    dragging = false; cv.classList.remove('drag');
    saveView();
    try { cv.releasePointerCapture(e.pointerId); } catch (_) {}
  }
  cv.addEventListener('pointerup', endDrag);
  cv.addEventListener('pointercancel', endDrag);

  cv.addEventListener('wheel', function (e) {
    e.preventDefault();
    fov = Math.max(15*Math.PI/180,
                   Math.min(140*Math.PI/180, fov * (1 + e.deltaY*0.0016)));
    draw(); saveView();
  }, { passive: false });

  document.getElementById('reset').addEventListener('click', function () {
    yaw = YAW0; pitch = PIT0; fov = FOV0; clearView(); draw();
  });

  // Fullscreen on the wrapper, not the canvas, so the controls come along.
  // Inside a Streamlit iframe the request can be refused by permissions
  // policy, so the button reports that rather than failing silently.
  var wrap = document.querySelector('.wrap');
  var fullBtn = document.getElementById('full');
  function fsElement() {
    return document.fullscreenElement || document.webkitFullscreenElement;
  }
  fullBtn.addEventListener('click', function () {
    if (fsElement()) {
      (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      return;
    }
    var req = wrap.requestFullscreen || wrap.webkitRequestFullscreen;
    if (!req) { fullBtn.textContent = 'Not available'; return; }
    var p = req.call(wrap);
    if (p && p.catch) p.catch(function () {
      fullBtn.textContent = 'Blocked here';
      document.querySelector('.hint').textContent =
        'This page will not allow fullscreen. Use Large view in the sidebar.';
    });
  });
  ['fullscreenchange', 'webkitfullscreenchange'].forEach(function (ev) {
    document.addEventListener(ev, function () {
      var on = !!fsElement();
      fullBtn.textContent = on ? 'Exit fullscreen' : 'Fullscreen';
      cv.style.height = on ? 'calc(100vh - 66px)' : '__CH__px';
      setTimeout(function () { size(); draw(); }, 40);
    });
  });

  var playBtn = document.getElementById('play');
  if (FRAMES.length > 1) {
    playBtn.addEventListener('click', function () {
      playing = !playing;
      playBtn.textContent = playing ? 'Pause' : '__PLAYLABEL__';
      if (timer) { clearInterval(timer); timer = null; }
      if (playing) tick();
    });
    document.getElementById('spd').addEventListener('change', function () {
      if (playing) { clearInterval(timer); tick(); }
    });
  }

  function tick() {
    // The frames are a fixed interval of sky time apart, so the speed
    // multiplier is just that interval times the frame rate. One render
    // serves every speed on the menu.
    var fps = parseFloat(document.getElementById('spd').value);
    timer = setInterval(function () {
      cur = (cur + 1) % FRAMES.length;
      if (!imgs[cur].complete) return;
      upload(cur); draw();
    }, 1000 / fps);
  }

  window.addEventListener('resize', function () { size(); draw(); });
  size();
  if (!gl) {
    document.querySelector('.hint').textContent =
      'This browser did not give us WebGL, so the sky cannot be panned here.';
  } else {
    var maxTex = gl.getParameter(gl.MAX_TEXTURE_SIZE);
    if (maxTex < __TEXW__) {
      document.querySelector('.hint').textContent =
        'This graphics card tops out at ' + maxTex + ' pixel textures and the '
        + 'panorama is __TEXW__ wide, so it may not appear. Choose the lower '
        + 'resolution in the sidebar.';
    }
  }
  draw();
})();
</script>
"""


def encode(arr, quality=82):
    """
    A panorama as a data URL.

    Done here rather than in the page assembly so the caller can cache the
    encoded string. Holding sixty raw frames would be a couple of hundred
    megabytes; holding sixty JPEGs is a few.
    """
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG", quality=quality,
                              optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def pairs(alt, az, cap=6000, seed=3):
    """Interleaved alt,az radians, thinned to `cap`. Returns (list, weight)."""
    n = len(alt)
    if n == 0:
        return [], 1.0
    if n > cap:
        idx = np.random.default_rng(seed).choice(n, cap, replace=False)
        alt, az = alt[idx], az[idx]
    out = np.empty(alt.size * 2)
    out[0::2] = alt
    out[1::2] = az
    return [round(float(v), 4) for v in out], n / float(len(alt))


def html(frames, alt_max, sat_altaz, sat_weight, star_altaz, star_weight,
         yaw=315.0, pitch=27.0, fov=90.0, canvas_h=520, sat_color="#ff9a3c",
         speeds=((10, "10x"), (30, "30x"), (60, "60x")),
         play_label="Play orbital motion", tex_w=4096, view_key=""):
    """Assemble the viewer. `frames` is a list of data URLs from encode()."""
    srcs = "[" + ",".join('"%s"' % f for f in frames) + "]"
    sats, sw = sat_altaz
    stars, tw = star_altaz
    mid = len(speeds) // 2
    opts = "".join(
        '<option value="%g"%s>%s</option>'
        % (f, " selected" if i == mid else "", lab)
        for i, (f, lab) in enumerate(speeds))
    reps = {
        "__SPEEDS__": opts,
        "__PLAYLABEL__": play_label,
        "__TEXW__": str(int(tex_w)),
        "__VIEWKEY__": view_key or ("%.1f_%.1f_%.1f" % (yaw, pitch, fov)),
        "__FRAMES__": srcs,
        "__ALTMAX__": "%.4f" % alt_max,
        "__SATS__": "[" + ",".join(str(v) for v in sats) + "]",
        "__STARS__": "[" + ",".join(str(v) for v in stars) + "]",
        "__SATSCALE__": "%.6f" % (sw * sat_weight),
        "__STARSCALE__": "%.6f" % (tw * star_weight),
        "__YAW__": "%.3f" % yaw,
        "__PITCH__": "%.3f" % pitch,
        "__FOV__": "%.3f" % fov,
        "__CH__": str(int(canvas_h)),
        "__SATC__": sat_color,
        "__PLAYHIDE__": "" if len(frames) > 1 else 'style="display:none"',
    }
    out = _HTML
    for k, v in reps.items():
        out = out.replace(k, v)
    return out
