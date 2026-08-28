"""
CampusMatch 深度问卷系统

参考 SJTU Date 的 65 题设计，提炼为 39 题问卷：
  1. 核心价值观 (8题) — Q1-Q8
  2. 生活习惯   (8题) — Q9-Q16（含对宠物的态度）
  3. 情感风格   (8题) — Q17-Q24
  4. 兴趣爱好   (8题) — Q25-Q32
  5. 相处预期   (7题) — Q33-Q39（消费/定居/约会等；宠物题已并入 Q15）

输出 80+ 维特征向量，用于余弦相似度匹配。
"""

QUESTIONS = [
    # ===== 维度1: 核心价值观 =====
    {
        "id": 1,
        "dimension": "values",
        "text": "现阶段你更愿意把时间和精力投入哪里？（3 = 两边兼顾）",
        "type": "scale",  # 1-5 Likert
        "left": "事业发展",
        "right": "家庭生活",
        "dealbreaker": False,
    },
    {
        "id": 2,
        "dimension": "values",
        "text": "你的生活方式更偏向？",
        "type": "scale",
        "left": "传统",
        "right": "开放",
        "dealbreaker": False,
    },
    {
        "id": 3,
        "dimension": "values",
        "text": "宗教信仰在你生活中的重要性？",
        "type": "scale",
        "left": "非常重要",
        "right": "完全不重要",
        "dealbreaker": False,
    },
    {
        "id": 4,
        "dimension": "values",
        "text": "收入如何分配？",
        "type": "scale",
        "left": "储蓄为主，未雨绸缪",
        "right": "享受当下，及时行乐",
        "dealbreaker": False,
    },
    {
        "id": 5,
        "dimension": "values",
        "text": "你对结婚的态度？（3 = 可有可无 / 暂不确定）",
        "type": "scale",
        "left": "人生必须结婚",
        "right": "完全不接受婚姻",
        "dealbreaker": True,  # 一票否决
    },
    {
        "id": 6,
        "dimension": "values",
        "text": "是否想要孩子？",
        "type": "scale",
        "left": "一定要",
        "right": "一定不要",
        "dealbreaker": True,
    },
    {
        "id": 7,
        "dimension": "values",
        "text": "伴侣和朋友的安排冲突时，你更倾向？（3 = 协调平衡）",
        "type": "scale",
        "left": "优先伴侣",
        "right": "优先朋友",
        "dealbreaker": False,
    },
    {
        "id": 8,
        "dimension": "values",
        "text": "如果伴侣发生精神或身体出轨，你更倾向？",
        "type": "scale",
        "left": "结束关系",
        "right": "愿意尝试修复",
        "dealbreaker": True,
    },

    # ===== 维度2: 生活习惯 =====
    {
        "id": 9,
        "dimension": "lifestyle",
        "text": "你的作息时间？",
        "type": "scale",
        "left": "早睡早起（22点睡6点起）",
        "right": "夜猫子（凌晨2点后睡）",
        "dealbreaker": False,
    },
    {
        "id": 10,
        "dimension": "lifestyle",
        "text": "你能接受多辣的食物？",
        "type": "scale",
        "left": "完全不吃辣",
        "right": "无辣不欢",
        "dealbreaker": False,
    },
    {
        "id": 11,
        "dimension": "lifestyle",
        "text": "运动频率？",
        "type": "scale",
        "left": "每天坚持",
        "right": "几乎不运动",
        "dealbreaker": False,
    },
    {
        "id": 12,
        "dimension": "lifestyle",
        "text": "居住空间的整洁程度？",
        "type": "scale",
        "left": "一尘不染，物品归位",
        "right": "随意就好，不拘小节",
        "dealbreaker": False,
    },
    {
        "id": 13,
        "dimension": "lifestyle",
        "text": "你对吸烟的态度？（1 不吸且不能接受 · 2 不吸但介意 · 3 不吸但可接受 · 4 偶尔吸 · 5 经常吸）",
        "type": "scale",
        "left": "不吸且不能接受",
        "right": "本人经常吸烟",
        "dealbreaker": True,
    },
    {
        "id": 14,
        "dimension": "lifestyle",
        "text": "喝酒习惯？",
        "type": "scale",
        "left": "滴酒不沾",
        "right": "经常小酌/聚会喝酒",
        "dealbreaker": False,
    },
    {
        "id": 15,
        "dimension": "lifestyle",
        "text": "未来是否愿意和伴侣养宠物？",
        "type": "scale",
        "left": "很想养",
        "right": "不想养或不能养",
        "dealbreaker": False,
    },
    {
        "id": 16,
        "dimension": "lifestyle",
        "text": "旅行风格？",
        "type": "scale",
        "left": "精致规划，打卡清单",
        "right": "随性流浪，走到哪算哪",
        "dealbreaker": False,
    },

    # ===== 维度3: 情感风格 =====
    {
        "id": 17,
        "dimension": "emotional",
        "text": "发生矛盾时，你更倾向什么时候沟通？",
        "type": "scale",
        "left": "当下沟通",
        "right": "先冷静，之后再沟通",
        "dealbreaker": False,
    },
    {
        "id": 18,
        "dimension": "emotional",
        "text": "你常用哪些方式表达爱意？（可多选）",
        "type": "multi",
        "options": ["直接说爱与赞美", "拥抱牵手等接触", "帮对方做事", "准备礼物惊喜"],
    },
    {
        "id": 19,
        "dimension": "emotional",
        "text": "你需要多少独处时间？",
        "type": "scale",
        "left": "几乎不需要，喜欢腻在一起",
        "right": "需要大量独处空间",
        "dealbreaker": False,
    },
    {
        "id": 20,
        "dimension": "emotional",
        "text": "对伴侣与其他人正常社交的看法？",
        "type": "scale",
        "left": "完全不介意，充分信任",
        "right": "会比较介意/需要边界",
        "dealbreaker": False,
    },
    {
        "id": 21,
        "dimension": "emotional",
        "text": "你情绪低落时，希望伴侣怎么做？",
        "type": "scale",
        "left": "主动陪伴安慰",
        "right": "给我空间自己消化",
        "dealbreaker": False,
    },
    {
        "id": 22,
        "dimension": "emotional",
        "text": "恋爱中你更看重什么？（3 = 两者兼顾）",
        "type": "scale",
        "left": "浪漫与仪式感",
        "right": "实际行动与稳定",
        "dealbreaker": False,
    },
    {
        "id": 23,
        "dimension": "emotional",
        "text": "期望每天和伴侣沟通的频率？",
        "type": "scale",
        "left": "时刻保持联系，分享日常",
        "right": "有事再说，不必天天聊",
        "dealbreaker": False,
    },
    {
        "id": 24,
        "dimension": "emotional",
        "text": "对前任的态度？",
        "type": "scale",
        "left": "可以做朋友",
        "right": "最好彻底删除/不联系",
        "dealbreaker": False,
    },

    # ===== 维度4: 兴趣爱好 =====
    {
        "id": 25,
        "dimension": "interests",
        "text": "最喜欢的影视类型？（可多选）",
        "type": "multi",
        "options": ["科幻/奇幻", "悬疑/犯罪", "爱情/文艺", "喜剧", "动作/冒险", "动画/二次元", "纪录片", "恐怖/惊悚"],
    },
    {
        "id": 26,
        "dimension": "interests",
        "text": "音乐品味？（可多选）",
        "type": "multi",
        "options": ["流行", "摇滚/金属", "嘻哈/R&B", "电子/EDM", "古典/爵士", "民谣/独立", "K-Pop/J-Pop", "什么都听"],
        "exclusive_options": ["什么都听"],
    },
    {
        "id": 27,
        "dimension": "interests",
        "text": "阅读偏好？（可多选）",
        "type": "multi",
        "options": ["文学/小说", "科幻/奇幻", "历史/哲学", "心理学/自我提升", "科技/科普", "漫画/轻小说", "不太看书", "学术/专业书籍"],
        "exclusive_options": ["不太看书"],
    },
    {
        "id": 28,
        "dimension": "interests",
        "text": "游戏类型？（可多选）",
        "type": "multi",
        "options": ["MOBA（王者/LOL）", "FPS/射击", "RPG/开放世界", "独立游戏", "手游/休闲", "桌游/剧本杀", "不玩游戏", "主机/PC大作"],
        "exclusive_options": ["不玩游戏"],
    },
    {
        "id": 29,
        "dimension": "interests",
        "text": "户外 vs 室内？",
        "type": "scale",
        "left": "户外探险家，周末必须出去",
        "right": "宅家达人，在家最舒服",
        "dealbreaker": False,
    },
    {
        "id": 30,
        "dimension": "interests",
        "text": "运动项目偏好？（可多选）",
        "type": "multi",
        "options": ["跑步/健身", "球类运动", "游泳/水上", "瑜伽/普拉提", "极限运动", "舞蹈", "不运动", "徒步/登山"],
        "exclusive_options": ["不运动"],
    },
    {
        "id": 31,
        "dimension": "interests",
        "text": "文化活动兴趣？（可多选）",
        "type": "multi",
        "options": ["看展/博物馆", "音乐会/Livehouse", "话剧/音乐剧", "电影/影展", "读书会/讲座", "咖啡馆/美食探店", "不太参加", "市集/艺术节"],
        "exclusive_options": ["不太参加"],
    },
    {
        "id": 32,
        "dimension": "interests",
        "text": "你通常用什么方式放松？（可多选）",
        "type": "multi",
        "options": ["追剧/看电影", "打游戏", "运动出汗", "看书/写作", "和朋友聊天", "睡觉", "做饭/烘焙", "刷社交媒体"],
    },

    # ===== 维度5: 相处预期（消费观 / 定居 / 约会节奏等）=====
    {
        "id": 33,
        "dimension": "expectations",
        "text": "约会账单更倾向怎样处理？（3 = 视情况决定）",
        "type": "scale",
        "left": "每次 AA",
        "right": "双方轮流请客",
        "dealbreaker": False,
    },
    {
        "id": 34,
        "dimension": "expectations",
        "text": "毕业后愿意去哪些地方发展？（可多选）",
        "type": "multi",
        "options": ["一线城市", "二线城市", "三四线城市", "小县城", "海外", "暂不确定"],
        "exclusive_options": ["暂不确定"],
        "dealbreaker": False,
    },
    {
        "id": 35,
        "dimension": "expectations",
        "text": "理想的约会频率？",
        "type": "scale",
        "left": "每周多次见面",
        "right": "每月几次就够，更重线上联络",
        "dealbreaker": False,
    },
    {
        "id": 36,
        "dimension": "expectations",
        "text": "恋爱节奏？",
        "type": "scale",
        "left": "慢热，先做朋友再确定关系",
        "right": "来得快，聊得来就认真推进",
        "dealbreaker": False,
    },
    {
        "id": 37,
        "dimension": "expectations",
        "text": "对异地恋的态度？",
        "type": "scale",
        "left": "可以接受，信任最重要",
        "right": "很难接受，必须同城",
        "dealbreaker": False,
    },
    {
        "id": 38,
        "dimension": "expectations",
        "text": "约会时你更偏好哪种形式？",
        "type": "scale",
        "left": "和朋友一起活动",
        "right": "两人单独约会",
        "dealbreaker": False,
    },
    {
        "id": 39,
        "dimension": "expectations",
        "text": "共同生活时，家务更倾向怎样安排？",
        "type": "scale",
        "left": "提前明确分工",
        "right": "按当时空闲灵活分配",
        "dealbreaker": False,
    },
    {
        "id": 40,
        "dimension": "open",
        "text": "留给匹配对象的话（可选）",
        "type": "text",
        "optional": True,
        "max_length": 2000,
        "placeholder": "写给 TA 的一段话：自我介绍、一首小诗、最近的吐槽、想被怎样对待……真诚就是必杀技。可不填。",
        "hint": "配对成功后对方可见；不参与算法打分，纯粹留给聊天的开口。",
        "dealbreaker": False,
    },
]


