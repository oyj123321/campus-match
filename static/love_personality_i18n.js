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
                subtitle: '你想要一个可以依靠的肩膀，而不是一场冒险的旅程',
                traits: ['用行动把在乎落到实处', '关系里愿意靠近、也期待被接住', '更看重长期承诺而非一时激情'],
                strength: '稳定付出，让对方感到「有人在」。',
                match_tip: '感性、愿意回应你的人——能接住你的认真，也给你一点仪式感。'
            },
            tw: {
                name: '守護者型',
                subtitle: '你想要一個可以依靠的肩膀，而不是一場冒險的旅程',
                traits: ['用行動把在乎落到實處', '關係裡願意靠近、也期待被接住', '更看重長期承諾而非一時激情'],
                strength: '穩定付出，讓對方感到「有人在」。',
                match_tip: '感性、願意回應你的人——能接住你的認真，也給你一點儀式感。'
            },
            en: {
                name: 'Guardian',
                subtitle: 'You want a shoulder to lean on—not just another adventure',
                traits: ['You show care through actions', 'You want closeness—and to be met halfway', 'You value lasting commitment over short sparks'],
                strength: 'Steady devotion that makes someone feel they are not alone.',
                match_tip: 'Someone warm and responsive—who meets your seriousness and adds a little romance.'
            },
            pt: {
                name: 'Guardião/ã',
                subtitle: 'Queres um ombro em quem te apoiar—não só mais uma aventura',
                traits: ['Mostras carinho com gestos', 'Queres proximidade—e ser correspondido/a', 'Valorizas compromisso duradouro mais do que faíscas'],
                strength: 'Dedicação estável que faz a outra pessoa sentir que não está sozinha.',
                match_tip: 'Alguém sensível e responsivo—que acolhe a tua seriedade e traz um pouco de ritual.'
            }
        },
        ESCA: {
            zh: {
                name: '开明领航型',
                subtitle: '认真经营关系，也愿意一起看见更大的世界',
                traits: ['表达直接，推进感强', '生活有节奏，但不死板', '对未来持开放态度'],
                strength: '能把关系带向清晰方向，同时留出探索空间。',
                match_tip: '独立又愿意同行的人——既跟得上你的节奏，也不怕新计划。'
            },
            tw: {
                name: '開明領航型',
                subtitle: '認真經營關係，也願意一起看見更大的世界',
                traits: ['表達直接，推進感強', '生活有節奏，但不死板', '對未來持開放態度'],
                strength: '能把關係帶向清晰方向，同時留出探索空間。',
                match_tip: '獨立又願意同行的人——既跟得上你的節奏，也不怕新計劃。'
            },
            en: {
                name: 'Open Navigator',
                subtitle: 'You take relationships seriously—and still want to see more of the world together',
                traits: ['Direct communication, strong forward energy', 'A steady pace without rigidity', 'Open-minded about the future'],
                strength: 'You steer the bond with clarity while leaving room to explore.',
                match_tip: 'Someone independent who still walks with you—keeps your pace and isn’t afraid of new plans.'
            },
            pt: {
                name: 'Navegador/a Aberto/a',
                subtitle: 'Levas a relação a sério—e ainda queres ver o mundo juntos',
                traits: ['Comunicação direta, energia de avanço', 'Ritmo estável sem rigidez', 'Mente aberta quanto ao futuro'],
                strength: 'Dás direção clara à relação e deixas espaço para explorar.',
                match_tip: 'Alguém independente que caminha contigo—acompanha o teu ritmo e não teme novos planos.'
            }
        },
        EFCP: {
            zh: {
                name: '阳光筑巢型',
                subtitle: '松弛地靠近，认真地成家',
                traits: ['情感外放，气氛感强', '日常随性，讨厌过度规矩', '对承诺偏稳健'],
                strength: '让关系轻松有温度，又不失长期感。',
                match_tip: '能一起玩、也谈得拢以后的人——别太闷，也别太飘。'
            },
            tw: {
                name: '陽光築巢型',
                subtitle: '鬆弛地靠近，認真地成家',
                traits: ['情感外放，氣氛感強', '日常隨性，討厭過度規矩', '對承諾偏穩健'],
                strength: '讓關係輕鬆有溫度，又不失長期感。',
                match_tip: '能一起玩、也談得攏以後的人——別太悶，也別太飄。'
            },
            en: {
                name: 'Sunny Nest-builder',
                subtitle: 'You come close with ease—and still mean it about building a home',
                traits: ['Emotionally open, great atmosphere', 'Casual day-to-day; dislike over-rules', 'Steady about commitment'],
                strength: 'You keep love light and warm without losing the long view.',
                match_tip: 'Someone fun who can also talk about the future—not too dull, not too flaky.'
            },
            pt: {
                name: 'Construtor/a Solar',
                subtitle: 'Aproximas-te com leveza—e falas a sério em construir um ninho',
                traits: ['Emocionalmente aberto/a, ótimo ambiente', 'Dia a dia descontraído; detestas excesso de regras', 'Compromisso estável'],
                strength: 'Manténs a relação leve e quente sem perder o longo prazo.',
                match_tip: 'Alguém divertido que também fala do futuro—nem demasiado sério, nem demasiado volátil.'
            }
        },
        EFCA: {
            zh: {
                name: '浪漫牧者型',
                subtitle: '热烈、自由，想把喜欢过成一场旅途',
                traits: ['表达热烈', '生活灵活多变', '亲密与冒险可以并存'],
                strength: '点燃日常，把相处变成值得回忆的体验。',
                match_tip: '同样外放、敢尝试的人——别用过度管束浇灭热情。'
            },
            tw: {
                name: '浪漫牧者型',
                subtitle: '熱烈、自由，想把喜歡過成一場旅途',
                traits: ['表達熱烈', '生活靈活多變', '親密與冒險可以並存'],
                strength: '點燃日常，把相處變成值得回憶的體驗。',
                match_tip: '同樣外放、敢嘗試的人——別用過度管束澆滅熱情。'
            },
            en: {
                name: 'Romantic Shepherd',
                subtitle: 'Warm, free—you want liking someone to feel like a journey',
                traits: ['Passionate expression', 'Flexible, ever-changing days', 'Closeness and adventure can coexist'],
                strength: 'You light up ordinary days into memories worth keeping.',
                match_tip: 'Someone equally open and game—don’t smother the spark with control.'
            },
            pt: {
                name: 'Pastor/a Romântico/a',
                subtitle: 'Intenso/a e livre—queres que gostar de alguém seja uma viagem',
                traits: ['Expressão apaixonada', 'Dias flexíveis e mutáveis', 'Intimidade e aventura podem coexistir'],
                strength: 'Acendes o quotidiano e transformas o convívio em memórias.',
                match_tip: 'Alguém igualmente aberto e aventureiro—não apagues a chama com controlo excessivo.'
            }
        },
        ESOP: {
            zh: {
                name: '灯塔型',
                subtitle: '给你稳定的光，也保留自己的岸',
                traits: ['表达清晰', '生活有序', '需要个人空间与清晰边界'],
                strength: '靠谱且边界清楚，减少消耗型纠缠。',
                match_tip: '尊重你节奏的人——靠近时认真，分开时也不焦虑。'
            },
            tw: {
                name: '燈塔型',
                subtitle: '給你穩定的光，也保留自己的岸',
                traits: ['表達清晰', '生活有序', '需要個人空間與清晰邊界'],
                strength: '靠譜且邊界清楚，減少消耗型糾纏。',
                match_tip: '尊重你節奏的人——靠近時認真，分開時也不焦慮。'
            },
            en: {
                name: 'Lighthouse',
                subtitle: 'Steady light for someone else—while keeping your own shore',
                traits: ['Clear communication', 'Ordered daily life', 'Need space and clear boundaries'],
                strength: 'Reliable and boundaried—less draining entanglement.',
                match_tip: 'Someone who respects your pace—present when close, calm when apart.'
            },
            pt: {
                name: 'Farol',
                subtitle: 'Luz estável para outrem—e a tua própria margem intacta',
                traits: ['Comunicação clara', 'Vida quotidiana ordenada', 'Precisas de espaço e limites claros'],
                strength: 'Confiável e com limites—menos relações desgastantes.',
                match_tip: 'Alguém que respeita o teu ritmo—presente na proximidade, calmo na distância.'
            }
        },
        ESOA: {
            zh: {
                name: '自由先驱型',
                subtitle: '热烈地喜欢，也热烈地做自己',
                traits: ['情感外放', '秩序感偏强', '独立、开放、不喜欢被绑死'],
                strength: '带动气氛，同时守住自我。',
                match_tip: '同样独立的人——并肩而非吞并。'
            },
            tw: {
                name: '自由先驅型',
                subtitle: '熱烈地喜歡，也熱烈地做自己',
                traits: ['情感外放', '秩序感偏強', '獨立、開放、不喜歡被綁死'],
                strength: '帶動氣氛，同時守住自我。',
                match_tip: '同樣獨立的人——並肩而非吞併。'
            },
            en: {
                name: 'Free Pioneer',
                subtitle: 'You love fiercely—and stay fiercely yourself',
                traits: ['Emotionally open', 'Prefer some structure', 'Independent, open, hate being tied down'],
                strength: 'You lift the mood while holding your own center.',
                match_tip: 'Someone equally independent—side by side, not swallowed whole.'
            },
            pt: {
                name: 'Pioneiro/a Livre',
                subtitle: 'Gostas com intensidade—e és intensamente tu',
                traits: ['Emocionalmente aberto/a', 'Preferes alguma estrutura', 'Independente, aberto/a, detestas amarras'],
                strength: 'Elevas o ambiente e manténs o teu centro.',
                match_tip: 'Alguém igualmente independente—lado a lado, não absorvido/a.'
            }
        },
        EFOP: {
            zh: {
                name: '热心管家型',
                subtitle: '对喜欢的人很热络，生活随性，边界也在',
                traits: ['表达外放', '日常不拘小节', '亲近里保留独立', '对大事偏稳'],
                strength: '热情但不黏到窒息。',
                match_tip: '能接受你「热一阵、也要自己空间」的人。'
            },
            tw: {
                name: '熱心管家型',
                subtitle: '對喜歡的人很熱絡，生活隨性，邊界也在',
                traits: ['表達外放', '日常不拘小節', '親近裡保留獨立', '對大事偏穩'],
                strength: '熱情但不黏到窒息。',
                match_tip: '能接受你「熱一陣、也要自己空間」的人。'
            },
            en: {
                name: 'Warm Host',
                subtitle: 'Warm with people you like, easygoing day-to-day—with boundaries intact',
                traits: ['Open expression', 'Casual about small stuff', 'Close yet independent', 'Steady on big decisions'],
                strength: 'Warm without becoming smothering.',
                match_tip: 'Someone okay with your “hot for a while, then need space” rhythm.'
            },
            pt: {
                name: 'Anfitrião/ã Afetuoso/a',
                subtitle: 'Caloroso/a com quem gostas, descontraído/a no dia a dia—com limites',
                traits: ['Expressão aberta', 'Pouco formal no quotidiano', 'Próximo/a mas independente', 'Estável nas grandes decisões'],
                strength: 'Calor sem sufocar.',
                match_tip: 'Alguém que aceita o teu ritmo de «perto um tempo, depois espaço».'
            }
        },
        EFOA: {
            zh: {
                name: '春风旅人型',
                subtitle: '走到哪，喜欢就燃到哪',
                traits: ['表达热烈', '随性自由', '独立自主', '开放冒险'],
                strength: '把关系变成共同探险。',
                match_tip: '爱玩、不爱束缚的人——一起走，而不是互相拴。'
            },
            tw: {
                name: '春風旅人型',
                subtitle: '走到哪，喜歡就燃到哪',
                traits: ['表達熱烈', '隨性自由', '獨立自主', '開放冒險'],
                strength: '把關係變成共同探險。',
                match_tip: '愛玩、不愛束縛的人——一起走，而不是互相拴。'
            },
            en: {
                name: 'Spring Traveler',
                subtitle: 'Wherever you go, liking someone lights up along the way',
                traits: ['Passionate expression', 'Easygoing freedom', 'Independence', 'Open to adventure'],
                strength: 'You turn a relationship into a shared expedition.',
                match_tip: 'Someone playful who hates cages—walk together, don’t leash each other.'
            },
            pt: {
                name: 'Viajante da Primavera',
                subtitle: 'Onde fores, o gostar acende-se pelo caminho',
                traits: ['Expressão apaixonada', 'Liberdade descontraída', 'Independência', 'Aberto/a à aventura'],
                strength: 'Transformas a relação numa expedição partilhada.',
                match_tip: 'Alguém brincalhão que odeia amarras—caminhem juntos, não se amarrem.'
            }
        },
        ISCP: {
            zh: {
                name: '静谧港湾型',
                subtitle: '不吵不闹，却想把安全感给你',
                traits: ['情感含蓄', '生活有序', '渴望深度融合', '态度稳健'],
                strength: '深度陪伴，让人安静下来。',
                match_tip: '温柔有耐心的人——读得懂你的慢热。'
            },
            tw: {
                name: '靜謐港灣型',
                subtitle: '不吵不鬧，卻想把安全感給你',
                traits: ['情感含蓄', '生活有序', '渴望深度融合', '態度穩健'],
                strength: '深度陪伴，讓人安靜下來。',
                match_tip: '溫柔有耐心的人——讀得懂你的慢熱。'
            },
            en: {
                name: 'Quiet Harbor',
                subtitle: 'Not loud—but you want to give someone real safety',
                traits: ['Reserved emotion', 'Ordered life', 'Crave deep closeness', 'Steady attitude'],
                strength: 'Deep presence that helps people settle.',
                match_tip: 'Someone gentle and patient—who can read your slow warm-up.'
            },
            pt: {
                name: 'Porto Sereno',
                subtitle: 'Sem barulho—mas queres dar segurança a alguém',
                traits: ['Emoção reservada', 'Vida ordenada', 'Desejas fusão profunda', 'Atitude estável'],
                strength: 'Presença profunda que acalma.',
                match_tip: 'Alguém gentil e paciente—que entende o teu aquecimento lento.'
            }
        },
        ISCA: {
            zh: {
                name: '内秀构建型',
                subtitle: '内心认真，向外慢慢打开世界',
                traits: ['含蓄但真心', '做事有章法', '重视亲密', '对变化开放'],
                strength: '把关系盖成可长期住的结构。',
                match_tip: '愿意慢慢走进你世界、也带你看新风景的人。'
            },
            tw: {
                name: '內秀構建型',
                subtitle: '內心認真，向外慢慢打開世界',
                traits: ['含蓄但真心', '做事有章法', '重視親密', '對變化開放'],
                strength: '把關係蓋成可長期住的結構。',
                match_tip: '願意慢慢走進你世界、也帶你看新風景的人。'
            },
            en: {
                name: 'Quiet Builder',
                subtitle: 'Serious inside—opening the world outward, slowly',
                traits: ['Reserved but sincere', 'Methodical', 'Value intimacy', 'Open to change'],
                strength: 'You build a relationship like a home meant to last.',
                match_tip: 'Someone who enters your world slowly—and also shows you new views.'
            },
            pt: {
                name: 'Construtor/a Discreto/a',
                subtitle: 'Sério/a por dentro—abrindo o mundo para fora, aos poucos',
                traits: ['Reservado/a mas sincero/a', 'Metódico/a', 'Valorizas intimidade', 'Aberto/a à mudança'],
                strength: 'Constróis a relação como uma casa para durar.',
                match_tip: 'Alguém que entra no teu mundo com calma—e também te mostra novas vistas.'
            }
        },
        IFCP: {
            zh: {
                name: '温柔守望型',
                subtitle: '柔软、随性，却把承诺放在心里',
                traits: ['情感细腻内敛', '生活松弛', '渴望靠近', '大事上偏保守'],
                strength: '用柔软接住对方的情绪。',
                match_tip: '稳定且会主动确认关系的人——别让你一直猜。'
            },
            tw: {
                name: '溫柔守望型',
                subtitle: '柔軟、隨性，卻把承諾放在心裡',
                traits: ['情感細膩內斂', '生活鬆弛', '渴望靠近', '大事上偏保守'],
                strength: '用柔軟接住對方的情緒。',
                match_tip: '穩定且會主動確認關係的人——別讓你一直猜。'
            },
            en: {
                name: 'Gentle Watcher',
                subtitle: 'Soft and easygoing—yet commitment lives quietly in your heart',
                traits: ['Subtle, reserved feelings', 'Relaxed days', 'Want closeness', 'Cautious on big stakes'],
                strength: 'You catch someone’s feelings with softness.',
                match_tip: 'Someone steady who names the relationship—so you don’t have to guess forever.'
            },
            pt: {
                name: 'Vigia Gentil',
                subtitle: 'Suave e descontraído/a—mas o compromisso vive no coração',
                traits: ['Sentimentos finos e reservados', 'Dias relaxados', 'Queres proximidade', 'Cauteloso/a nas grandes coisas'],
                strength: 'Acolhes as emoções do outro com suavidade.',
                match_tip: 'Alguém estável que confirma a relação—para não ficares sempre a adivinhar.'
            }
        },
        IFCA: {
            zh: {
                name: '诗意栖居型',
                subtitle: '安静地感受，开放地生活',
                traits: ['内敛细腻', '随性', '重视亲密氛围', '心态开放'],
                strength: '把日常过出一点诗意。',
                match_tip: '懂氛围、不催促的人——一起慢慢展开。'
            },
            tw: {
                name: '詩意棲居型',
                subtitle: '安靜地感受，開放地生活',
                traits: ['內斂細膩', '隨性', '重視親密氛圍', '心態開放'],
                strength: '把日常過出一點詩意。',
                match_tip: '懂氛圍、不催促的人——一起慢慢展開。'
            },
            en: {
                name: 'Poetic Dweller',
                subtitle: 'Feel quietly; live with an open heart',
                traits: ['Reserved and nuanced', 'Easygoing', 'Care about intimate atmosphere', 'Open mindset'],
                strength: 'You give ordinary days a touch of poetry.',
                match_tip: 'Someone who gets the vibe and never rushes—unfolding together, slowly.'
            },
            pt: {
                name: 'Habitante Poético/a',
                subtitle: 'Sentes em silêncio; vives de coração aberto',
                traits: ['Reservado/a e subtil', 'Descontraído/a', 'Valorizas a atmosfera íntima', 'Mente aberta'],
                strength: 'Dás um pouco de poesia ao quotidiano.',
                match_tip: 'Alguém que percebe o ambiente e não pressiona—desenrolar juntos, sem pressa.'
            }
        },
        ISOP: {
            zh: {
                name: '沉思者型',
                subtitle: '先想清楚，再决定要不要靠近',
                traits: ['情感内敛', '生活有序', '边界清晰', '态度稳健'],
                strength: '理性清醒，减少冲动伤害。',
                match_tip: '尊重思考时间、不逼表态的人。'
            },
            tw: {
                name: '沉思者型',
                subtitle: '先想清楚，再決定要不要靠近',
                traits: ['情感內斂', '生活有序', '邊界清晰', '態度穩健'],
                strength: '理性清醒，減少衝動傷害。',
                match_tip: '尊重思考時間、不逼表態的人。'
            },
            en: {
                name: 'Contemplative',
                subtitle: 'Think it through before you decide to get closer',
                traits: ['Reserved emotion', 'Ordered life', 'Clear boundaries', 'Steady attitude'],
                strength: 'Clear-headed—fewer impulsive wounds.',
                match_tip: 'Someone who respects your thinking time and doesn’t force a label.'
            },
            pt: {
                name: 'Contemplativo/a',
                subtitle: 'Pensas bem antes de decidir aproximar-te',
                traits: ['Emoção reservada', 'Vida ordenada', 'Limites claros', 'Atitude estável'],
                strength: 'Mente clara—menos feridas por impulso.',
                match_tip: 'Alguém que respeita o teu tempo de pensar e não força uma definição.'
            }
        },
        ISOA: {
            zh: {
                name: '孤岛哲人型',
                subtitle: '独立是底色，开放是选择',
                traits: ['含蓄', '有秩序', '很需要自主', '对人生持开放态度'],
                strength: '自我完整，不靠关系填空。',
                match_tip: '同样完整、能并肩讨论世界的人。'
            },
            tw: {
                name: '孤島哲人型',
                subtitle: '獨立是底色，開放是選擇',
                traits: ['含蓄', '有秩序', '很需要自主', '對人生持開放態度'],
                strength: '自我完整，不靠關係填空。',
                match_tip: '同樣完整、能並肩討論世界的人。'
            },
            en: {
                name: 'Island Sage',
                subtitle: 'Independence is your base coat; openness is a choice',
                traits: ['Reserved', 'Ordered', 'Strong need for autonomy', 'Open toward life'],
                strength: 'Whole in yourself—not filling voids with romance.',
                match_tip: 'Someone equally whole—who can talk about the world beside you.'
            },
            pt: {
                name: 'Sábio/a da Ilha',
                subtitle: 'A independência é a base; a abertura é uma escolha',
                traits: ['Reservado/a', 'Ordenado/a', 'Forte necessidade de autonomia', 'Aberto/a à vida'],
                strength: 'Inteiro/a em ti—não enchendo o vazio com romance.',
                match_tip: 'Alguém igualmente inteiro—com quem discutir o mundo lado a lado.'
            }
        },
        IFOP: {
            zh: {
                name: '花园隐士型',
                subtitle: '有自己的小世界，也守着一份踏实',
                traits: ['内敛', '随性', '独立', '稳健'],
                strength: '不打扰别人，也不愿被过度打扰。',
                match_tip: '轻声靠近、不侵入你节奏的人。'
            },
            tw: {
                name: '花園隱士型',
                subtitle: '有自己的小世界，也守著一份踏實',
                traits: ['內斂', '隨性', '獨立', '穩健'],
                strength: '不打擾別人，也不願被過度打擾。',
                match_tip: '輕聲靠近、不侵入你節奏的人。'
            },
            en: {
                name: 'Garden Hermit',
                subtitle: 'You keep a small world of your own—and a quiet steadiness',
                traits: ['Reserved', 'Easygoing', 'Independent', 'Steady'],
                strength: 'You don’t crowd others—and don’t want to be crowded.',
                match_tip: 'Someone who approaches softly and never invades your rhythm.'
            },
            pt: {
                name: 'Eremita do Jardim',
                subtitle: 'Tens o teu pequeno mundo—e uma firmeza quieta',
                traits: ['Reservado/a', 'Descontraído/a', 'Independente', 'Estável'],
                strength: 'Não incomodas os outros—e não queres ser invadido/a.',
                match_tip: 'Alguém que se aproxima em voz baixa e não invade o teu ritmo.'
            }
        },
        IFOA: {
            zh: {
                name: '星尘游吟型',
                subtitle: '安静，自由，心里装着远方',
                traits: ['情感内敛', '生活随性', '独立', '开放冒险'],
                strength: '给关系留下想象与呼吸。',
                match_tip: '不强迫黏连、愿一起出走的人。'
            },
            tw: {
                name: '星塵遊吟型',
                subtitle: '安靜，自由，心裡裝著遠方',
                traits: ['情感內斂', '生活隨性', '獨立', '開放冒險'],
                strength: '給關係留下想像與呼吸。',
                match_tip: '不強迫黏連、願一起出走的人。'
            },
            en: {
                name: 'Stardust Bard',
                subtitle: 'Quiet, free—with faraway places in your heart',
                traits: ['Reserved emotion', 'Easygoing life', 'Independent', 'Open to adventure'],
                strength: 'You leave room for imagination and breathing space in love.',
                match_tip: 'Someone who won’t force clinginess—and will wander with you.'
            },
            pt: {
                name: 'Bardo/a do Pó Estelar',
                subtitle: 'Quieto/a, livre—com lugares distantes no coração',
                traits: ['Emoção reservada', 'Vida descontraída', 'Independente', 'Aberto/a à aventura'],
                strength: 'Deixas imaginação e respiração na relação.',
                match_tip: 'Alguém que não força apegos—e sai contigo pelo mundo.'
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
