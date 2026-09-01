"""API 文案四语：读请求头 X-CM-Lang（与前端 cm_lang 一致）。"""

from flask import jsonify, request

LANGS = ("zh", "tw", "en", "pt")

M = {
    "err.login": {
        "zh": "请先登录", "tw": "請先登入",
        "en": "Please sign in first", "pt": "Inicia sessão primeiro",
    },
    "err.email_invalid": {
        "zh": "请输入有效的邮箱地址", "tw": "請輸入有效的電郵地址",
        "en": "Please enter a valid email address", "pt": "Indica um email válido",
    },
    "err.privacy": {
        "zh": "请先阅读并同意《隐私政策》", "tw": "請先閱讀並同意《隱私政策》",
        "en": "Please read and accept the Privacy Policy", "pt": "Lê e aceita a Política de Privacidade",
    },
    "err.school": {
        "zh": "暂不支持该学校邮箱。目前支持: {schools}",
        "tw": "暫不支援該學校電郵。目前支援：{schools}",
        "en": "This school email is not supported yet. Currently: {schools}",
        "pt": "Este email escolar ainda não é suportado. Atualmente: {schools}",
    },
    "err.sibling": {
        "zh": "该学号/账号已在本平台使用邮箱 {email} 注册过。请用该邮箱登录，勿用同校其他域名重复注册。",
        "tw": "該學號／帳號已用電郵 {email} 註冊。請用該電郵登入，勿用同校其他網域重複註冊。",
        "en": "This student ID already registered as {email}. Sign in with that address; do not re-register on another campus domain.",
        "pt": "Este número de aluno já está registado como {email}. Entra com esse email; não te voltes a registar noutro domínio da mesma escola.",
    },
    "err.rate": {
        "zh": "发送过于频繁，请 {mins} 分钟后再试。若邮箱里已有验证码，可直接输入。",
        "tw": "發送過於頻繁，請 {mins} 分鐘後再試。若電郵裡已有驗證碼，可直接輸入。",
        "en": "Too many send attempts. Wait {mins} minutes. If a code is already in your inbox, enter it below.",
        "pt": "Demasiados envios. Espera {mins} minutos. Se já tens um código no email, introduz-o abaixo.",
    },
    "err.rate_enter": {
        "zh": "发送次数已达上限，请 {mins} 分钟后再点发送。邮箱里若已有验证码，可在下方直接输入。",
        "tw": "發送次數已達上限，請 {mins} 分鐘後再點發送。電郵裡若已有驗證碼，可在下方直接輸入。",
        "en": "Send limit reached. Wait {mins} minutes before requesting another code. You can still enter a code already in your inbox.",
        "pt": "Limite de envios atingido. Espera {mins} minutos. Podes ainda introduzir um código que já esteja no email.",
    },
    "err.rate_verify": {
        "zh": "验证码试错次数过多，请 {mins} 分钟后再试",
        "tw": "驗證碼試錯次數過多，請 {mins} 分鐘後再試",
        "en": "Too many incorrect codes. Please wait {mins} minutes.",
        "pt": "Demasiados códigos incorretos. Espera {mins} minutos.",
    },
    "err.email_empty": {
        "zh": "邮箱不能为空", "tw": "電郵不能為空",
        "en": "Email is required", "pt": "O email é obrigatório",
    },
    "err.user_missing": {
        "zh": "用户不存在", "tw": "用戶不存在",
        "en": "User not found", "pt": "Utilizador não encontrado",
    },
    "err.email_token_empty": {
        "zh": "邮箱和验证码不能为空", "tw": "電郵和驗證碼不能為空",
        "en": "Email and verification code are required", "pt": "Email e código são obrigatórios",
    },
    "err.token_bad": {
        "zh": "验证码错误", "tw": "驗證碼錯誤",
        "en": "Incorrect verification code", "pt": "Código incorreto",
    },
    "err.token_expired": {
        "zh": "验证码已过期", "tw": "驗證碼已過期",
        "en": "Verification code expired", "pt": "O código expirou",
    },
    "err.login_once": {
        "zh": "今日已登录过（紧急限流：新设备每人每天仅可登录一次，以澳门时区计日）。同一设备验证后 7 天内输入邮箱即可再进。若你仍保持登录可继续使用。",
        "tw": "今日已登入過（緊急限流：新裝置每人每天僅可登入一次）。同一裝置驗證後 7 天內輸入電郵即可再進。",
        "en": "You already signed in today from a new device (one login per Macau day). This device can skip the code for 7 days after verifying once. Stay signed in to keep using the site.",
        "pt": "Já iniciaste sessão hoje num dispositivo novo (um login por dia, Macau). Este dispositivo pode saltar o código durante 7 dias depois de verificar uma vez.",
    },
    "err.email_once": {
        "zh": "今日验证码已发送过，请查收学校邮箱（含垃圾箱），勿重复申请。紧急限流期间每人每天仅发一封登录验证码。",
        "tw": "今日驗證碼已發送，請查收學校電郵（含垃圾箱），勿重複申請。",
        "en": "A code was already sent today. Check your school inbox (and spam). During this limit, one login code per day.",
        "pt": "Já enviámos um código hoje. Vê a caixa escolar (e o spam). Durante este limite, um código por dia.",
    },
    "err.answers_format": {
        "zh": "问卷答案格式错误", "tw": "問卷答案格式錯誤",
        "en": "Invalid questionnaire payload", "pt": "Formato do questionário inválido",
    },
    "err.answers_missing": {
        "zh": "请完成全部 {n} 道必答题（未完成：{ids}）",
        "tw": "請完成全部 {n} 道必答題（未完成：{ids}）",
        "en": "Please finish all {n} required questions (missing: {ids})",
        "pt": "Completa as {n} perguntas obrigatórias (faltam: {ids})",
    },
    "err.need_questionnaire": {
        "zh": "请先完成问卷", "tw": "請先完成問卷",
        "en": "Please finish the questionnaire first", "pt": "Completa primeiro o questionário",
    },
    "err.need_verify": {
        "zh": "请先验证邮箱", "tw": "請先驗證電郵",
        "en": "Please verify your email first", "pt": "Verifica primeiro o email",
    },
    "err.need_survey_submit": {
        "zh": "请先完成问卷并提交", "tw": "請先完成問卷並提交",
        "en": "Please complete and submit the questionnaire", "pt": "Completa e submete o questionário",
    },
    "err.need_gender": {
        "zh": "请先在问卷页设置性别与择偶取向", "tw": "請先在問卷頁設定性別與擇偶取向",
        "en": "Please set your gender and who you want to match on the profile page",
        "pt": "Define o género e quem queres conhecer na página de perfil",
    },
    "err.need_wechat": {
        "zh": "请先填写附加联系方式", "tw": "請先填寫附加聯絡方式",
        "en": "Please add an extra contact method", "pt": "Indica um contacto extra",
    },
    "err.profile_incomplete": {
        "zh": "资料不完整，请返回问卷页补全", "tw": "資料不完整，請返回問卷頁補全",
        "en": "Profile incomplete — go back to the questionnaire page",
        "pt": "Perfil incompleto — volta à página do questionário",
    },
    "err.match_closed": {
        "zh": "你已关闭「参与匹配」。可在匹配中心重新打开后再试。",
        "tw": "你已關閉「參與配對」。可在配對中心重新打開後再試。",
        "en": "Matching is turned off. Turn it back on in the match center.",
        "pt": "A participação está desligada. Liga-a novamente no centro de matching.",
    },
    "err.weekly_only": {
        "zh": "当前为「每周揭晓」模式，请先预约本周匹配，等待统一揭晓。",
        "tw": "目前為「每週揭曉」模式，請先預約本週配對，等待統一揭曉。",
        "en": "Weekly reveal is on. Opt in for this week and wait for the reveal.",
        "pt": "Está no modo de revelação semanal. Inscreve-te nesta semana e espera.",
    },
    "err.cooldown": {
        "zh": "匹配冷却中，请约 {mins} 分钟后再试（冷却 {hours} 小时）",
        "tw": "配對冷卻中，請約 {mins} 分鐘後再試（冷卻 {hours} 小時）",
        "en": "Matching cooldown: try again in about {mins} minutes ({hours}h cooldown).",
        "pt": "Arrefecimento de matching: tenta daqui a cerca de {mins} minutos ({hours} h).",
    },
    "err.weekly_cap": {
        "zh": "本周新建匹配已达上限（{n} 个）。可查看历史结果，或等下周 / {when} 批量匹配。",
        "tw": "本週新建配對已達上限（{n} 個）。可查看歷史結果，或等下週 / {when} 批量配對。",
        "en": "Weekly new-match limit reached ({n}). See history, or wait until next week / {when}.",
        "pt": "Limite semanal de novos matches atingido ({n}). Vê o histórico, ou espera até à próxima semana / {when}.",
    },
    "err.need_ready_optin": {
        "zh": "请先完成隐私资料或完整问卷、性别、择偶取向（隐私模式微信可不填）",
        "tw": "請先完成隱私資料或完整問卷、性別、擇偶取向（隱私模式微信可不填）",
        "en": "Finish Privacy mode or the full survey, gender, and preference (WeChat optional in Privacy mode)",
        "pt": "Completa o modo privacidade ou o questionário, género e preferência (WeChat opcional no modo privacidade)",
    },
    "err.need_open_optin": {
        "zh": "请先开启「参与匹配」，再预约本周揭晓",
        "tw": "請先開啟「參與配對」，再預約本週揭曉",
        "en": "Turn on matching before you opt in for this week",
        "pt": "Liga a participação antes de te inscreveres nesta semana",
    },
    "err.wechat_required": {
        "zh": "请填写附加联系方式（微信或其他均可）",
        "tw": "請填寫附加聯絡方式（微信或其他均可）",
        "en": "Please add an extra contact (WeChat or anything that works)",
        "pt": "Indica um contacto extra (WeChat ou outro)",
    },
    "err.cross_list": {
        "zh": "cross_schools 须为学校名列表", "tw": "cross_schools 須為學校名列表",
        "en": "cross_schools must be a list of school names",
        "pt": "cross_schools tem de ser uma lista de escolas",
    },
    "err.search_q": {
        "zh": "请输入昵称或邮箱", "tw": "請輸入暱稱或電郵",
        "en": "Enter a nickname or email", "pt": "Indica uma alcunha ou email",
    },
    "err.block_pick": {
        "zh": "请指定要拉黑的用户（从搜索结果点选）",
        "tw": "請指定要封鎖的用戶（從搜尋結果點選）",
        "en": "Pick someone to block from the search results",
        "pt": "Escolhe alguém para bloquear nos resultados",
    },
    "err.block_self": {
        "zh": "不能拉黑自己", "tw": "不能封鎖自己",
        "en": "You cannot block yourself", "pt": "Não podes bloquear-te a ti",
    },
    "err.admin_secret_missing": {
        "zh": "未配置 ADMIN_SECRET，拒绝执行", "tw": "未設定 ADMIN_SECRET，拒絕執行",
        "en": "ADMIN_SECRET is not configured", "pt": "ADMIN_SECRET não está configurado",
    },
    "err.admin_secret_bad": {
        "zh": "密钥错误", "tw": "密鑰錯誤",
        "en": "Invalid secret", "pt": "Segredo inválido",
    },
    "err.express_name": {
        "zh": "请填写昵称", "tw": "請填寫暱稱",
        "en": "Please enter a nickname", "pt": "Indica uma alcunha",
    },
    "err.express_bio": {
        "zh": "请写一段自我介绍（至少 {n} 字），匹配会参考这段话",
        "tw": "請寫一段自我介紹（至少 {n} 字），配對會參考這段話",
        "en": "Write a short intro (at least {n} characters). Matching uses this text.",
        "pt": "Escreve uma apresentação (pelo menos {n} caracteres). O matching usa este texto.",
    },
    "ok.beta_login": {
        "zh": "内测账号已直接登录（{email}）。验证码可随便填，或不填直接点验证亦可。",
        "tw": "內測帳號已直接登入（{email}）。驗證碼可隨便填。",
        "en": "Beta account signed in ({email}). Any code works, or skip the code field.",
        "pt": "Conta beta com sessão iniciada ({email}). Qualquer código serve.",
    },
    "ok.device_login": {
        "zh": "本设备 7 天内免验证码，已直接登录",
        "tw": "本裝置 7 天內免驗證碼，已直接登入",
        "en": "This device is trusted for 7 days — signed in without a code",
        "pt": "Este dispositivo está confiável por 7 dias — sessão iniciada sem código",
    },
    "ok.direct_login": {
        "zh": "已登录。紧急限流期间每人每天仅可登录一次，请勿随意退出。",
        "tw": "已登入。緊急限流期間每人每天僅可登入一次，請勿隨意退出。",
        "en": "Signed in. During the daily-login limit, please do not sign out casually.",
        "pt": "Sessão iniciada. Durante o limite diário, não saias sem necessidade.",
    },
    "ok.code_already": {
        "zh": "今日验证码已发送，请查收学校邮箱（含垃圾箱）并在下方输入；请勿重复申请。",
        "tw": "今日驗證碼已發送，請查收學校電郵（含垃圾箱）並在下方輸入。",
        "en": "A code was already sent today. Check your school inbox (and spam) and enter it below.",
        "pt": "Já enviámos um código hoje. Vê a caixa escolar (e o spam) e introduz-o abaixo.",
    },
    "ok.code_wait": {
        "zh": "验证码已发送，请查收学校邮箱（含垃圾箱）。{secs} 秒内不必重复点发送，可直接在下方输入。",
        "tw": "驗證碼已發送，請查收學校電郵（含垃圾箱）。{secs} 秒內不必重複點發送，可直接在下方輸入。",
        "en": "A code was already sent. Check your school inbox (and spam). Wait {secs}s before requesting another; you can enter it below now.",
        "pt": "Já enviámos um código. Vê a caixa escolar (e o spam). Espera {secs}s antes de pedir outro; podes introduzi-lo já abaixo.",
    },
    "ok.code_sent": {
        "zh": "验证码已发送至 {email}", "tw": "驗證碼已發送至 {email}",
        "en": "Verification code sent to {email}", "pt": "Código enviado para {email}",
    },
    "ok.code_fail": {
        "zh": "邮件发送失败，请使用页面验证码。详情: {info}",
        "tw": "郵件發送失敗，請使用頁面驗證碼。詳情：{info}",
        "en": "Email failed to send. Use the on-page code if shown. Details: {info}",
        "pt": "Falha a enviar o email. Usa o código na página se aparecer. Detalhe: {info}",
    },
    "ok.beta_in": {"zh": "内测账号已登录", "tw": "內測帳號已登入", "en": "Beta account signed in", "pt": "Conta beta autenticada"},
    "ok.logged_in": {"zh": "已登录", "tw": "已登入", "en": "Signed in", "pt": "Sessão iniciada"},
    "ok.verified": {"zh": "验证成功！", "tw": "驗證成功！", "en": "Verified!", "pt": "Verificado!"},
    "ok.already_verified": {"zh": "已验证", "tw": "已驗證", "en": "Already verified", "pt": "Já verificado"},
    "ok.beta_any_code": {
        "zh": "内测账号已登录，验证码可随便填",
        "tw": "內測帳號已登入，驗證碼可隨便填",
        "en": "Beta account signed in; any code works",
        "pt": "Conta beta autenticada; qualquer código serve",
    },
    "ok.survey_saved": {"zh": "问卷已保存", "tw": "問卷已儲存", "en": "Questionnaire saved", "pt": "Questionário guardado"},
    "ok.express_saved": {
        "zh": "隐私资料已保存，已进入匹配池",
        "tw": "隱私資料已儲存，已進入配對池",
        "en": "Privacy profile saved — you are in the match pool",
        "pt": "Perfil de privacidade guardado — estás no pool de matching",
    },
    "ok.optin": {
        "zh": "已预约本周匹配，将在 {when} 揭晓",
        "tw": "已預約本週配對，將在 {when} 揭曉",
        "en": "Opted in for this week. Reveal: {when}",
        "pt": "Inscrito nesta semana. Revelação: {when}",
    },
    "ok.blocked": {
        "zh": "已将 {name} 加入黑名单，之后不会再匹配",
        "tw": "已將 {name} 加入黑名單，之後不會再配對",
        "en": "{name} is blocked and will not be matched again",
        "pt": "{name} foi bloqueado e não voltará a fazer match",
    },
    "match.none_orient": {
        "zh": "当前暂无符合你择偶取向的可匹配用户",
        "tw": "目前暫無符合你擇偶取向的可配對用戶",
        "en": "No one in the pool currently matches your gender preference",
        "pt": "Ninguém no pool corresponde à tua preferência de género",
    },
    "match.none_orient_cross": {
        "zh": "（可在问卷/匹配页勾选愿意跨配的学校，且对方也须勾选你的学校）",
        "tw": "（可在問卷／配對頁勾選願意跨校的學校，且對方也須勾選你的學校）",
        "en": " (You can allow other schools on the profile/match page; they must also allow yours.)",
        "pt": " (Podes permitir outras escolas na página de perfil; elas também têm de permitir a tua.)",
    },
    "match.none_fit": {
        "zh": "池子里有人，但暂时没有足够合适的人选（或合适人选本周已配过）。宁缺毋滥，请下周再试或完善问卷。",
        "tw": "池子裡有人，但暫時沒有足夠合適的人選（或合適人選本週已配過）。請下週再試或完善問卷。",
        "en": "People are in the pool, but no good enough match this week (or they already matched). Try next week or add more to your profile.",
        "pt": "Há pessoas no pool, mas ainda não há um match suficientemente bom esta semana. Tenta na próxima ou completa o perfil.",
    },
    "match.fail_db": {
        "zh": "未能完成配对：当前过门槛的候选人均与你存在硬性底线冲突，未强行配对。可完善问卷或下周再试。",
        "tw": "未能完成配對：過門檻的候選人均與你存在硬性底線衝突，未強行配對。可完善問卷或下週再試。",
        "en": "No match: remaining candidates conflict on hard deal-breakers. We will not force a pair. Edit the survey or try next week.",
        "pt": "Sem match: os candidatos restantes conflitam em limites rígidos. Não forçamos o par. Edita o questionário ou tenta na próxima semana.",
    },
    "match.fail": {
        "zh": "未能完成配对：{reason}。",
        "tw": "未能完成配對：{reason}。",
        "en": "Could not complete a match: {reason}.",
        "pt": "Não foi possível concluir o match: {reason}.",
    },
    "match.rs.partner": {
        "zh": "对方本周已有配对", "tw": "對方本週已有配對",
        "en": "the other person already matched this week", "pt": "a outra pessoa já fez match esta semana",
    },
    "match.rs.score": {
        "zh": "相似度未达内部门槛", "tw": "相似度未達內部門檻",
        "en": "similarity below the internal threshold", "pt": "similaridade abaixo do limiar interno",
    },
    "match.rs.db": {
        "zh": "部分人选硬性底线冲突", "tw": "部分人選硬性底線衝突",
        "en": "some candidates hit deal-breakers", "pt": "alguns candidatos bateram em limites rígidos",
    },
    "match.rs.quota": {
        "zh": "你的本周额度已用完", "tw": "你的本週額度已用完",
        "en": "you have used this week's quota", "pt": "já usaste a quota desta semana",
    },
    "match.rs.none": {
        "zh": "暂无合适人选", "tw": "暫無合適人選",
        "en": "no suitable person right now", "pt": "ninguém adequado de momento",
    },
    "match.note": {
        "zh": "结果以本页为准；邮件仅作通知，发送失败不影响查看。",
        "tw": "結果以本頁為準；郵件僅作通知，發送失敗不影響查看。",
        "en": "This page is the source of truth; email is only a notice.",
        "pt": "Esta página é a referência; o email é só um aviso.",
    },
    "match.list_note": {
        "zh": "一对一：你只能看到当前有效配对；学校邮箱已互见，可先邮件开聊。",
        "tw": "一對一：你只能看到當前有效配對；學校電郵已互見，可先用電郵開聊。",
        "en": "One-to-one: you only see the current active match. School emails are shared — start there.",
        "pt": "Um-para-um: só vês o match ativo. Os emails escolares já estão partilhados — começa por aí.",
    },
    "explain.one": {
        "zh": "一对一：在取向互相接受、本周仍有额度的人里算问卷/自我介绍相似度，只给你得分最高的 1 人；页面不展示匹配度分数，只给契合点与破冰话题",
        "tw": "一對一：在取向互相接受、本週仍有額度的人裡算問卷／自我介紹相似度，只給你得分最高的 1 人；頁面不展示分數，只給契合點與破冰話題",
        "en": "One-to-one: among people who accept each other's gender preference and still have weekly quota, we rank survey/intro similarity and keep the top 1. The page shows fit notes, not a score",
        "pt": "Um-para-um: entre quem aceita a preferência de género e ainda tem quota, ordenamos por similaridade e ficamos com o 1.º. A página mostra notas de afinidade, não uma pontuação",
    },
    "explain.cross_on": {
        "zh": "；默认同校，跨校需双方互相勾选对方学校（双向白名单）。",
        "tw": "；預設同校，跨校需雙方互相勾選對方學校（雙向白名單）。",
        "en": "; same school by default. Cross-school needs both of you to allow each other's campus.",
        "pt": "; mesma escola por defeito. Entre escolas, ambos têm de permitir o campus um do outro.",
    },
    "explain.same": {
        "zh": "（同校）。", "tw": "（同校）。", "en": " (same school).", "pt": " (mesma escola).",
    },
    "explain.topn": {
        "zh": "Top-N：按相似度返回多人（调试用）。",
        "tw": "Top-N：按相似度返回多人（除錯用）。",
        "en": "Top-N: return several people by similarity (debug).",
        "pt": "Top-N: devolve várias pessoas por similaridade (debug).",
    },
    "explain.batch": {
        "zh": "批量匈牙利：先按校配对，再跑跨校池；每人每周最多配到 1 人；结果只展示契合点，不展示分数。",
        "tw": "批量匈牙利：先按校配對，再跑跨校池；每人每週最多配到 1 人；結果只展示契合點，不展示分數。",
        "en": "Batch matching: school pools first, then cross-school; at most one new match per person per week; fit notes only, no score.",
        "pt": "Matching em lote: primeiro por escola, depois entre escolas; no máximo 1 match novo por pessoa/semana; só notas de afinidade.",
    },
}


def request_lang():
    raw = (
        (request.headers.get("X-CM-Lang") or "")
        or (request.args.get("lang") or "")
        or (request.cookies.get("cm_lang") or "")
        or "zh"
    ).strip().lower()
    if raw in ("zh-tw", "zh-hk", "tw"):
        return "tw"
    if raw.startswith("en"):
        return "en"
    if raw.startswith("pt"):
        return "pt"
    if raw in ("zh", "zh-cn", "zh-hans"):
        return "zh"
    return "zh"


def t_api(key, **kwargs):
    row = M.get(key) or {}
    lang = request_lang()
    s = row.get(lang) or row.get("en") or row.get("zh") or key
    for k, v in kwargs.items():
        s = s.replace("{" + k + "}", str(v))
    return s


def api_err(key, status=400, **kwargs):
    return jsonify({
        "ok": False,
        "error": t_api(key, **kwargs),
        "error_key": key,
        "error_vars": kwargs,
    }), status
