/* 恋爱人格 16 型 + 四维标签：zh / tw / en / pt
   API 仍返回简体正文；展示与分享前调用 localizeLovePersonality(p)。
*/
(function () {
    'use strict';

    var LP_DIMS = {
        expression: {
            label: { zh: '情感表达', tw: '情感表達', en: 'Expression', pt: 'Expressão' },
            E: { zh: '外放热烈', tw: '外放熱烈', en: 'Warm & open', pt: 'Aberta e calorosa' },
            I: { zh: '内敛含蓄', tw: '內斂含蓄', en: 'Reserved', pt: 'Reservada' }
        },
        rhythm: {
            label: { zh: '生活节奏', tw: '生活節奏', en: 'Life rhythm', pt: 'Ritmo de vida' },
            S: { zh: '结构秩序', tw: '結構秩序', en: 'Structured', pt: 'Estruturado' },
            F: { zh: '随性自由', tw: '隨性自由', en: 'Easygoing', pt: 'Descontraído' }
        },
        boundary: {
            label: { zh: '关系边界', tw: '關係邊界', en: 'Boundaries', pt: 'Limites' },
            C: { zh: '亲密融合', tw: '親密融合', en: 'Closely bonded', pt: 'Fusão íntima' },
            O: { zh: '独立自主', tw: '獨立自主', en: 'Independent', pt: 'Independente' }
        },
        risk: {
            label: { zh: '风险态度', tw: '風險態度', en: 'Risk attitude', pt: 'Atitude ao risco' },
            P: { zh: '稳健保守', tw: '穩健保守', en: 'Steady & cautious', pt: 'Estável e cautelosa' },
            A: { zh: '开放冒险', tw: '開放冒險', en: 'Open to adventure', pt: 'Aberta à aventura' }
        }
    };

    // code → { zh|tw|en|pt: { name, subtitle, traits[], strength, match_tip } }
    // 语气对齐 personality.py：E 口语热、I 克制诗意；勿 16 型同一骨架
    var LP_TYPES = {
        ESCP: {
            zh: {
                name: '守护者型',
                subtitle: 'I am constant as the northern star.',
                traits: ['心里有事会摊开讲，不爱让人猜', '日子有章法，承诺更不随便开出口', '想走进你，也想被你认真接住'],
                strength: '把「我在」变成摸得到的安全感，对方不必猜。',
                match_tip: '敢接住你认真、也会把喜欢说出口的人。'
            },
            tw: {
                name: '守護者型',
                subtitle: 'I am constant as the northern star.',
                traits: ['心裡有事會攤開講，不愛讓人猜', '日子有章法，承諾更不隨便開出口', '想走進你，也想被你認真接住'],
                strength: '把「我在」變成摸得到的安全感，對方不必猜。',
                match_tip: '敢接住你認真、也會把喜歡說出口的人。'
            },
            en: {
                name: 'Guardian',
                subtitle: 'I am constant as the northern star.',
                traits: ['I put things on the table; I hate guessing games', 'Life has order; promises aren’t cheap', 'I want in—and I want to be met for real'],
                strength: 'You make “I’m here” something they can feel—no guessing required.',
                match_tip: 'Someone who can hold your seriousness—and say liking out loud too.'
            },
            pt: {
                name: 'Guardião/ã',
                subtitle: 'I am constant as the northern star.',
                traits: ['Pões as coisas na mesa; odeias adivinhações', 'A vida tem ordem; promessas não são baratas', 'Queres entrar—e ser acolhido/a a sério'],
                strength: 'Tornas o «estou aqui» palpável—sem adivinhar.',
                match_tip: 'Alguém que segura a tua seriedade—e também diz o gostar em voz alta.'
            }
        },
        ESCA: {
            zh: {
                name: '开明领航型',
                subtitle: 'To strive, to seek, to find, and not to yield.',
                traits: ['说话直接，绕弯子太累', '日子有节奏，却随时准备翻新页', '亲密要并肩商量，也要敢往前闯'],
                strength: '给你方向，也给你余量：靠近变成一起长大。',
                match_tip: '跟得上你、不怕开新局的人——独立，但肯并肩。'
            },
            tw: {
                name: '開明領航型',
                subtitle: 'To strive, to seek, to find, and not to yield.',
                traits: ['說話直接，繞彎子太累', '日子有節奏，卻隨時準備翻新頁', '親密要並肩商量，也要敢往前闖'],
                strength: '給你方向，也給你餘量：靠近變成一起長大。',
                match_tip: '跟得上你、不怕開新局的人——獨立，但肯並肩。'
            },
            en: {
                name: 'Open Navigator',
                subtitle: 'To strive, to seek, to find, and not to yield.',
                traits: ['Straight talk; circling is exhausting', 'A paced life that’s ready for a new page', 'Closeness means planning side by side—and daring the next turn'],
                strength: 'You give direction and room: closeness becomes growing together.',
                match_tip: 'Someone who keeps up and isn’t scared of a new chapter—independent, but willing to walk with you.'
            },
            pt: {
                name: 'Navegador/a Aberto/a',
                subtitle: 'To strive, to seek, to find, and not to yield.',
                traits: ['Fala direta; rodeios cansam', 'Ritmo no dia a dia, sempre pronto/a a virar página', 'Intimidade é planear a par—e ousar a próxima curva'],
                strength: 'Dás direção e margem: a proximidade vira crescer juntos.',
                match_tip: 'Alguém que acompanha e não teme um capítulo novo—independente, mas disposto a caminhar contigo.'
            }
        },
        EFCP: {
            zh: {
                name: '阳光筑巢型',
                subtitle: 'Grow old along with me.',
                traits: ['一来就能把气氛焐热，情绪藏不住', '日常随性，最烦被规矩拴死', '玩归玩，说到承诺你偏稳'],
                strength: '相处像晒太阳：暖、松，明天还看得见。',
                match_tip: '能一起疯、也肯谈以后的人——别闷成石头，也别飘成风。'
            },
            tw: {
                name: '陽光築巢型',
                subtitle: 'Grow old along with me.',
                traits: ['一來就能把氣氛焐熱，情緒藏不住', '日常隨性，最煩被規矩拴死', '玩歸玩，說到承諾你偏穩'],
                strength: '相處像曬太陽：暖、鬆，明天還看得見。',
                match_tip: '能一起瘋、也肯談以後的人——別悶成石頭，也別飄成風。'
            },
            en: {
                name: 'Sunny Nest-builder',
                subtitle: 'Grow old along with me.',
                traits: ['You warm a room fast; feelings don’t stay hidden', 'Casual days; hate being rule-tied', 'Play hard—commitment, though, you keep steady'],
                strength: 'Love like sunbathing: warm, loose—and tomorrow’s still in view.',
                match_tip: 'Someone who can goof off with you and still talk about later—not a stone, not a breeze.'
            },
            pt: {
                name: 'Construtor/a Solar',
                subtitle: 'Grow old along with me.',
                traits: ['Aqueces o ambiente depressa; emoção não se esconde', 'Dia a dia solto; detestas regras que prendem', 'Brincar vale—no compromisso, és estável'],
                strength: 'Convívio como sol: quente, folgado—e o amanhã ainda se vê.',
                match_tip: 'Alguém que brinca contigo e ainda fala do depois—nem pedra, nem vento.'
            }
        },
        EFCA: {
            zh: {
                name: '浪漫牧者型',
                subtitle: 'How do I love thee? Let me count the ways.',
                traits: ['感情来了嘴比脑子快半拍', '日子要活，一成不变会闷出火星', '想黏着你，也想拉着你去试新的'],
                strength: '把平淡日子点成记得住的火花。',
                match_tip: '同样敢靠近、敢试的人——别用管束把火花浇灭。'
            },
            tw: {
                name: '浪漫牧者型',
                subtitle: 'How do I love thee? Let me count the ways.',
                traits: ['感情來了嘴比腦子快半拍', '日子要活，一成不變會悶出火星', '想黏著你，也想拉著你去試新的'],
                strength: '把平淡日子點成記得住的火花。',
                match_tip: '同樣敢靠近、敢試的人——別用管束把火花澆滅。'
            },
            en: {
                name: 'Romantic Shepherd',
                subtitle: 'How do I love thee? Let me count the ways.',
                traits: ['When feelings hit, mouth outruns brain', 'Days need life; sameness sparks cabin fever', 'Want to stick close—and drag you into something new'],
                strength: 'You turn plain days into sparks worth keeping.',
                match_tip: 'Someone equally brave to come close and try—don’t drown the spark in control.'
            },
            pt: {
                name: 'Pastor/a Romântico/a',
                subtitle: 'How do I love thee? Let me count the ways.',
                traits: ['Quando a emoção chega, a boca vai à frente da cabeça', 'Os dias precisam de vida; a monotonia faz faísca', 'Queres colar—e puxar para algo novo'],
                strength: 'Acendes o quotidiano em faíscas que ficam.',
                match_tip: 'Alguém igualmente corajoso a aproximar-se e tentar—não afogues a faísca com controlo.'
            }
        },
        ESOP: {
            zh: {
                name: '灯塔型',
                subtitle: 'To thine own self be true.',
                traits: ['话讲清楚，少让人猜忌', '生活有谱，心里有地图', '亲近可以，边界和呼吸也要'],
                strength: '靠谱却不吞没——靠近有光，分开也不慌。',
                match_tip: '尊重你节奏的人：认真靠近，也能安静各自站立。'
            },
            tw: {
                name: '燈塔型',
                subtitle: 'To thine own self be true.',
                traits: ['話講清楚，少讓人猜忌', '生活有譜，心裡有地圖', '親近可以，邊界和呼吸也要'],
                strength: '靠譜卻不吞沒——靠近有光，分開也不慌。',
                match_tip: '尊重你節奏的人：認真靠近，也能安靜各自站立。'
            },
            en: {
                name: 'Lighthouse',
                subtitle: 'To thine own self be true.',
                traits: ['Clear words; less suspicion', 'Ordered days, an inner map', 'Closeness is fine—edge and breath still matter'],
                strength: 'Reliable without swallowing anyone—close with light, apart without panic.',
                match_tip: 'Someone who respects your pace: present when near, calm standing alone.'
            },
            pt: {
                name: 'Farol',
                subtitle: 'To thine own self be true.',
                traits: ['Palavras claras; menos suspeita', 'Dias ordenados, mapa interior', 'Proximidade ok—limite e ar ainda importam'],
                strength: 'Confiável sem absorver—perto com luz, longe sem pânico.',
                match_tip: 'Alguém que respeita o teu ritmo: presente ao perto, calmo sozinho.'
            }
        },
        ESOA: {
            zh: {
                name: '自由先驱型',
                subtitle: 'I am large, I contain multitudes.',
                traits: ['一进场就能带起气场', '有秩序感，但绝不要被绑死', '并肩比占有更让你心动'],
                strength: '把热情变成同行，不是吞并。',
                match_tip: '同样完整的人——一起走，别互相化掉。'
            },
            tw: {
                name: '自由先驅型',
                subtitle: 'I am large, I contain multitudes.',
                traits: ['一進場就能帶起氣場', '有秩序感，但絕不要被綁死', '並肩比佔有更讓你心動'],
                strength: '把熱情變成同行，不是吞併。',
                match_tip: '同樣完整的人——一起走，別互相化掉。'
            },
            en: {
                name: 'Free Pioneer',
                subtitle: 'I am large, I contain multitudes.',
                traits: ['You lift a room the second you walk in', 'Some order—zero interest in being tied down', 'Side-by-side thrills you more than owning'],
                strength: 'You turn heat into walking together, not swallowing whole.',
                match_tip: 'Someone equally whole—walk together; don’t melt into each other.'
            },
            pt: {
                name: 'Pioneiro/a Livre',
                subtitle: 'I am large, I contain multitudes.',
                traits: ['Elevas o ambiente ao entrar', 'Há ordem—zero interesse em amarras', 'Lado a lado excita-te mais do que possuir'],
                strength: 'Transformas calor em caminhar juntos, não em absorver.',
                match_tip: 'Alguém igualmente inteiro—caminhem; não se dissolvam.'
            }
        },
        EFOP: {
            zh: {
                name: '热心管家型',
                subtitle: 'Love moderately; long love doth so.',
                traits: ['热情来得快，关心说得出、做得动', '日常不拘小节，讨厌被管太细', '亲近可以，独立也得在', '大事上偏稳，不轻易甩手'],
                strength: '热情摸得到，却不会黏到喘不过气。',
                match_tip: '懂你热一阵、也要自己空间的人。'
            },
            tw: {
                name: '熱心管家型',
                subtitle: 'Love moderately; long love doth so.',
                traits: ['熱情來得快，關心說得出、做得動', '日常不拘小節，討厭被管太細', '親近可以，獨立也得在', '大事上偏穩，不輕易甩手'],
                strength: '熱情摸得到，卻不會黏到喘不過氣。',
                match_tip: '懂你熱一陣、也要自己空間的人。'
            },
            en: {
                name: 'Warm Host',
                subtitle: 'Love moderately; long love doth so.',
                traits: ['Warmth arrives fast; care shows in words and deeds', 'Casual about small stuff; hate micromanagement', 'Close is fine—independence stays', 'Steady on big things; don’t bail lightly'],
                strength: 'Warmth you can touch—without smothering the air out of anyone.',
                match_tip: 'Someone who gets “hot for a stretch, then I need room.”'
            },
            pt: {
                name: 'Anfitrião/ã Afetuoso/a',
                subtitle: 'Love moderately; long love doth so.',
                traits: ['O calor chega depressa; o cuidado sai em palavras e gestos', 'Pouco formal no miúdo; detestas microgestão', 'Perto ok—independência fica', 'Estável no importante; não desistes de ânimo leve'],
                strength: 'Calor que se toca—sem sufocar o ar de ninguém.',
                match_tip: 'Alguém que percebe o «quente um tempo, depois preciso de espaço».'
            }
        },
        EFOA: {
            zh: {
                name: '春风旅人型',
                subtitle: 'Come live with me and be my love.',
                traits: ['心里一热就说出口', '随性自由，日程表别太硬', '独立得很，并肩比占有更香', '爱冒险，最怕被拴成宠物'],
                strength: '让关系变成共同出走，也共同呼吸。',
                match_tip: '爱玩、不爱笼子的人——并肩走，别互相拴。'
            },
            tw: {
                name: '春風旅人型',
                subtitle: 'Come live with me and be my love.',
                traits: ['心裡一熱就說出口', '隨性自由，日程表別太硬', '獨立得很，並肩比佔有更香', '愛冒險，最怕被拴成寵物'],
                strength: '讓關係變成共同出走，也共同呼吸。',
                match_tip: '愛玩、不愛籠子的人——並肩走，別互相拴。'
            },
            en: {
                name: 'Spring Traveler',
                subtitle: 'Come live with me and be my love.',
                traits: ['Heat hits the chest, words come out', 'Easy freedom; rigid schedules kill the vibe', 'Very independent; side-by-side beats owning', 'Adventure-hungry; hate being kept like a pet'],
                strength: 'You turn a bond into shared leaving—and shared breathing room.',
                match_tip: 'Someone playful who hates cages—walk beside, don’t tie each other down.'
            },
            pt: {
                name: 'Viajante da Primavera',
                subtitle: 'Come live with me and be my love.',
                traits: ['O peito aquece e a boca fala', 'Liberdade solta; agenda rígida mata o ritmo', 'Muito independente; lado a lado > possuir', 'Ama aventura; odeia ser tratado/a como animal de estimação'],
                strength: 'Transformas a ligação em partida partilhada—e ar partilhado.',
                match_tip: 'Alguém brincalhão que odeia gaiolas—lado a lado, sem se amarrar.'
            }
        },
        ISCP: {
            zh: {
                name: '静谧港湾型',
                subtitle: 'Peace comes dropping slow.',
                traits: ['慢热，开口少，心意真', '日子沉、有序，不爱起哄', '渴望深度靠近，而非热闹凑合', '态度稳健，宁可静也不闹'],
                strength: '用安静的陪伴让人落地。',
                match_tip: '有耐心读你沉默、也敢轻轻邀你聊聊的人。'
            },
            tw: {
                name: '靜謐港灣型',
                subtitle: 'Peace comes dropping slow.',
                traits: ['慢熱，開口少，心意真', '日子沉、有序，不愛起哄', '渴望深度靠近，而非熱鬧湊合', '態度穩健，寧可靜也不鬧'],
                strength: '用安靜的陪伴讓人落地。',
                match_tip: '有耐心讀你沉默、也敢輕輕邀你聊聊的人。'
            },
            en: {
                name: 'Quiet Harbor',
                subtitle: 'Peace comes dropping slow.',
                traits: ['Slow to warm; sparse speech; real intent', 'Settled, ordered days; dislike hype', 'Crave deep closeness, not noisy almost-love', 'Steady; rather quiet than dramatic'],
                strength: 'Quiet presence that helps people land.',
                match_tip: 'Someone patient with your silence—and soft enough to invite a real talk.'
            },
            pt: {
                name: 'Porto Sereno',
                subtitle: 'Peace comes dropping slow.',
                traits: ['Aquece lento; fala pouco; intenção verdadeira', 'Dias assentes e ordenados; detestas alarido', 'Desejas proximidade profunda, não quase-amor barulhento', 'Estável; preferes silêncio a drama'],
                strength: 'Presença quieta que faz aterrar.',
                match_tip: 'Alguém paciente com o teu silêncio—e suave a convidar uma conversa real.'
            }
        },
        ISCA: {
            zh: {
                name: '内秀构建型',
                subtitle: 'I dwell in Possibility.',
                traits: ['含蓄，但每句都落得住', '做事有章法，关系也想盖得牢', '重视亲密，也肯一起慢慢长大', '对变化开放，却不慌不抢'],
                strength: '把关系盖成可以长期住的地方。',
                match_tip: '愿慢慢走进你，也愿意带你看见新风景的人。'
            },
            tw: {
                name: '內秀構建型',
                subtitle: 'I dwell in Possibility.',
                traits: ['含蓄，但每句都落得住', '做事有章法，關係也想蓋得牢', '重視親密，也肯一起慢慢長大', '對變化開放，卻不慌不搶'],
                strength: '把關係蓋成可以長期住的地方。',
                match_tip: '願慢慢走進你，也願意帶你看見新風景的人。'
            },
            en: {
                name: 'Quiet Builder',
                subtitle: 'I dwell in Possibility.',
                traits: ['Reserved, but every line lands', 'Method in what you do; you want the bond built solid', 'Value intimacy; willing to grow slowly together', 'Open to change—without rush or panic'],
                strength: 'You build a bond like a place meant to be lived in.',
                match_tip: 'Someone who enters slowly—and will show you new views too.'
            },
            pt: {
                name: 'Construtor/a Discreto/a',
                subtitle: 'I dwell in Possibility.',
                traits: ['Reservado/a, mas cada frase pousa', 'Método no que fazes; queres a ligação bem feita', 'Valorizas intimidade; queres crescer a par, sem pressa', 'Aberto/a à mudança—sem corrida nem pânico'],
                strength: 'Constróis a ligação como um sítio para habitar.',
                match_tip: 'Alguém que entra com calma—e também te mostra novas vistas.'
            }
        },
        IFCP: {
            zh: {
                name: '温柔守望型',
                subtitle: 'O my Luve\'s like a red, red rose.',
                traits: ['细腻内敛，感受比话多', '生活松着走，不赶场', '渴望被靠近、被确认', '大事上偏保守，怕伤到人'],
                strength: '用柔软接住情绪，让对方敢卸下防备。',
                match_tip: '稳定且会主动确认关系的人——别让你一直猜。'
            },
            tw: {
                name: '溫柔守望型',
                subtitle: 'O my Luve\'s like a red, red rose.',
                traits: ['細膩內斂，感受比話多', '生活鬆著走，不趕場', '渴望被靠近、被確認', '大事上偏保守，怕傷到人'],
                strength: '用柔軟接住情緒，讓對方敢卸下防備。',
                match_tip: '穩定且會主動確認關係的人——別讓你一直猜。'
            },
            en: {
                name: 'Gentle Watcher',
                subtitle: 'O my Luve\'s like a red, red rose.',
                traits: ['Subtle; you feel more than you say', 'Relaxed days; no rush', 'Want to be approached and named', 'Cautious on big stakes; hate wounding anyone'],
                strength: 'You catch feelings softly—so someone can drop their armor.',
                match_tip: 'Someone steady who confirms the bond—so you don’t guess forever.'
            },
            pt: {
                name: 'Vigia Gentil',
                subtitle: 'O my Luve\'s like a red, red rose.',
                traits: ['Sutil; sentes mais do que falas', 'Dias relaxados; sem pressa', 'Queres ser aproximado/a e nomeado/a', 'Cauteloso/a no importante; odeias ferir'],
                strength: 'Acolhes emoções com suavidade—para o outro baixar a guarda.',
                match_tip: 'Alguém estável que confirma a ligação—para não adivinhares sempre.'
            }
        },
        IFCA: {
            zh: {
                name: '诗意栖居型',
                subtitle: 'If music be the food of love, play on.',
                traits: ['内敛细腻，捕捉微小温度', '随性，不爱非黑即白', '重视亲密氛围多过表象热闹', '心态开放，留得下转弯'],
                strength: '把日常过出可回味的层次。',
                match_tip: '懂氛围、不催促的人——一起慢慢展开。'
            },
            tw: {
                name: '詩意棲居型',
                subtitle: 'If music be the food of love, play on.',
                traits: ['內斂細膩，捕捉微小溫度', '隨性，不愛非黑即白', '重視親密氛圍多過表象熱鬧', '心態開放，留得下轉彎'],
                strength: '把日常過出可回味的層次。',
                match_tip: '懂氛圍、不催促的人——一起慢慢展開。'
            },
            en: {
                name: 'Poetic Dweller',
                subtitle: 'If music be the food of love, play on.',
                traits: ['Reserved and fine; catch small warmth', 'Easygoing; dislike black-and-white', 'Care about intimate atmosphere more than loud show', 'Open enough to allow a turn'],
                strength: 'You give ordinary days layers worth tasting again.',
                match_tip: 'Someone who gets the vibe and never rushes—unfolding together, slowly.'
            },
            pt: {
                name: 'Habitante Poético/a',
                subtitle: 'If music be the food of love, play on.',
                traits: ['Reservado/a e fino/a; captas calor miúdo', 'Descontraído/a; detestas preto e branco', 'Valorizas a atmosfera íntima mais do que o espetáculo', 'Aberto/a o bastante para uma curva'],
                strength: 'Dás ao quotidiano camadas que se saboreiam outra vez.',
                match_tip: 'Alguém que percebe o ambiente e não pressiona—desenrolar juntos, sem pressa.'
            }
        },
        ISOP: {
            zh: {
                name: '沉思者型',
                subtitle: 'The heart has its reasons.',
                traits: ['情感内敛，厌恶轻飘的喜欢', '生活有序，心思也要排齐', '边界清晰，靠近需要理由', '宁可慢，不可悔'],
                strength: '清醒地靠近，少一些冲动留下的伤。',
                match_tip: '尊重你思考时间、不逼表态的人。'
            },
            tw: {
                name: '沉思者型',
                subtitle: 'The heart has its reasons.',
                traits: ['情感內斂，厭惡輕飄的喜歡', '生活有序，心思也要排齊', '邊界清晰，靠近需要理由', '寧可慢，不可悔'],
                strength: '清醒地靠近，少一些衝動留下的傷。',
                match_tip: '尊重你思考時間、不逼表態的人。'
            },
            en: {
                name: 'Contemplative',
                subtitle: 'The heart has its reasons.',
                traits: ['Reserved; dislike weightless liking', 'Ordered life; thoughts want lining up too', 'Clear boundaries; closeness needs a reason', 'Rather slow than sorry'],
                strength: 'You come close awake—fewer wounds left by impulse.',
                match_tip: 'Someone who respects thinking time and won’t force a label.'
            },
            pt: {
                name: 'Contemplativo/a',
                subtitle: 'The heart has its reasons.',
                traits: ['Reservado/a; detestas gostar leve demais', 'Vida ordenada; a mente também quer alinhar', 'Limites claros; aproximar precisa de razão', 'Preferes lento a arrependido'],
                strength: 'Aproximas-te acordado/a—menos feridas por impulso.',
                match_tip: 'Alguém que respeita o tempo de pensar e não força uma definição.'
            }
        },
        ISOA: {
            zh: {
                name: '孤岛哲人型',
                subtitle: 'The mind is its own place.',
                traits: ['话少，落下来却重', '守着有秩序的自我世界', '自主感很强，容不下被填满', '对人生开放，对交付仍谨慎'],
                strength: '自我完整，不靠关系填空——靠近才更真。',
                match_tip: '同样完整、能并肩谈世界的人。'
            },
            tw: {
                name: '孤島哲人型',
                subtitle: 'The mind is its own place.',
                traits: ['話少，落下來卻重', '守著有秩序的自我世界', '自主感很強，容不下被填滿', '對人生開放，對交付仍謹慎'],
                strength: '自我完整，不靠關係填空——靠近才更真。',
                match_tip: '同樣完整、能並肩談世界的人。'
            },
            en: {
                name: 'Island Sage',
                subtitle: 'The mind is its own place.',
                traits: ['Few words—heavy when they land', 'You keep an ordered inner world', 'Autonomy runs deep; hate being filled in', 'Open to life—still careful what you hand over'],
                strength: 'Whole in yourself—not filling voids with romance; closeness gets truer.',
                match_tip: 'Someone equally whole—who can talk about the world beside you.'
            },
            pt: {
                name: 'Sábio/a da Ilha',
                subtitle: 'The mind is its own place.',
                traits: ['Poucas palavras—pesadas quando caem', 'Guardas um mundo interior ordenado', 'Autonomia forte; não queres ser preenchido/a', 'Aberto/a à vida—ainda cuidadoso/a no que entregas'],
                strength: 'Inteiro/a em ti—não enchendo o vazio com romance; a proximidade fica mais verdadeira.',
                match_tip: 'Alguém igualmente inteiro—com quem falar do mundo lado a lado.'
            }
        },
        IFOP: {
            zh: {
                name: '花园隐士型',
                subtitle: 'I wandered lonely as a cloud.',
                traits: ['不抢声量，也不急着被看见', '随性呼吸，按自己的节奏活', '独立，却并非冷漠', '稳健，珍惜真正被接住的瞬间'],
                strength: '不打扰别人，也不愿被廉价黏合。',
                match_tip: '轻声靠近、愿认真谈谈的人——不侵入，也不假装看不见你。'
            },
            tw: {
                name: '花園隱士型',
                subtitle: 'I wandered lonely as a cloud.',
                traits: ['不搶聲量，也不急著被看見', '隨性呼吸，按自己的節奏活', '獨立，卻並非冷漠', '穩健，珍惜真正被接住的瞬間'],
                strength: '不打擾別人，也不願被廉價黏合。',
                match_tip: '輕聲靠近、願認真談談的人——不侵入，也不假裝看不見你。'
            },
            en: {
                name: 'Garden Hermit',
                subtitle: 'I wandered lonely as a cloud.',
                traits: ['Don’t fight for volume; not eager to be seen', 'Breathe easy; live at your own pace', 'Independent, not cold', 'Steady; treasure moments of being truly met'],
                strength: 'You don’t crowd others—and refuse cheap glue.',
                match_tip: 'Someone who approaches softly and will talk for real—won’t invade, won’t pretend not to see you.'
            },
            pt: {
                name: 'Eremita do Jardim',
                subtitle: 'I wandered lonely as a cloud.',
                traits: ['Não disputas volume; não tens pressa de ser visto/a', 'Respiras solto; vives ao teu ritmo', 'Independente, não frio/a', 'Estável; valorizas o instante de seres realmente acolhido/a'],
                strength: 'Não invades os outros—e recusas cola barata.',
                match_tip: 'Alguém que se aproxima em voz baixa e fala a sério—não invade, não finge não te ver.'
            }
        },
        IFOA: {
            zh: {
                name: '星尘游吟型',
                subtitle: 'A thing of beauty is a joy for ever.',
                traits: ['感受深，开口却不急', '走走停停，生活随性', '独立完整，不靠黏连证明存在', '开放冒险，却怕一厢情愿的重量'],
                strength: '给关系留下想象与呼吸，也留下可以说清楚的缝隙。',
                match_tip: '不强迫黏连、愿一起出走、也敢把心里话说开的人。'
            },
            tw: {
                name: '星塵遊吟型',
                subtitle: 'A thing of beauty is a joy for ever.',
                traits: ['感受深，開口卻不急', '走走停停，生活隨性', '獨立完整，不靠黏連證明存在', '開放冒險，卻怕一廂情願的重量'],
                strength: '給關係留下想像與呼吸，也留下可以說清楚的縫隙。',
                match_tip: '不強迫黏連、願一起出走、也敢把心裡話說開的人。'
            },
            en: {
                name: 'Stardust Bard',
                subtitle: 'A thing of beauty is a joy for ever.',
                traits: ['Feel deep; no rush to speak', 'Stop and go; easy life', 'Independent and whole—clinginess isn’t proof you exist', 'Open to adventure—wary of one-sided weight'],
                strength: 'You leave imagination and breath in love—and a gap where words can land.',
                match_tip: 'Someone who won’t force clinginess, will wander with you—and dares to open what’s inside.'
            },
            pt: {
                name: 'Bardo/a do Pó Estelar',
                subtitle: 'A thing of beauty is a joy for ever.',
                traits: ['Sentes fundo; sem pressa de falar', 'Para e segue; vida solta', 'Independente e inteiro/a—apego não prova que existes', 'Aberto/a à aventura—cauteloso/a com peso unilateral'],
                strength: 'Deixas imaginação e ar na relação—e uma fenda onde as palavras pousam.',
                match_tip: 'Alguém que não força apego, sai contigo—e ousa abrir o que vai por dentro.'
            }
        }
    };

    function pickLang(map) {
        if (!map) return null;
        var lang = window.CM_LANG || 'zh';
        return map[lang] || map.zh || null;
    }

    function dimText(meta, key) {
        if (!meta || !meta[key]) return '';
        return meta[key][window.CM_LANG] || meta[key].zh || '';
    }

    /** 轴两端：左=low（低分极），右=high（高分极），与 score 填充方向一致 */
    var LP_AXIS = {
        expression: ['I', 'E'],
        rhythm: ['F', 'S'],
        boundary: ['O', 'C'],
        risk: ['A', 'P']
    };

    function escLp(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    /** 某维两端文案：{ low:{letter,label}, high:{letter,label} } */
    window.lovePersonalityDimPoles = function (key) {
        var meta = LP_DIMS[key];
        var pair = LP_AXIS[key];
        if (!meta || !pair) return null;
        return {
            low: { letter: pair[0], label: dimText(meta, pair[0]) },
            high: { letter: pair[1], label: dimText(meta, pair[1]) }
        };
    };

    /** 四字母图例行：维名 + 两极（含字母） */
    window.lovePersonalityLetterLines = function () {
        var lang = window.CM_LANG || 'zh';
        var sep = (lang === 'en' || lang === 'pt') ? ': ' : '：';
        var order = [
            ['expression', 'E', 'I'],
            ['rhythm', 'S', 'F'],
            ['boundary', 'C', 'O'],
            ['risk', 'P', 'A']
        ];
        return order.map(function (item) {
            var meta = LP_DIMS[item[0]];
            var label = dimText(meta, 'label');
            var a = item[1] + ' ' + dimText(meta, item[1]);
            var b = item[2] + ' ' + dimText(meta, item[2]);
            return label + sep + a + ' / ' + b;
        });
    };

    /** 结果卡维度条：两端极点 + 中间进度（score 朝 high） */
    window.renderLovePersonalityBars = function (container, dims) {
        if (!container) return;
        container.innerHTML = '';
        if (!dims) return;
        ['expression', 'rhythm', 'boundary', 'risk'].forEach(function (key) {
            var d = dims[key];
            if (!d) return;
            var poles = window.lovePersonalityDimPoles(key);
            if (!poles) return;
            var pct = Math.max(0, Math.min(100, d.score || 0));
            var label = d.label || dimText(LP_DIMS[key], 'label') || key;
            var letter = d.letter || '';
            var lowActive = letter === poles.low.letter;
            var highActive = letter === poles.high.letter;
            var lowTxt = poles.low.letter + ' · ' + poles.low.label;
            var highTxt = poles.high.letter + ' · ' + poles.high.label;
            var row = document.createElement('div');
            row.className = 'personality-bar-row';
            row.innerHTML =
                '<span class="personality-bar-label">' + escLp(label) + '</span>'
                + '<div class="personality-bar-axis">'
                + '<span class="personality-bar-pole personality-bar-low'
                + (lowActive ? ' is-active' : '') + '">' + escLp(lowTxt) + '</span>'
                + '<div class="personality-bar-track" role="meter" aria-valuenow="' + pct
                + '" aria-valuemin="0" aria-valuemax="100" aria-label="'
                + escLp(label + ': ' + lowTxt + ' — ' + highTxt) + '">'
                + '<div class="personality-bar-fill" style="width:' + pct + '%"></div>'
                + '</div>'
                + '<span class="personality-bar-pole personality-bar-high'
                + (highActive ? ' is-active' : '') + '">' + escLp(highTxt) + '</span>'
                + '</div>';
            container.appendChild(row);
        });
    };

    /** 填充结果卡上的「四字母怎么读」折叠说明 */
    window.fillLovePersonalityLetterGuide = function (root) {
        if (!root) return;
        var summary = root.querySelector('summary');
        var hint = root.querySelector('.lp-letter-guide-hint');
        var list = root.querySelector('.lp-letter-guide-list');
        if (summary && typeof window.t === 'function') {
            summary.textContent = window.t('lp.lettersTitle');
        }
        if (hint && typeof window.t === 'function') {
            hint.textContent = window.t('lp.lettersHint');
        }
        if (list) {
            list.innerHTML = '';
            window.lovePersonalityLetterLines().forEach(function (line) {
                var li = document.createElement('li');
                li.textContent = line;
                list.appendChild(li);
            });
        }
    };

    window.localizeLovePersonality = function (p) {
        if (!p) return p;
        var code = p.code || p.type;
        var pack = code && LP_TYPES[code] ? pickLang(LP_TYPES[code]) : null;
        var out = {};
        for (var k in p) {
            if (Object.prototype.hasOwnProperty.call(p, k)) out[k] = p[k];
        }
        if (pack) {
            out.name = pack.name;
            out.label = pack.name;
            out.subtitle = pack.subtitle;
            out.summary = pack.subtitle;
            out.traits = pack.traits.slice();
            out.strength = pack.strength;
            out.match_tip = pack.match_tip;
        }
        var dims = p.dimensions || {};
        var nd = {};
        ['expression', 'rhythm', 'boundary', 'risk'].forEach(function (key) {
            var d = dims[key];
            if (!d) return;
            var meta = LP_DIMS[key];
            var letter = d.letter;
            var copy = {};
            for (var dk in d) {
                if (Object.prototype.hasOwnProperty.call(d, dk)) copy[dk] = d[dk];
            }
            if (meta) {
                copy.label = (meta.label && (meta.label[window.CM_LANG] || meta.label.zh)) || copy.label;
                if (letter && meta[letter]) {
                    copy.pole = meta[letter][window.CM_LANG] || meta[letter].zh || copy.pole;
                }
            }
            nd[key] = copy;
        });
        if (Object.keys(nd).length) out.dimensions = nd;
        out.disclaimer = (typeof window.t === 'function' ? window.t('lp.disc') : out.disclaimer);
        return out;
    };

    window.lovePersonalityShareText = function (m) {
        var base = String(window.CM_PUBLIC_URL || '').trim()
            || ((typeof location !== 'undefined' && location.origin) ? location.origin : '');
        /* 文案里的链接也不要带本机/裸 IP */
        if (!base || /localhost|127\.0\.0\.1/i.test(base)
            || /\b\d{1,3}(?:\.\d{1,3}){3}\b/.test(base)) {
            base = 'https://campusmatch.com.cn';
        }
        var url = base.replace(/\/$/, '') + '/?from=lp_share';
        var inv = String(window.CM_INVITE_CODE || '').trim().toUpperCase();
        if (inv) url += '&invite=' + encodeURIComponent(inv);
        var body;
        if (typeof window.tf === 'function') {
            body = window.tf('lp.shareBody', {
                name: m.name || '',
                code: m.code || m.type || '',
                subtitle: m.subtitle || m.summary || '',
                url: url
            });
        } else {
            body = 'CampusMatch · ' + (m.name || '') + ' (' + (m.code || '') + ')\n' + url;
        }
        if (inv && typeof window.t === 'function') {
            body += '\n' + window.t('lp.inviteLine').replace('{code}', inv);
        }
        return body;
    };
})();
