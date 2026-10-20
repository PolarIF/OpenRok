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
