/* 16 型恋爱人格徽章（原创几何线稿，currentColor 随主题变色）
 * 灵感：Jokeyou/mbti-test 几何头像思路 + Tabler 线宽，非抄图标库 */
(function () {
    'use strict';

    function svg(body) {
        return (
            '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" fill="none" '
            + 'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
            + body
            + '</svg>'
        );
    }

    window.LP_EMBLEMS = {
        /* 守护者 · 盾 */
        ESCP: svg(
            '<path d="M32 8l18 6v14c0 12-8 20-18 24C22 48 14 40 14 28V14l18-6z"/>'
            + '<path d="M32 22v16M25 30h14"/>'
        ),
        /* 开明领航 · 罗盘 */
        ESCA: svg(
            '<circle cx="32" cy="32" r="18"/>'
            + '<circle cx="32" cy="32" r="3" fill="currentColor" stroke="none"/>'
            + '<path d="M32 14v6M32 44v6M14 32h6M44 32h6"/>'
            + '<path d="M32 32l10-14M32 32l-8 12"/>'
        ),
        /* 阳光筑巢 · 日+巢 */
        EFCP: svg(
            '<circle cx="32" cy="26" r="9"/>'
            + '<path d="M32 8v5M32 39v5M14 26h5M45 26h5M19 13l3.5 3.5M41.5 35.5L45 39M19 39l3.5-3.5M41.5 16.5L45 13"/>'
            + '<path d="M16 50c4-8 12-12 16-12s12 4 16 12"/>'
        ),
        /* 浪漫牧者 · 心+星 */
        EFCA: svg(
            '<path d="M32 48s-16-10-16-22a9 9 0 0 1 16-5 9 9 0 0 1 16 5c0 12-16 22-16 22z"/>'
            + '<path d="M48 14l1.5 3.5L53 19l-3.5 1.5L48 24l-1.5-3.5L43 19l3.5-1.5z" fill="currentColor" stroke="none"/>'
        ),
        /* 灯塔 · 塔+光 */
        ESOP: svg(
            '<path d="M28 54h8M26 46h12l-2-28h-8l-2 28z"/>'
            + '<path d="M30 18h4v-4h-4z"/>'
            + '<path d="M32 10v4M20 16l4 3M44 16l-4 3"/>'
            + '<path d="M18 28h8M38 28h8" opacity=".7"/>'
        ),
        /* 自由先驱 · 旗帜 */
        ESOA: svg(
            '<path d="M18 12v40"/>'
            + '<path d="M18 14h22l-4 8 4 8H18"/>'
            + '<path d="M14 52h28"/>'
        ),
        /* 热心管家 · 屋+心 */
        EFOP: svg(
            '<path d="M10 30L32 12l22 18"/>'
            + '<path d="M16 28v22h32V28"/>'
            + '<path d="M32 38c-3-3-8-1-8 3 0 5 8 9 8 9s8-4 8-9c0-4-5-6-8-3z" fill="currentColor" stroke="none" opacity=".85"/>'
        ),
        /* 春风旅人 · 叶+风 */
        EFOA: svg(
            '<path d="M40 12c-12 2-20 12-22 24 10-4 20 0 26 8 2-14-2-26-4-32z"/>'
            + '<path d="M20 34c8 2 14 8 16 16"/>'
            + '<path d="M12 44c8 0 14 2 20 6M14 50c6 0 12 1 18 4"/>'
        ),
        /* 静谧港湾 · 月+波 */
        ISCP: svg(
            '<path d="M38 16a14 14 0 1 0 10 22 12 12 0 1 1-10-22z"/>'
            + '<path d="M12 44c4 4 8 6 12 6s8-2 12-2 8 2 12 2 8-2 12-6"/>'
            + '<path d="M14 50c4 3 8 4 12 4s8-1 12-1 8 1 12 1"/>'
        ),
        /* 内秀构建 · 积木 */
        ISCA: svg(
            '<rect x="12" y="34" width="16" height="16" rx="2"/>'
            + '<rect x="30" y="34" width="16" height="16" rx="2"/>'
            + '<rect x="21" y="16" width="16" height="16" rx="2"/>'
            + '<path d="M29 16V12M21 24h-4M37 24h4"/>'
        ),
        /* 温柔守望 · 眼+心 */
        IFCP: svg(
            '<path d="M8 32c8-12 16-16 24-16s16 4 24 16c-8 12-16 16-24 16S16 44 8 32z"/>'
            + '<circle cx="32" cy="32" r="7"/>'
            + '<circle cx="32" cy="32" r="2.5" fill="currentColor" stroke="none"/>'
        ),
        /* 诗意栖居 · 羽/花 */
        IFCA: svg(
            '<path d="M18 48c14-4 24-16 28-30-12 2-22 10-28 22z"/>'
            + '<path d="M20 40c6-2 12-8 16-14"/>'
            + '<circle cx="44" cy="16" r="4"/>'
            + '<path d="M44 12v-4M48 16h4M40 16h-4M47 13l3-3M41 13l-3-3"/>'
        ),
        /* 沉思者 · 圆环思考 */
        ISOP: svg(
            '<circle cx="32" cy="28" r="12"/>'
            + '<path d="M24 42c2 6 6 10 8 10s6-4 8-10"/>'
            + '<path d="M28 26h.01M32 26h.01M36 26h.01" stroke-width="3.2"/>'
            + '<path d="M20 14l-4-6M44 14l4-6"/>'
        ),
        /* 孤岛哲人 · 岛 */
        ISOA: svg(
            '<path d="M14 40c6-14 12-20 18-20s12 6 18 20"/>'
            + '<path d="M10 44h44"/>'
            + '<path d="M18 48c6 3 12 4 14 4s8-1 14-4"/>'
            + '<circle cx="40" cy="16" r="5"/>'
            + '<path d="M40 11V8"/>'
        ),
        /* 花园隐士 · 花盆 */
        IFOP: svg(
            '<path d="M24 36h16l-2 16H26l-2-16z"/>'
            + '<path d="M22 36h20"/>'
            + '<circle cx="32" cy="22" r="7"/>'
            + '<path d="M32 10v5M22 22h5M37 22h5M24 14l3.5 3.5M36.5 26.5L40 30M24 30l3.5-3.5M36.5 17.5L40 14"/>'
        ),
        /* 星尘游吟 · 星+弧 */
        IFOA: svg(
            '<path d="M32 10l3 9h9l-7 5 3 9-8-5-8 5 3-9-7-5h9z" fill="currentColor" stroke="none" opacity=".9"/>'
            + '<path d="M14 40c6 8 14 12 18 12s12-4 18-12"/>'
            + '<circle cx="18" cy="22" r="1.6" fill="currentColor" stroke="none"/>'
            + '<circle cx="48" cy="28" r="1.2" fill="currentColor" stroke="none"/>'
            + '<circle cx="50" cy="18" r="1" fill="currentColor" stroke="none"/>'
        )
    };

    function removeDeco(el, sel) {
        el.querySelectorAll(sel).forEach(function (n) {
            if (n.parentNode) n.parentNode.removeChild(n);
        });
    }

    window.ensureLovePersonalityEmblem = function (el, code) {
        if (!el) return;
        var c = String(code || '').toUpperCase().replace(/[^A-Z]/g, '').slice(0, 4);
        removeDeco(el, '.lp-emblem, .lp-stamp, .lp-watermark, .lp-corners, .lp-grid');
        if (c.length !== 4 || !window.LP_EMBLEMS[c]) return;
        /* 外框 (.lp-share-frame) 不挂装饰，只给内卡 */
        if (el.classList && el.classList.contains('lp-share-frame')) return;

        var grid = document.createElement('div');
        grid.className = 'lp-grid';
        grid.setAttribute('aria-hidden', 'true');
        el.insertBefore(grid, el.firstChild);

        var mark = document.createElement('div');
        mark.className = 'lp-watermark';
        mark.setAttribute('aria-hidden', 'true');
        mark.textContent = c;
        el.insertBefore(mark, el.firstChild);

        var corners = document.createElement('div');
        corners.className = 'lp-corners';
        corners.setAttribute('aria-hidden', 'true');
        corners.innerHTML = '<i class="c tl"></i><i class="c tr"></i><i class="c bl"></i><i class="c br"></i>';
        el.insertBefore(corners, el.firstChild);

        var wrap = document.createElement('div');
        wrap.className = 'lp-emblem';
        wrap.setAttribute('aria-hidden', 'true');
        wrap.innerHTML = window.LP_EMBLEMS[c] + '<span class="lp-emblem-ring"></span>';
        el.insertBefore(wrap, el.firstChild);

        var stamp = document.createElement('span');
        stamp.className = 'lp-stamp';
        stamp.setAttribute('aria-hidden', 'true');
        stamp.textContent = 'No. ' + c;
        el.appendChild(stamp);
    };
})();