# ============================================================
# 问卷多语言（简体 zh 为基准字段；tw/en/pt 为翻译）
# scale: (text, left, right)   multi: (text, [options...])
# 注意：multi 选项翻译仅作展示，提交仍存简体原值
# ============================================================
QUESTION_I18N = {
    1: {"tw": ("現階段你更願意把時間和精力投入哪裡？（3 = 兩邊兼顧）", "事業發展", "家庭生活"),
        "en": ("Where would you rather invest your time and energy now? (3 = balance both)", "Career growth", "Family life"),
        "pt": ("Onde prefere investir tempo e energia agora? (3 = equilibrar ambos)", "Carreira", "Vida familiar")},
    2: {"tw": ("你的生活方式更偏向？", "傳統", "開放"),
        "en": ("Your lifestyle is more…?", "Traditional", "Open"),
        "pt": ("O seu estilo de vida é mais…?", "Tradicional", "Aberto")},
    3: {"tw": ("宗教信仰在你生活中的重要性？", "非常重要", "完全不重要"),
        "en": ("How important is religion to you?", "Very important", "Not important at all"),
        "pt": ("Qual a importância da religião para si?", "Muito importante", "Nada importante")},
    4: {"tw": ("收入如何分配？", "儲蓄為主，未雨綢繆", "享受當下，及時行樂"),
        "en": ("How do you manage your income?", "Save first, plan ahead", "Enjoy now, live in the moment"),
        "pt": ("Como gere o seu dinheiro?", "Poupar e planear o futuro", "Aproveitar o momento")},
    5: {"tw": ("你對結婚的態度？（3 = 可有可無 / 暫不確定）", "人生必須結婚", "完全不接受婚姻"),
        "en": ("Your attitude toward marriage? (3 = optional / unsure)", "Marriage is a must", "I completely reject marriage"),
        "pt": ("A sua atitude perante o casamento? (3 = opcional / indeciso)", "Casar é essencial", "Rejeito totalmente o casamento")},
    6: {"tw": ("是否想要孩子？", "一定要", "一定不要"),
        "en": ("Do you want children?", "Definitely yes", "Definitely no"),
        "pt": ("Quer ter filhos?", "Com certeza sim", "Com certeza não")},
    7: {"tw": ("伴侶和朋友的安排衝突時，你更傾向？（3 = 協調平衡）", "優先伴侶", "優先朋友"),
        "en": ("When plans with your partner and friends clash, what do you prefer? (3 = balance)", "Prioritize partner", "Prioritize friends"),
        "pt": ("Quando os planos com o par e amigos coincidem? (3 = equilibrar)", "Priorizar o par", "Priorizar os amigos")},
    8: {"tw": ("如果伴侶發生精神或身體出軌，你更傾向？", "結束關係", "願意嘗試修復"),
        "en": ("If your partner cheats emotionally or physically, you would…?", "End the relationship", "Try to repair it"),
        "pt": ("Se o par for infiel emocional ou fisicamente, prefere…?", "Terminar a relação", "Tentar reparar a relação")},
    9: {"tw": ("你的作息時間？", "早睡早起（22點睡6點起）", "夜貓子（凌晨2點後睡）"),
        "en": ("Your sleep schedule?", "Early bird (10pm–6am)", "Night owl (after 2am)"),
        "pt": ("O seu horário de sono?", "Madrugador (22h–6h)", "Noctívago (depois das 2h)")},
    10: {"tw": ("你能接受多辣的食物？", "完全不吃辣", "無辣不歡"),
         "en": ("How spicy can your food be?", "No spice at all", "The spicier the better"),
         "pt": ("Quanto picante aceita na comida?", "Nada picante", "Quanto mais picante melhor")},
    11: {"tw": ("運動頻率？", "每天堅持", "幾乎不運動"),
         "en": ("How often do you exercise?", "Every day", "Almost never"),
         "pt": ("Com que frequência faz exercício?", "Todos os dias", "Quase nunca")},
    12: {"tw": ("居住空間的整潔程度？", "一塵不染，物品歸位", "隨意就好，不拘小節"),
         "en": ("How tidy is your space?", "Spotless, everything in place", "Casual, easygoing"),
         "pt": ("Quão arrumado é o seu espaço?", "Impecável, tudo no lugar", "Descontraído")},
    13: {"tw": ("你對吸菸的態度？（1 不吸且不能接受 · 2 不吸但介意 · 3 不吸但可接受 · 4 偶爾吸 · 5 經常吸）", "不吸且不能接受", "本人經常吸菸"),
         "en": ("Your attitude toward smoking? (1 don't smoke/can't accept · 2 don't smoke/dislike · 3 don't smoke/accept · 4 occasionally · 5 often)", "Do not smoke or accept it", "I smoke often"),
         "pt": ("A sua atitude perante o tabaco? (1 não fumo/não aceito · 2 não fumo/incomoda · 3 não fumo/aceito · 4 ocasionalmente · 5 frequentemente)", "Não fumo nem aceito", "Fumo frequentemente")},
    14: {"tw": ("喝酒習慣？", "滴酒不沾", "經常小酌/聚會喝酒"),
         "en": ("Drinking?", "Never", "Social drinks often"),
         "pt": ("Bebe álcool?", "Nunca", "Socialmente, com frequência")},
    15: {"tw": ("未來是否願意和伴侶養寵物？", "很想養", "不想養或不能養"),
         "en": ("Would you raise pets with a partner in the future?", "Would love to", "Do not want to / cannot"),
         "pt": ("Gostaria de ter animais com o seu par no futuro?", "Gostaria muito", "Não quero / não posso")},
    16: {"tw": ("旅行風格？", "精緻規劃，打卡清單", "隨性流浪，走到哪算哪"),
         "en": ("Travel style?", "Well planned, checklist", "Go with the flow"),
         "pt": ("Estilo de viagem?", "Tudo planeado, com roteiro", "Ao sabor do momento")},
    17: {"tw": ("發生矛盾時，你更傾向什麼時候溝通？", "當下溝通", "先冷靜，之後再溝通"),
         "en": ("When conflict happens, when do you prefer to talk?", "Talk right away", "Cool down, then talk"),
         "pt": ("Num conflito, quando prefere conversar?", "Conversar logo", "Acalmar primeiro, conversar depois")},
    18: {"tw": ("你常用哪些方式表達愛意？（可多選）",
               ["直接說愛與讚美", "擁抱牽手等接觸", "幫對方做事", "準備禮物驚喜"]),
         "en": ("How do you usually express love? (select all)",
                ["Say it & give compliments", "Hugs, hand-holding & touch", "Help with things", "Prepare gifts & surprises"]),
         "pt": ("Como costuma expressar amor? (várias opções)",
                ["Dizer e elogiar", "Abraçar, dar a mão e tocar", "Ajudar com tarefas", "Preparar presentes e surpresas"])},
    19: {"tw": ("你需要多少獨處時間？", "幾乎不需要，喜歡膩在一起", "需要大量獨處空間"),
         "en": ("How much alone time do you need?", "Barely any, love being together", "A lot of personal space"),
         "pt": ("De quanto tempo sozinho precisa?", "Quase nenhum, adoro estar juntos", "Muito espaço pessoal")},
    20: {"tw": ("對伴侶與其他人正常社交的看法？", "完全不介意，充分信任", "希望有明確邊界"),
         "en": ("Your partner socializing normally with others?", "Totally fine, full trust", "Prefer clear boundaries"),
         "pt": ("O seu par socializar normalmente com outras pessoas?", "Sem problema, confiança total", "Prefiro limites claros")},
    21: {"tw": ("你情緒低落時，希望伴侶怎麼做？", "主動陪伴安慰", "給我空間自己消化"),
         "en": ("When you feel low, what should your partner do?", "Stay close and comfort me", "Give me space to process"),
         "pt": ("Quando está em baixo, o que prefere que o par faça?", "Acompanhar e confortar", "Dar-me espaço")},
    22: {"tw": ("戀愛中你更看重什麼？（3 = 兩者兼顧）", "浪漫與儀式感", "實際行動與穩定"),
         "en": ("What matters more in a relationship? (3 = balance both)", "Romance & rituals", "Practical action & stability"),
         "pt": ("O que valoriza mais numa relação? (3 = equilibrar)", "Romance e rituais", "Ações práticas e estabilidade")},
    23: {"tw": ("期望每天和伴侶溝通的頻率？", "時刻保持聯繫，分享日常", "有事再說，不必天天聊"),
         "en": ("Daily communication with your partner?", "Stay in touch all day", "Only when needed"),
         "pt": ("Comunicação diária com o par?", "Contacto constante", "Só quando necessário")},
    24: {"tw": ("對前任的態度？", "可以做朋友", "最好徹底刪除/不聯繫"),
         "en": ("Attitude toward exes?", "Can stay friends", "Delete & no contact"),
         "pt": ("Atitude com ex-namorados(as)?", "Podemos ser amigos", "Apagar e cortar contacto")},
    25: {"tw": ("最喜歡的影視類型？（可多選）",
                ["科幻/奇幻", "懸疑/犯罪", "愛情/文藝", "喜劇", "動作/冒險", "動畫/二次元", "紀錄片", "恐怖/驚悚"]),
         "en": ("Favorite film & TV genres? (multi)",
                ["Sci-fi/Fantasy", "Mystery/Crime", "Romance/Arthouse", "Comedy", "Action/Adventure", "Anime", "Documentary", "Horror/Thriller"]),
         "pt": ("Géneros de filmes e séries favoritos? (vários)",
                ["Ficção científica/Fantasia", "Mistério/Crime", "Romance/Arte", "Comédia", "Ação/Aventura", "Anime", "Documentário", "Terror/Suspense"])},
    26: {"tw": ("音樂品味？（可多選）",
                ["流行", "搖滾/金屬", "嘻哈/R&B", "電子/EDM", "古典/爵士", "民謠/獨立", "K-Pop/J-Pop", "什麼都聽"]),
         "en": ("Music taste? (multi)",
                ["Pop", "Rock/Metal", "Hip-hop/R&B", "Electronic/EDM", "Classical/Jazz", "Folk/Indie", "K-Pop/J-Pop", "Anything"]),
         "pt": ("Gosto musical? (vários)",
                ["Pop", "Rock/Metal", "Hip-hop/R&B", "Eletrónica/EDM", "Clássica/Jazz", "Folk/Indie", "K-Pop/J-Pop", "Ouço de tudo"])},
    27: {"tw": ("閱讀偏好？（可多選）",
                ["文學/小說", "科幻/奇幻", "歷史/哲學", "心理學/自我提升", "科技/科普", "漫畫/輕小說", "不太看書", "學術/專業書籍"]),
         "en": ("Reading preference? (multi)",
                ["Fiction/Novels", "Sci-fi/Fantasy", "History/Philosophy", "Psychology/Self-help", "Tech/Pop science", "Manga/Light novels", "Rarely read", "Academic books"]),
         "pt": ("Preferência de leitura? (vários)",
                ["Literatura/Romances", "Ficção científica/Fantasia", "História/Filosofia", "Psicologia/Autoajuda", "Tecnologia/Ciência", "Manga/Light novels", "Leio pouco", "Livros académicos"])},
    28: {"tw": ("遊戲類型？（可多選）",
                ["MOBA（王者/LOL）", "FPS/射擊", "RPG/開放世界", "獨立遊戲", "手遊/休閒", "桌遊/劇本殺", "不玩遊戲", "主機/PC大作"]),
         "en": ("Games? (multi)",
                ["MOBA (LoL/HoK)", "FPS/Shooters", "RPG/Open world", "Indie games", "Mobile/Casual", "Board games", "Don't play games", "Console/PC AAA"]),
         "pt": ("Jogos? (vários)",
                ["MOBA (LoL/HoK)", "FPS/Tiro", "RPG/Mundo aberto", "Jogos indie", "Mobile/Casual", "Jogos de tabuleiro", "Não jogo", "Consola/PC AAA"])},
    29: {"tw": ("戶外 vs 室內？", "戶外探險家，週末必須出去", "宅家達人，在家最舒服"),
         "en": ("Outdoors vs indoors?", "Outdoor explorer, out every weekend", "Homebody, home is best"),
         "pt": ("Ar livre ou em casa?", "Explorador, fim de semana fora", "Caseiro, em casa é melhor")},
    30: {"tw": ("運動項目偏好？（可多選）",
                ["跑步/健身", "球類運動", "游泳/水上", "瑜伽/普拉提", "極限運動", "舞蹈", "不運動", "徒步/登山"]),
         "en": ("Sports? (multi)",
                ["Running/Gym", "Ball sports", "Swimming", "Yoga/Pilates", "Extreme sports", "Dance", "No sports", "Hiking/Climbing"]),
         "pt": ("Desportos? (vários)",
                ["Corrida/Ginásio", "Desportos com bola", "Natação", "Ioga/Pilates", "Desportos radicais", "Dança", "Não pratico", "Caminhada/Montanhismo"])},
    31: {"tw": ("文化活動興趣？（可多選）",
                ["看展/博物館", "音樂會/Livehouse", "話劇/音樂劇", "電影/影展", "讀書會/講座", "咖啡館/美食探店", "不太參加", "市集/藝術節"]),
         "en": ("Cultural activities? (multi)",
                ["Exhibitions/Museums", "Concerts/Live music", "Theater/Musicals", "Cinema/Film festivals", "Book clubs/Talks", "Cafés/Food hunting", "Rarely join", "Markets/Art festivals"]),
         "pt": ("Atividades culturais? (vários)",
                ["Exposições/Museus", "Concertos/Música ao vivo", "Teatro/Musicais", "Cinema/Festivais", "Clubes de leitura", "Cafés/Gastronomia", "Raramente participo", "Feiras/Festivais de arte"])},
    32: {"tw": ("你通常用什麼方式放鬆？（可多選）",
                ["追劇/看電影", "打遊戲", "運動出汗", "看書/寫作", "和朋友聊天", "睡覺", "做飯/烘焙", "刷社交媒體"]),
         "en": ("How do you unwind? (multi)",
                ["Shows & movies", "Gaming", "Working out", "Reading/Writing", "Chatting with friends", "Sleeping", "Cooking/Baking", "Social media"]),
         "pt": ("Como relaxa? (vários)",
                ["Séries e filmes", "Jogar", "Exercício", "Ler/Escrever", "Conversar com amigos", "Dormir", "Cozinhar", "Redes sociais"])},
    33: {"tw": ("約會帳單更傾向怎樣處理？（3 = 視情況決定）", "每次 AA", "雙方輪流請客"),
         "en": ("How should dating bills be handled? (3 = depends)", "Split every time", "Take turns treating"),
         "pt": ("Como dividir as contas dos encontros? (3 = depende)", "Dividir sempre", "Pagar à vez")},
    34: {"tw": ("畢業後願意去哪裡發展？（可多選）",
               ["一線城市", "二線城市", "三四線城市", "小縣城", "海外", "暫不確定"]),
         "en": ("Where would you consider living after graduation? (select all)",
                ["Major city", "Mid-sized city", "Smaller city", "Small town", "Abroad", "Not sure yet"]),
         "pt": ("Onde aceitaria viver depois de se formar? (várias opções)",
                ["Grande cidade", "Cidade média", "Cidade pequena", "Vila", "Estrangeiro", "Ainda não sei"])},
    35: {"tw": ("理想的約會頻率？", "每週多次見面", "每月幾次就夠，更重線上聯絡"),
         "en": ("Ideal dating frequency?", "Meet several times a week", "A few times a month, more online"),
         "pt": ("Frequência ideal de encontros?", "Várias vezes por semana", "Algumas vezes por mês, mais online")},
    36: {"tw": ("戀愛節奏？", "慢熱，先做朋友再確定關係", "來得快，聊得來就認真推進"),
         "en": ("Relationship pace?", "Slow burn, friends first", "Fast, commit when it clicks"),
         "pt": ("Ritmo da relação?", "Devagar, amigos primeiro", "Rápido, avançar quando há química")},
    37: {"tw": ("對異地戀的態度？", "可以接受，信任最重要", "很難接受，必須同城"),
         "en": ("Long-distance relationships?", "Acceptable, trust matters most", "Hard no, must be same city"),
         "pt": ("Relação à distância?", "Aceitável, confiança é o essencial", "Difícil, tem de ser na mesma cidade")},
    38: {"tw": ("約會時你更偏好哪種形式？", "和朋友一起活動", "兩人單獨約會"),
         "en": ("What kind of date do you prefer?", "Activities with friends", "One-on-one dates"),
         "pt": ("Que tipo de encontro prefere?", "Atividades com amigos", "Encontros a dois")},
    39: {"tw": ("共同生活時，家務更傾向怎樣安排？", "提前明確分工", "按當時空閒靈活分配"),
         "en": ("How should chores be arranged when living together?", "Agree on roles in advance", "Divide flexibly by availability"),
         "pt": ("Como organizar tarefas ao viver juntos?", "Definir funções antes", "Dividir conforme a disponibilidade")},
    40: {"tw": ("留給配對對象的話（可選）",
               "寫給 TA 的一段話：自我介紹、一首小詩、最近的吐槽、想被怎樣對待……真誠就是必殺技。可不填。"),
         "en": ("A note for your match (optional)",
                "Anything for them: intro, a short poem, a rant, how you'd like to be treated… Sincerity wins. Leave blank if you prefer."),
         "pt": ("Uma mensagem para o teu match (opcional)",
                "Escreve o que quiseres: apresentação, um poema, um desabafo… A sinceridade resulta. Podes deixar em branco.")},
}


