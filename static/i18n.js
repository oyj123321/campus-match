/* CampusMatch i18n — 简体(zh) / 繁體(tw) / English(en) / Português(pt)
   用法：
   - 静态文本：<span data-i18n="key"></span>、placeholder 用 data-i18n-ph
   - 学校名：<span data-school="澳门大学"></span>
   - 揭晓时间（含“每周X”）：<span data-batch="每周二 21:00"></span>
   - JS 动态串：t('key') / tf('key', {n: 3})
   - 切换语言后广播 window 事件 'cm:lang'，页面可重渲染动态区域
*/
(function () {
    'use strict';

    var SCHOOLS = {
        '澳门大学':     { tw: '澳門大學', en: 'University of Macau', pt: 'Universidade de Macau' },
        '澳门科技大学': { tw: '澳門科技大學', en: 'Macau Univ. of Science & Technology', pt: 'Univ. de Ciência e Tecnologia de Macau' },
        '澳门理工大学': { tw: '澳門理工大學', en: 'Macao Polytechnic University', pt: 'Universidade Politécnica de Macau' },
        '澳门旅游大学': { tw: '澳門旅遊大學', en: 'Macao University of Tourism', pt: 'Universidade de Turismo de Macau' },
        '澳门城市大学': { tw: '澳門城市大學', en: 'City University of Macau', pt: 'Universidade da Cidade de Macau' }
    };

    var WEEKDAYS = {
        '周一': { tw: '週一', en: 'Mon', pt: 'seg.' }, '周二': { tw: '週二', en: 'Tue', pt: 'ter.' },
        '周三': { tw: '週三', en: 'Wed', pt: 'qua.' }, '周四': { tw: '週四', en: 'Thu', pt: 'qui.' },
        '周五': { tw: '週五', en: 'Fri', pt: 'sex.' }, '周六': { tw: '週六', en: 'Sat', pt: 'sáb.' },
        '周日': { tw: '週日', en: 'Sun', pt: 'dom.' }
    };

    var I18N = {
    zh: {
        'nav.matches': '匹配结果', 'nav.questionnaire': '问卷', 'nav.logout': '返回首页',
        'footer.line1': 'CampusMatch — 深度问卷 · 算法匹配 · 每周揭晓',
        'footer.line2': '账号删除 / 反馈：请用学校邮箱联系运营（暂用注册所用 SMTP 发件邮箱）',
        // 首页
        'kicker': 'Campus Match · 澳门 & 大湾区',
        'hero.t1': '在你的校园里，', 'hero.t2': '遇见那个刚好合拍的人',
        'hero.sub': '学校邮箱验证在校身份 → 39 题走心问卷 → 每周一对一揭晓，附相处说明书与破冰话题。慢一点，但更认真。',
        'stat.pre': '已有', 'stat.post': '位同学验证加入 · 揭晓时间',
        'step1.title': '① 输入学校邮箱', 'form.email': '学校邮箱', 'form.email.ph': '例如：yc12345@um.edu.mo',
        'btn.send': '发送验证码', 'btn.resendCode': '重新发送', 'schools.support': '支持学校（已验证人数）：',
        'step2.title': '② 输入验证码', 'step2.sent': '验证码已发送到你的学校邮箱，请检查收件箱（和垃圾邮件）',
        'form.token': '6 位验证码', 'form.token.ph': '输入验证码', 'btn.verify': '验证',
        'how.title': '三步，认识那个合拍的人',
        'step01.h': '答一份走心问卷', 'step01.p': '39 道题覆盖价值观、生活习惯、情感风格、兴趣与相处预期，可标记「对我很重要」加权。',
        'step02.h': '预约本周匹配', 'step02.p': '每周统一揭晓一位一对一对象：昵称、几个契合点与破冰话题——分数不展示，让你们自己聊。',
        'step03.h': '照着破冰开聊', 'step03.p': '配对成功互见学校邮箱与你留下的联系方式；附破冰话题，开口不再尴尬。',
        'why.title': '我们和「刷脸软件」不一样',
        'feat1.h': '只限在校生', 'feat1.p': '仅支持列表内学校邮箱注册，你遇到的每个人都经过校园身份验证。',
        'feat2.h': '一周一位，宁缺毋滥', 'feat2.p': '没有无限右滑。每人每周最多被配一次；页面只给契合点，不晒匹配度分数。',
        'feat3.h': '隐私优先', 'feat3.p': '资料不公开陈列；学校邮箱与附加联系方式只在配对成功后互见，还可拉黑不想遇到的人。',
        'feat4.h': '告诉你「为什么是 TA」', 'feat4.p': '不给分数焦虑：只列出几个契合点与破冰话题，剩下的交给聊天。',
        'privacy.title': '使用说明 & 隐私',
        'privacy.li1': '仅接受支持列表内的学校邮箱注册，用于确认在校身份。',
        'privacy.li2': '问卷与择偶取向用于匹配；学校邮箱与附加联系方式仅在匹配成功后互见。',
        'privacy.li3': '每人每周最多匹配一次（双向）；结果只展示契合点与联系渠道，不以分数衡量；以网站页面为准。',
        'privacy.li4': '可随时退出登录；如需删除账号请联系运营邮箱（见页脚）。',
        'privacy.li5': '请友善使用，禁止骚扰；本平台不提供线下担保。',
        'roadmap.title': '扩展路线图', 'roadmap.hk': '香港大学 / 中大 / 科大', 'roadmap.next': '下一阶段',
        'cta.title': '准备好了？', 'cta.sub': '用学校邮箱开始，整个流程 10 分钟。', 'cta.btn': '立即开始匹配',
        'msg.enterEmail': '请输入邮箱地址', 'msg.enterToken': '请输入验证码', 'msg.registerFirst': '请先输入邮箱注册',
        'msg.sending': '发送中...', 'msg.verifying': '验证中...', 'msg.verifyOk': '验证成功！跳转到问卷...',
        'msg.devCode': '开发模式 — 验证码：',
        // 验证页
        'vf.title': '② 验证邮箱', 'vf.sentTo': '验证码已发送至', 'vf.spam': '检查收件箱和垃圾邮件文件夹。开发模式下验证码打印在服务器终端。',
        'vf.ok': '验证成功！跳转中...', 'vf.resending': '重新发送中...', 'vf.resent': '已重新发送', 'vf.code': '验证码：',
        // 问卷页
        'qn.title': '填写资料 & 问卷', 'qn.sub1': '共',         'qn.sub2': '道必答题 · 另有可选留言；量表/多选未选不算已答',
        'qn.basic': '基本信息', 'qn.name': '昵称 *', 'qn.name.ph': '你的名字', 'qn.gender': '我的性别 *',
        'qn.select': '请选择', 'qn.male': '男', 'qn.female': '女',
        'qn.lf': '希望匹配的性别（择偶取向）*', 'qn.lf.both': '男女都可以',
        'qn.lf.hint': '男生可选男或女，女生也可选男或女；匹配需双方取向互相接受。',
        'qn.wechat': '附加联系方式（必填）',
        'qn.wechat.ph': '例如：wechat:mahuateng1998',
        'qn.wechat.hint': '配对成功后双方会互见学校邮箱，并互见你在此留下的联系方式。微信/其他通讯均可，请认真填写。',
        'qn.bio': '一句话介绍',
        'qn.bio.ph': '例：大三心理学在读，喜欢猫咪和下雨天',
        'qn.openMatch': '参与匹配（关闭后不进池，历史仍可看）',
        'qn.openMatch.hint': '提交后默认开启。想暂停被匹配时关掉即可，不必删号。',
        'qn.cross': '愿意跨配的学校（双向：对方也须勾选你的学校）',
        'qn.cross.hint': '不勾选 = 只同校。勾选后仅会与「也勾选了你学校」的对方跨校配对。',
        'qn.progress': '问卷进度', 'qn.progress.hint': '点击 1–5 作答量表题；兴趣题至少选一项',
        'qn.left': '还需完成', 'qn.left2': '题（量表点选数字，兴趣至少选 1 项）', 'qn.alldone': '全部完成，可以提交啦',
        'qn.submit': '提交问卷 & 开始匹配', 'qn.saving': '保存中...', 'qn.saved': '问卷已保存！正在跳转匹配页...',
        'qn.saveFail': '问卷保存失败: ', 'qn.profileFail': '基本资料保存失败: ',
        'qn.needName': '请填写昵称', 'qn.needGender': '请选择你的性别', 'qn.needLf': '请选择希望匹配的性别（择偶取向）',
        'qn.needWechat': '请填写附加联系方式（微信或其他均可）', 'qn.missing': '还有未完成的题目，请先答完再提交',
        'qn.done': '已答', 'qn.todo': '未答', 'qn.db': '一票否决',
        'qn.db.title': '什么是「一票否决」？',
        'qn.db.hint': '标有「一票否决」的题（婚姻、孩子、出轨、吸烟接受度）是硬性底线：婚姻或孩子出现明确相反意愿，或其它底线答案差 ≥3 时，系统会直接跳过对方。请按真实想法作答。',
        'qn.db.tip': '硬性底线：出现明确冲突时不会配对',
        'qn.imp.on': '★ 很重要', 'qn.imp.off': '☆ 标记为重要',
        'dim.values': '核心价值观', 'dim.lifestyle': '生活习惯', 'dim.emotional': '情感风格',
        'dim.interests': '兴趣爱好', 'dim.expectations': '相处预期', 'dim.open': '写给 TA',
        'qn.open.hint': '配对成功后对方可见；不参与算法打分，纯粹留给聊天的开口。',
        // 匹配页
        'm.center': '匹配中心', 'g.male': '男', 'g.female': '女', 'g.unset': '未设性别',
        'lf.male': '想找男生', 'lf.female': '想找女生', 'lf.both': '想找男女均可', 'lf.unset': '未设取向',
        'hdr.answered': '已答', 'hdr.q': '题', 'hdr.noq': '未填问卷', 'hdr.cross': '跨校', 'hdr.openMatch': '参与匹配', 'on': '开', 'off': '关',
        'pool.title': '参与匹配', 'pool.hint': '关闭后不会再进入匹配池、不能预约/提前揭晓；历史配对仍可查看，资料不会删除。', 'pool.status': '当前：',
        'cross.title': '跨校学校（双向严选）', 'cross.hint': '勾选你愿意跨配的学校；对方也必须勾选你的学校才会配对。不勾 = 只同校。',
        'rv.title': '本周揭晓仪式', 'rv.hint': '每周二晚统一揭晓，制造期待；不是随时刷脸。',
        'rv.next': '下次揭晓：', 'rv.calc': '计算中…', 'rv.optin': '本周预约状态：', 'rv.crosspref': '跨校偏好：',
        'opt.yes': '已预约 ✓', 'opt.no': '未预约', 'cross.on': '已开启', 'cross.off': '仅同校',
        'btn.optin': '预约本周匹配', 'btn.optout': '取消本周预约', 'btn.crossToggle': '切换跨校',
        'btn.crossOn': '开启跨校', 'btn.crossOff': '关闭跨校', 'btn.current': '查看当前配对', 'btn.editQ': '修改问卷',
        'btn.openOn': '开启参与匹配', 'btn.openOff': '关闭参与匹配', 'btn.saveCross': '保存跨校偏好', 'btn.openFirst': '请先开启参与匹配',
        'al.openOn': '已开启参与匹配', 'al.openOff': '已关闭参与匹配（历史结果仍可看）', 'al.crossSaved': '跨校偏好已保存',
        'q.mode': '模式：', 'q.quota': '本周额度：', 'q.cool': '冷却', 'q.hours': '小时',
        'q.minScore': '契合门槛：',
        'btn.instant': '提前揭晓（冷启动）', 'instant.hint': '冷启动阶段保留即时配对；正式运营可关掉，只走每周揭晓。',
        'btn.cooling': '冷却中（约 {m} 分钟）', 'btn.quotaOut': '本周额度已用完',
        'cd.over': '已到揭晓时段（或请查看当前配对）', 'cd.dh': '还有 {d} 天 {h} 小时', 'cd.hm': '还有 {h} 小时 {m} 分钟',
        'bl.title': '不想匹配的人', 'bl.hint': '输入对方昵称搜索后点选确认（也可输完整学校邮箱），避免撞名误伤。',
        'bl.ph': '昵称或邮箱', 'btn.search': '搜索', 'bl.searching': '搜索中…',
        'bl.none': '没有找到。请确认对方已注册且昵称拼写正确；也可用完整邮箱。',
        'btn.block': '拉黑', 'bl.blocked': '已拉黑', 'btn.remove': '移除', 'bl.empty': '黑名单为空。', 'bl.cur': '当前黑名单',
        'bl.confirm': '确认拉黑？之后不会再匹配此人；若已有配对将失效。', 'bl.enter': '请输入昵称或邮箱',
        'ex.title': '匹配是怎么算的？', 'ex.zhOnly': '（算法说明暂仅提供中文）',
        'res.loading': '加载中...', 'res.matching': '正在一对一寻找最合拍的人...',
        'res.none': '暂无匹配', 'res.cand': '候选', 'res.people': '人',
        'res.done1': '配对完成（候选', 'res.done2': '人）。下面是相处说明书与破冰话题。',
        'res.active': '当前有效配对', 'res.noactive': '暂无有效配对。先「预约本周匹配」，或冷启动时用「提前揭晓」。',
        'card.assigned': '系统派单', 'card.manual': '相处说明书', 'card.strengths': '你们的契合点',
        'card.diff': '需要包容的差异', 'card.ice': '破冰话题',
        'card.ice.hint': '基于你们的共同点，找个轻松的方式聊起来。',
        'card.ice.send': '可以发：', 'card.ice.copy': '复制', 'card.ice.copied': '已复制',
        'card.ice.copyManual': '复制下面这句发给对方：',
        'card.letter': 'TA 留给你的话',
        'card.email': '学校邮箱: ', 'card.wechat': '附加联系: ', 'card.nowechat': '未填写',
        'card.opener': '军师嘱咐：先邮件/微信丢一句具体的，比「你好呀匹配到的」存活率高。',
        'btn.noMore': '不再匹配此人',
        'mail.title': '邮件通知状态', 'mail.you': '发给你（', 'mail.partner': '发给对方 ', 'ok': '成功', 'fail': '失败',
        'mail.failN': '邮件发送有失败（{n}）。演示邮箱失败正常。',
        'al.optout': '已取消本周预约', 'al.optin': '已预约本周匹配',
        'al.crossOn': '已开启跨校（对方也要开才会配对）', 'al.crossOff': '已关闭跨校，仅同校匹配', 'al.fail': '操作失败'
    },
    tw: {
        'nav.matches': '配對結果', 'nav.questionnaire': '問卷', 'nav.logout': '返回首頁',
        'footer.line1': 'CampusMatch — 深度問卷 · 演算法配對 · 每週揭曉',
        'footer.line2': '帳號刪除 / 意見回饋：請用學校信箱聯絡營運（暫用註冊所用 SMTP 寄件信箱）',
        'kicker': 'Campus Match · 澳門 & 大灣區',
        'hero.t1': '在你的校園裡，', 'hero.t2': '遇見那個剛好合拍的人',
        'hero.sub': '學校信箱驗證在校身份 → 39 題走心問卷 → 每週一對一揭曉，附相處說明書與破冰話題。慢一點，但更認真。',
        'stat.pre': '已有', 'stat.post': '位同學驗證加入 · 揭曉時間',
        'step1.title': '① 輸入學校信箱', 'form.email': '學校信箱', 'form.email.ph': '例如：yc12345@um.edu.mo',
        'btn.send': '發送驗證碼', 'btn.resendCode': '重新發送', 'schools.support': '支援學校（已驗證人數）：',
        'step2.title': '② 輸入驗證碼', 'step2.sent': '驗證碼已發送到你的學校信箱，請檢查收件匣（和垃圾郵件）',
        'form.token': '6 位驗證碼', 'form.token.ph': '輸入驗證碼', 'btn.verify': '驗證',
        'how.title': '三步，認識那個合拍的人',
        'step01.h': '答一份走心問卷', 'step01.p': '39 道題涵蓋價值觀、生活習慣、情感風格、興趣與相處預期，可標記「對我很重要」加權。',
        'step02.h': '預約本週配對', 'step02.p': '每週統一揭曉一位一對一對象：暱稱、幾個契合點與破冰話題——不展示分數，讓你們自己聊。',
        'step03.h': '照著破冰開聊', 'step03.p': '配對成功互見學校信箱與你留下的聯絡方式；附破冰話題，開口不再尷尬。',
        'why.title': '我們和「刷臉軟體」不一樣',
        'feat1.h': '只限在校生', 'feat1.p': '僅支援列表內學校信箱註冊，你遇到的每個人都經過校園身份驗證。',
        'feat2.h': '一週一位，寧缺毋濫', 'feat2.p': '沒有無限右滑。每人每週最多被配一次；頁面只給契合點，不晒匹配度分數。',
        'feat3.h': '隱私優先', 'feat3.p': '資料不公開陳列；學校信箱與附加聯絡方式只在配對成功後互見，還可封鎖不想遇到的人。',
        'feat4.h': '告訴你「為什麼是 TA」', 'feat4.p': '不給分數焦慮：只列出幾個契合點與破冰話題，剩下的交給聊天。',
        'privacy.title': '使用說明 & 隱私',
        'privacy.li1': '僅接受支援列表內的學校信箱註冊，用於確認在校身份。',
        'privacy.li2': '問卷與擇偶取向用於配對；學校信箱與附加聯絡方式僅在配對成功後互見。',
        'privacy.li3': '每人每週最多配對一次（雙向）；結果只展示契合點與聯絡渠道，不以分數衡量；以網站頁面為準。',
        'privacy.li4': '可隨時登出；如需刪除帳號請聯絡營運信箱（見頁尾）。',
        'privacy.li5': '請友善使用，禁止騷擾；本平台不提供線下擔保。',
        'roadmap.title': '擴展路線圖', 'roadmap.hk': '香港大學 / 中大 / 科大', 'roadmap.next': '下一階段',
        'cta.title': '準備好了？', 'cta.sub': '用學校信箱開始，整個流程 10 分鐘。', 'cta.btn': '立即開始配對',
        'msg.enterEmail': '請輸入信箱地址', 'msg.enterToken': '請輸入驗證碼', 'msg.registerFirst': '請先輸入信箱註冊',
        'msg.sending': '發送中...', 'msg.verifying': '驗證中...', 'msg.verifyOk': '驗證成功！跳轉到問卷...',
        'msg.devCode': '開發模式 — 驗證碼：',
        'vf.title': '② 驗證信箱', 'vf.sentTo': '驗證碼已發送至', 'vf.spam': '檢查收件匣和垃圾郵件資料夾。開發模式下驗證碼列印在伺服器終端。',
        'vf.ok': '驗證成功！跳轉中...', 'vf.resending': '重新發送中...', 'vf.resent': '已重新發送', 'vf.code': '驗證碼：',
        'qn.title': '填寫資料 & 問卷', 'qn.sub1': '共',         'qn.sub2': '道必答題 · 另有可選留言；量表/多選未選不算已答',
        'qn.basic': '基本資訊', 'qn.name': '暱稱 *', 'qn.name.ph': '你的名字', 'qn.gender': '我的性別 *',
        'qn.select': '請選擇', 'qn.male': '男', 'qn.female': '女',
        'qn.lf': '希望配對的性別（擇偶取向）*', 'qn.lf.both': '男女都可以',
        'qn.lf.hint': '男生可選男或女，女生也可選男或女；配對需雙方取向互相接受。',
        'qn.wechat': '附加聯絡方式（必填）',
        'qn.wechat.ph': '例如：wechat:mahuateng1998',
        'qn.wechat.hint': '配對成功後雙方會互見學校信箱，並互見你在此留下的聯絡方式。微信/其他通訊均可，請認真填寫。',
        'qn.bio': '一句話介紹',
        'qn.bio.ph': '例：大三心理學在讀，喜歡貓咪和下雨天',
        'qn.openMatch': '參與配對（關閉後不進池，歷史仍可看）',
        'qn.openMatch.hint': '提交後預設開啟。想暫停被配對時關掉即可，不必刪號。',
        'qn.cross': '願意跨校的學校（雙向：對方也須勾選你的學校）',
        'qn.cross.hint': '不勾選 = 只同校。勾選後僅會與「也勾選了你學校」的對方跨校配對。',
        'qn.progress': '問卷進度', 'qn.progress.hint': '點擊 1–5 作答量表題；興趣題至少選一項',
        'qn.left': '還需完成', 'qn.left2': '題（量表點選數字，興趣至少選 1 項）', 'qn.alldone': '全部完成，可以提交啦',
        'qn.submit': '提交問卷 & 開始配對', 'qn.saving': '儲存中...', 'qn.saved': '問卷已儲存！正在跳轉配對頁...',
        'qn.saveFail': '問卷儲存失敗: ', 'qn.profileFail': '基本資料儲存失敗: ',
        'qn.needName': '請填寫暱稱', 'qn.needGender': '請選擇你的性別', 'qn.needLf': '請選擇希望配對的性別（擇偶取向）',
        'qn.needWechat': '請填寫附加聯絡方式（微信或其他均可）', 'qn.missing': '還有未完成的題目，請先答完再提交',
        'qn.done': '已答', 'qn.todo': '未答', 'qn.db': '一票否決',
        'qn.db.title': '什麼是「一票否決」？',
        'qn.db.hint': '標有「一票否決」的題（婚姻、孩子、出軌、吸菸接受度）是硬性底線：婚姻或孩子出現明確相反意願，或其它底線答案差 ≥3 時，系統會直接跳過對方。請按真實想法作答。',
        'qn.db.tip': '硬性底線：出現明確衝突時不會配對',
        'qn.imp.on': '★ 很重要', 'qn.imp.off': '☆ 標記為重要',
        'dim.values': '核心價值觀', 'dim.lifestyle': '生活習慣', 'dim.emotional': '情感風格',
        'dim.interests': '興趣愛好', 'dim.expectations': '相處預期', 'dim.open': '寫給 TA',
        'qn.open.hint': '配對成功後對方可見；不參與算法打分，純粹留給聊天的開口。',
        'm.center': '配對中心', 'g.male': '男', 'g.female': '女', 'g.unset': '未設性別',
        'lf.male': '想找男生', 'lf.female': '想找女生', 'lf.both': '想找男女均可', 'lf.unset': '未設取向',
        'hdr.answered': '已答', 'hdr.q': '題', 'hdr.noq': '未填問卷', 'hdr.cross': '跨校', 'hdr.openMatch': '參與配對', 'on': '開', 'off': '關',
        'pool.title': '參與配對', 'pool.hint': '關閉後不會再進入配對池、不能預約/提前揭曉；歷史配對仍可查看，資料不會刪除。', 'pool.status': '目前：',
        'cross.title': '跨校學校（雙向嚴選）', 'cross.hint': '勾選你願意跨配的學校；對方也必須勾選你的學校才會配對。不勾 = 只同校。',
        'rv.title': '本週揭曉儀式', 'rv.hint': '每週二晚統一揭曉，製造期待；不是隨時刷臉。',
        'rv.next': '下次揭曉：', 'rv.calc': '計算中…', 'rv.optin': '本週預約狀態：', 'rv.crosspref': '跨校偏好：',
        'opt.yes': '已預約 ✓', 'opt.no': '未預約', 'cross.on': '已開啟', 'cross.off': '僅同校',
        'btn.optin': '預約本週配對', 'btn.optout': '取消本週預約', 'btn.crossToggle': '切換跨校',
        'btn.crossOn': '開啟跨校', 'btn.crossOff': '關閉跨校', 'btn.current': '查看當前配對', 'btn.editQ': '修改問卷',
        'btn.openOn': '開啟參與配對', 'btn.openOff': '關閉參與配對', 'btn.saveCross': '儲存跨校偏好', 'btn.openFirst': '請先開啟參與配對',
        'al.openOn': '已開啟參與配對', 'al.openOff': '已關閉參與配對（歷史結果仍可看）', 'al.crossSaved': '跨校偏好已儲存',
        'q.mode': '模式：', 'q.quota': '本週額度：', 'q.cool': '冷卻', 'q.hours': '小時',
        'q.minScore': '契合門檻：',
        'btn.instant': '提前揭曉（冷啟動）', 'instant.hint': '冷啟動階段保留即時配對；正式營運可關掉，只走每週揭曉。',
        'btn.cooling': '冷卻中（約 {m} 分鐘）', 'btn.quotaOut': '本週額度已用完',
        'cd.over': '已到揭曉時段（或請查看當前配對）', 'cd.dh': '還有 {d} 天 {h} 小時', 'cd.hm': '還有 {h} 小時 {m} 分鐘',
        'bl.title': '不想配對的人', 'bl.hint': '輸入對方暱稱搜尋後點選確認（也可輸完整學校信箱），避免撞名誤傷。',
        'bl.ph': '暱稱或信箱', 'btn.search': '搜尋', 'bl.searching': '搜尋中…',
        'bl.none': '沒有找到。請確認對方已註冊且暱稱拼寫正確；也可用完整信箱。',
        'btn.block': '封鎖', 'bl.blocked': '已封鎖', 'btn.remove': '移除', 'bl.empty': '黑名單為空。', 'bl.cur': '當前黑名單',
        'bl.confirm': '確認封鎖？之後不會再配對此人；若已有配對將失效。', 'bl.enter': '請輸入暱稱或信箱',
        'ex.title': '配對是怎麼算的？', 'ex.zhOnly': '（演算法說明暫僅提供簡體中文）',
        'res.loading': '載入中...', 'res.matching': '正在一對一尋找最合拍的人...',
        'res.none': '暫無配對', 'res.cand': '候選', 'res.people': '人',
        'res.done1': '配對完成（候選', 'res.done2': '人）。下面是相處說明書與破冰話題。',
        'res.active': '當前有效配對', 'res.noactive': '暫無有效配對。先「預約本週配對」，或冷啟動時用「提前揭曉」。',
        'card.assigned': '系統派單', 'card.manual': '相處說明書', 'card.strengths': '你們的契合點',
        'card.diff': '需要包容的差異', 'card.ice': '破冰話題',
        'card.ice.hint': '基於你們的共同點，找個輕鬆的方式聊起來。',
        'card.ice.send': '可以發：', 'card.ice.copy': '複製', 'card.ice.copied': '已複製',
        'card.ice.copyManual': '複製下面這句發給對方：',
        'card.letter': 'TA 留給你的話',
        'card.email': '學校信箱: ', 'card.wechat': '附加聯絡: ', 'card.nowechat': '未填寫',
        'card.opener': '軍師囑咐：先丟一句具體的，比「你好呀配對到的」存活率高。',
        'btn.noMore': '不再配對此人',
        'mail.title': '郵件通知狀態', 'mail.you': '發給你（', 'mail.partner': '發給對方 ', 'ok': '成功', 'fail': '失敗',
        'mail.failN': '郵件發送有失敗（{n}）。演示信箱失敗正常。',
        'al.optout': '已取消本週預約', 'al.optin': '已預約本週配對',
        'al.crossOn': '已開啟跨校（對方也要開才會配對）', 'al.crossOff': '已關閉跨校，僅同校配對', 'al.fail': '操作失敗'
    },
    en: {
        'nav.matches': 'Matches', 'nav.questionnaire': 'Questionnaire', 'nav.logout': 'Back to home',
        'footer.line1': 'CampusMatch — deep questionnaire · algorithmic matching · weekly reveal',
        'footer.line2': 'Account deletion / feedback: contact us from your school email (SMTP sender used for registration)',
        'kicker': 'Campus Match · Macau & Greater Bay Area',
        'hero.t1': 'On your campus,', 'hero.t2': 'meet someone who just clicks',
        'hero.sub': 'Verify with your school email → a thoughtful 39-question survey → one 1-on-1 match revealed weekly, with a compatibility guide and icebreakers. Slower, but more sincere.',
        'stat.pre': 'Joined by', 'stat.post': 'verified students · reveal at',
        'step1.title': '① Enter your school email', 'form.email': 'School email', 'form.email.ph': 'e.g. yc12345@um.edu.mo',
        'btn.send': 'Send code', 'btn.resendCode': 'Resend', 'schools.support': 'Supported schools (verified count):',
        'step2.title': '② Enter the code', 'step2.sent': 'The code was sent to your school email. Check your inbox (and spam).',
        'form.token': '6-digit code', 'form.token.ph': 'Enter code', 'btn.verify': 'Verify',
        'how.title': 'Three steps to meet your match',
        'step01.h': 'Take a thoughtful survey', 'step01.p': '39 questions on values, lifestyle, emotional style, interests and expectations. Mark what matters most to weight it higher.',
        'step02.h': 'Opt in for this week', 'step02.p': 'One 1-on-1 match revealed each week: their name, a few shared points, and icebreakers — no score shown; go chat.',
        'step03.h': 'Break the ice', 'step03.p': 'Once matched you exchange school emails and the contact you left; plus icebreakers.',
        'why.title': 'Not another swipe app',
        'feat1.h': 'Students only', 'feat1.p': 'Registration only with supported school emails — everyone you meet is campus-verified.',
        'feat2.h': 'One match a week', 'feat2.p': 'No endless swiping. Anyone can be matched at most once per week; we show shared points, never a compatibility percentage.',
        'feat3.h': 'Privacy first', 'feat3.p': 'No public profiles. School email and extra contact are shared only after a match; you can block anyone.',
        'feat4.h': 'Know why it\u2019s them', 'feat4.p': 'No score anxiety: just a few shared points and icebreakers — the rest is conversation.',
        'privacy.title': 'How it works & privacy',
        'privacy.li1': 'Only supported school emails can register, to verify student identity.',
        'privacy.li2': 'Survey answers are used for matching; school emails and extra contact are shared only after a match.',
        'privacy.li3': 'At most one match per person per week (both sides); results show shared points and contact channels, not a score; the website is the source of truth.',
        'privacy.li4': 'Log out anytime; contact us by email to delete your account (see footer).',
        'privacy.li5': 'Be kind. Harassment is banned. No offline guarantees are provided.',
        'roadmap.title': 'Roadmap', 'roadmap.hk': 'HKU / CUHK / HKUST', 'roadmap.next': 'next phase',
        'cta.title': 'Ready?', 'cta.sub': 'Start with your school email — about 10 minutes.', 'cta.btn': 'Start matching',
        'msg.enterEmail': 'Please enter your email', 'msg.enterToken': 'Please enter the code', 'msg.registerFirst': 'Register with your email first',
        'msg.sending': 'Sending...', 'msg.verifying': 'Verifying...', 'msg.verifyOk': 'Verified! Redirecting to the survey...',
        'msg.devCode': 'Dev mode — code: ',
        'vf.title': '② Verify email', 'vf.sentTo': 'Code sent to', 'vf.spam': 'Check your inbox and spam folder. In dev mode the code is printed in the server terminal.',
        'vf.ok': 'Verified! Redirecting...', 'vf.resending': 'Resending...', 'vf.resent': 'Sent again', 'vf.code': 'Code: ',
        'qn.title': 'Profile & Questionnaire', 'qn.sub1': '',         'qn.sub2': ' required + optional note · tap to answer; blank scales/multi don\u2019t count',
        'qn.basic': 'Basic info', 'qn.name': 'Nickname *', 'qn.name.ph': 'Your name', 'qn.gender': 'My gender *',
        'qn.select': 'Select', 'qn.male': 'Male', 'qn.female': 'Female',
        'qn.lf': 'Looking for (gender) *', 'qn.lf.both': 'Either',
        'qn.lf.hint': 'Any combination is fine; a match requires both sides to accept each other.',
        'qn.wechat': 'Extra contact (required)',
        'qn.wechat.ph': 'e.g. wechat:mahuateng1998',
        'qn.wechat.hint': 'After a match you both see school emails and this contact. WeChat or other — please fill sincerely.',
        'qn.bio': 'One-line intro',
        'qn.bio.ph': 'e.g. Psychology junior, loves cats and rainy days',
        'qn.openMatch': 'Open to matching (off = leave the pool; history stays)',
        'qn.openMatch.hint': 'On by default after submit. Turn off to pause matching without deleting your account.',
        'qn.cross': 'Schools you accept for cross-match (mutual whitelist)',
        'qn.cross.hint': 'None checked = same school only. Both sides must list each other\'s school.',
        'qn.progress': 'Progress', 'qn.progress.hint': 'Tap 1–5 for scale questions; pick at least one interest',
        'qn.left': 'Still', 'qn.left2': 'to go (tap a number; pick at least 1 interest)', 'qn.alldone': 'All done — ready to submit!',
        'qn.submit': 'Submit & start matching', 'qn.saving': 'Saving...', 'qn.saved': 'Saved! Redirecting to matches...',
        'qn.saveFail': 'Failed to save survey: ', 'qn.profileFail': 'Failed to save profile: ',
        'qn.needName': 'Please enter a nickname', 'qn.needGender': 'Please select your gender', 'qn.needLf': 'Please select who you\u2019re looking for',
        'qn.needWechat': 'Please enter an extra contact (WeChat or other)', 'qn.missing': 'Some questions are unanswered — finish them first',
        'qn.done': 'Done', 'qn.todo': 'To do', 'qn.db': 'Dealbreaker',
        'qn.db.title': 'What is a dealbreaker?',
        'qn.db.hint': 'Dealbreakers (marriage, children, cheating, smoking tolerance) are hard filters: clearly opposing wishes on marriage/children, or a gap of ≥3 on other limits, means no match. Answer honestly.',
        'qn.db.tip': 'Hard filter: a clear conflict means no match',
        'qn.imp.on': '★ Matters a lot', 'qn.imp.off': '☆ Mark as important',
        'dim.values': 'Core values', 'dim.lifestyle': 'Lifestyle', 'dim.emotional': 'Emotional style',
        'dim.interests': 'Interests', 'dim.expectations': 'Expectations', 'dim.open': 'A note for them',
        'qn.open.hint': 'Visible to your match after pairing; not used in scoring — just an opener for chat.',
        'm.center': 'Match Center', 'g.male': 'Male', 'g.female': 'Female', 'g.unset': 'Gender not set',
        'lf.male': 'looking for men', 'lf.female': 'looking for women', 'lf.both': 'open to anyone', 'lf.unset': 'preference not set',
        'hdr.answered': 'Answered', 'hdr.q': 'questions', 'hdr.noq': 'Survey not done', 'hdr.cross': 'Cross-school', 'hdr.openMatch': 'Open to match', 'on': 'on', 'off': 'off',
        'pool.title': 'Open to matching', 'pool.hint': 'Off = leave the pool; no opt-in / early reveal. History stays; profile is kept.', 'pool.status': 'Status:',
        'cross.title': 'Cross-school list (mutual)', 'cross.hint': 'Pick schools you accept; they must pick yours too. None = same school only.',
        'rv.title': 'Weekly reveal', 'rv.hint': 'Matches are revealed together every Tuesday night — anticipation, not endless swiping.',
        'rv.next': 'Next reveal: ', 'rv.calc': 'calculating…', 'rv.optin': 'This week: ', 'rv.crosspref': 'Cross-school: ',
        'opt.yes': 'Opted in ✓', 'opt.no': 'Not opted in', 'cross.on': 'Enabled', 'cross.off': 'Same school only',
        'btn.optin': 'Opt in this week', 'btn.optout': 'Cancel opt-in', 'btn.crossToggle': 'Toggle cross-school',
        'btn.crossOn': 'Enable cross-school', 'btn.crossOff': 'Disable cross-school', 'btn.current': 'View current match', 'btn.editQ': 'Edit survey',
        'btn.openOn': 'Turn matching on', 'btn.openOff': 'Turn matching off', 'btn.saveCross': 'Save cross-school prefs', 'btn.openFirst': 'Turn matching on first',
        'al.openOn': 'Matching is on', 'al.openOff': 'Matching is off (history still visible)', 'al.crossSaved': 'Cross-school prefs saved',
        'q.mode': 'Mode: ', 'q.quota': 'Weekly quota: ', 'q.cool': 'Cooldown', 'q.hours': 'h',
        'q.minScore': 'Min score: ',
        'btn.instant': 'Reveal early (cold start)', 'instant.hint': 'Instant matching stays on during cold start; can be disabled later for weekly-only reveals.',
        'btn.cooling': 'Cooling down (~{m} min)', 'btn.quotaOut': 'Weekly quota used up',
        'cd.over': 'Reveal time reached — check your current match', 'cd.dh': '{d}d {h}h to go', 'cd.hm': '{h}h {m}min to go',
        'bl.title': 'People to avoid', 'bl.hint': 'Search by nickname and confirm by clicking (full school email also works) — avoids name collisions.',
        'bl.ph': 'Nickname or email', 'btn.search': 'Search', 'bl.searching': 'Searching…',
        'bl.none': 'No results. Make sure they registered and the spelling is right, or use their full email.',
        'btn.block': 'Block', 'bl.blocked': 'Blocked', 'btn.remove': 'Remove', 'bl.empty': 'Blocklist is empty.', 'bl.cur': 'Current blocklist',
        'bl.confirm': 'Block this person? You will never be matched; any current match is deactivated.', 'bl.enter': 'Enter a nickname or email',
        'ex.title': 'How does matching work?', 'ex.zhOnly': '(algorithm notes currently in Chinese only)',
        'res.loading': 'Loading...', 'res.matching': 'Finding your best 1-on-1 match...',
        'res.none': 'No match yet', 'res.cand': 'candidates:', 'res.people': '',
        'res.done1': 'Matched! (from', 'res.done2': 'candidates). Here is your compatibility guide and icebreakers.',
        'res.active': 'Current match', 'res.noactive': 'No active match. Opt in for this week, or use "Reveal early" during cold start.',
        'card.assigned': 'Your match', 'card.manual': 'Compatibility guide', 'card.strengths': 'What you share',
        'card.diff': 'Differences to embrace', 'card.ice': 'Conversation starters',
        'card.ice.hint': 'Based on your common ground — a few easy ways to get talking.',
        'card.ice.send': 'Try sending: ', 'card.ice.copy': 'Copy', 'card.ice.copied': 'Copied',
        'card.ice.copyManual': 'Copy this and send it:',
        'card.letter': 'A note they left for you',
        'card.email': 'School email: ', 'card.wechat': 'Extra contact: ', 'card.nowechat': 'not set',
        'card.opener': 'Pro tip: send one concrete line first — beats “hi, we matched”.',
        'btn.noMore': 'Don\u2019t match again',
        'mail.title': 'Email notifications', 'mail.you': 'To you (', 'mail.partner': 'To ', 'ok': 'sent', 'fail': 'failed',
        'mail.failN': 'Some emails failed ({n}). Demo inboxes failing is normal.',
        'al.optout': 'Opt-in cancelled', 'al.optin': 'Opted in for this week',
        'al.crossOn': 'Cross-school enabled (both sides must enable)', 'al.crossOff': 'Cross-school disabled — same school only', 'al.fail': 'Action failed'
    },
    pt: {
        'nav.matches': 'Matches', 'nav.questionnaire': 'Questionário', 'nav.logout': 'Voltar ao início',
        'footer.line1': 'CampusMatch — questionário profundo · matching algorítmico · revelação semanal',
        'footer.line2': 'Eliminar conta / feedback: contacte-nos pelo email escolar (remetente SMTP do registo)',
        'kicker': 'Campus Match · Macau e Grande Baía',
        'hero.t1': 'No teu campus,', 'hero.t2': 'encontra alguém que combina contigo',
        'hero.sub': 'Verificação com email escolar → 39 perguntas com alma → um match 1-a-1 revelado por semana, com guia de convivência e quebra-gelos. Mais devagar, mas mais a sério.',
        'stat.pre': 'Já somos', 'stat.post': 'estudantes verificados · revelação',
        'step1.title': '① Introduz o teu email escolar', 'form.email': 'Email escolar', 'form.email.ph': 'ex.: yc12345@um.edu.mo',
        'btn.send': 'Enviar código', 'btn.resendCode': 'Reenviar', 'schools.support': 'Escolas suportadas (nº verificados):',
        'step2.title': '② Introduz o código', 'step2.sent': 'O código foi enviado para o teu email escolar. Verifica a caixa de entrada (e o spam).',
        'form.token': 'Código de 6 dígitos', 'form.token.ph': 'Introduz o código', 'btn.verify': 'Verificar',
        'how.title': 'Três passos para conhecer o teu match',
        'step01.h': 'Responde a um questionário com alma', 'step01.p': '39 perguntas sobre valores, estilo de vida, estilo emocional, interesses e expectativas. Marca o que mais importa para dar mais peso.',
        'step02.h': 'Inscreve-te esta semana', 'step02.p': 'Um match 1-a-1 revelado por semana: nome, alguns pontos em comum e quebra-gelos — sem pontuação; vão conversar.',
        'step03.h': 'Quebra o gelo', 'step03.p': 'Com match feito trocam emails escolares e o contacto que deixaste; mais quebra-gelos.',
        'why.title': 'Não somos mais uma app de swipes',
        'feat1.h': 'Só estudantes', 'feat1.p': 'Registo apenas com emails escolares suportados — todos verificados no campus.',
        'feat2.h': 'Um match por semana', 'feat2.p': 'Sem swipes infinitos. Cada pessoa só pode ser emparelhada uma vez por semana; mostramos pontos em comum, nunca uma percentagem.',
        'feat3.h': 'Privacidade primeiro', 'feat3.p': 'Sem perfis públicos. Email escolar e contacto extra só após match; podes bloquear quem quiseres.',
        'feat4.h': 'Sabe porquê essa pessoa', 'feat4.p': 'Sem ansiedade de score: só alguns pontos em comum e quebra-gelos — o resto é conversa.',
        'privacy.title': 'Como funciona & privacidade',
        'privacy.li1': 'Só emails escolares suportados podem registar-se, para verificar a identidade.',
        'privacy.li2': 'Respostas servem para matching; emails escolares e contacto extra só após match.',
        'privacy.li3': 'No máximo um match por pessoa por semana (ambos os lados); o resultado mostra pontos em comum e canais de contacto, não uma pontuação; o site é a fonte oficial.',
        'privacy.li4': 'Sai quando quiseres; para eliminar a conta contacta-nos por email (ver rodapé).',
        'privacy.li5': 'Sê gentil. Assédio é proibido. Não damos garantias offline.',
        'roadmap.title': 'Roteiro', 'roadmap.hk': 'HKU / CUHK / HKUST', 'roadmap.next': 'próxima fase',
        'cta.title': 'Pronto?', 'cta.sub': 'Começa com o teu email escolar — cerca de 10 minutos.', 'cta.btn': 'Começar o matching',
        'msg.enterEmail': 'Introduz o teu email', 'msg.enterToken': 'Introduz o código', 'msg.registerFirst': 'Regista-te primeiro com o email',
        'msg.sending': 'A enviar...', 'msg.verifying': 'A verificar...', 'msg.verifyOk': 'Verificado! A redirecionar para o questionário...',
        'msg.devCode': 'Modo dev — código: ',
        'vf.title': '② Verificar email', 'vf.sentTo': 'Código enviado para', 'vf.spam': 'Verifica a caixa de entrada e o spam. Em modo dev o código aparece no terminal do servidor.',
        'vf.ok': 'Verificado! A redirecionar...', 'vf.resending': 'A reenviar...', 'vf.resent': 'Enviado de novo', 'vf.code': 'Código: ',
        'qn.title': 'Perfil & Questionário', 'qn.sub1': '',         'qn.sub2': ' obrigatórias + nota opcional · toca para responder; sem seleção não conta',
        'qn.basic': 'Dados básicos', 'qn.name': 'Alcunha *', 'qn.name.ph': 'O teu nome', 'qn.gender': 'O meu género *',
        'qn.select': 'Seleciona', 'qn.male': 'Masculino', 'qn.female': 'Feminino',
        'qn.lf': 'À procura de (género) *', 'qn.lf.both': 'Ambos',
        'qn.lf.hint': 'Qualquer combinação é válida; o match exige aceitação mútua.',
        'qn.wechat': 'Contacto extra (obrigatório)',
        'qn.wechat.ph': 'ex.: wechat:mahuateng1998',
        'qn.wechat.hint': 'Após o match veem o email escolar e este contacto. WeChat ou outro — preenche com sinceridade.',
        'qn.bio': 'Intro numa frase',
        'qn.bio.ph': 'ex.: 3º ano de Psicologia, adora gatos e dias de chuva',
        'qn.openMatch': 'Aberto a matching (desligado = sai do pool; histórico fica)',
        'qn.openMatch.hint': 'Ligado por defeito após submeter. Desliga para pausar sem apagar a conta.',
        'qn.cross': 'Escolas que aceitas para cross-match (lista mútua)',
        'qn.cross.hint': 'Nenhuma marcada = só a mesma escola. Ambos têm de listar a escola um do outro.',
        'qn.progress': 'Progresso', 'qn.progress.hint': 'Toca 1–5 nas escalas; escolhe pelo menos um interesse',
        'qn.left': 'Faltam', 'qn.left2': 'perguntas (toca num número; escolhe ≥1 interesse)', 'qn.alldone': 'Tudo pronto — podes submeter!',
        'qn.submit': 'Submeter & começar matching', 'qn.saving': 'A guardar...', 'qn.saved': 'Guardado! A redirecionar...',
        'qn.saveFail': 'Falha ao guardar o questionário: ', 'qn.profileFail': 'Falha ao guardar o perfil: ',
        'qn.needName': 'Introduz uma alcunha', 'qn.needGender': 'Seleciona o teu género', 'qn.needLf': 'Seleciona quem procuras',
        'qn.needWechat': 'Introduz um contacto extra (WeChat ou outro)', 'qn.missing': 'Há perguntas por responder — termina primeiro',
        'qn.done': 'Feito', 'qn.todo': 'Por fazer', 'qn.db': 'Eliminatório',
        'qn.db.title': 'O que é «Eliminatório»?',
        'qn.db.hint': 'Os eliminatórios (casamento, filhos, infidelidade e tolerância ao tabaco) são filtros rígidos: desejos claramente opostos sobre casamento/filhos, ou diferença ≥3 nos outros limites, impedem o match.',
        'qn.db.tip': 'Filtro rígido: conflito claro = sem match',
        'qn.imp.on': '★ Muito importante', 'qn.imp.off': '☆ Marcar como importante',
        'dim.values': 'Valores', 'dim.lifestyle': 'Estilo de vida', 'dim.emotional': 'Estilo emocional',
        'dim.interests': 'Interesses', 'dim.expectations': 'Expectativas', 'dim.open': 'Nota para o match',
        'qn.open.hint': 'Visível após o match; não entra na pontuação — só uma abertura para a conversa.',
        'm.center': 'Centro de Matches', 'g.male': 'Masculino', 'g.female': 'Feminino', 'g.unset': 'Género não definido',
        'lf.male': 'procura homens', 'lf.female': 'procura mulheres', 'lf.both': 'aberto a todos', 'lf.unset': 'preferência não definida',
        'hdr.answered': 'Respondeu', 'hdr.q': 'perguntas', 'hdr.noq': 'Questionário por fazer', 'hdr.cross': 'Entre escolas', 'hdr.openMatch': 'Aberto a match', 'on': 'sim', 'off': 'não',
        'pool.title': 'Aberto a matching', 'pool.hint': 'Desligado = sais do pool; sem inscrição / revelação antecipada. Histórico fica; perfil mantém-se.', 'pool.status': 'Estado:',
        'cross.title': 'Lista entre escolas (mútua)', 'cross.hint': 'Escolhe escolas que aceitas; elas também têm de te escolher. Nenhuma = só a mesma escola.',
        'rv.title': 'Revelação semanal', 'rv.hint': 'Os matches são revelados juntos à terça à noite — expectativa, não swipes.',
        'rv.next': 'Próxima revelação: ', 'rv.calc': 'a calcular…', 'rv.optin': 'Esta semana: ', 'rv.crosspref': 'Entre escolas: ',
        'opt.yes': 'Inscrito ✓', 'opt.no': 'Não inscrito', 'cross.on': 'Ativado', 'cross.off': 'Só a mesma escola',
        'btn.optin': 'Inscrever esta semana', 'btn.optout': 'Cancelar inscrição', 'btn.crossToggle': 'Alternar entre escolas',
        'btn.crossOn': 'Ativar entre escolas', 'btn.crossOff': 'Desativar entre escolas', 'btn.current': 'Ver match atual', 'btn.editQ': 'Editar questionário',
        'btn.openOn': 'Ligar matching', 'btn.openOff': 'Desligar matching', 'btn.saveCross': 'Guardar preferências', 'btn.openFirst': 'Liga o matching primeiro',
        'al.openOn': 'Matching ligado', 'al.openOff': 'Matching desligado (histórico ainda visível)', 'al.crossSaved': 'Preferências entre escolas guardadas',
        'q.mode': 'Modo: ', 'q.quota': 'Quota semanal: ', 'q.cool': 'Espera', 'q.hours': 'h',
        'q.minScore': 'Limiar: ',
        'btn.instant': 'Revelar já (arranque)', 'instant.hint': 'O matching imediato fica ativo no arranque; depois pode passar a só semanal.',
        'btn.cooling': 'Em espera (~{m} min)', 'btn.quotaOut': 'Quota semanal esgotada',
        'cd.over': 'Hora da revelação — vê o teu match atual', 'cd.dh': 'faltam {d}d {h}h', 'cd.hm': 'faltam {h}h {m}min',
        'bl.title': 'Pessoas a evitar', 'bl.hint': 'Pesquisa pela alcunha e confirma com um clique (o email completo também funciona) — evita enganos de nomes.',
        'bl.ph': 'Alcunha ou email', 'btn.search': 'Pesquisar', 'bl.searching': 'A pesquisar…',
        'bl.none': 'Sem resultados. Confirma o registo e a grafia, ou usa o email completo.',
        'btn.block': 'Bloquear', 'bl.blocked': 'Bloqueado', 'btn.remove': 'Remover', 'bl.empty': 'Lista vazia.', 'bl.cur': 'Bloqueados',
        'bl.confirm': 'Bloquear esta pessoa? Nunca mais haverá match; um match atual é desativado.', 'bl.enter': 'Introduz alcunha ou email',
        'ex.title': 'Como funciona o matching?', 'ex.zhOnly': '(notas do algoritmo por agora só em chinês)',
        'res.loading': 'A carregar...', 'res.matching': 'À procura do teu melhor match 1-a-1...',
        'res.none': 'Ainda sem match', 'res.cand': 'candidatos:', 'res.people': '',
        'res.done1': 'Match feito! (de', 'res.done2': 'candidatos). Aqui tens o guia de convivência e os quebra-gelos.',
        'res.active': 'Match atual', 'res.noactive': 'Sem match ativo. Inscreve-te esta semana, ou usa "Revelar já" no arranque.',
        'card.assigned': 'O teu match', 'card.manual': 'Guia de convivência', 'card.strengths': 'Pontos em comum',
        'card.diff': 'Diferenças a aceitar', 'card.ice': 'Tópicos para conversar',
        'card.ice.hint': 'Com base nos pontos em comum — formas fáceis de começar a conversa.',
        'card.ice.send': 'Podes enviar: ', 'card.ice.copy': 'Copiar', 'card.ice.copied': 'Copiado',
        'card.ice.copyManual': 'Copia e envia isto:',
        'card.letter': 'Nota que te deixaram',
        'card.email': 'Email escolar: ', 'card.wechat': 'Contacto extra: ', 'card.nowechat': 'não definido',
        'card.opener': 'Dica: manda uma frase concreta — melhor do que “olá, deu match”.',
        'btn.noMore': 'Não voltar a fazer match',
        'mail.title': 'Notificações por email', 'mail.you': 'Para ti (', 'mail.partner': 'Para ', 'ok': 'enviado', 'fail': 'falhou',
        'mail.failN': 'Alguns emails falharam ({n}). É normal em caixas de demonstração.',
        'al.optout': 'Inscrição cancelada', 'al.optin': 'Inscrito para esta semana',
        'al.crossOn': 'Entre escolas ativado (ambos têm de ativar)', 'al.crossOff': 'Entre escolas desativado — só a mesma escola', 'al.fail': 'A ação falhou'
    }
    };

    var stored = null;
    try { stored = localStorage.getItem('cm_lang'); } catch (e) {}
    window.CM_LANG = (stored && I18N[stored]) ? stored : 'zh';

    window.t = function (key) {
        var d = I18N[window.CM_LANG] || I18N.zh;
        if (d[key] !== undefined) return d[key];
        if (I18N.zh[key] !== undefined) return I18N.zh[key];
        return key;
    };

    window.tf = function (key, vars) {
        var s = window.t(key);
        for (var k in vars) s = s.replace(new RegExp('\\{' + k + '\\}', 'g'), vars[k]);
        return s;
    };

    window.tSchool = function (name) {
        if (window.CM_LANG === 'zh') return name;
        var m = SCHOOLS[name];
        return (m && m[window.CM_LANG]) || name;
    };

    // "每周二 21:00" → 当前语言
    window.tBatch = function (label) {
        if (!label) return label;
        if (window.CM_LANG === 'zh') return label;
        var out = label;
        for (var day in WEEKDAYS) {
            if (out.indexOf(day) >= 0) {
                var rep = WEEKDAYS[day][window.CM_LANG] || day;
                if (window.CM_LANG === 'tw') out = out.replace('每' + day, '每' + rep);
                else out = out.replace('每' + day, rep).replace(day, rep);
                break;
            }
        }
        return out;
    };

    // 问卷题目字段（text/left/right），multi 选项标签
    window.qi = function (q, field) {
        if (window.CM_LANG !== 'zh' && q.i18n && q.i18n[window.CM_LANG] && q.i18n[window.CM_LANG][field]) {
            return q.i18n[window.CM_LANG][field];
        }
        return q[field];
    };
    window.qOptLabels = function (q) {
        if (window.CM_LANG !== 'zh' && q.i18n && q.i18n[window.CM_LANG] && q.i18n[window.CM_LANG].options) {
            return q.i18n[window.CM_LANG].options;
        }
        return q.options;
    };

    window.applyI18n = function () {
        document.documentElement.lang = { zh: 'zh-CN', tw: 'zh-TW', en: 'en', pt: 'pt' }[window.CM_LANG] || 'zh-CN';
        var els = document.querySelectorAll('[data-i18n]');
        for (var i = 0; i < els.length; i++) els[i].textContent = window.t(els[i].getAttribute('data-i18n'));
        var phs = document.querySelectorAll('[data-i18n-ph]');
        for (var j = 0; j < phs.length; j++) phs[j].setAttribute('placeholder', window.t(phs[j].getAttribute('data-i18n-ph')));
        var sch = document.querySelectorAll('[data-school]');
        for (var k = 0; k < sch.length; k++) sch[k].textContent = window.tSchool(sch[k].getAttribute('data-school'));
        var bt = document.querySelectorAll('[data-batch]');
        for (var b = 0; b < bt.length; b++) bt[b].textContent = window.tBatch(bt[b].getAttribute('data-batch'));
        var sel = document.getElementById('lang-sel');
        if (sel && sel.value !== window.CM_LANG) sel.value = window.CM_LANG;
    };

    window.setLang = function (lang) {
        if (!I18N[lang]) return;
        window.CM_LANG = lang;
        try { localStorage.setItem('cm_lang', lang); } catch (e) {}
        window.applyI18n();
        window.dispatchEvent(new CustomEvent('cm:lang', { detail: { lang: lang } }));
    };

    document.addEventListener('DOMContentLoaded', window.applyI18n);
})();
