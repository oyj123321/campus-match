/* 恋爱人格卡片：精简分享卡 → 截图 → 桌面复制图 / 手机预览长按保存 */
(function () {
    'use strict';

    function t(key) {
        return (typeof window.t === 'function') ? window.t(key) : key;
    }

    function isTouchMobile() {
        var ua = navigator.userAgent || '';
        if (/Android|iPhone|iPad|iPod|Mobile|MicroMessenger|QQ\//i.test(ua)) return true;
        return (navigator.maxTouchPoints > 1 && Math.min(window.innerWidth, window.innerHeight) < 900);
    }

    function normalizeLpCode(code) {
        return String(code || '').toUpperCase().replace(/[^A-Z]/g, '').slice(0, 4);
    }

    var CM_SHARE_HOST = 'campusmatch.com.cn';
    var CM_SHARE_ORIGIN = 'https://campusmatch.com.cn';

    /** 本机 / 裸 IP：可见文案与扫码落地都改用正式域名，避免卡片露出 IP */
    function isDevOrIpOrigin(url) {
        var s = String(url || '');
        if (!s) return true;
        if (/localhost|127\.0\.0\.1/i.test(s)) return true;
        try {
            var host = String(new URL(s).hostname || '');
            if (/^\d{1,3}(?:\.\d{1,3}){3}$/.test(host)) return true;
            if (/^\[?[0-9a-f:]+\]?$/i.test(host) && host.indexOf(':') >= 0) return true;
        } catch (e) {
            if (/\b\d{1,3}(?:\.\d{1,3}){3}\b/.test(s)) return true;
        }
        return false;
    }

    function currentInviteCode() {
        return String(window.CM_INVITE_CODE || '').trim().toUpperCase();
    }

    /** 分享落地页：可用 PUBLIC_URL；本机/IP 则回落正式域名；带邀请码便于扫卡注册 */
    function shareLandingUrl() {
        var base = String(window.CM_PUBLIC_URL || '').trim()
            || ((typeof location !== 'undefined' && location.origin) ? location.origin : '');
        if (isDevOrIpOrigin(base)) {
            base = CM_SHARE_ORIGIN;
        }
        var url = base.replace(/\/$/, '') + '/?from=lp_share';
        var inv = currentInviteCode();
        if (inv) url += '&invite=' + encodeURIComponent(inv);
        return url;
    }

    /** 卡片可见域名：永远正式站名，不跟 CM_PUBLIC_URL / location 的 IP */
    function displayHost() {
        return CM_SHARE_HOST;
    }

    /** E/I 系别水印文案（极淡，不抢型名） */
    function shareSeriesWatermark(code) {
        var c = normalizeLpCode(code);
        var letter = c.charAt(0);
        if (letter === 'E') return t('lp.wmExtra');
        if (letter === 'I') return t('lp.wmIntro');
        return t('lp.wmLove');
    }

    function blobToDataUrl(blob) {
        return new Promise(function (resolve, reject) {
            var reader = new FileReader();
            reader.onload = function () { resolve(reader.result); };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    /** 本地生成二维码 data URL（优先）；失败再试外部 API */
    async function loadQrDataUrl(targetUrl) {
        try {
            if (typeof qrcode === 'function') {
                var qr = qrcode(0, 'M');
                qr.addData(targetUrl);
                qr.make();
                var cell = 4;
                var count = qr.getModuleCount();
                var size = count * cell;
                var canvas = document.createElement('canvas');
                canvas.width = size;
                canvas.height = size;
                var ctx = canvas.getContext('2d');
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, size, size);
                ctx.fillStyle = '#0f172a';
                for (var r = 0; r < count; r++) {
                    for (var c = 0; c < count; c++) {
                        if (qr.isDark(r, c)) {
                            ctx.fillRect(c * cell, r * cell, cell, cell);
                        }
                    }
                }
                return canvas.toDataURL('image/png');
            }
        } catch (errLocal) {
            console.warn('local QR failed', errLocal);
        }
        var api = 'https://api.qrserver.com/v1/create-qr-code/?size=160x160&margin=6&data='
            + encodeURIComponent(targetUrl);
        try {
            var res = await fetch(api);
            if (!res.ok) throw new Error('qr http ' + res.status);
            var blob = await res.blob();
            return await blobToDataUrl(blob);
        } catch (err) {
            console.warn('QR fetch failed', err);
            return '';
        }
    }

    function waitImg(img) {
        return new Promise(function (resolve) {
            if (!img || !img.src) return resolve();
            if (img.complete && img.naturalWidth > 0) return resolve();
            var done = function () {
                img.removeEventListener('load', done);
                img.removeEventListener('error', done);
                resolve();
            };
            img.addEventListener('load', done);
            img.addEventListener('error', done);
            setTimeout(done, 2500);
        });
    }

    /** html2canvas 截图前等书法体就绪，避免金句回落到系统无衬线 */
    async function waitVerseFont() {
        try {
            if (document.fonts && document.fonts.load) {
                await Promise.race([
                    document.fonts.load('400 32px "CM Verse"'),
                    new Promise(function (r) { setTimeout(r, 1200); })
                ]);
            }
        } catch (err) {}
    }

    function readPersonalityFromCard(cardEl) {
        if (!cardEl) return {};
        var nameEl = cardEl.querySelector('.personality-name');
        var codeEl = cardEl.querySelector('.personality-code');
        var subEl = cardEl.querySelector('.personality-sub');
        return {
            name: nameEl ? (nameEl.textContent || '').trim() : '',
            code: codeEl ? (codeEl.textContent || '').trim() : '',
            subtitle: subEl ? (subEl.textContent || '').trim() : ''
        };
    }

    /** 只套配色/class（外框用）；不挂徽章，避免 frame+card 双重装饰重叠 */
    window.applyLovePersonalityColors = function (el, code) {
        if (!el) return;
        var c = normalizeLpCode(code);
        el.className = String(el.className || '')
            .replace(/\blp-theme-[A-Z]{4}\b/g, '')
            .replace(/\s+/g, ' ')
            .trim();
        if (c.length === 4) {
            el.setAttribute('data-lp-code', c);
            el.classList.add('lp-theme-' + c);
        } else {
            el.removeAttribute('data-lp-code');
        }
    };

    /** 16 型岛图 URL（文件名大写四字母） */
    window.lovePersonalityIslandUrl = function (code) {
        var c = normalizeLpCode(code);
        return c.length === 4 ? ('/static/personality_islands/' + c + '.png?v=1970') : '';
    };

    /**
     * 在结果卡 / 分享卡上挂岛图作主视觉；缺图则隐藏并回退纹章。
     * 插入点：分享卡 `.lp-share-visual`（出血主视觉）优先；
     * 否则 `.personality-name` 前 / `.lp-share-hero` 顶部。
     */
    window.ensureLovePersonalityIsland = function (el, code) {
        if (!el) return null;
        var c = normalizeLpCode(code);
        var wrap = el.querySelector('.lp-island-wrap');
        if (c.length !== 4) {
            if (wrap && wrap.parentNode) wrap.parentNode.removeChild(wrap);
            el.classList.remove('lp-has-island', 'lp-island-pending');
            return null;
        }

        var visual = el.querySelector('.lp-share-visual');
        var nameEl = el.querySelector('.personality-name');
        var hero = el.querySelector('.lp-share-hero');
        var parent = visual
            || (nameEl && nameEl.parentNode)
            || hero
            || el.querySelector('.lp-modal-scroll')
            || el;
        var before = visual ? null : (nameEl || (hero ? hero.firstChild : null));

        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'lp-island-wrap';
            wrap.setAttribute('aria-hidden', 'true');
            wrap.hidden = true;
            var img = document.createElement('img');
            img.className = 'lp-island';
            img.alt = '';
            img.decoding = 'async';
            img.loading = 'eager';
            wrap.appendChild(img);
        }
        if (visual) {
            if (wrap.parentNode !== visual) visual.appendChild(wrap);
        } else if (wrap.parentNode !== parent) {
            if (before && before.parentNode === parent) parent.insertBefore(wrap, before);
            else parent.insertBefore(wrap, parent.firstChild);
        } else if (before && wrap.nextSibling !== before && before.parentNode === parent) {
            parent.insertBefore(wrap, before);
        }

        var imgEl = wrap.querySelector('.lp-island');
        if (!imgEl) return wrap;
        var url = window.lovePersonalityIslandUrl(c);
        var applyOk = function () {
            wrap.hidden = false;
            el.classList.remove('lp-island-pending');
            el.classList.add('lp-has-island');
        };
        var applyFail = function () {
            wrap.hidden = true;
            el.classList.remove('lp-has-island', 'lp-island-pending');
        };
        imgEl.onload = applyOk;
        imgEl.onerror = applyFail;
        imgEl.alt = c;
        if (imgEl.getAttribute('src') === url && imgEl.complete && imgEl.naturalWidth > 0) {
            applyOk();
        } else {
            wrap.hidden = true;
            el.classList.remove('lp-has-island');
            el.classList.add('lp-island-pending');
            imgEl.src = url;
        }
        return wrap;
    };

    /** 给人格卡套上 16 型主题（配色 + 岛图主视觉 + 徽章/水印等装饰） */
    window.applyLovePersonalityTheme = function (el, code) {
        if (!el) return;
        var c = normalizeLpCode(code);
        window.applyLovePersonalityColors(el, c);
        if (c.length === 4) {
            if (typeof window.ensureLovePersonalityEmblem === 'function') {
                window.ensureLovePersonalityEmblem(el, c);
            }
            window.ensureLovePersonalityIsland(el, c);
        } else {
            if (typeof window.ensureLovePersonalityEmblem === 'function') {
                window.ensureLovePersonalityEmblem(el, '');
            }
            window.ensureLovePersonalityIsland(el, '');
        }
    };

    function ensurePreviewDom() {
        var root = document.getElementById('lp-share-preview');
        if (root) return root;
        root = document.createElement('div');
        root.id = 'lp-share-preview';
        root.className = 'lp-share-preview';
        root.style.display = 'none';
        root.setAttribute('aria-hidden', 'true');
        root.innerHTML =
            '<div class="lp-share-preview-backdrop" data-lp-close></div>'
            + '<div class="lp-share-preview-panel card" role="dialog">'
            +   '<h3 data-i18n="lp.shareReady">' + t('lp.shareReady') + '</h3>'
            +   '<p class="hint" id="lp-share-hint" data-i18n="lp.shareHint">' + t('lp.shareHint') + '</p>'
            +   '<p class="lp-share-longpress-tip" id="lp-share-longpress-tip" style="display:none;" data-i18n="lp.longPressTip">' + t('lp.longPressTip') + '</p>'
            +   '<img id="lp-share-preview-img" class="lp-share-preview-img" alt="CampusMatch personality">'
            +   '<div class="lp-share-preview-actions">'
            +     '<button type="button" class="btn btn-primary" id="lp-share-primary" style="display:none;"></button>'
            +     '<button type="button" class="btn btn-secondary" id="lp-share-copy-img" style="display:none;" data-i18n="lp.copyImg">' + t('lp.copyImg') + '</button>'
            +     '<button type="button" class="btn btn-secondary" data-lp-close data-i18n="lp.close">' + t('lp.close') + '</button>'
            +   '</div>'
            + '</div>';
        document.body.appendChild(root);
        root.addEventListener('click', function (e) {
            if (e.target && e.target.getAttribute('data-lp-close') !== null) {
                hidePreview();
            }
        });
        return root;
    }

    function hidePreview() {
        var root = document.getElementById('lp-share-preview');
        if (!root) return;
        root.style.display = 'none';
        root.setAttribute('aria-hidden', 'true');
    }

    function canShareFile(file) {
        try {
            return !!(file && navigator.canShare && navigator.canShare({ files: [file] }));
        } catch (e) {
            return false;
        }
    }

    function tryBlobDownload(blob) {
        var url = URL.createObjectURL(blob);
        try {
            var a = document.createElement('a');
            a.href = url;
            a.download = 'campusmatch-personality.png';
            a.rel = 'noopener';
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } finally {
            setTimeout(function () { URL.revokeObjectURL(url); }, 2500);
        }
    }

    function showPreview(dataUrl, blob, file) {
        var root = ensurePreviewDom();
        if (typeof window.applyI18n === 'function') window.applyI18n();
        var mobile = isTouchMobile();
        var shareOk = canShareFile(file);
        var hint = document.getElementById('lp-share-hint');
        var longTip = document.getElementById('lp-share-longpress-tip');
        var img = document.getElementById('lp-share-preview-img');
        var primary = document.getElementById('lp-share-primary');
        var copyBtn = document.getElementById('lp-share-copy-img');
        img.src = dataUrl;
        img.classList.remove('lp-share-preview-img-pulse');

        // 原则：没有把握生效的按钮就不展示，避免用户空点
        if (mobile && !shareOk) {
            // 微信等：只引导长按，不放「保存」按钮
            if (hint) {
                hint.setAttribute('data-i18n', 'lp.shareHintMobile');
                hint.textContent = t('lp.shareHintMobile');
            }
            if (longTip) {
                longTip.style.display = '';
                longTip.textContent = t('lp.longPressTip');
            }
            primary.style.display = 'none';
            copyBtn.style.display = 'none';
            img.classList.add('lp-share-preview-img-pulse');
        } else if (mobile && shareOk) {
            // Safari/Chrome：一个「分享」按钮打开系统面板（含存相册）
            if (hint) {
                hint.setAttribute('data-i18n', 'lp.shareHintMobileShare');
                hint.textContent = t('lp.shareHintMobileShare');
            }
            if (longTip) longTip.style.display = 'none';
            primary.style.display = '';
            primary.setAttribute('data-i18n', 'lp.sysShare');
            primary.textContent = t('lp.sysShare');
            primary.onclick = async function () {
                try {
                    await navigator.share({
                        files: [file],
                        title: 'CampusMatch',
                        text: t('lp.title')
                    });
                } catch (err) {
                    if (err && err.name === 'AbortError') return;
                    // 分享失败再退回长按引导，仍不假装「已保存」
                    if (longTip) {
                        longTip.style.display = '';
                        longTip.textContent = t('lp.longPressTip');
                    }
                    img.classList.add('lp-share-preview-img-pulse');
                    alert(t('lp.saveFallbackLongPress'));
                }
            };
            copyBtn.style.display = 'none';
        } else {
            // 桌面：复制图片 + 下载（Blob）
            if (hint) {
                hint.setAttribute('data-i18n', 'lp.shareHint');
                hint.textContent = t('lp.shareHint');
            }
            if (longTip) longTip.style.display = 'none';
            primary.style.display = '';
            primary.setAttribute('data-i18n', 'lp.saveImg');
            primary.textContent = t('lp.saveImg');
            primary.onclick = function () { tryBlobDownload(blob); };
            copyBtn.style.display = '';
            copyBtn.onclick = async function () {
                var ok = await copyImageBlob(blob);
                if (ok) alert(t('lp.imgCopied'));
                else alert(t('lp.copyImgFail'));
            };
        }

        root.style.display = 'flex';
        root.setAttribute('aria-hidden', 'false');
    }

    function canvasToBlob(canvas) {
        return new Promise(function (resolve) {
            if (canvas.toBlob) {
                canvas.toBlob(function (blob) { resolve(blob); }, 'image/png');
            } else {
                var data = canvas.toDataURL('image/png');
                var bin = atob(data.split(',')[1]);
                var arr = new Uint8Array(bin.length);
                for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
                resolve(new Blob([arr], { type: 'image/png' }));
            }
        });
    }

    async function copyImageBlob(blob) {
        if (!blob || !navigator.clipboard || typeof ClipboardItem === 'undefined') {
            return false;
        }
        try {
            await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
            return true;
        } catch (e1) {
            try {
                await navigator.clipboard.write([
                    new ClipboardItem({ 'image/png': Promise.resolve(blob) })
                ]);
                return true;
            } catch (e2) {
                console.warn('copy image failed', e2);
                return false;
            }
        }
    }

    /**
     * 构建精简分享卡（海报感 / 打磨试版）：
     * 洗底外框（无厚彩框）→ 顶栏 → 出血岛图 → 型名/code/金句 → 底栏 CTA+域名+二维码
     */
    async function buildSlimShareStage(personality, themeCode) {
        var landing = shareLandingUrl();
        var qrData = await loadQrDataUrl(landing);
        var hostLabel = displayHost();
        var p = personality || {};
        var name = p.name || p.label || '—';
        var code = normalizeLpCode(p.code || p.type) || String(p.code || p.type || '—');
        var subtitle = p.subtitle || p.summary || '';

        var stage = document.createElement('div');
        stage.id = 'lp-share-stage';
        stage.className = 'lp-share-stage lp-share-stage-live';
        stage.setAttribute('aria-hidden', 'true');

        var frame = document.createElement('div');
        frame.className = 'lp-share-frame';

        /* 主题色洗底层：用 --lp-1/--lp-2 全色 + opacity，避开 color-mix（截图更稳） */
        var wash = document.createElement('div');
        wash.className = 'lp-share-wash';
        wash.setAttribute('aria-hidden', 'true');

        var card = document.createElement('div');
        card.className = 'lp-share-card lp-share-card-slim';

        if (themeCode && themeCode.length === 4) {
            window.applyLovePersonalityColors(frame, themeCode);
        }

        var brand = document.createElement('div');
        brand.className = 'lp-share-brandbar';
        brand.innerHTML =
            '<div class="lp-share-brand-name">CampusMatch</div>'
            + '<div class="lp-share-brand-meta">'
            +   '<span class="lp-share-brand-tag">' + t('lp.brandTag') + '</span>'
            + '</div>'
            + '<div class="lp-share-brand-modes">' + t('lp.shareModes') + '</div>';

        /* 岛图出血区：全宽贴顶，主题色带托底 */
        var visual = document.createElement('div');
        visual.className = 'lp-share-visual';

        var hero = document.createElement('div');
        hero.className = 'lp-share-hero';
        var nameEl = document.createElement('p');
        nameEl.className = 'personality-name';
        nameEl.textContent = name;
        var codeEl = document.createElement('p');
        codeEl.className = 'personality-code';
        codeEl.textContent = code;
        var subEl = document.createElement('p');
        subEl.className = 'personality-sub';
        if (subtitle) subEl.textContent = subtitle;
        hero.appendChild(nameEl);
        hero.appendChild(codeEl);
        if (subtitle) hero.appendChild(subEl);

        var foot = document.createElement('div');
        foot.className = 'lp-share-foot';
        var ctaWrap = document.createElement('div');
        ctaWrap.className = 'lp-share-cta';
        var cta = document.createElement('p');
        cta.className = 'lp-share-cta-text';
        cta.textContent = t('lp.shareCta');
        var host = document.createElement('p');
        host.className = 'lp-share-cta-host';
        host.textContent = hostLabel;
        ctaWrap.appendChild(cta);
        ctaWrap.appendChild(host);
        var inv = currentInviteCode();
        if (inv) {
            var invEl = document.createElement('p');
            invEl.className = 'lp-share-invite';
            invEl.textContent = t('lp.inviteLine').replace('{code}', inv);
            ctaWrap.appendChild(invEl);
            var invHint = document.createElement('p');
            invHint.className = 'lp-share-invite-hint';
            invHint.textContent = t('lp.inviteHint');
            ctaWrap.appendChild(invHint);
        }

        var qrWrap = document.createElement('div');
        qrWrap.className = 'lp-share-qr';
        if (qrData) {
            var qrImg = document.createElement('img');
            qrImg.className = 'lp-share-qr-img';
            qrImg.alt = 'QR';
            qrImg.src = qrData;
            qrWrap.appendChild(qrImg);
        } else {
            var qrFallback = document.createElement('div');
            qrFallback.className = 'lp-share-qr-fallback';
            qrFallback.textContent = hostLabel;
            qrWrap.appendChild(qrFallback);
        }

        foot.appendChild(ctaWrap);
        foot.appendChild(qrWrap);

        var disc = document.createElement('p');
        disc.className = 'lp-share-disc';
        disc.textContent = t('lp.shareDisc');

        card.appendChild(brand);
        card.appendChild(visual);
        card.appendChild(hero);
        card.appendChild(foot);
        card.appendChild(disc);

        frame.appendChild(card);

        /* 结构就绪后再挂主题/岛图（岛图进 .lp-share-visual） */
        if (themeCode && themeCode.length === 4) {
            window.applyLovePersonalityTheme(card, themeCode);
            /* 海报感：系别大字水印，弱化报表角标 */
            var wm = card.querySelector('.lp-watermark');
            if (wm) wm.textContent = shareSeriesWatermark(themeCode);
            card.querySelectorAll('.lp-corners, .lp-grid').forEach(function (n) {
                if (n.parentNode) n.parentNode.removeChild(n);
            });
        }
        /* 洗底只盖插画，不盖型名/金句 */
        visual.appendChild(wash);

        stage.appendChild(frame);
        document.body.appendChild(stage);

        var islandImg = card.querySelector('.lp-island');
        if (islandImg) await waitImg(islandImg);
        var img = card.querySelector('.lp-share-qr-img');
        if (img) await waitImg(img);
        await waitVerseFont();
        return stage;
    }

    function showCaptureMask() {
        var mask = document.createElement('div');
        mask.id = 'lp-share-mask';
        mask.className = 'lp-share-mask';
        mask.innerHTML = '<span>' + t('lp.sharing') + '</span>';
        document.body.appendChild(mask);
        return mask;
    }

    async function captureCard(cardEl, personality) {
        if (typeof html2canvas !== 'function') {
            throw new Error('html2canvas missing');
        }
        var fromDom = readPersonalityFromCard(cardEl);
        var p = Object.assign({}, fromDom, personality || {});
        var themeCode = normalizeLpCode(
            (personality && (personality.code || personality.type))
            || (cardEl && cardEl.getAttribute('data-lp-code'))
            || p.code
        );

        var mask = showCaptureMask();
        var stage = await buildSlimShareStage(p, themeCode);
        var captureTarget = stage.querySelector('.lp-share-frame') || stage;
        var y = window.scrollY || window.pageYOffset || 0;
        // iOS：离屏/负坐标会出空白；先滚到顶再截视口内节点
        window.scrollTo(0, 0);
        await new Promise(function (r) {
            requestAnimationFrame(function () {
                requestAnimationFrame(function () { setTimeout(r, 120); });
            });
        });
        var mobile = isTouchMobile();
        var scale = mobile
            ? Math.min(2, window.devicePixelRatio || 2)
            : Math.min(2.2, (window.devicePixelRatio || 2) * 1.1);
        var opts = {
            backgroundColor: null,
            scale: scale,
            useCORS: true,
            allowTaint: true,
            logging: false,
            scrollX: 0,
            scrollY: 0,
            windowWidth: Math.max(captureTarget.offsetWidth, 320),
            windowHeight: Math.max(captureTarget.offsetHeight, 200),
            x: 0,
            y: 0,
            ignoreElements: function (el) {
                return !!(el && el.classList && el.classList.contains('lp-grid'));
            },
            onclone: function (doc) {
                var root = doc.getElementById('lp-share-stage');
                if (!root) return;
                root.querySelectorAll('.lp-emblem-ring').forEach(function (n) {
                    n.style.animation = 'none';
                });
                root.querySelectorAll('.lp-grid').forEach(function (n) {
                    if (n.parentNode) n.parentNode.removeChild(n);
                });
            }
        };
        try {
            try {
                return await html2canvas(captureTarget, opts);
            } catch (err1) {
                console.warn('themed capture failed, retry simplified', err1);
                // 降级：去掉装饰层再截，避免冷门 CSS 拖垮 html2canvas
                stage.querySelectorAll('.lp-emblem, .lp-stamp, .lp-watermark, .lp-corners, .lp-grid')
                    .forEach(function (n) {
                        if (n.parentNode) n.parentNode.removeChild(n);
                    });
                await new Promise(function (r) { setTimeout(r, 40); });
                return await html2canvas(captureTarget, opts);
            }
        } finally {
            if (stage && stage.parentNode) stage.parentNode.removeChild(stage);
            if (mask && mask.parentNode) mask.parentNode.removeChild(mask);
            window.scrollTo(0, y);
        }
    }

    window.buildLovePersonalityShareStage = buildSlimShareStage;

    window.sharePersonalityCard = async function (cardEl, personality) {
        if (!cardEl) return;
        if (personality) {
            window.applyLovePersonalityTheme(cardEl, personality.code || personality.type);
        }
        var btn = document.activeElement;
        var oldLabel = btn && btn.textContent;
        if (btn && btn.tagName === 'BUTTON') {
            btn.disabled = true;
            btn.textContent = t('lp.sharing');
        }
        try {
            var canvas = await captureCard(cardEl, personality);
            if (!canvas || canvas.width < 8 || canvas.height < 8) {
                throw new Error('empty canvas');
            }
            var blob = await canvasToBlob(canvas);
            if (!blob || blob.size < 100) throw new Error('blob failed');
            var dataUrl = canvas.toDataURL('image/png');
            var file = new File([blob], 'campusmatch-personality.png', { type: 'image/png' });

            // 手机：剪贴板写图大多不可用 → 直接出预览长按保存
            if (isTouchMobile()) {
                showPreview(dataUrl, blob, file);
                return;
            }

            var ok = await copyImageBlob(blob);
            if (ok) {
                alert(t('lp.imgCopied'));
                return;
            }
            showPreview(dataUrl, blob, file);
        } catch (err) {
            console.error(err);
            alert(t('lp.shareFail'));
        } finally {
            if (btn && btn.tagName === 'BUTTON') {
                btn.disabled = false;
                btn.textContent = oldLabel || t('lp.share');
            }
        }
    };
})();