def _merge_question_i18n():
    """把翻译合并进 QUESTIONS（q["i18n"][lang] = {text, left/right 或 options 或 placeholder}）。"""
    for q in QUESTIONS:
        tr = QUESTION_I18N.get(q["id"])
        if not tr:
            continue
        q["i18n"] = {}
        for lang, val in tr.items():
            if q["type"] == "scale":
                q["i18n"][lang] = {"text": val[0], "left": val[1], "right": val[2]}
            elif q["type"] == "text":
                q["i18n"][lang] = {"text": val[0], "placeholder": val[1]}
            else:
                q["i18n"][lang] = {"text": val[0], "options": list(val[1])}


_merge_question_i18n()


def _norm_answers(answers):
    """兼容 int / str 题号键。"""
    if not answers:
        return {}
    out = {}
    for k, v in answers.items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            continue
    return out


def _norm_important_ids(important_ids):
    if not important_ids:
        return set()
    out = set()
    for x in important_ids:
        try:
            out.add(int(x))
        except (TypeError, ValueError):
            continue
    return out


def build_feature_vector(answers, important_ids=None):
    """
    将用户答案转换为特征向量。

    Args:
        answers: dict {question_id: answer_value}
                 scale 题: answer_value 是 1-5 的整数
                 multi 题: answer_value 是 ["选项A", "选项C"] 的列表
        important_ids: set of question_ids 用户标记为"对我很重要"

    Returns:
        vector: list of float, 归一化的特征向量
        dimension_names: list of str, 每个维度的名称（用于调试和可解释性）
    """
    answers = _norm_answers(answers)
    important_ids = _norm_important_ids(important_ids)

    vector = []
    dim_names = []

    for q in QUESTIONS:
        qid = q["id"]
        weight = 2.0 if qid in important_ids else 1.0

        if q["type"] == "scale":
            val = answers.get(qid, 3)  # 默认中间值
            try:
                val = int(val)
            except (TypeError, ValueError):
                val = 3
            val = max(1, min(5, val))
            # 双维互补编码，消除单维 [0,1] 对右端答案的余弦偏置：
            # 1 -> [1,0]，3 -> [.5,.5]，5 -> [0,1]
            # 因而“两人都选 1”和“两人都选 5”会得到对称贡献。
            right = (float(val) - 1) / 4.0
            left = 1.0 - right
            vector.extend([left * weight, right * weight])
            dim_names.extend([
                f"Q{qid}_{q['dimension']}_left",
                f"Q{qid}_{q['dimension']}_right",
            ])

        elif q["type"] == "multi":
            raw = answers.get(qid, []) or []
            selected = set(raw) if isinstance(raw, (list, tuple, set)) else set()
            for opt in q["options"]:
                val = 1.0 if opt in selected else 0.0
                vector.append(val * weight)
                dim_names.append(f"Q{qid}_{opt}")

        # type == "text"：自由留言不进入特征向量

    return vector, dim_names


