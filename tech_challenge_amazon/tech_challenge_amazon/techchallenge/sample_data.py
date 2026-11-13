"""Gerador de DADOS SINTÉTICOS, usado apenas para testar o pipeline.

ATENÇÃO: nada aqui é dado real da Amazon. Os números, categorias e textos são inventados para
reproduzir o FORMATO e as "sujeiras" que o CSV original do Kaggle costuma ter (preço com ₹ e vírgula,
percentual com %, rating com valor inválido, rating_count vazio, product_id repetido, várias reviews
concatenadas com vírgula na mesma célula). Nunca use resultados gerados a partir deste arquivo
como insight.

Uso:  python -m techchallenge.sample_data [caminho_de_saida.csv]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

CATEGORIAS = [
    ("Computers&Accessories|Accessories&Peripherals|Cables&Accessories|Cables|USBCables", 0.22, 0.4),
    ("Electronics|HomeTheater,TV&Video|Televisions|SmartTelevisions", 0.10, 1.8),
    ("Electronics|Headphones,Earbuds&Accessories|Headphones|In-Ear", 0.14, 0.9),
    ("Home&Kitchen|Kitchen&HomeAppliances|SmallKitchenAppliances|MixerGrinders", 0.12, 1.2),
    ("Home&Kitchen|Heating,Cooling&AirQuality|Fans|TableFans", 0.08, 1.0),
    ("Computers&Accessories|NetworkingDevices|Routers", 0.07, 1.1),
    ("OfficeProducts|OfficePaperProducts|Paper|Stationery", 0.05, 0.3),
    ("HomeImprovement|Electrical|Adapters", 0.04, 0.5),
    ("Toys&Games|Arts&Crafts|Drawing", 0.03, 0.3),
    ("Car&Motorbike|Car|Accessories", 0.02, 0.6),
    ("MusicalInstruments|Microphones|Condenser", 0.02, 0.8),
    ("Health&PersonalCare|HomeMedicalSupplies|Thermometers", 0.01, 0.4),
]

FRASES_POS = [
    "Great product, easy to use and good value for money", "Works perfectly, sound quality is excellent",
    "Very sturdy build quality, totally worth the price", "Fast delivery and nice packaging, happy with it",
    "Easy to install and setup took two minutes", "Battery backup is amazing, charges fast",
    "Display is crisp and bright, love it", "Good performance, highly recommend",
]
FRASES_NEG = [
    "Stopped working after two months, poor durability", "Build quality is flimsy and cheap, waste of money",
    "Charging issue, battery drains very fast", "Not compatible with my device, connection problems",
    "Packaging was damaged and delivery was late, disappointed", "Defective piece, asked for refund and replacement",
    "Sound quality is bad and it keeps disconnecting", "Broke within a week, very bad quality",
]
FRASES_NEU = [
    "Okay for the price, nothing special", "Does the job but the screen could be better",
    "Average product, decent battery", "Good but the cable is a bit short",
]


def gerar(n_produtos: int = 600, semente: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    pesos = np.array([c[1] for c in CATEGORIAS])
    pesos = pesos / pesos.sum()
    linhas = []
    for i in range(n_produtos):
        k = rng.choice(len(CATEGORIAS), p=pesos)
        cat, _, escala_preco = CATEGORIAS[k]
        pid = f"B0{rng.integers(10**8, 10**9)}"
        preco = float(np.round(rng.lognormal(mean=6.4 + escala_preco * 0.6, sigma=0.9), 0))
        preco = max(preco, 99.0)
        desc = float(np.clip(rng.beta(3.2, 2.6) * 0.9 + 0.02, 0.0, 0.9))
        final = float(np.round(preco * (1 - desc), 0))
        pct = int(round((1 - final / preco) * 100))
        rating = float(np.clip(np.round(rng.normal(4.1, 0.32), 1), 2.6, 5.0))
        engaj = int(np.clip(rng.lognormal(mean=7.3, sigma=1.5), 2, 400_000))
        n_rev = int(rng.integers(3, 9))
        p_pos = np.clip((rating - 3.0) / 2.2, 0.05, 0.95)
        titulos, conteudos, ids, users = [], [], [], []
        for _ in range(n_rev):
            r = rng.random()
            frase = (rng.choice(FRASES_POS) if r < p_pos * 0.85 else
                     rng.choice(FRASES_NEG) if r > 1 - (1 - p_pos) * 0.8 else rng.choice(FRASES_NEU))
            titulos.append("Great buy" if "Great" in frase else "Not satisfied" if "poor" in frase.lower() else "Decent")
            conteudos.append(frase + ", " + rng.choice(["would buy again", "not sure about long term", "as described"]))
            ids.append(f"R{rng.integers(10**9, 10**10)}")
            users.append(f"AG{rng.integers(10**10, 10**11)}")
        linhas.append({
            "product_id": pid,
            "product_name": f"Produto sintético {i:04d} ({cat.split('|')[-1]})",
            "category": cat,
            "discounted_price": f"₹{int(final):,}",
            "actual_price": f"₹{int(preco):,}",
            "discount_percentage": f"{pct}%",
            "rating": f"{rating}",
            "rating_count": f"{engaj:,}",
            "about_product": "Descrição sintética do produto. " * 3,
            "user_id": ",".join(users),
            "user_name": ",".join(f"Usuario{j}" for j in range(n_rev)),
            "review_id": ",".join(ids),
            "review_title": ",".join(titulos),
            "review_content": ",".join(conteudos),
            "img_link": "https://example.com/img.jpg",
            "product_link": f"https://example.com/dp/{pid}",
        })
    df = pd.DataFrame(linhas)

    # --- sujeiras típicas
    df.loc[3, "rating"] = "|"                       # rating inválido
    df.loc[5, "product_name"] = df.loc[5, "product_name"] + "\x0b"  # caractere de controle (quebra o Excel se não for tratado)
    df.loc[[10, 11], "rating_count"] = np.nan       # rating_count vazio
    dup = df.sample(40, random_state=semente).copy()  # product_id repetido (outras reviews)
    dup["review_content"] = "Repeated review row, works fine, good value"
    df = pd.concat([df, dup], ignore_index=True)
    return df.sample(frac=1, random_state=semente).reset_index(drop=True)


def main() -> None:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/amazon_SINTETICO_apenas_teste.csv")
    destino.parent.mkdir(parents=True, exist_ok=True)
    gerar().to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"Dados SINTÉTICOS gravados em {destino} (somente para testar o pipeline).")


if __name__ == "__main__":
    main()
