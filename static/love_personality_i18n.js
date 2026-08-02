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
    var LP_TYPES = {
        ESCP: {
            zh: {
                name: '守护者型',
                subtitle: '靠近不是冲动，是愿意把在乎说清楚、放长久',
                traits: ['喜欢用行动证明「我在」', '愿意走进关系，也渴望被认真接住', '宁可慢一点谈明白，也不想轻轻带过'],
                strength: '把稳定变成可感知的安全感，让对方不必猜。',
                match_tip: '会回应你的认真、也敢把喜欢说出口的人。'
            },
            tw: {
                name: '守護者型',
                subtitle: '靠近不是衝動，是願意把在乎說清楚、放長久',
                traits: ['喜歡用行動證明「我在」', '願意走進關係，也渴望被認真接住', '寧可慢一點談明白，也不想輕輕帶過'],
                strength: '把穩定變成可感知的安全感，讓對方不必猜。',
                match_tip: '會回應你的認真、也敢把喜歡說出口的人。'
            },
            en: {
                name: 'Guardian',
                subtitle: 'Closeness isn’t impulse—it’s choosing to name care, and keep it',
                traits: ['You prove “I’m here” through actions', 'You step into love—and hope to be met seriously', 'You’d rather talk it through slowly than brush it past'],
                strength: 'You turn steadiness into felt safety—so they don’t have to guess.',
                match_tip: 'Someone who answers your seriousness—and dares to say liking out loud.'
            },
            pt: {
                name: 'Guardião/ã',
                subtitle: 'Aproximar não é impulso—é escolher nomear o cuidado e mantê-lo',
                traits: ['Provas “estou aqui” com gestos', 'Entras na relação—e queres ser acolhido/a a sério', 'Preferes esclarecer com calma a passar por cima'],
                strength: 'Transformas estabilidade em segurança sentida—sem adivinhações.',
                match_tip: 'Alguém que responde à tua seriedade—e ousa dizer o gostar em voz alta.'
            }
        },
        ESCA: {
            zh: {
                name: '开明领航型',
                subtitle: '一边把关系经营清楚，一边邀请对方看见更远的风景',
                traits: ['表达直接，不爱绕弯', '日子有节奏，却留得下意外', '对未来开放，也肯并肩商量'],
                strength: '给方向，也给余地——让靠近变成一起长大。',
                match_tip: '独立却肯同行的人：跟得上你，也不怕新的一页。'
            },
            tw: {
                name: '開明領航型',
                subtitle: '一邊把關係經營清楚，一邊邀請對方看見更遠的風景',
                traits: ['表達直接，不愛繞彎', '日子有節奏，卻留得下意外', '對未來開放，也肯並肩商量'],
                strength: '給方向，也給餘地——讓靠近變成一起長大。',
                match_tip: '獨立卻肯同行的人：跟得上你，也不怕新的一頁。'
            },
            en: {
                name: 'Open Navigator',
                subtitle: 'You clear the path of a relationship—and invite someone farther out',
                traits: ['Direct words, little circling', 'A paced life that still allows surprise', 'Open to the future, ready to plan side by side'],
                strength: 'You offer direction and room—so closeness becomes growing together.',
                match_tip: 'Someone independent who still walks with you—keeps pace, unafraid of a new page.'
            },
            pt: {
                name: 'Navegador/a Aberto/a',
                subtitle: 'Clarificas a relação—e convidas alguém a ver mais longe',
                traits: ['Palavras diretas, pouco rodeio', 'Ritmo no dia a dia com espaço para o acaso', 'Aberto/a ao futuro, disposto/a a planear a par'],
                strength: 'Dás direção e margem—para a proximidade ser crescer juntos.',
                match_tip: 'Alguém independente que caminha contigo—acompanha o ritmo e não teme uma página nova.'
            }
        },
        EFCP: {
            zh: {
                name: '阳光筑巢型',
                subtitle: '轻松地靠近，却把「以后」放在心上',
                traits: ['情感外放，能把气氛焐热', '日常随性，讨厌被规矩拴住', '承诺这件事，你偏稳健'],
                strength: '让相处像日光：暖、松，却看得见明天。',
                match_tip: '能一起玩、也肯谈以后的人——别太闷，也别太飘。'
            },
            tw: {
                name: '陽光築巢型',
                subtitle: '輕鬆地靠近，卻把「以後」放在心上',
                traits: ['情感外放，能把氣氛焐熱', '日常隨性，討厭被規矩拴住', '承諾這件事，你偏穩健'],
                strength: '讓相處像日光：暖、鬆，卻看得見明天。',
                match_tip: '能一起玩、也肯談以後的人——別太悶，也別太飄。'
            },
            en: {
                name: 'Sunny Nest-builder',
                subtitle: 'You come close lightly—yet keep “later” in your heart',
                traits: ['Emotionally open; you warm a room', 'Casual days; hate being tied by rules', 'Steady when it comes to commitment'],
                strength: 'Love like daylight: warm, easy—and tomorrow is still in view.',
                match_tip: 'Someone fun who will also talk about later—not too dull, not too flaky.'
            },
            pt: {
                name: 'Construtor/a Solar',
                subtitle: 'Aproximas-te com leveza—e guardas o «depois» no coração',
                traits: ['Emocionalmente aberto/a; aqueces o ambiente', 'Dia a dia descontraído; detestas regras que prendem', 'Estável quanto ao compromisso'],
                strength: 'Convívio como luz do dia: quente, leve—e o amanhã ainda se vê.',
                match_tip: 'Alguém divertido que também fala do depois—nem demasiado sério, nem volátil.'
            }
        },
        EFCA: {
            zh: {
                name: '浪漫牧者型',
                subtitle: '热烈可以自由，喜欢值得被过成一段路',
                traits: ['表达热烈，藏不住喜欢', '生活灵活，讨厌一成不变', '亲密与出走，可以同时发生'],
                strength: '把平凡日子点燃成记得住的瞬间。',
                match_tip: '同样敢靠近、敢尝试的人——别用管束浇灭火花。'
            },
            tw: {
                name: '浪漫牧者型',
                subtitle: '熱烈可以自由，喜歡值得被過成一段路',
                traits: ['表達熱烈，藏不住喜歡', '生活靈活，討厭一成不變', '親密與出走，可以同時發生'],
                strength: '把平凡日子點燃成記得住的瞬間。',
                match_tip: '同樣敢靠近、敢嘗試的人——別用管束澆滅火花。'
            },
            en: {
                name: 'Romantic Shepherd',
                subtitle: 'Passion can stay free—liking someone deserves to become a stretch of road',
                traits: ['Warm expression; hard to hide liking', 'Flexible days; dislike sameness', 'Closeness and getting out can happen together'],
                strength: 'You light ordinary days into moments worth keeping.',
                match_tip: 'Someone equally brave to come close and try—don’t smother the spark with control.'
            },
            pt: {
                name: 'Pastor/a Romântico/a',
                subtitle: 'A intensidade pode ser livre—gostar merece virar um troço de estrada',
                traits: ['Expressão quente; o gostar não se esconde', 'Dias flexíveis; detestas a monotonia', 'Intimidade e sair pelo mundo podem coexistir'],
                strength: 'Acendes o quotidiano em momentos que ficam.',
                match_tip: 'Alguém igualmente corajoso a aproximar-se e tentar—não apagues a chama com controlo.'
            }
        },
        ESOP: {
            zh: {
                name: '灯塔型',
                subtitle: '愿意照亮你，也守着自己的岸',
                traits: ['表达清晰，少猜忌', '生活有序，心里有谱', '亲近里仍要边界与呼吸'],
                strength: '靠谱而不吞没——靠近有光，分开也不慌。',
                match_tip: '尊重你节奏的人：认真靠近，也能安静各自站立。'
            },
            tw: {
                name: '燈塔型',
                subtitle: '願意照亮你，也守著自己的岸',
                traits: ['表達清晰，少猜忌', '生活有序，心裡有譜', '親近裡仍要邊界與呼吸'],
                strength: '靠譜而不吞沒——靠近有光，分開也不慌。',
                match_tip: '尊重你節奏的人：認真靠近，也能安靜各自站立。'
            },
            en: {
                name: 'Lighthouse',
                subtitle: 'Willing to cast light—while keeping your own shore',
                traits: ['Clear words, little suspicion', 'Ordered days, an inner map', 'Even in closeness you need edge and breath'],
                strength: 'Reliable without swallowing anyone—close with light, apart without panic.',
                match_tip: 'Someone who respects your pace: present when near, calm standing alone.'
            },
            pt: {
                name: 'Farol',
                subtitle: 'Disposto/a a iluminar—e a guardar a tua própria margem',
                traits: ['Palavras claras, pouca suspeita', 'Dias ordenados, mapa interior', 'Na proximidade ainda precisas de limite e ar'],
                strength: 'Confiável sem absorver—perto com luz, longe sem pânico.',
                match_tip: 'Alguém que respeita o teu ritmo: presente ao perto, calmo sozinho.'
            }
        },
        ESOA: {
            zh: {
                name: '自由先驱型',
                subtitle: '热烈地喜欢，也热烈地做完整的自己',
                traits: ['情感外放，带动场', '秩序感在，却拒绝被绑死', '独立开放，并肩比占有更吸引你'],
                strength: '把热情变成同行，而不是吞并。',
                match_tip: '同样完整的人——一起走，而不是互相消融。'
            },
            tw: {
                name: '自由先驅型',
                subtitle: '熱烈地喜歡，也熱烈地做完整的自己',
                traits: ['情感外放，帶動場', '秩序感在，卻拒絕被綁死', '獨立開放，並肩比佔有更吸引你'],
                strength: '把熱情變成同行，而不是吞併。',
                match_tip: '同樣完整的人——一起走，而不是互相消融。'
            },
            en: {
                name: 'Free Pioneer',
                subtitle: 'You like fiercely—and stay fiercely whole',
                traits: ['Open emotion; you lift a room', 'Some order—yet refuse to be tied down', 'Independent and open; walking beside beats owning'],
                strength: 'You turn heat into companionship, not absorption.',
                match_tip: 'Someone equally whole—walk together, don’t dissolve into each other.'
            },
            pt: {
                name: 'Pioneiro/a Livre',
                subtitle: 'Gostas com intensidade—e permaneces inteiro/a',
                traits: ['Emoção aberta; elevas o ambiente', 'Há ordem—mas recusas amarras', 'Independente e aberto/a; lado a lado vale mais do que possuir'],
                strength: 'Transformas calor em companhia, não em absorção.',
                match_tip: 'Alguém igualmente inteiro—caminhem juntos, sem se dissolver.'
            }
        },
        EFOP: {
            zh: {
                name: '热心管家型',
                subtitle: '对在乎的人很热络，也留得下自己的空',
                traits: ['表达外放，热情来得快', '日常不拘小节', '亲近里仍保有独立', '大事上偏稳，不轻易甩手'],
                strength: '热情可感，却不黏到窒息。',
                match_tip: '懂你热一阵、也要自己空间的人。'
            },
            tw: {
                name: '熱心管家型',
                subtitle: '對在乎的人很熱絡，也留得下自己的空',
                traits: ['表達外放，熱情來得快', '日常不拘小節', '親近裡仍保有獨立', '大事上偏穩，不輕易甩手'],
                strength: '熱情可感，卻不黏到窒息。',
                match_tip: '懂你熱一陣、也要自己空間的人。'
            },
            en: {
                name: 'Warm Host',
                subtitle: 'Warm with who you care for—and still leave yourself room',
                traits: ['Open expression; warmth arrives fast', 'Casual about small stuff', 'Close, yet keep independence', 'Steady on big things; don’t walk away lightly'],
                strength: 'Warmth you can feel—without smothering.',
                match_tip: 'Someone who gets your “close for a while, then need space” rhythm.'
            },
            pt: {
                name: 'Anfitrião/ã Afetuoso/a',
                subtitle: 'Caloroso/a com quem te importa—e ainda deixas espaço para ti',
                traits: ['Expressão aberta; o calor chega depressa', 'Pouco formal no quotidiano', 'Próximo/a, mas independente', 'Estável no importante; não desistes de ânimo leve'],
                strength: 'Calor que se sente—sem sufocar.',
                match_tip: 'Alguém que entende o teu «perto um tempo, depois espaço».'
            }
        },
        EFOA: {
            zh: {
                name: '春风旅人型',
                subtitle: '喜欢燃到哪儿，脚步就跟到哪儿',
                traits: ['表达热烈', '随性自由', '独立自主', '开放冒险，怕被拴住'],
                strength: '把关系变成共同的出走与呼吸。',
                match_tip: '爱玩、不爱束缚的人——并肩，而不是互相拴。'
            },
            tw: {
                name: '春風旅人型',
                subtitle: '喜歡燃到哪兒，腳步就跟到哪兒',
                traits: ['表達熱烈', '隨性自由', '獨立自主', '開放冒險，怕被拴住'],
                strength: '把關係變成共同的出走與呼吸。',
                match_tip: '愛玩、不愛束縛的人——並肩，而不是互相拴。'
            },
            en: {
                name: 'Spring Traveler',
                subtitle: 'Wherever liking lights up, your feet follow',
                traits: ['Passionate expression', 'Easy freedom', 'Independence', 'Open to adventure; hate being leashed'],
                strength: 'You turn a bond into shared leaving and breathing room.',
                match_tip: 'Someone playful who hates cages—side by side, not tied together.'
            },
            pt: {
                name: 'Viajante da Primavera',
                subtitle: 'Onde o gostar acende, os pés seguem',
                traits: ['Expressão apaixonada', 'Liberdade descontraída', 'Independência', 'Aberto/a à aventura; detestas amarras'],
                strength: 'Transformas a ligação em partida partilhada e respiração.',
                match_tip: 'Alguém brincalhão que odeia gaiolas—lado a lado, sem se amarrar.'
            }
        },
        ISCP: {
            zh: {
                name: '静谧港湾型',
                subtitle: '话不多，却想把安稳悄悄递到你手里',
                traits: ['情感含蓄，慢热却真', '生活有序，心里沉', '渴望深度靠近', '态度稳健，不爱闹'],
                strength: '用安静的陪伴让人落地。',
                match_tip: '有耐心读你沉默、也敢邀你聊聊的人。'
            },
            tw: {
                name: '靜謐港灣型',
                subtitle: '話不多，卻想把安穩悄悄遞到你手裡',
                traits: ['情感含蓄，慢熱卻真', '生活有序，心裡沉', '渴望深度靠近', '態度穩健，不愛鬧'],
                strength: '用安靜的陪伴讓人落地。',
                match_tip: '有耐心讀你沉默、也敢邀你聊聊的人。'
            },
            en: {
                name: 'Quiet Harbor',
                subtitle: 'Few words—yet you want to place steadiness quietly in someone’s hands',
                traits: ['Reserved; slow to warm, sincere', 'Ordered days, a settled heart', 'Crave deep closeness', 'Steady; dislike drama'],
                strength: 'Quiet presence that helps people land.',
                match_tip: 'Someone patient with your silence—and brave enough to invite a real talk.'
            },
            pt: {
                name: 'Porto Sereno',
                subtitle: 'Poucas palavras—mas queres pôr sossego, em silêncio, nas mãos de alguém',
                traits: ['Reservado/a; aquece lento, sincero/a', 'Dias ordenados, coração assente', 'Desejas proximidade profunda', 'Estável; detestas drama'],
                strength: 'Presença quieta que faz aterrar.',
                match_tip: 'Alguém paciente com o teu silêncio—e corajoso a convidar uma conversa real.'
            }
        },
        ISCA: {
            zh: {
                name: '内秀构建型',
                subtitle: '内心认真，向外慢慢打开世界',
                traits: ['含蓄但句句真心', '做事有章法', '重视亲密，也肯一起长大', '对变化开放，不慌'],
                strength: '把关系盖成可以长期住的地方。',
                match_tip: '愿慢慢走进你，也带你看见新风景的人。'
            },
            tw: {
                name: '內秀構建型',
                subtitle: '內心認真，向外慢慢打開世界',
                traits: ['含蓄但句句真心', '做事有章法', '重視親密，也肯一起長大', '對變化開放，不慌'],
                strength: '把關係蓋成可以長期住的地方。',
                match_tip: '願慢慢走進你，也帶你看見新風景的人。'
            },
            en: {
                name: 'Quiet Builder',
                subtitle: 'Serious inside—opening the world outward, slowly',
                traits: ['Reserved, every line sincere', 'Method in how you move', 'Value intimacy; willing to grow together', 'Open to change without panic'],
                strength: 'You build a bond like a place meant to be lived in.',
                match_tip: 'Someone who enters slowly—and also shows you new views.'
            },
            pt: {
                name: 'Construtor/a Discreto/a',
                subtitle: 'Sério/a por dentro—abrindo o mundo para fora, aos poucos',
                traits: ['Reservado/a, cada frase sincera', 'Método no que fazes', 'Valorizas intimidade; queres crescer a par', 'Aberto/a à mudança sem pânico'],
                strength: 'Constróis a ligação como um sítio para habitar.',
                match_tip: 'Alguém que entra com calma—e também te mostra novas vistas.'
            }
        },
        IFCP: {
            zh: {
                name: '温柔守望型',
                subtitle: '柔软随性，却把承诺藏在心里最稳的地方',
                traits: ['细腻内敛，感受很深', '生活松弛，不赶场', '渴望被靠近、被确认', '大事上偏保守，怕伤人'],
                strength: '用柔软接住情绪，让对方敢卸下防备。',
                match_tip: '稳定且会主动确认关系的人——别让你一直猜。'
            },
            tw: {
                name: '溫柔守望型',
                subtitle: '柔軟隨性，卻把承諾藏在心裡最穩的地方',
                traits: ['細膩內斂，感受很深', '生活鬆弛，不趕場', '渴望被靠近、被確認', '大事上偏保守，怕傷人'],
                strength: '用柔軟接住情緒，讓對方敢卸下防備。',
                match_tip: '穩定且會主動確認關係的人——別讓你一直猜。'
            },
            en: {
                name: 'Gentle Watcher',
                subtitle: 'Soft and easy—yet commitment sits in the steadiest place in you',
                traits: ['Subtle, deep feeler', 'Relaxed days; no rush', 'Want to be approached and named', 'Cautious on big stakes; hate wounding'],
                strength: 'You catch feelings softly—so someone can drop their armor.',
                match_tip: 'Someone steady who confirms the bond—so you don’t guess forever.'
            },
            pt: {
                name: 'Vigia Gentil',
                subtitle: 'Suave e solto/a—mas o compromisso mora no sítio mais firme em ti',
                traits: ['Sutil, sente fundo', 'Dias relaxados; sem pressa', 'Queres ser aproximado/a e nomeado/a', 'Cauteloso/a no importante; odeias ferir'],
                strength: 'Acolhes emoções com suavidade—para o outro baixar a guarda.',
                match_tip: 'Alguém estável que confirma a ligação—para não adivinhares sempre.'
            }
        },
        IFCA: {
            zh: {
                name: '诗意栖居型',
                subtitle: '安静地感受，开放地生活；苦过之后，仍信余韵',
                traits: ['内敛细腻，捕捉微小温度', '随性，不爱非黑即白', '重视亲密氛围', '心态开放，留得下转弯'],
                strength: '把日常过出可回味的层次。',
                match_tip: '懂氛围、不催促的人——一起慢慢展开。'
            },
            tw: {
                name: '詩意棲居型',
                subtitle: '安靜地感受，開放地生活；苦過之後，仍信餘韻',
                traits: ['內斂細膩，捕捉微小溫度', '隨性，不愛非黑即白', '重視親密氛圍', '心態開放，留得下轉彎'],
                strength: '把日常過出可回味的層次。',
                match_tip: '懂氛圍、不催促的人——一起慢慢展開。'
            },
            en: {
                name: 'Poetic Dweller',
                subtitle: 'Feel quietly, live openly; after bitter seasons, still trust the aftertaste',
                traits: ['Reserved and fine; catch small warmth', 'Easygoing; dislike black-and-white', 'Care about intimate atmosphere', 'Open enough to allow a turn'],
                strength: 'You give ordinary days layers worth tasting again.',
                match_tip: 'Someone who gets the vibe and never rushes—unfolding together, slowly.'
            },
            pt: {
                name: 'Habitante Poético/a',
                subtitle: 'Sentes em silêncio, vives em aberto; depois do amargo, ainda crês no residual',
                traits: ['Reservado/a e fino/a; captas calor miúdo', 'Descontraído/a; detestas preto e branco', 'Valorizas a atmosfera íntima', 'Aberto/a o bastante para uma curva'],
                strength: 'Dás ao quotidiano camadas que se saboreiam outra vez.',
                match_tip: 'Alguém que percebe o ambiente e não pressiona—desenrolar juntos, sem pressa.'
            }
        },
        ISOP: {
            zh: {
                name: '沉思者型',
                subtitle: '先想清楚，再决定要不要把心递出去',
                traits: ['情感内敛，厌恶轻飘', '生活有序', '边界清晰', '态度稳健，宁可慢不可悔'],
                strength: '清醒地靠近，减少冲动的伤。',
                match_tip: '尊重你思考时间、不逼表态的人。'
            },
            tw: {
                name: '沉思者型',
                subtitle: '先想清楚，再決定要不要把心遞出去',
                traits: ['情感內斂，厭惡輕飄', '生活有序', '邊界清晰', '態度穩健，寧可慢不可悔'],
                strength: '清醒地靠近，減少衝動的傷。',
                match_tip: '尊重你思考時間、不逼表態的人。'
            },
            en: {
                name: 'Contemplative',
                subtitle: 'Think it clear before you hand your heart across',
                traits: ['Reserved; dislike weightless feelings', 'Ordered life', 'Clear boundaries', 'Steady; rather slow than sorry'],
                strength: 'You come close awake—fewer wounds from impulse.',
                match_tip: 'Someone who respects thinking time and won’t force a label.'
            },
            pt: {
                name: 'Contemplativo/a',
                subtitle: 'Pensas bem antes de passar o coração',
                traits: ['Reservado/a; detestas leveza vazia', 'Vida ordenada', 'Limites claros', 'Estável; preferes lento a arrependido'],
                strength: 'Aproximas-te acordado/a—menos feridas por impulso.',
                match_tip: 'Alguém que respeita o tempo de pensar e não força uma definição.'
            }
        },
        ISOA: {
            zh: {
                name: '孤岛哲人型',
                subtitle: '独立是底色；开放，是你选择后的邀请',
                traits: ['含蓄，话少但重', '有秩序的自我世界', '很需要自主', '对人生持开放，却不随便交付'],
                strength: '自我完整，不靠关系填空——靠近才更真。',
                match_tip: '同样完整、能并肩谈世界的人。'
            },
            tw: {
                name: '孤島哲人型',
                subtitle: '獨立是底色；開放，是你選擇後的邀請',
                traits: ['含蓄，話少但重', '有秩序的自我世界', '很需要自主', '對人生持開放，卻不隨便交付'],
                strength: '自我完整，不靠關係填空——靠近才更真。',
                match_tip: '同樣完整、能並肩談世界的人。'
            },
            en: {
                name: 'Island Sage',
                subtitle: 'Independence is the base coat; openness is an invitation you choose',
                traits: ['Reserved; few words, heavy ones', 'An ordered inner world', 'Strong need for autonomy', 'Open to life—yet careful what you hand over'],
                strength: 'Whole in yourself—not filling voids with romance; closeness gets truer.',
                match_tip: 'Someone equally whole—who can talk about the world beside you.'
            },
            pt: {
                name: 'Sábio/a da Ilha',
                subtitle: 'A independência é a base; a abertura é um convite que escolhes',
                traits: ['Reservado/a; poucas palavras, pesadas', 'Mundo interior ordenado', 'Forte necessidade de autonomia', 'Aberto/a à vida—mas cuidadoso/a no que entregas'],
                strength: 'Inteiro/a em ti—não enchendo o vazio com romance; a proximidade fica mais verdadeira.',
                match_tip: 'Alguém igualmente inteiro—com quem falar do mundo lado a lado.'
            }
        },
        IFOP: {
            zh: {
                name: '花园隐士型',
                subtitle: '守着自己的小世界，也守着一份不吵闹的踏实',
                traits: ['内敛，不抢声量', '随性，按自己的节奏呼吸', '独立，却并非冷漠', '稳健，珍惜真正被接住的瞬间'],
                strength: '不打扰别人，也不愿被廉价黏合。',
                match_tip: '轻声靠近、愿认真谈谈的人——不侵入，也不假装看不见你。'
            },
            tw: {
                name: '花園隱士型',
                subtitle: '守著自己的小世界，也守著一份不吵鬧的踏實',
                traits: ['內斂，不搶聲量', '隨性，按自己的節奏呼吸', '獨立，卻並非冷漠', '穩健，珍惜真正被接住的瞬間'],
                strength: '不打擾別人，也不願被廉價黏合。',
                match_tip: '輕聲靠近、願認真談談的人——不侵入，也不假裝看不見你。'
            },
            en: {
                name: 'Garden Hermit',
                subtitle: 'You keep a small world—and a quiet kind of steadiness',
                traits: ['Reserved; don’t fight for volume', 'Easygoing; breathe at your own pace', 'Independent, not cold', 'Steady; treasure moments of being truly met'],
                strength: 'You don’t crowd others—and refuse cheap glue.',
                match_tip: 'Someone who approaches softly and will talk for real—won’t invade, won’t pretend not to see you.'
            },
            pt: {
                name: 'Eremita do Jardim',
                subtitle: 'Guardas o teu pequeno mundo—e uma firmeza sem barulho',
                traits: ['Reservado/a; não disputas volume', 'Descontraído/a; respiras ao teu ritmo', 'Independente, não frio/a', 'Estável; valorizas o instante de seres realmente acolhido/a'],
                strength: 'Não invades os outros—e recusas cola barata.',
                match_tip: 'Alguém que se aproxima em voz baixa e fala a sério—não invade, não finge não te ver.'
            }
        },
        IFOA: {
            zh: {
                name: '星尘游吟型',
                subtitle: '安静自由，心里装着远方；也等一个愿并肩的灵魂',
                traits: ['情感内敛，长于感受', '生活随性，走走停停', '独立完整', '开放冒险，却怕一厢情愿的重量'],
                strength: '给关系留下想象与呼吸，也留下可以说清楚的缝隙。',
                match_tip: '不强迫黏连、愿一起出走、也敢把心里话说开的人。'
            },
            tw: {
                name: '星塵遊吟型',
                subtitle: '安靜自由，心裡裝著遠方；也等一個願並肩的靈魂',
                traits: ['情感內斂，長於感受', '生活隨性，走走停停', '獨立完整', '開放冒險，卻怕一廂情願的重量'],
                strength: '給關係留下想像與呼吸，也留下可以說清楚的縫隙。',
                match_tip: '不強迫黏連、願一起出走、也敢把心裡話說開的人。'
            },
            en: {
                name: 'Stardust Bard',
                subtitle: 'Quiet and free, far places in your chest—also waiting for a soul who’d walk beside',
                traits: ['Reserved; strong at feeling', 'Easy life; stop and go', 'Independent and whole', 'Open to adventure—wary of one-sided weight'],
                strength: 'You leave imagination and breath in love—and a gap where words can land.',
                match_tip: 'Someone who won’t force clinginess, will wander with you—and dares to open what’s inside.'
            },
            pt: {
                name: 'Bardo/a do Pó Estelar',
                subtitle: 'Quieto/a e livre, com o longe no peito—também à espera de uma alma que caminhe a par',
                traits: ['Reservado/a; forte a sentir', 'Vida solta; para e segue', 'Independente e inteiro/a', 'Aberto/a à aventura—cauteloso/a com peso unilateral'],
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
        var url = (typeof location !== 'undefined' && location.origin) ? location.origin : 'https://campusmatch.com.cn';
        if (typeof window.tf === 'function') {
            return window.tf('lp.shareBody', {
                name: m.name || '',
                code: m.code || m.type || '',
                subtitle: m.subtitle || m.summary || '',
                url: url
            });
        }
        return 'CampusMatch · ' + (m.name || '') + ' (' + (m.code || '') + ')\n' + url;
    };
})();