def build_express_vector(bio):
    """与问卷同维：中性量表底 + 自我介绍 n-gram 哈希，便于同一匹配器。"""
    import hashlib

    base, names = build_feature_vector({})
    n = len(base)
    hashed = [0.0] * n
    text = (bio or "").strip().lower()
    if len(text) >= 2:
        for i in range(len(text) - 1):
            bg = text[i : i + 2].encode("utf-8")
            idx = int(hashlib.md5(bg).hexdigest(), 16) % n
            hashed[idx] += 1.0
    mx = max(hashed) if hashed and max(hashed) > 0 else 1.0
    hashed = [x / mx for x in hashed]
    mixed = [0.28 * b + 0.72 * h for b, h in zip(base, hashed)]
    return mixed, names


OPEN_LETTER_QID = 40
OPEN_LETTER_MAX_LEN = 2000


def get_open_letter(answers):
    """取出可选自由留言（纯展示，不参与打分）。"""
    answers = _norm_answers(answers)
    raw = answers.get(OPEN_LETTER_QID)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raw = str(raw)
    text = raw.strip()
    if not text:
        return None
    return text[:OPEN_LETTER_MAX_LEN]


def cosine_similarity(vec1, vec2):
    """计算两个向量的余弦相似度 [0, 1]"""
    if len(vec1) != len(vec2):
        raise ValueError(f"向量维度不匹配: {len(vec1)} vs {len(vec2)}")

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / (norm1 * norm2)


