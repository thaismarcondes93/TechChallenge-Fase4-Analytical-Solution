"""Configurações centrais do projeto.

Tudo o que é "decisão analítica" (cortes, dicionários de palavras, temas) fica aqui,
para que a equipe possa calibrar sem mexer na lógica dos scripts.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
ARQUIVO_PADRAO = DATA_RAW / "amazon.csv"

KAGGLE_DATASET = "karkavelrajaj/amazon-sales-dataset"

# --------------------------------------------------------------------------------------
# Cortes analíticos (calibrar depois de olhar as distribuições em outputs/figures)
# --------------------------------------------------------------------------------------
# Grupos de nota: "Baixa" = abaixo deste quantil; "Alta" = a partir do quantil alto.
RATING_BAIXO_Q = 0.25
RATING_ALTO_Q = 0.75
# Grupos de engajamento (rating_count): "Alto" >= quantil alto; "Baixo" <= quantil baixo.
ENGAJ_ALTO_Q = 0.75
ENGAJ_BAIXO_Q = 0.25

# Faixas de desconto (fração) e de preço original (moeda do dataset, rupias).
# Listas de limites INFERIORES; a última faixa é aberta.
FAIXAS_DESCONTO = [0.0, 0.2, 0.4, 0.6, 0.8]
ROTULOS_DESCONTO = ["1. 0-19%", "2. 20-39%", "3. 40-59%", "4. 60-79%", "5. 80% ou mais"]
FAIXAS_PRECO = [0, 500, 2000, 5000]
ROTULOS_PRECO = ["1. Até 500", "2. 500-1.999", "3. 2.000-4.999", "4. 5.000 ou mais"]
SEM_DADO = "0. Sem dado"

# Amostras mínimas para não tirar conclusão de grupo pequeno.
MIN_PRODUTOS_CATEGORIA = 10
MIN_PRODUTOS_CELULA = 5
MIN_MENCOES_TEMA = 20          # mínimo de menções (por grupo) para comentar o lift de um tema
MIN_PRODUTOS_GRUPO_TEXTO = 20  # mínimo de produtos em cada grupo de nota para a análise de texto

BOOTSTRAP_REPETICOES = 1000
SEMENTE = 42

# --------------------------------------------------------------------------------------
# Análise de texto (as reviews do dataset estão em inglês)
# --------------------------------------------------------------------------------------
PALAVRAS_POSITIVAS = {
    "great", "good", "excellent", "love", "loved", "perfect", "best", "worth", "value", "nice",
    "amazing", "fast", "easy", "sturdy", "durable", "recommend", "recommended", "happy",
    "satisfied", "awesome", "superb", "fantastic", "wonderful", "impressed", "smooth",
    "comfortable", "reliable", "useful", "helpful", "bright", "clear", "crisp",
}
PALAVRAS_NEGATIVAS = {
    "bad", "poor", "worst", "waste", "broke", "broken", "stopped", "defective", "fake",
    "disappointed", "disappointing", "useless", "issue", "issues", "problem", "problems",
    "fail", "failed", "failure", "slow", "faulty", "damaged", "refund", "refunded", "flimsy",
    "loose", "overheating", "heating", "terrible", "horrible", "worthless", "scam", "returned",
    "noisy", "laggy", "drains",
}

# Temas: nome -> radicais/trechos procurados no texto em minúsculas (contagem de ocorrências).
# Use radicais curtos de propósito (ex.: "charg" pega charger/charging), mas evite trechos que
# apareçam dentro de outras palavras (ex.: "last" pegaria "plastic").
TEMAS = {
    "Qualidade e acabamento": ["quality", "build", "material", "sturdy", "flimsy", "finish"],
    "Durabilidade e defeitos": ["durab", "broke", "stopped working", "defect", "faulty", "damag", "died"],
    "Preço e custo-benefício": ["price", "money", "value", "worth", "cheap", "affordable", "budget", "expensive"],
    "Bateria e carregamento": ["batter", "charg", "backup"],
    "Instalação e facilidade de uso": ["install", "setup", "set up", "easy", "user friendly"],
    "Compatibilidade e conexão": ["compatib", "connect", "bluetooth", "wifi", "wi-fi", "usb", "port"],
    "Som, imagem e desempenho": ["sound", "bass", "audio", "picture", "display", "screen", "speed", "performance"],
    "Entrega, embalagem e atendimento": ["deliver", "packag", "seller", "customer service", "warranty", "refund", "replacement"],
}

STOPWORDS = set(
    """
a about above after again all also am an and any are as at be because been before being below between both but by
can could did do does doing down during each few for from further get got had has have having he her here hers
him his how i if in into is it its itself just me more most my no nor not now of off on once only or other our out
over own same she should so some such than that the their theirs them then there these they this those through to
too under until up very was we were what when where which while who whom why will with would you your yours
product item one use used using really much like bought buy purchase purchased amazon still even
""".split()
)
