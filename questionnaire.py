"""
CampusMatch 深度问卷系统

参考 SJTU Date 的 65 题设计，提炼为 40 题问卷：
  1. 核心价值观 (8题) — Q1-Q8
  2. 生活习惯   (8题) — Q9-Q16
  3. 情感风格   (8题) — Q17-Q24
  4. 兴趣爱好   (8题) — Q25-Q32
  5. 相处预期   (8题) — Q33-Q40（消费/定居/约会频率等）

输出 80+ 维特征向量，用于余弦相似度匹配。
"""

QUESTIONS = [
    # ===== 维度1: 核心价值观 =====
    {
        "id": 1,
        "dimension": "values",
        "text": "你的人生追求更偏向哪边？",
        "type": "scale",  # 1-5 Likert
        "left": "事业成就",
        "right": "家庭幸福",
        "dealbreaker": False,
    },
    {
        "id": 2,
        "dimension": "values",
        "text": "对社会议题的态度？",
        "type": "scale",
        "left": "保守传统",
        "right": "开放进步",
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
        "text": "对婚姻的看法？",
        "type": "scale",
        "left": "人生必需",
        "right": "可有可无",
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
        "text": "朋友和恋人的时间分配？",
        "type": "scale",
        "left": "恋人为重",
        "right": "朋友同样重要",
        "dealbreaker": False,
    },
    {
        "id": 8,
        "dimension": "values",
        "text": "对精神/肉体出轨的态度？",
        "type": "scale",
        "left": "绝对不可原谅",
        "right": "可以理解/沟通解决",
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
        "text": "饮食偏好？",
        "type": "scale",
        "left": "清淡健康",
        "right": "无辣不欢/重口味",
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
        "text": "抽烟习惯？",
        "type": "scale",
        "left": "从不抽烟",
        "right": "经常抽烟",
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
        "text": "对宠物的态度？",
        "type": "scale",
        "left": "非常喜欢，一定要养",
        "right": "不太喜欢/过敏/不养",
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
        "text": "吵架时你通常怎么做？",
        "type": "scale",
        "left": "立刻冷静沟通解决",
        "right": "需要时间冷静/先回避",
        "dealbreaker": False,
    },
    {
        "id": 18,
        "dimension": "emotional",
        "text": "你更偏向如何表达爱意？",
        "type": "scale",
        "left": "言语表达+身体接触",
        "right": "实际行动+惊喜礼物",
        "dealbreaker": False,
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
        "text": "对伴侣与异性正常社交的看法？",
        "type": "scale",
        "left": "完全不介意，充分信任",
        "right": "会比较介意/需要边界",
        "dealbreaker": False,
    },
    {
        "id": 21,
        "dimension": "emotional",
        "text": "你的吃醋频率？",
        "type": "scale",
        "left": "几乎不吃醋",
        "right": "比较容易吃醋",
        "dealbreaker": False,
    },
    {
        "id": 22,
        "dimension": "emotional",
        "text": "浪漫 vs 务实？",
        "type": "scale",
        "left": "极度浪漫，仪式感很重要",
        "right": "极度务实，过日子才重要",
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
    },
    {
        "id": 27,
        "dimension": "interests",
        "text": "阅读偏好？（可多选）",
        "type": "multi",
        "options": ["文学/小说", "科幻/奇幻", "历史/哲学", "心理学/自我提升", "科技/科普", "漫画/轻小说", "不太看书", "学术/专业书籍"],
    },
    {
        "id": 28,
        "dimension": "interests",
        "text": "游戏类型？（可多选）",
        "type": "multi",
        "options": ["MOBA（王者/LOL）", "FPS/射击", "RPG/开放世界", "独立游戏", "手游/休闲", "桌游/剧本杀", "不玩游戏", "主机/PC大作"],
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
    },
    {
        "id": 31,
        "dimension": "interests",
        "text": "文化活动兴趣？（可多选）",
        "type": "multi",
        "options": ["看展/博物馆", "音乐会/Livehouse", "话剧/音乐剧", "电影/影展", "读书会/讲座", "咖啡馆/美食探店", "不太参加", "市集/艺术节"],
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
        "text": "约会消费更倾向？",
        "type": "scale",
        "left": "AA / 各自付各自的",
        "right": "谁提出谁请客 / 传统分工",
        "dealbreaker": False,
    },
    {
        "id": 34,
        "dimension": "expectations",
        "text": "毕业后希望主要生活在哪里？",
        "type": "scale",
        "left": "回老家 / 小城市",
        "right": "北上广深港 / 国际都市",
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
        "dealbreaker": True,
    },
    {
        "id": 38,
        "dimension": "expectations",
        "text": "想养宠物吗？",
        "type": "scale",
        "left": "一定要养（猫狗等）",
        "right": "坚决不养",
        "dealbreaker": False,
    },
    {
        "id": 39,
        "dimension": "expectations",
        "text": "恋爱中的社交频率？",
        "type": "scale",
        "left": "经常一起见朋友 / 参加局",
        "right": "两人世界为主，少社交",
        "dealbreaker": False,
    },
    {
        "id": 40,
        "dimension": "expectations",
        "text": "同居后家务怎么分？",
        "type": "scale",
        "left": "明确分工、对半分",
        "right": "谁有空谁做 / 随性",
        "dealbreaker": False,
    },
]