def check_dealbreakers(answers1, answers2):
    """
    检查一票否决条件。

    仅检查标记为 dealbreaker 的 scale 题：
    - 婚姻/孩子（Q5/Q6）：一方明确想要（1–2）、另一方明确不要（4–5）
    - 其它硬底线：答案差距 ≥ 3

    Returns:
        list of question texts that triggered dealbreaker
    """
    answers1 = _norm_answers(answers1)
    answers2 = _norm_answers(answers2)
    triggered = []

    for q in QUESTIONS:
        if not q.get("dealbreaker"):
            continue
        if q["type"] != "scale":
            continue

        qid = q["id"]
        if qid not in answers1 or qid not in answers2:
            continue
        try:
            v1 = float(answers1[qid])
            v2 = float(answers2[qid])
        except (TypeError, ValueError):
            continue

        if qid in (5, 6):
            conflict = min(v1, v2) <= 2 and max(v1, v2) >= 4
        else:
            conflict = abs(v1 - v2) >= 3
        if conflict:
            triggered.append(q["text"])

    return triggered


def get_compatibility_insight(user_vec, match_vec, answers, match_answers, score=None, seed=None,
                              my_school=None, their_school=None):
    """
    生成相处提示：共同点、差异、破冰口语。
    icebreakers 为纯字符串列表（校园口语，可直接发出）；seed 建议传双方 user id。
    """
    from icebreakers import pick_icebreakers

    answers = _norm_answers(answers)
    match_answers = _norm_answers(match_answers)

    scale_filled = sum(
        1 for q in QUESTIONS
        if q["type"] == "scale" and q["id"] in answers and q["id"] in match_answers
    )
    if scale_filled < 8:
        from icebreakers import pick_icebreakers

        icebreakers = pick_icebreakers(
            shared_tags=[], seed=seed, n=3,
            my_school=my_school, their_school=their_school,
        )
        strengths = [
            "双方都愿意先认识：用一段自我介绍进池，不强制交卷面问卷",
        ]
        if (answers or match_answers):
            strengths.append("其中一方写了更完整的问卷，相处时多问、少猜")
        return {
            "summary": "这次配对更看重自我介绍与取向是否合拍；深度问卷未双方填齐，不编造「量表很接近」。",
            "strengths": strengths[:6],
            "differences": ["问卷完整度不同——以聊天核实习惯与底线，不要默认对方填过同一套题。"],
            "icebreakers": icebreakers[:3],
            "shared_tags": [],
            "total_strengths": len(strengths),
            "total_differences": 1,
        }

    strengths = []
    differences = []
    shared_tags = []

    # 敏感话题不做共同点/差异素材（婚姻/孩子/出轨/吸烟/前任）
    ice_ban_qids = {5, 6, 8, 13, 24}

    for q in QUESTIONS:
        qid = q["id"]
        if q["type"] == "scale":
            try:
                v1 = float(answers.get(qid, 3))
                v2 = float(match_answers.get(qid, 3))
            except (TypeError, ValueError):
                continue
            diff = abs(v1 - v2)
            if diff <= 1:
                mid = (v1 + v2) / 2
                lean = q.get("left", "左侧") if mid <= 3 else q.get("right", "右侧")
                if qid not in ice_ban_qids:
                    strengths.append(f"在「{q['text']}」上很接近，都更偏向「{lean}」一侧")
            elif diff >= 3 and qid not in ice_ban_qids:
                differences.append(
                    f"「{q['text']}」差异较大（你偏「{q.get('left','一端')}」方向，对方偏「{q.get('right','另一端')}」方向）——见面时多问问对方真实习惯"
                )
        elif q["type"] == "multi":
            s1 = set(answers.get(q["id"], []) or [])
            s2 = set(match_answers.get(q["id"], []) or [])
            common = list(s1 & s2)
            if common:
                shared_tags.extend(common[:3])
                show = "、".join(common[:3])
                strengths.append(f"「{q['text']}」都喜欢：{show}")

    # 破冰：口语库按 seed 抽取；兴趣 tag 优先映射，否则通用库；不套题干人机句
    uniq_tags = list(dict.fromkeys(shared_tags))
    icebreakers = pick_icebreakers(
        shared_tags=uniq_tags, seed=seed, n=3,
        my_school=my_school, their_school=their_school,
    )

    summary = (
        f"找到 {len(strengths)} 处相近、{len(differences)} 处差异。"
        "把这次当作「系统给的开口理由」，轻松一点就好。"
    )

    if uniq_tags:
        summary += f" 共同标签：{'、'.join(uniq_tags[:4])}。"

    return {
        "summary": summary,
        "strengths": strengths[:6],
        "differences": differences[:4],
        "icebreakers": icebreakers[:3],
        "shared_tags": uniq_tags[:6],
        "total_strengths": len(strengths),
        "total_differences": len(differences),
        "score_pct": None,
    }


