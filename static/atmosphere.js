/* CampusMatch 氛围底：WebGL 流体雾 + 港澳市花（莲花 / 洋紫荆） */
(function () {
    'use strict';
    if (window.__cmAtmosphere) return;
    window.__cmAtmosphere = true;

    var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var coarse = window.matchMedia && window.matchMedia('(hover: none), (pointer: coarse)').matches;
    var desktop = window.matchMedia && window.matchMedia('(min-width: 860px)').matches;
    if (reduced) return;

    var wrap = document.createElement('div');
    wrap.className = 'cm-atmosphere';
    wrap.setAttribute('aria-hidden', 'true');
    document.body.insertBefore(wrap, document.body.firstChild);
    document.body.classList.add('cm-has-atmosphere');

    var mouse = { x: 0.5, y: 0.42, tx: 0.5, ty: 0.42 };
    var onMove = function (e) {
        mouse.tx = e.clientX / Math.max(1, window.innerWidth);
        mouse.ty = 1 - e.clientY / Math.max(1, window.innerHeight);
    };
    if (!coarse) window.addEventListener('mousemove', onMove, { passive: true });

    var hidden = false;
    document.addEventListener('visibilitychange', function () {
        hidden = document.hidden;
    });

    function tickMouse() {
        mouse.x += (mouse.tx - mouse.x) * 0.08;
        mouse.y += (mouse.ty - mouse.y) * 0.08;
    }

    function startFluid() {
        var canvas = document.createElement('canvas');
        canvas.className = 'cm-atmosphere-fluid';
        wrap.appendChild(canvas);
        var gl = canvas.getContext('webgl2', {
            alpha: true,
            premultipliedAlpha: false,
            powerPreference: 'low-power',
            antialias: false
        });
        if (!gl) return;

        function compile(type, src) {
            var sh = gl.createShader(type);
            gl.shaderSource(sh, src);
            gl.compileShader(sh);
            if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
                console.warn('CM atmosphere shader', gl.getShaderInfoLog(sh));
                gl.deleteShader(sh);
                return null;
            }
            return sh;
        }

        var vs = compile(gl.VERTEX_SHADER, '#version 300 es\nin vec2 a; void main(){ gl_Position=vec4(a,0.,1.); }');
        var fs = compile(gl.FRAGMENT_SHADER, '#version 300 es\nprecision mediump float;\nuniform vec2 u_res;\nuniform float u_time;\nuniform vec2 u_mouse;\nout vec4 fragColor;\nfloat hash(vec2 p){ return fract(sin(dot(p,vec2(127.1,311.7))) * 43758.5453); }\nfloat noise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f); float a=hash(i), b=hash(i+vec2(1.,0.)), c=hash(i+vec2(0.,1.)), d=hash(i+vec2(1.,1.)); return mix(mix(a,b,f.x), mix(c,d,f.x), f.y); }\nfloat fbm(vec2 p){ float v=0., a=.5; for(int i=0;i<5;i++){ v+=a*noise(p); p=p*2.03+vec2(1.7,9.2); a*=.5; } return v; }\nvoid main(){\n  vec2 uv=gl_FragCoord.xy/u_res;\n  float aspect=u_res.x/max(u_res.y,1.);\n  vec2 p=vec2((uv.x-.5)*aspect, uv.y-.5);\n  vec2 m=vec2((u_mouse.x-.5)*aspect, u_mouse.y-.5);\n  float md=length(p-m);\n  p += normalize(p-m+1e-4)*exp(-md*md*8.)*0.18;\n  float t=u_time*.06;\n  float n=fbm(p*2.2+vec2(t*.4,-t*.25));\n  float n2=fbm(p*3.1-vec2(t*.2,t*.35)+n);\n  float fog=smoothstep(.22,.78, mix(n,n2,.45));\n  vec3 c1=vec3(0.93,0.96,1.0);\n  vec3 c2=vec3(0.75,0.83,1.0);\n  vec3 c3=vec3(0.78,0.95,0.98);\n  vec3 c4=vec3(1.0,0.84,0.93);\n  vec3 col=mix(c1,c2,fog);\n  col=mix(col,c3,smoothstep(.35,.8,n2)*.55);\n  col=mix(col,c4,smoothstep(.55,.95,n)*.28);\n  float vign=smoothstep(1.15,.2,length(p));\n  fragColor=vec4(col, .42*vign);\n}');
        if (!vs || !fs) return;
        var prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return;
        gl.useProgram(prog);
        var buf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        var loc = gl.getAttribLocation(prog, 'a');
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
        var uRes = gl.getUniformLocation(prog, 'u_res');
        var uTime = gl.getUniformLocation(prog, 'u_time');
        var uMouse = gl.getUniformLocation(prog, 'u_mouse');
        var dprCap = 1.25;
        var last = 0;
        var raf = 0;

        function resize() {
            var dpr = Math.min(window.devicePixelRatio || 1, dprCap);
            var w = Math.round(window.innerWidth * dpr);
            var h = Math.round(window.innerHeight * dpr);
            if (canvas.width !== w || canvas.height !== h) {
                canvas.width = w;
                canvas.height = h;
                gl.viewport(0, 0, w, h);
            }
        }

        function frame(t) {
            raf = requestAnimationFrame(frame);
            if (hidden) return;
            if (t - last < 1000 / 28) return;
            last = t;
            tickMouse();
            resize();
            gl.disable(gl.DEPTH_TEST);
            gl.enable(gl.BLEND);
            gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
            gl.uniform2f(uRes, canvas.width, canvas.height);
            gl.uniform1f(uTime, t * 0.001);
            gl.uniform2f(uMouse, mouse.x, mouse.y);
            gl.drawArrays(gl.TRIANGLES, 0, 3);
        }
        raf = requestAnimationFrame(frame);
        window.addEventListener('resize', resize, { passive: true });
    }

    function startBlooms() {
        if (coarse || !desktop) return;
        var canvas = document.createElement('canvas');
        canvas.className = 'cm-atmosphere-grid';
        wrap.appendChild(canvas);
        var ctx = canvas.getContext('2d');
        if (!ctx) return;
        var blooms = [];
        var w = 0;
        var h = 0;
        var dpr = Math.min(window.devicePixelRatio || 1, 1.5);
        var raf = 0;
        var last = 0;

        function petalLotus(s) {
            ctx.beginPath();
            ctx.moveTo(0, s * 0.06);
            ctx.bezierCurveTo(s * 0.5, -s * 0.08, s * 0.46, -s * 0.72, 0, -s);
            ctx.bezierCurveTo(-s * 0.46, -s * 0.72, -s * 0.5, -s * 0.08, 0, s * 0.06);
            ctx.closePath();
        }

        function petalBauhinia(s) {
            ctx.beginPath();
            ctx.moveTo(0, s * 0.1);
            ctx.bezierCurveTo(s * 0.68, -s * 0.02, s * 0.62, -s * 0.7, s * 0.16, -s * 0.98);
            ctx.quadraticCurveTo(0, -s * 0.78, -s * 0.16, -s * 0.98);
            ctx.bezierCurveTo(-s * 0.62, -s * 0.7, -s * 0.68, -s * 0.02, 0, s * 0.1);
            ctx.closePath();
        }

        function drawLotus(a, near) {
            var s = a.s * (1 + near * 0.35);
            var petals = 8;
            var i;
            ctx.save();
            ctx.translate(a.x, a.y);
            ctx.rotate(a.rot);
            ctx.globalAlpha = 0.22 + near * 0.38;
            for (i = 0; i < petals; i++) {
                ctx.save();
                ctx.rotate((Math.PI * 2 * i) / petals);
                ctx.fillStyle = i % 2
                    ? 'rgba(236,72,153,0.85)'
                    : 'rgba(251,207,232,0.95)';
                petalLotus(s);
                ctx.fill();
                ctx.restore();
            }
            ctx.beginPath();
            ctx.arc(0, 0, s * 0.18, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(253, 224, 71, 0.55)';
            ctx.fill();
            ctx.restore();
        }

        function drawBauhinia(a, near) {
            var s = a.s * (1 + near * 0.35);
            var i;
            ctx.save();
            ctx.translate(a.x, a.y);
            ctx.rotate(a.rot);
            ctx.globalAlpha = 0.2 + near * 0.4;
            for (i = 0; i < 5; i++) {
                ctx.save();
                ctx.rotate((Math.PI * 2 * i) / 5);
                ctx.fillStyle = i === 0
                    ? 'rgba(99,102,241,0.9)'
                    : 'rgba(219,39,119,0.88)';
                petalBauhinia(s);
                ctx.fill();
                ctx.restore();
            }
            ctx.beginPath();
            ctx.arc(0, 0, s * 0.14, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255,255,255,0.55)';
            ctx.fill();
            ctx.restore();
        }

        function spawn() {
            var n = Math.max(22, Math.min(36, Math.round((w * h) / 42000)));
            blooms = [];
            for (var i = 0; i < n; i++) {
                var x = Math.random() * w;
                var y = Math.random() * h;
                blooms.push({
                    hx: x, hy: y, x: x, y: y, vx: 0, vy: 0,
                    s: 7 + Math.random() * 7,
                    lotus: i % 2 === 0,
                    ph: Math.random() * Math.PI * 2,
                    sp: 0.28 + Math.random() * 0.5,
                    rot: Math.random() * Math.PI * 2,
                    rv: (Math.random() - 0.5) * 0.012
                });
            }
        }

        function layout() {
            w = window.innerWidth;
            h = window.innerHeight;
            canvas.width = Math.round(w * dpr);
            canvas.height = Math.round(h * dpr);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            spawn();
        }
        layout();
        var resizeT;
        window.addEventListener('resize', function () {
            clearTimeout(resizeT);
            resizeT = setTimeout(layout, 120);
        }, { passive: true });

        function frame(t) {
            raf = requestAnimationFrame(frame);
            if (hidden) return;
            if (t - last < 1000 / 28) return;
            last = t;
            tickMouse();
            var mx = mouse.x * w;
            var my = (1 - mouse.y) * h;
            var sec = t * 0.001;
            ctx.clearRect(0, 0, w, h);

            var i, a, dx, dy, dist, f, homeX, homeY, near;
            for (i = 0; i < blooms.length; i++) {
                a = blooms[i];
                homeX = a.hx + Math.sin(sec * a.sp + a.ph) * 22;
                homeY = a.hy + Math.cos(sec * a.sp * 0.75 + a.ph) * 16;
                dx = a.x - mx;
                dy = a.y - my;
                dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 180 && dist > 0.3) {
                    f = (1 - dist / 180) * 2.2;
                    a.vx += (dx / dist) * f;
                    a.vy += (dy / dist) * f;
                    a.rv += (dx > 0 ? 1 : -1) * 0.0008;
                }
                a.vx += (homeX - a.x) * 0.016;
                a.vy += (homeY - a.y) * 0.016;
                a.vx *= 0.92;
                a.vy *= 0.92;
                a.x += a.vx;
                a.y += a.vy;
                a.rot += a.rv + Math.sin(sec * a.sp + a.ph) * 0.004;
                a.rv *= 0.96;
                near = Math.max(0, 1 - dist / 210);
                if (a.lotus) drawLotus(a, near);
                else drawBauhinia(a, near);
            }
        }
        raf = requestAnimationFrame(frame);
    }

    try { startFluid(); } catch (e) { /* ignore */ }
    try { startBlooms(); } catch (e) { /* ignore */ }
})();