# ============================================================
# 问卷多语言（简体 zh 为基准字段；tw/en/pt 为翻译）
# scale: (text, left, right)   multi: (text, [options...])
# 注意：multi 选项翻译仅作展示，提交仍存简体原值
# ============================================================
QUESTION_I18N = {
    1: {"tw": ("你的人生追求更偏向哪邊？", "事業成就", "家庭幸福"),
        "en": ("What matters more in your life?", "Career achievement", "Family happiness"),
        "pt": ("O que importa mais na sua vida?", "Sucesso profissional", "Felicidade familiar")},
    2: {"tw": ("對社會議題的態度？", "保守傳統", "開放進步"),
        "en": ("Your stance on social issues?", "Conservative & traditional", "Open & progressive"),
        "pt": ("A sua posição em questões sociais?", "Conservador e tradicional", "Aberto e progressista")},
    3: {"tw": ("宗教信仰在你生活中的重要性？", "非常重要", "完全不重要"),
        "en": ("How important is religion to you?", "Very important", "Not important at all"),
        "pt": ("Qual a importância da religião para si?", "Muito importante", "Nada importante")},
    4: {"tw": ("收入如何分配？", "儲蓄為主，未雨綢繆", "享受當下，及時行樂"),
        "en": ("How do you manage your income?", "Save first, plan ahead", "Enjoy now, live in the moment"),
        "pt": ("Como gere o seu dinheiro?", "Poupar e planear o futuro", "Aproveitar o momento")},
    5: {"tw": ("對婚姻的看法？", "人生必需", "可有可無"),
        "en": ("Your view on marriage?", "A must in life", "Optional"),
        "pt": ("A sua visão sobre o casamento?", "Essencial na vida", "Opcional")},
    6: {"tw": ("是否想要孩子？", "一定要", "一定不要"),
        "en": ("Do you want children?", "Definitely yes", "Definitely no"),
        "pt": ("Quer ter filhos?", "Com certeza sim", "Com certeza não")},
    7: {"tw": ("朋友和戀人的時間分配？", "戀人為重", "朋友同樣重要"),
        "en": ("Time between partner and friends?", "Partner comes first", "Friends matter equally"),
        "pt": ("Tempo entre par e amigos?", "O par em primeiro lugar", "Os amigos importam igualmente")},
    8: {"tw": ("對精神/肉體出軌的態度？", "絕對不可原諒", "可以理解/溝通解決"),
        "en": ("Attitude toward cheating (emotional/physical)?", "Absolutely unforgivable", "Can be talked through"),
        "pt": ("Atitude perante a infidelidade?", "Absolutamente imperdoável", "Pode ser conversado")},
    9: {"tw": ("你的作息時間？", "早睡早起（22點睡6點起）", "夜貓子（凌晨2點後睡）"),
        "en": ("Your sleep schedule?", "Early bird (10pm–6am)", "Night owl (after 2am)"),
        "pt": ("O seu horário de sono?", "Madrugador (22h–6h)", "Noctívago (depois das 2h)")},
    10: {"tw": ("飲食偏好？", "清淡健康", "無辣不歡/重口味"),
         "en": ("Food preference?", "Light & healthy", "Spicy & bold flavors"),
         "pt": ("Preferência alimentar?", "Leve e saudável", "Picante e intenso")},
    11: {"tw": ("運動頻率？", "每天堅持", "幾乎不運動"),
         "en": ("How often do you exercise?", "Every day", "Almost never"),
         "pt": ("Com que frequência faz exercício?", "Todos os dias", "Quase nunca")},
    12: {"tw": ("居住空間的整潔程度？", "一塵不染，物品歸位", "隨意就好，不拘小節"),
         "en": ("How tidy is your space?", "Spotless, everything in place", "Casual, easygoing"),
         "pt": ("Quão arrumado é o seu espaço?", "Impecável, tudo no lugar", "Descontraído")},
    13: {"tw": ("抽菸習慣？", "從不抽菸", "經常抽菸"),
         "en": ("Smoking?", "Never", "Often"),
         "pt": ("Fuma?", "Nunca", "Frequentemente")},
    14: {"tw": ("喝酒習慣？", "滴酒不沾", "經常小酌/聚會喝酒"),
         "en": ("Drinking?", "Never", "Social drinks often"),
         "pt": ("Bebe álcool?", "Nunca", "Socialmente, com frequência")},
    15: {"tw": ("對寵物的態度？", "非常喜歡，一定要養", "不太喜歡/過敏/不養"),
         "en": ("Pets?", "Love them, must have", "Not a fan / allergic"),
         "pt": ("Animais de estimação?", "Adoro, quero ter", "Não gosto / alergia")},
    16: {"tw": ("旅行風格？", "精緻規劃，打卡清單", "隨性流浪，走到哪算哪"),
         "en": ("Travel style?", "Well planned, checklist", "Go with the flow"),
         "pt": ("Estilo de viagem?", "Tudo planeado, com roteiro", "Ao sabor do momento")},
    17: {"tw": ("吵架時你通常怎麼做？", "立刻冷靜溝通解決", "需要時間冷靜/先迴避"),
         "en": ("During a fight, you usually…?", "Talk it out calmly right away", "Need time alone first"),
         "pt": ("Numa discussão, costuma…?", "Conversar logo com calma", "Preciso de tempo sozinho primeiro")},
    18: {"tw": ("你更偏向如何表達愛意？", "言語表達+身體接觸", "實際行動+驚喜禮物"),
         "en": ("How do you express love?", "Words & physical affection", "Actions & surprise gifts"),
         "pt": ("Como expressa o amor?", "Palavras e carinho físico", "Ações e presentes surpresa")},
    19: {"tw": ("你需要多少獨處時間？", "幾乎不需要，喜歡膩在一起", "需要大量獨處空間"),
         "en": ("How much alone time do you need?", "Barely any, love being together", "A lot of personal space"),
         "pt": ("De quanto tempo sozinho precisa?", "Quase nenhum, adoro estar juntos", "Muito espaço pessoal")},
    20: {"tw": ("對伴侶與異性正常社交的看法？", "完全不介意，充分信任", "會比較介意/需要邊界"),
         "en": ("Partner socializing with the opposite sex?", "Totally fine, full trust", "Prefer clear boundaries"),
         "pt": ("O par socializar com o sexo oposto?", "Sem problema, confiança total", "Prefiro limites claros")},
    21: {"tw": ("你的吃醋頻率？", "幾乎不吃醋", "比較容易吃醋"),
         "en": ("How jealous do you get?", "Almost never", "Quite easily"),
         "pt": ("É ciumento(a)?", "Quase nunca", "Com facilidade")},
    22: {"tw": ("浪漫 vs 務實？", "極度浪漫，儀式感很重要", "極度務實，過日子才重要"),
         "en": ("Romantic vs practical?", "Very romantic, rituals matter", "Very practical, daily life matters"),
         "pt": ("Romântico ou prático?", "Muito romântico, rituais importam", "Muito prático, o dia a dia importa")},
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
    33: {"tw": ("約會消費更傾向？", "AA / 各自付各自的", "誰提出誰請客 / 傳統分工"),
         "en": ("Dating expenses?", "Split the bill", "Whoever invites pays / traditional"),
         "pt": ("Despesas nos encontros?", "Dividir a conta", "Quem convida paga / tradicional")},
    34: {"tw": ("畢業後希望主要生活在哪裡？", "回老家 / 小城市", "北上廣深港 / 國際都市"),
         "en": ("Where do you want to live after graduation?", "Hometown / smaller city", "Big city / international"),
         "pt": ("Onde quer viver depois de se formar?", "Terra natal / cidade pequena", "Grande metrópole / internacional")},
    35: {"tw": ("理想的約會頻率？", "每週多次見面", "每月幾次就夠，更重線上聯絡"),
         "en": ("Ideal dating frequency?", "Meet several times a week", "A few times a month, more online"),
         "pt": ("Frequência ideal de encontros?", "Várias vezes por semana", "Algumas vezes por mês, mais online")},
    36: {"tw": ("戀愛節奏？", "慢熱，先做朋友再確定關係", "來得快，聊得來就認真推進"),
         "en": ("Relationship pace?", "Slow burn, friends first", "Fast, commit when it clicks"),
         "pt": ("Ritmo da relação?", "Devagar, amigos primeiro", "Rápido, avançar quando há química")},
    37: {"tw": ("對異地戀的態度？", "可以接受，信任最重要", "很難接受，必須同城"),
         "en": ("Long-distance relationships?", "Acceptable, trust matters most", "Hard no, must be same city"),
         "pt": ("Relação à distância?", "Aceitável, confiança é o essencial", "Difícil, tem de ser na mesma cidade")},
    38: {"tw": ("想養寵物嗎？", "一定要養（貓狗等）", "堅決不養"),
         "en": ("Want to raise pets together?", "Definitely (cats/dogs etc.)", "Absolutely not"),
         "pt": ("Ter animais de estimação juntos?", "Com certeza (gatos/cães)", "De maneira nenhuma")},
    39: {"tw": ("戀愛中的社交頻率？", "經常一起見朋友 / 參加局", "兩人世界為主，少社交"),
         "en": ("Social life as a couple?", "Often out with friends", "Mostly just the two of us"),
         "pt": ("Vida social em casal?", "Muitas saídas com amigos", "Principalmente nós os dois")},
    40: {"tw": ("同居後家務怎麼分？", "明確分工、對半分", "誰有空誰做 / 隨性"),
         "en": ("Housework if living together?", "Clear 50/50 split", "Whoever is free does it"),
         "pt": ("Tarefas domésticas se viverem juntos?", "Divisão clara 50/50", "Quem estiver livre faz")},
}


