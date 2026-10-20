LETRAS = ("A", "B", "C", "D")


# ==========================================================
# LANGUAGES
# ==========================================================
# Everything that changes between the EN and PT versions:
# OCR language, question database, interface text and prompt.
# ==========================================================

IDIOMAS = {
    "en": {
        "nome": "English",
        "ocr": "eng",
        "csv": "perguntas_respostas_en.csv",
        "textos": {
            "pergunta": "Question:",
            "resposta": "Answer:",
            "fixar": "Pin Window",
            "pesquisar": "Search",
            "pesquisando": "Searching...",
            "sem_texto": "No text detected.",
            "fonte_banco": "Source: local database",
            "fonte_ia": "Source: Gemini (saved to database)",
            "fonte_ia_nao_validada": "Source: Gemini (could not match an option, not saved)",
            "sem_chave": "Question not in database and GEMINI_API_KEY is not set.",
            "erro_ia": "Gemini error: {erro}",
            "selo_banco": "✓ database · {tempo} s",
            "selo_ia": "AI · suggestion · {tempo} s",
            "aba_inicio": "Home",
            "aba_banco": "Database",
            "aba_ajustes": "Settings",
            "status_vigiando": "Watching · Rise of Kingdoms found",
            "status_aguardando": "Waiting for the game",
            "status_outra_tela": "Game open · not on a question screen",
            "sem_pergunta": "No question yet. Open a Lyceum of Wisdom exam.",
            "sem_resposta_fora": "Not in the database",
            "sem_resposta_opcoes": "Database answer is not among the options: {resposta}",
            "stat_banco": "in database",
            "stat_aprendidas": "learned this session",
            "stat_acertos": "right this session",
            "marcar_no_jogo": "Mark the answer in the game",
            "usar_ia": "Use AI when the answer is unknown",
            "busca": "Search question or answer…",
            "filtro_todas": "All",
            "filtro_aprendidas": "Learned",
            "filtro_corrigidas": "Corrected",
            "filtro_nao_confirmadas": "Not confirmed",
            "item_confirmada": "✓ confirmed by the game",
            "item_corrigida": "⟲ corrected by the game (was \"{antiga}\")",
            "item_base": "original database · not confirmed yet",
            "exportar": "Export confirmed",
            "importar": "Import CSV",
            "desfazer": "Undo last correction",
            "exportadas": "{n} questions exported",
            "importadas": "{n} questions imported",
            "nada_a_desfazer": "No correction to undo",
            "desfeita": "Undone: {pergunta} → {resposta}",
            "idioma": "Language",
            "opacidade": "Outline opacity",
            "fixar_topo": "Keep this window on top",
            "iniciar_sistema": "Start with the system",
            "calibrar": "Calibrate areas…",
            "calibrar_ajuda": "Drag a rectangle around the question and the four options.",
            "calibrar_padrao": "Restore default",
            "calibrar_sem_jogo": "Open the game on a question screen to calibrate.",
            "mostrar": "Show",
            "sair": "Quit",
        },
        "prompt": (
            "This is a multiple-choice question from the Lyceum of Wisdom event "
            "in Rise of Kingdoms (game lore and world history). The text was read "
            "with OCR and may contain small errors.\n\n"
            "Question: {pergunta}\n{opcoes}\n\n"
            "Reply with only the letter of the correct option: A, B, C or D."
        ),
    },
    "pt": {
        "nome": "Português",
        "ocr": "por",
        "csv": "perguntas_respostas_pt.csv",
        "textos": {
            "pergunta": "Pergunta:",
            "resposta": "Resposta:",
            "fixar": "Fixar Janela",
            "pesquisar": "Pesquisar",
            "pesquisando": "Pesquisando...",
            "sem_texto": "Nenhum texto detectado.",
            "fonte_banco": "Fonte: banco local",
            "fonte_ia": "Fonte: Gemini (salvo no banco)",
            "fonte_ia_nao_validada": "Fonte: Gemini (não bateu com nenhuma opção, não salvo)",
            "sem_chave": "Pergunta fora do banco e GEMINI_API_KEY não está definida.",
            "erro_ia": "Erro no Gemini: {erro}",
            "selo_banco": "✓ banco · {tempo} s",
            "selo_ia": "IA · sugestão · {tempo} s",
            "aba_inicio": "Início",
            "aba_banco": "Banco",
            "aba_ajustes": "Ajustes",
            "status_vigiando": "Vigiando · Rise of Kingdoms encontrado",
            "status_aguardando": "Aguardando o jogo",
            "status_outra_tela": "Jogo aberto · fora da tela de perguntas",
            "sem_pergunta": "Nenhuma pergunta ainda. Abra um exame do Liceu da Sabedoria.",
            "sem_resposta_fora": "Fora do banco",
            "sem_resposta_opcoes": "A resposta do banco não está entre as opções: {resposta}",
            "stat_banco": "no banco",
            "stat_aprendidas": "aprendidas na sessão",
            "stat_acertos": "acertos na sessão",
            "marcar_no_jogo": "Marcar a resposta no jogo",
            "usar_ia": "Usar IA se não souber",
            "busca": "Buscar pergunta ou resposta…",
            "filtro_todas": "Todas",
            "filtro_aprendidas": "Aprendidas",
            "filtro_corrigidas": "Corrigidas",
            "filtro_nao_confirmadas": "Não confirmadas",
            "item_confirmada": "✓ confirmada pelo jogo",
            "item_corrigida": "⟲ corrigida pelo jogo (era \"{antiga}\")",
            "item_base": "banco original · ainda não confirmada",
            "exportar": "Exportar confirmadas",
            "importar": "Importar CSV",
            "desfazer": "Desfazer última correção",
            "exportadas": "{n} perguntas exportadas",
            "importadas": "{n} perguntas importadas",
            "nada_a_desfazer": "Nenhuma correção para desfazer",
            "desfeita": "Desfeito: {pergunta} → {resposta}",
            "idioma": "Idioma",
            "opacidade": "Opacidade do contorno",
            "fixar_topo": "Manter esta janela no topo",
            "iniciar_sistema": "Iniciar com o sistema",
            "calibrar": "Calibrar áreas…",
            "calibrar_ajuda": "Arraste um retângulo em volta da pergunta e das quatro opções.",
            "calibrar_padrao": "Restaurar padrão",
            "calibrar_sem_jogo": "Abra o jogo numa tela de perguntas para calibrar.",
            "mostrar": "Mostrar",
            "sair": "Sair",
        },
        "prompt": (
            "Esta é uma pergunta de múltipla escolha do evento Liceu da Sabedoria "
            "do Rise of Kingdoms (história do jogo e história mundial). O texto foi "
            "lido com OCR e pode conter pequenos erros.\n\n"
            "Pergunta: {pergunta}\n{opcoes}\n\n"
            "Responda apenas com a letra da opção correta: A, B, C ou D."
        ),
    },
}
