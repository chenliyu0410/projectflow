import { useEffect, useRef } from 'react';
import type { FormEvent } from 'react';

// Login screen "深潭" (prototype E2): a WebGL water surface behind a frosted card. Clicking the water, focusing a
// field or signing in sends a ripple; a failed sign-in sways the card; a successful one sinks the card and parts the
// water before the workspace opens. Without WebGL or with reduced motion it falls back to a still gradient.

const FRAGMENT = `
precision highp float;
uniform vec2 uRes;
uniform float uDpr, uTime, uPart, uSurge, uGap;
uniform vec4 uRip[6];

float hash(vec2 p) { vec3 q = fract(vec3(p.xyx) * .1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p), u = f * f * f * (f * (f * 6. - 15.) + 10.);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
  float v = 0., a = .5; mat2 m = mat2(1.6, 1.2, -1.2, 1.6);
  for (int i = 0; i < 3; i++) { v += a * noise(p); p = m * p; a *= .45; }
  return v;
}
float ripples(vec2 p) {
  float h = 0.;
  for (int i = 0; i < 6; i++) {
    vec4 r = uRip[i];
    float age = uTime - r.z;
    if (r.w <= 0. || age < 0. || age > 3.5) continue;
    float x = length(p - r.xy) - age * 200.;
    h += r.w * sin(x * .065) * exp(-x * x / 2600.) * exp(-age * 1.05);
  }
  return h;
}
float cells(vec2 q, float t) {
  vec2 i = floor(q), f = fract(q);
  float d1 = 8., d2 = 8.;
  for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
    vec2 g = vec2(float(x), float(y));
    vec2 o = .5 + .4 * sin(t + 6.2831 * vec2(hash(i + g), hash(i + g + 17.3)));
    float d = length(g + o - f);
    if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) d2 = d;
  }
  return exp(-(d2 - d1) * 7.);
}
float swell(vec2 s) {
  float h = 0.;
  for (int i = 0; i < 8; i++) {
    float fi = float(i);
    float ang = .55 + (hash(vec2(fi, 3.7)) - .5) * 1.7;
    float L = 340. * pow(.74, fi), k = 6.2831 / L, spd = 24. * sqrt(L / 100.);
    h += L * .010 * sin(dot(vec2(cos(ang), sin(ang)), s) * k - uTime * k * spd + hash(vec2(fi, 9.1)) * 6.2831);
  }
  return h;
}
float gapHalf(float y) {
  if (uPart <= 0.) return 0.;
  float span = uRes.y * (.12 + 2.3 * uPart), dy = (y - uRes.y * .5) / span;
  float prof = max(0., 1. - dy * dy);
  float wob = (fbm(vec2(y * .011, uTime * .55)) - .5) * (16. + 34. * uSurge);
  return max(0., (uGap * uPart + wob * smoothstep(0., .15, uPart)) * prof);
}
float wallDist(vec2 p) { return max(abs(p.x - uRes.x * .5) - gapHalf(p.y), 0.); }
float edgeAmt(float g) { return smoothstep(0., 14., g); }
vec2 source(vec2 p) {
  if (uPart <= 0.) return p;
  float mid = uRes.x * .5, dx = p.x - mid, e = wallDist(p), g = gapHalf(p.y), s = uGap * .9 + 80.;
  return vec2(mid + (dx < 0. ? -1. : 1.) * (e + g * (1. - exp(-e / s))), p.y);
}
float height(vec2 p) {
  vec2 src = source(p);
  float big = fbm(src / 560. + uTime * vec2(.018, .007));
  float h = swell(src) * (.45 + big) + big * 30. + ripples(p) * 5.;
  if (uPart > 0.) {
    float e = wallDist(p), k = edgeAmt(gapHalf(p.y));
    h += k * 18. * exp(-e / 55.);
    h += k * uSurge * 9. * sin(e * .055 - uTime * 7.) * exp(-e / 170.);
  }
  return h;
}
void main() {
  vec2 p = gl_FragCoord.xy / uDpr;
  vec3 hi = vec3(.97, .95, .90);
  float mid = uRes.x * .5, g = gapHalf(p.y), ax = abs(p.x - mid), y = p.y / uRes.y;
  float inside = max(g - ax, 0.);
  vec3 floorCol = mix(vec3(.90, .88, .83), vec3(.955, .937, .893), smoothstep(0., 1., y)) * (1. - .04 * length((p - uRes * .5) / uRes));
  floorCol *= 1. - .22 * exp(-inside / 40.) - .08 * exp(-inside / 120.);
  floorCol = mix(floorCol, floorCol * vec3(.93, .98, .97), exp(-inside / 70.));
  floorCol += (hash(p) - .5) * .014;
  float h = height(p), e = 1.5;
  float hx = height(p + vec2(e, 0.)), hy = height(p + vec2(0., e));
  vec3 n = normalize(vec3(-(hx - h) / e * 1.15, -(hy - h) / e * 1.15, 1.));
  vec3 deep = vec3(.040, .150, .148), teal = vec3(.115, .355, .340), jade = vec3(.20, .45, .42);
  float tone = fbm(p / 560. + uTime * vec2(.018, .007));
  vec3 col = mix(deep, teal, clamp(.05 + .75 * tone + .2 * y, 0., 1.));
  col = mix(col, jade, clamp(h * .004, 0., .25));
  col *= .74 + .34 * clamp(dot(n, normalize(vec3(-.4, .6, .7))), 0., 1.);
  vec3 R = reflect(vec3(0., 0., -1.), n);
  col += hi * pow(max(dot(R, normalize(vec3(-.55, .55, .63))), 0.), 6.) * .07;
  float rl = max(dot(R, normalize(vec3(-.12, .3, 1.))), 0.);
  col += hi * (pow(rl, 160.) * .16 + pow(rl, 1100.) * .38);
  col += hi * pow(1. - n.z, 2.) * .3;
  if (uPart > 0.) {
    float wd = wallDist(p), k = edgeAmt(g);
    vec2 fs = source(p);
    float crest = exp(-wd / (5. + 12. * uSurge)) * (.55 + .45 * smoothstep(.3, .7, fbm(vec2(p.y / 14., wd / 10.) + uTime * .8)));
    vec2 warp = (vec2(fbm(fs / 30.), fbm(fs / 30. + 7.7)) - .5) * 1.8;
    float net = pow(cells(fs / 11. + warp + vec2(0., uTime * .35), uTime * .9), 1.6);
    float patch = smoothstep(.42, .75, fbm(fs / 34. + vec2(uTime * .15, uTime * .3)));
    float clump = smoothstep(.55, .78, fbm(fs / 8. + uTime * .6)) * exp(-wd / (14. + 20. * uSurge));
    float lace = net * exp(-wd / (16. + 42. * uSurge)) * patch;
    float foam = clamp(crest * .95 + clump * .8 + lace * .75, 0., 1.) * k * (.6 + .4 * uSurge);
    col = mix(col, vec3(.90, .94, .92), foam);
    col += hi * .45 * exp(-wd / 1.8) * k;
  }
  vec2 v = p / uRes - .5;
  col *= 1. - .36 * dot(v, v);
  col += (hash(p + fract(uTime)) - .5) / 110.;
  float inGap = uPart > 0. ? (1. - smoothstep(g - 1.2, g + 1.2, ax)) * smoothstep(0., 2., g) : 0.;
  gl_FragColor = vec4(mix(col, floorCol, inGap), 1.);
}`;

