/* 恋爱人格卡片：视口内渲染圆角卡 → 截图 → 桌面复制图 / 手机预览长按保存 */
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

    /** 给人格卡套上 16 型主题（配色 + 徽章/水印等装饰） */
    window.applyLovePersonalityTheme = function (el, code) {
        if (!el) return;
        var c = normalizeLpCode(code);
        window.applyLovePersonalityColors(el, c);
        if (c.length === 4) {
            if (typeof window.ensureLovePersonalityEmblem === 'function') {
                window.ensureLovePersonalityEmblem(el, c);
            }
        } else if (typeof window.ensureLovePersonalityEmblem === 'function') {
            window.ensureLovePersonalityEmblem(el, '');
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

    function buildShareStage(cardEl) {
        var stage = document.createElement('div');
        stage.id = 'lp-share-stage';
        stage.className = 'lp-share-stage lp-share-stage-live';
        stage.setAttribute('aria-hidden', 'true');

        var frame = document.createElement('div');
        frame.className = 'lp-share-frame';

        var card = document.createElement('div');
        card.className = 'lp-share-card';

        var themeCode = cardEl.getAttribute('data-lp-code')
            || normalizeLpCode(cardEl.dataset && cardEl.dataset.lpCode);
        if (themeCode && themeCode.length === 4) {
            // 外框只铺渐变底；徽章/印章/水印只挂在内卡，防止重叠
            window.applyLovePersonalityColors(frame, themeCode);
            window.applyLovePersonalityTheme(card, themeCode);
        }

        function appendClone(node) {
            if (!node || !node.cloneNode) return;
            if (node.classList && (
                node.classList.contains('personality-actions')
                || node.classList.contains('lp-no-capture')
                || node.classList.contains('lp-emblem')
                || node.classList.contains('lp-stamp')
                || node.classList.contains('lp-watermark')
                || node.classList.contains('lp-corners')
                || node.classList.contains('lp-grid')
                || node.classList.contains('lp-modal-scroll')
            )) return;
            var clone = node.cloneNode(true);
            if (clone.classList && clone.classList.contains('lp-capture-brand')) {
                clone.style.display = 'block';
            }
            card.appendChild(clone);
        }

        var kids = cardEl.children;
        for (var i = 0; i < kids.length; i++) {
            var node = kids[i];
            // 弹窗内容包在 .lp-modal-scroll 里：摊平其子节点，保证分享卡结构一致
            if (node.classList && node.classList.contains('lp-modal-scroll')) {
                var inner = node.children;
                for (var j = 0; j < inner.length; j++) {
                    appendClone(inner[j]);
                }
                continue;
            }
            appendClone(node);
        }
        /* 徽章由 applyLovePersonalityTheme 重新挂上，避免重复 */

        if (!card.querySelector('.lp-capture-brand')) {
            var brand = document.createElement('p');
            brand.className = 'lp-capture-brand';
            brand.textContent = 'CampusMatch · campusmatch.com.cn';
            card.appendChild(brand);
        }

        frame.appendChild(card);
        stage.appendChild(frame);
        document.body.appendChild(stage);
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

    async function captureCard(cardEl) {
        if (typeof html2canvas !== 'function') {
            throw new Error('html2canvas missing');
        }
        var mask = showCaptureMask();
        var stage = buildShareStage(cardEl);
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
            backgroundColor: '#ffffff',
            scale: scale,
            useCORS: true,
            allowTaint: true,
            logging: false,
            scrollX: 0,
            scrollY: 0,
            windowWidth: Math.max(stage.offsetWidth, 320),
            windowHeight: Math.max(stage.offsetHeight, 200),
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
                return await html2canvas(stage, opts);
            } catch (err1) {
                console.warn('themed capture failed, retry simplified', err1);
                // 降级：去掉装饰层再截，避免冷门 CSS 拖垮 html2canvas
                stage.querySelectorAll('.lp-emblem, .lp-stamp, .lp-watermark, .lp-corners, .lp-grid')
                    .forEach(function (n) {
                        if (n.parentNode) n.parentNode.removeChild(n);
                    });
                await new Promise(function (r) { setTimeout(r, 40); });
                return await html2canvas(stage, opts);
            }
        } finally {
            if (stage && stage.parentNode) stage.parentNode.removeChild(stage);
            if (mask && mask.parentNode) mask.parentNode.removeChild(mask);
            window.scrollTo(0, y);
        }
    }

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
            var canvas = await captureCard(cardEl);
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
