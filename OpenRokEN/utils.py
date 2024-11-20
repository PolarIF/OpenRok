import pandas as pd

def load_csv_data(csv_file):
    # Carrega o banco de dados CSV
    return pd.read_csv(csv_file)

def find_answer(question, data):
    # Busca a resposta para a pergunta no banco de dados.
    row = data[data["pergunta"].str.contains(question, case=False, na=False)]
    if not row.empty:
        return row["resposta"].values[0]
    return "Resposta não encontrada"