const LOGO = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23ffffff' fill-opacity='.12' stroke='white' stroke-opacity='.45'/%3E%3Cpath d='M9 10h14M9 16h10M9 22h6' stroke='white' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E";
const SINK_MS = 250, PART_MS = 1300, DEPART_MS = 1600;

const reducedMotion = () => !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
let waterActive = false;
/** How long sign-in should wait for the parting water: zero when nothing animates. */
export function departureMs() { return waterActive && !reducedMotion() ? DEPART_MS : 0; }

type Water = { ripple: (x: number, y: number, amp?: number) => void; part: () => void };
type Drop = { x: number; y: number; vx: number; vy: number; life: number; age: number; r: number };

function startWater(canvas: HTMLCanvasElement, sprayCanvas: HTMLCanvasElement): (Water & { stop: () => void }) | null {
  if (typeof WebGLRenderingContext === 'undefined') return null;
  const gl = canvas.getContext('webgl', { antialias: false, premultipliedAlpha: false });
  const sctx = sprayCanvas.getContext('2d');
  if (!gl || !sctx) return null;
  const vs = gl.createShader(gl.VERTEX_SHADER)!, fs = gl.createShader(gl.FRAGMENT_SHADER)!;
  gl.shaderSource(vs, 'attribute vec2 a; void main(){ gl_Position = vec4(a, 0., 1.); }'); gl.compileShader(vs);
  gl.shaderSource(fs, FRAGMENT); gl.compileShader(fs);
  if (!gl.getShaderParameter(fs, gl.COMPILE_STATUS)) return null;
  const prog = gl.createProgram()!; gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog); gl.useProgram(prog);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  const U = Object.fromEntries(['uRes', 'uDpr', 'uTime', 'uPart', 'uSurge', 'uGap', 'uRip'].map(k => [k, gl.getUniformLocation(prog, k)]));

  const reduce = reducedMotion();
  const t0 = performance.now(), now = () => (performance.now() - t0) / 1000;
  const rip = new Float32Array(24); let slot = 0;
  let part = { from: 0, to: 0, t0: 0, dur: 1 }, W = 1, H = 1, dpr = 1, last = 0, raf = 0;
  const drops: Drop[] = [];
  const gapWidth = () => Math.max(160, Math.min(W * 0.32, 440));
  const ease = (x: number) => x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2;
  function state(t: number) {
    const x = Math.min(1, Math.max(0, (t - part.t0) / part.dur));
    return { p: part.from + (part.to - part.from) * (reduce ? 1 : ease(x)), surge: reduce || x >= 1 ? 0 : Math.sin(Math.PI * x) };
  }
  function resize() {
    dpr = Math.min(devicePixelRatio || 1, 1.5);
    W = Math.max(1, innerWidth); H = Math.max(1, innerHeight);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    sprayCanvas.width = canvas.width; sprayCanvas.height = canvas.height;
    sctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    gl!.viewport(0, 0, canvas.width, canvas.height);
    if (reduce) draw(now());
  }
  // Spray: small drops thrown out from the water's edge while it parts.
  function spawnSpray(p: number, surge: number) {
    if (reduce || surge < 0.05) return;
    const span = H * (0.12 + 2.3 * p), n = Math.round(7 * surge);
    for (let k = 0; k < n; k++) {
      const y = H / 2 + (Math.random() * 2 - 1) * Math.min(span, H * 0.6);
      const dy = (y - H / 2) / span, g = gapWidth() * p * Math.max(0, 1 - dy * dy);
      if (g < 8) continue;
      const side = Math.random() < 0.5 ? -1 : 1, sp = 60 + Math.random() * 220;
      const ang = (Math.random() - 0.5) * 1.6 + (Math.random() < 0.25 ? Math.PI : 0);
      drops.push({ x: W / 2 + side * g, y, vx: side * Math.cos(ang) * sp, vy: Math.sin(ang) * sp * 0.6, life: 0.5 + Math.random() * 0.8, age: 0, r: 0.6 + Math.random() * 1.8 });
    }
  }
  function drawSpray(dt: number) {
    sctx!.clearRect(0, 0, W, H);
    for (let i = drops.length - 1; i >= 0; i--) {
      const d = drops[i];
      d.age += dt; if (d.age > d.life) { drops.splice(i, 1); continue; }
      d.vx *= 0.96; d.vy *= 0.96; d.x += d.vx * dt; d.y += d.vy * dt;
      const a = (1 - d.age / d.life) ** 1.5;
      sctx!.strokeStyle = `rgba(240,246,243,${0.7 * a})`; sctx!.lineWidth = d.r * 1.8; sctx!.lineCap = 'round';
      sctx!.beginPath(); sctx!.moveTo(d.x, d.y); sctx!.lineTo(d.x - d.vx * 0.012, d.y - d.vy * 0.012); sctx!.stroke();
      sctx!.fillStyle = `rgba(240,246,243,${0.12 * a})`;
      sctx!.beginPath(); sctx!.arc(d.x, d.y, d.r * 3, 0, Math.PI * 2); sctx!.fill();
    }
  }
  function draw(t: number) {
    const { p, surge } = state(t);
    gl!.uniform2f(U.uRes, W, H); gl!.uniform1f(U.uDpr, dpr); gl!.uniform1f(U.uTime, reduce ? 3 : t);
    gl!.uniform1f(U.uPart, p); gl!.uniform1f(U.uSurge, surge); gl!.uniform1f(U.uGap, gapWidth());
    gl!.uniform4fv(U.uRip, rip);
    gl!.drawArrays(gl!.TRIANGLES, 0, 3);
    spawnSpray(p, surge);
    drawSpray(Math.min(0.05, t - last)); last = t;
  }
  function frame() { if (!document.hidden) draw(now()); raf = requestAnimationFrame(frame); }
  addEventListener('resize', resize);
  resize();
  if (reduce) draw(now()); else raf = requestAnimationFrame(frame);
  waterActive = true;
  return {
    ripple(x, y, amp = 1) {
      if (reduce || part.to > 0) return;
      rip.set([x, H - y, now(), amp], slot * 4); slot = (slot + 1) % 6;
    },
    part() { part = { from: 0, to: 1, t0: now(), dur: PART_MS / 1000 }; if (reduce) draw(now()); },
    stop() { waterActive = false; cancelAnimationFrame(raf); removeEventListener('resize', resize); gl!.getExtension('WEBGL_lose_context')?.loseContext(); },
  };
}

