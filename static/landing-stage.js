/* 网络：最左/最右是网中点；路径沿已有短线走。视觉上加深浅和余晖。 */
(function () {
    var canvas = document.getElementById('ed-stage-canvas');
    var stage = document.getElementById('ed-stage');
    if (!canvas || !stage) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    var ctx = canvas.getContext('2d');
    var nodes = [];
    var mouse = { x: 0.5, y: 0.5 };
    var trail = [];
    var w = 0, h = 0, dpr = 1;
    var t0 = 0;
    var LINK = 152;

    function resize() {
        var rect = stage.getBoundingClientRect();
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        w = Math.max(1, rect.width);
        h = Math.max(1, rect.height);
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        seed();
    }

    function seed() {
        var n = Math.max(42, Math.floor(w / 17));
        nodes = [];
        var i;
        for (i = 0; i < n; i++) {
            nodes.push({
                x: Math.random() * w,
                y: h * (0.18 + Math.random() * 0.64),
                vx: (Math.random() - 0.5) * 0.32,
                vy: (Math.random() - 0.5) * 0.24,
                r: 1.1 + Math.random() * 1.8,
                pulse: Math.random() * Math.PI * 2
            });
        }
        nodes[0].x = w * 0.075;
        nodes[0].y = h * 0.5;
        nodes[0].r = 2.4;
        nodes[1].x = w * 0.925;
        nodes[1].y = h * 0.5;
        nodes[1].r = 2.4;
        var bridges = Math.min(7, Math.max(4, Math.floor(n / 10)));
        for (i = 0; i < bridges; i++) {
            var b = 2 + i;
            if (!nodes[b]) break;
            nodes[b].x = w * (0.18 + (0.64 * i) / (bridges - 1));
            nodes[b].y = h * (0.42 + Math.random() * 0.16);
            nodes[b].vy *= 0.5;
        }
        trail = [];
    }

    stage.addEventListener('pointermove', function (e) {
        var rect = stage.getBoundingClientRect();
        mouse.x = (e.clientX - rect.left) / Math.max(1, rect.width);
        mouse.y = (e.clientY - rect.top) / Math.max(1, rect.height);
    }, { passive: true });

    function neighbors() {
        var adj = [];
        var i, j, dx, dy, dist;
        for (i = 0; i < nodes.length; i++) adj[i] = [];
        for (i = 0; i < nodes.length; i++) {
            for (j = i + 1; j < nodes.length; j++) {
                dx = nodes[i].x - nodes[j].x;
                dy = nodes[i].y - nodes[j].y;
                dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < LINK && dist > 0.5) {
                    adj[i].push({ j: j, d: dist });
                    adj[j].push({ j: i, d: dist });
                }
            }
        }
        return adj;
    }

    function pathThrough(adj) {
        var prev = [];
        var dist = [];
        var seen = [];
        var i;
        for (i = 0; i < nodes.length; i++) {
            prev[i] = -1;
            dist[i] = Infinity;
            seen[i] = false;
        }
        dist[0] = 0;
        var q = [0];
        while (q.length) {
            var best = 0;
            for (i = 1; i < q.length; i++) if (dist[q[i]] < dist[q[best]]) best = i;
            var u = q.splice(best, 1)[0];
            if (u === 1) break;
            if (seen[u]) continue;
            seen[u] = true;
            var list = adj[u];
            for (i = 0; i < list.length; i++) {
                var v = list[i].j;
                var nd = dist[u] + list[i].d;
                if (nd < dist[v]) {
                    dist[v] = nd;
                    prev[v] = u;
                    q.push(v);
                }
            }
        }
        var path = [];
        for (i = 1; i !== -1; i = prev[i]) {
            path.push(i);
            if (i === 0) break;
        }
        path.reverse();
        return path[0] === 0 ? path : [];
    }

    function tick(now) {
        if (!t0) t0 = now;
        var t = (now - t0) / 1000;
        ctx.fillStyle = '#0b0a09';
        ctx.fillRect(0, 0, w, h);

        var gx = mouse.x * w;
        var gy = mouse.y * h;
        var i, p;

        for (i = 0; i < nodes.length; i++) {
            p = nodes[i];
            if (i === 0) {
                p.x += (w * 0.075 - p.x) * 0.018;
                p.y += (h * 0.5 + Math.sin(t * 0.55) * 14 - p.y) * 0.02;
                p.y += p.vy * 0.28;
            } else if (i === 1) {
                p.x += (w * 0.925 - p.x) * 0.018;
                p.y += (h * 0.5 + Math.cos(t * 0.5) * 14 - p.y) * 0.02;
                p.y += p.vy * 0.28;
            } else {
                p.x += p.vx + (gx - p.x) * 0.0007;
                p.y += p.vy + (gy - p.y) * 0.0007;
                if (p.x < -8) p.x = w + 8;
                if (p.x > w + 8) p.x = -8;
                if (p.y < -8) p.y = h + 8;
                if (p.y > h + 8) p.y = -8;
            }
        }

        var adj = neighbors();
        var path = pathThrough(adj);
        var onPath = {};
        var pathEdge = {};
        for (i = 0; i < path.length; i++) onPath[path[i]] = true;
        for (i = 0; i < path.length - 1; i++) {
            pathEdge[path[i] + '-' + path[i + 1]] = true;
            pathEdge[path[i + 1] + '-' + path[i]] = true;
        }

        ctx.save();
        for (i = 0; i < nodes.length; i++) {
            var list = adj[i];
            for (var k = 0; k < list.length; k++) {
                var j = list[k].j;
                if (j <= i) continue;
                if (pathEdge[i + '-' + j]) continue;
                var fade = 1 - list[k].d / LINK;
                ctx.strokeStyle = 'rgba(210, 196, 168,' + (0.14 + 0.22 * fade) + ')';
                ctx.lineWidth = 0.9;
                ctx.beginPath();
                ctx.moveTo(nodes[i].x, nodes[i].y);
                ctx.lineTo(nodes[j].x, nodes[j].y);
                ctx.stroke();
            }
        }

        var pulse = 0.5 + 0.5 * Math.sin(t * 2.1);
        for (i = 0; i < path.length - 1; i++) {
            var a = nodes[path[i]];
            var b = nodes[path[i + 1]];
            ctx.strokeStyle = 'rgba(255, 214, 150,' + (0.18 + 0.12 * pulse) + ')';
            ctx.lineWidth = 4.2;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
            ctx.strokeStyle = 'rgba(255, 236, 205,' + (0.55 + 0.3 * pulse) + ')';
            ctx.lineWidth = 1.35;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
        }
        ctx.restore();

        if (path.length > 1) {
            var segs = path.length - 1;
            var u = (t * 0.28) % 1;
            var f = u * segs;
            var s = Math.min(segs - 1, Math.floor(f));
            var frac = f - s;
            var n0 = nodes[path[s]];
            var n1 = nodes[path[s + 1]];
            var px = n0.x + (n1.x - n0.x) * frac;
            var py = n0.y + (n1.y - n0.y) * frac;
            trail.push({ x: px, y: py });
            if (trail.length > 14) trail.shift();
            for (i = 0; i < trail.length; i++) {
                var tr = trail[i];
                var ta = (i + 1) / trail.length;
                ctx.fillStyle = 'rgba(255, 246, 220,' + (0.12 * ta) + ')';
                ctx.beginPath();
                ctx.arc(tr.x, tr.y, 1.2 + 2.2 * ta, 0, Math.PI * 2);
                ctx.fill();
            }
            var tg = ctx.createRadialGradient(px, py, 0, px, py, 10);
            tg.addColorStop(0, 'rgba(255, 250, 235, 0.95)');
            tg.addColorStop(1, 'rgba(255, 220, 160, 0)');
            ctx.fillStyle = tg;
            ctx.beginPath();
            ctx.arc(px, py, 10, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#fff8ea';
            ctx.beginPath();
            ctx.arc(px, py, 2.1, 0, Math.PI * 2);
            ctx.fill();
        } else {
            trail = [];
        }

        for (i = 0; i < nodes.length; i++) {
            var q = nodes[i];
            var glow = 0.32 + 0.28 * Math.sin(t * 1.3 + q.pulse);
            var r = q.r;
            if (onPath[i] && i > 1) glow += 0.18;
            if (i === 0 || i === 1) {
                var breathe = 0.7 + 0.3 * Math.sin(t * 1.8);
                r = q.r + 0.8;
                var halo = ctx.createRadialGradient(q.x, q.y, 0, q.x, q.y, 22);
                halo.addColorStop(0, 'rgba(255, 230, 190,' + (0.28 * breathe) + ')');
                halo.addColorStop(1, 'rgba(255, 230, 190, 0)');
                ctx.fillStyle = halo;
                ctx.beginPath();
                ctx.arc(q.x, q.y, 22, 0, Math.PI * 2);
                ctx.fill();
                glow = 0.82 + 0.18 * breathe;
            }
            ctx.fillStyle = 'rgba(255, 236, 205,' + glow + ')';
            ctx.beginPath();
            ctx.arc(q.x, q.y, r, 0, Math.PI * 2);
            ctx.fill();
        }

        var vig = ctx.createRadialGradient(w * 0.5, h * 0.48, h * 0.15, w * 0.5, h * 0.5, Math.max(w, h) * 0.72);
        vig.addColorStop(0, 'rgba(11, 10, 9, 0)');
        vig.addColorStop(1, 'rgba(11, 10, 9, 0.42)');
        ctx.fillStyle = vig;
        ctx.fillRect(0, 0, w, h);

        requestAnimationFrame(tick);
    }

    window.addEventListener('resize', resize);
    if (window.ResizeObserver) new ResizeObserver(resize).observe(stage);
    resize();
    requestAnimationFrame(tick);
})();