def _merge_question_i18n():
    """把翻译合并进 QUESTIONS（q["i18n"][lang] = {text, left/right 或 options}）。"""
    for q in QUESTIONS:
        tr = QUESTION_I18N.get(q["id"])
        if not tr:
            continue
        q["i18n"] = {}
        for lang, val in tr.items():
            if q["type"] == "scale":
                q["i18n"][lang] = {"text": val[0], "left": val[1], "right": val[2]}
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
            # 归一化到 [0, 1]
            normalized = (float(val) - 1) / 4.0
            vector.append(normalized * weight)
            dim_names.append(f"Q{qid}_{q['dimension']}")

        elif q["type"] == "multi":
            selected = set(answers.get(qid, []) or [])
            for opt in q["options"]:
                val = 1.0 if opt in selected else 0.0
                vector.append(val * weight)
                dim_names.append(f"Q{qid}_{opt}")

    return vector, dim_names


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


def check_dealbreakers(answers1, answers2, threshold=0.6):
    """
    检查一票否决条件。

    对标记为 dealbreaker 的 scale 题，如果两人的答案差距超过
    threshold（即归一化后差距 > 0.6，相当于原始 scale 差 ≥ 3），
    则返回所有触发否决的问题。

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
        try:
            v1 = float(answers1.get(qid, 3))
            v2 = float(answers2.get(qid, 3))
        except (TypeError, ValueError):
            continue

        # scale 差 ≥ 3 → 否决
        if abs(v1 - v2) >= 3:
            triggered.append(q["text"])

    return triggered


def get_compatibility_insight(user_vec, match_vec, answers, match_answers, score=None):
    """
    生成「相处说明书」：共同点、差异、一句话总结、破冰话题。

    Returns:
        dict: summary, strengths, differences, icebreakers, totals
    """
    answers = _norm_answers(answers)
    match_answers = _norm_answers(match_answers)
    strengths = []
    differences = []
    icebreakers = []
    shared_tags = []

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
                strengths.append(f"在「{q['text']}」上很接近，都更偏向「{lean}」一侧")
                if len(icebreakers) < 3 and diff == 0:
                    icebreakers.append(
                        f"你们对「{q['text']}」看法几乎一样——可以聊聊：平时遇到这种情况你会怎么做？"
                    )
            elif diff >= 3:
                differences.append(
                    f"「{q['text']}」差异较大（你偏「{q.get('left','一端')}」方向，对方偏「{q.get('right','另一端')}」方向）——见面时多问问对方真实习惯"
                )
        elif q["type"] == "multi":
            s1 = set(answers.get(qid, []) or [])
            s2 = set(match_answers.get(qid, []) or [])
            common = list(s1 & s2)
            if common:
                shared_tags.extend(common[:3])
                show = "、".join(common[:3])
                strengths.append(f"「{q['text']}」都喜欢：{show}")
                if len(icebreakers) < 5:
                    tip = common[0]
                    icebreakers.append(f"你们都喜欢「{tip}」——可以问问：最近有没有相关的安利/体验想分享？")

    # 补足破冰到 3 条
    fallbacks = [
        "先从「最近校园里有什么想去但一个人懒得去的活动」聊起？",
        "互相问问对方问卷里「标记为很重要」的那几题，为什么在意？",
        "约一个低压力场景：咖啡/食堂/散步 30 分钟，不聊太深也没关系。",
    ]
    for fb in fallbacks:
        if len(icebreakers) >= 3:
            break
        if fb not in icebreakers:
            icebreakers.append(fb)

    pct = int(round((score or 0) * 100)) if score is not None else None
    if pct is not None:
        summary = (
            f"系统派单合拍度约 {pct}%：找到 {len(strengths)} 处相近、"
            f"{len(differences)} 处需要包容的差异。"
            "算法只能帮你们认识，剩下的靠聊天。"
        )
    else:
        summary = (
            f"找到 {len(strengths)} 处相近、{len(differences)} 处差异。"
            "把这次当作「系统给的开口理由」，轻松一点就好。"
        )

    if shared_tags:
        uniq = list(dict.fromkeys(shared_tags))[:4]
        summary += f" 共同兴趣关键词：{'、'.join(uniq)}。"

    return {
        "summary": summary,
        "strengths": strengths[:6],
        "differences": differences[:4],
        "icebreakers": icebreakers[:3],
        "shared_tags": list(dict.fromkeys(shared_tags))[:6],
        "total_strengths": len(strengths),
        "total_differences": len(differences),
        "score_pct": pct,
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