export default function LoginScreen({ organization, username, password, onOrganization, onUsername, onPassword, busy, message, leaving, onSubmit }: {
  organization: string; username: string; password: string;
  onOrganization: (value: string) => void; onUsername: (value: string) => void; onPassword: (value: string) => void;
  busy: boolean; message: string; leaving: boolean; onSubmit: (event: FormEvent) => void;
}) {
  const waterCanvas = useRef<HTMLCanvasElement>(null), sprayCanvas = useRef<HTMLCanvasElement>(null);
  const card = useRef<HTMLDivElement>(null);
  const water = useRef<Water | null>(null);
  useEffect(() => {
    const started = startWater(waterCanvas.current!, sprayCanvas.current!);
    water.current = started;
    // Ripples come only from the water itself, a field gaining focus, or signing in.
    const touch = (event: PointerEvent) => { if (!(event.target as Element).closest('.wl-card')) started?.ripple(event.clientX, event.clientY, 1); };
    addEventListener('pointerdown', touch);
    return () => { removeEventListener('pointerdown', touch); started?.stop(); water.current = null; };
  }, []);
  // A new error sways the card once; removing the class and forcing a reflow replays the animation.
  useEffect(() => {
    const el = card.current;
    if (!message || !el) return;
    el.classList.remove('sway'); void el.offsetWidth;
    if (!reducedMotion()) el.classList.add('sway');
  }, [message]);
  useEffect(() => {
    if (!leaving) return;
    const timer = setTimeout(() => water.current?.part(), reducedMotion() ? 0 : SINK_MS);
    return () => clearTimeout(timer);
  }, [leaving]);
  function focusRipple(input: HTMLInputElement) {
    const c = card.current?.getBoundingClientRect(), r = input.getBoundingClientRect();
    if (!c) return;
    if (c.left > 60) water.current?.ripple(c.left - 36, r.top + r.height / 2, 0.55);
    else water.current?.ripple(r.left + r.width / 2, c.bottom + 30, 0.55);
  }
  function submit(event: FormEvent) {
    const c = card.current?.getBoundingClientRect();
    if (c) water.current?.ripple(c.left + c.width / 2, Math.min(innerHeight - 20, c.bottom + 30), 1.3);
    onSubmit(event);
  }
  const field = (label: string, value: string, change: (value: string) => void, autoComplete: string, type = 'text') =>
    <label>{label}<span className="wl-field"><input type={type} value={value} onChange={event => change(event.target.value)} onFocus={event => focusRipple(event.currentTarget)} required disabled={busy} autoComplete={autoComplete} /></span></label>;
  return <div className="water-login">
    <canvas ref={waterCanvas} className="wl-water" aria-hidden="true" />
    <canvas ref={sprayCanvas} className="wl-spray" aria-hidden="true" />
    <header className={`wl-brand${leaving ? ' gone' : ''}`}><img src={LOGO} width="32" height="32" alt="" /><strong className="brand-name">專流 ProjectFlow</strong></header>
    <div className="wl-shell">
      <div ref={card} className={`wl-card${leaving ? ' sink' : ''}`} onAnimationEnd={event => event.currentTarget.classList.remove('sway')}>
        <form onSubmit={submit}>
          <div>
            <p className="wl-eyebrow">PROJECTFLOW</p>
            <h1>登入專流</h1>
            <p className="wl-lede">讓每一件工作，順著流程走到底。</p>
            <div className="wl-rule" />
          </div>
          {message && <p className="wl-alert" role="alert">{message}</p>}
          {field('公司', organization, onOrganization, 'organization')}
          {field('帳號', username, onUsername, 'username')}
          {field('密碼', password, onPassword, 'current-password', 'password')}
          <button className={`wl-submit${busy ? ' loading' : ''}`} type="submit" disabled={busy}>
            <span className="wl-wave" aria-hidden="true"><svg viewBox="0 0 400 22" preserveAspectRatio="none"><path d="M0 11 Q25 0 50 11 T100 11 T150 11 T200 11 T250 11 T300 11 T350 11 T400 11 V22 H0Z" fill="#2E7A74" /></svg><div /></span>
            <span>{busy ? '登入中' : '登入'}</span>
          </button>
        </form>
      </div>
    </div>
  </div>;
}