# ---- 学校兴趣标签数据库（爬虫填充 + 手工维护）----
# 可被 crawler.py 更新
SCHOOL_INTEREST_SEEDS = {
    "澳门大学": [
        "学术研究", "社团活动", "广东话", "葡语", "澳门美食",
        "旅行", "摄影", "编程", "金融", "创业",
        "桌游", "篮球", "游泳", "音乐会", "看展",
    ],
    "澳门科技大学": [
        "编程", "设计", "创业", "电竞", "摄影",
        "旅行", "美食", "电影", "健身", "舞蹈",
        "商科", "AI", "区块链", "音乐", "动漫",
    ],
    "澳门理工大学": [
        "翻译", "教育", "社工", "编程", "设计",
        "音乐", "运动", "读书", "旅行", "志愿服务",
    ],
    "澳门旅游大学": [
        "酒店管理", "旅游规划", "美食", "文化研究",
        "语言学习", "摄影", "户外运动", "社交活动",
    ],
    "香港大学": [
        "学术研究", "辩论", "编程", "金融", "法律",
        "音乐", "登山", "帆船", "创业", "国际关系",
    ],
    "香港中文大学": [
        "文学", "哲学", "社会学", "科技创新", "创业",
        "音乐", "戏剧", "行山", "环保", "志愿服务",
    ],
    "香港科技大学": [
        "编程", "AI", "机器人", "创业", "金融科技",
        "帆船", "登山", "摄影", "音乐", "电竞",
    ],
}
