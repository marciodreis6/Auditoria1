import os
import re
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================================
# CONFIG
# =========================================================

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
DATA_FOLDER = "data"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================


def calcular_shelf_life(data_fabricacao, data_validade, data_embarque):
    try:
        vida_total = (data_validade - data_fabricacao).days
        dias_restantes = (data_validade - data_embarque).days

        if vida_total <= 0:
            return 0

        return round((dias_restantes / vida_total) * 100, 2)

    except:
        return 0


# =========================================================
# LEITOR TXT
# =========================================================


def ler_txt(arquivo_txt):

    dados = []

    linhas = arquivo_txt.read().decode("utf-8").splitlines()

    for linha in linhas:

        partes = linha.strip().split(";")

        if len(partes) != 4:
            continue

        data = partes[0]
        hora = partes[1]
        chave_palete = partes[2]
        quantidade = partes[3]

        dados.append(
            {
                "data_bipagem": f"{data} {hora}",
                "chave_palete": chave_palete,
                "quantidade_txt": float(
                    str(quantidade).replace(",", ".")
                ),
            }
        )

    return pd.DataFrame(dados)


# =========================================================
# STREAMLIT
# =========================================================

st.set_page_config(page_title="Auditoria Logística", layout="wide")

st.title("📦 Auditoria Inteligente de Remessas")

# =========================================================
# UPLOADS
# =========================================================

st.subheader("Upload dos Arquivos")

arquivo_fabrica = st.file_uploader(
    "Relatório Fábrica",
    type=["xlsx"],
)

arquivo_detalhamento = st.file_uploader(
    "Detalhamento Remessas",
    type=["csv", "xlsx"],
)

arquivo_bloqueados = st.file_uploader(
    "Itens Bloqueados",
    type=["xlsx"],
)

arquivo_shelf = st.file_uploader(
    "Base Shelf Cliente",
    type=["xlsx"],
)

arquivos_txt = st.file_uploader(
    "Arquivos TXT",
    type=["txt"],
    accept_multiple_files=True,
)


# =========================================================
# PROCESSAMENTO
# =========================================================

if (
    arquivo_fabrica
    and arquivo_detalhamento
    and arquivo_bloqueados
    and arquivo_shelf
    and arquivos_txt
):

    st.info("Processando arquivos...")

    # =====================================================
    # LEITURA BASES
    # =====================================================

    # =====================================================
# LEITURA BASES
# =====================================================

    relatorio_fabrica = pd.read_excel(arquivo_fabrica)
    

    if arquivo_detalhamento.name.endswith(".csv"):

        try:

            detalhamento = pd.read_csv(
                arquivo_detalhamento,
                sep=";",
                encoding="latin1",
                on_bad_lines="skip",
            )

        except:

            detalhamento = pd.read_csv(
                arquivo_detalhamento,
                sep=",",
                encoding="utf-8",
                on_bad_lines="skip",
            )

    else:

        detalhamento = pd.read_excel(
            arquivo_detalhamento
        )

    bloqueados = pd.read_excel(
        arquivo_bloqueados
    )

    shelf_cliente = pd.read_excel(
        arquivo_shelf
    )
    st.write(shelf_cliente.columns.tolist())
    # =====================================================
    # CONCATENAR TXTS
    # =====================================================

    lista_txt = []

    for arquivo in arquivos_txt:
        
        df_txt = ler_txt(arquivo)

        lista_txt.append(df_txt)

    txt_final = pd.concat(lista_txt, ignore_index=True)

    # =====================================================
    # NORMALIZAÇÃO
    # =====================================================

    txt_final["chave_palete"] = txt_final["chave_palete"].astype(str)
    relatorio_fabrica["Chave Pallet"] = relatorio_fabrica[
    "Chave Pallet"
    ].astype(str)

    # =====================================================
    # CRUZAMENTO COM FÁBRICA
    # =====================================================
    
    # =====================================================
    # NORMALIZAÇÃO
    # =====================================================

    txt_final["chave_palete"] = (
        txt_final["chave_palete"]
        .astype(str)
        .str.strip()
    )

    relatorio_fabrica["Chave Pallet"] = (
        relatorio_fabrica["Chave Pallet"]
        .astype(str)
        .str.strip()
    )

    base = txt_final.merge(
    relatorio_fabrica,
    left_on="chave_palete",
    right_on="Chave Pallet",
    how="left",
)
    
    # =====================================================
    # DATAS
    # =====================================================

    base["Data de produção"] = pd.to_datetime(
        base["Data de produção"],
        errors="coerce",
    )

    base["Data do vencimento"] = pd.to_datetime(
        base["Data do vencimento"],
        errors="coerce",
    )

    base["data_embarque"] = pd.to_datetime(
        base["data_bipagem"],
        errors="coerce",
    )

    # =====================================================
    # SHELF LIFE
    # =====================================================

    base["shelf_calculado"] = base.apply(
        lambda row: calcular_shelf_life(
            row["Data de produção"],
            row["Data do vencimento"],
            row["data_embarque"],
        ),
        axis=1,
    )

    # =====================================================
    # DETALHAMENTO
    # =====================================================

    detalhamento_consolidado = (
    detalhamento.groupby(["ITEM"])["QTD_EMBALA"]
    .sum()
    .reset_index()
    )

    base["ITEM"] = (
    base["Material"]
    .astype(str)
    .str.strip()
    )

    detalhamento["ITEM"] = (
        detalhamento["ITEM"]
        .astype(str)
        .str.strip()
    )

    consolidado_txt = (
        base.groupby(["Material"])["quantidade_txt"]
        .sum()
        .reset_index()
    )

    consolidado_txt.rename(
        columns={"Material": "ITEM"},
        inplace=True
    )

    validacao = consolidado_txt.merge(
        detalhamento_consolidado,
        on="ITEM",
        how="left",
        suffixes=("_txt", "_detalhamento"),
    )
    validacao["QTD_EMBALA"] = pd.to_numeric(
        validacao["QTD_EMBALA"],
        errors="coerce"
    )

    validacao["quantidade_txt"] = pd.to_numeric(
        validacao["quantidade_txt"],
        errors="coerce"
    )
    validacao["divergencia"] = (
    validacao["quantidade_txt"]
    - validacao["QTD_EMBALA"]
)

    validacao["status_quantidade"] = validacao["divergencia"].apply(
        lambda x: "OK" if x == 0 else "DIVERGENTE"
    )

    # =====================================================
    # LOTES BLOQUEADOS
    # =====================================================

    base = base.merge(
        bloqueados[["Lote"]],
        left_on="Lote",
        right_on="Lote",
        how="left",
        indicator=True,
    )

    base["status_lote"] = base["_merge"].apply(
        lambda x: "BLOQUEADO" if x == "both" else "LIBERADO"
    )

    # =====================================================
    # SHELF CLIENTE
    # =====================================================
    base = base.merge(
    detalhamento[["ITEM", "NOME"]],
    on="ITEM",
    how="left",
    )
    
    base["NOME"] = (
        base["NOME"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    shelf_cliente["Destino"] = (
        shelf_cliente["Destino"]
        .astype(str)
        .str.upper()
        .str.strip()
    )
    
    base = base.merge(
        shelf_cliente,
        left_on="NOME",
        right_on="Destino",
        how="left",
    )

    base["Shelf"] = pd.to_numeric(
    base["Shelf"],
    errors="coerce"
    )

    base["shelf_calculado"] = pd.to_numeric(
        base["shelf_calculado"],
        errors="coerce"
    )

    base["status_shelf"] = "FORA SHELF"

    base.loc[
        base["shelf_calculado"] >= base["Shelf"],
        "status_shelf"
    ] = "OK",

    # =====================================================
    # STATUS FINAL
    # =====================================================

    def status_final(row):

        if row["status_lote"] == "BLOQUEADO":
            return "REPROVADO"

        if row["status_shelf"] == "FORA SHELF":
            return "REPROVADO"

        return "APROVADO"

    base["status_final"] = base.apply(status_final, axis=1)

    # =====================================================
    # DASHBOARD
    # =====================================================

    total = len(base)
    aprovados = len(base[base["status_final"] == "APROVADO"])
    reprovados = len(base[base["status_final"] == "REPROVADO"])

    percentual = round((aprovados / total) * 100, 2) if total > 0 else 0

    col1, col2, col3 = st.columns(3)

    col1.metric("Total", total)
    col2.metric("Aprovados", aprovados)
    col3.metric("Assertividade", f"{percentual}%")

    grafico = pd.DataFrame(
        {
            "Status": ["Aprovado", "Reprovado"],
            "Quantidade": [aprovados, reprovados],
        }
    )

    fig = px.pie(
        grafico,
        names="Status",
        values="Quantidade",
        title="Status das Remessas",
    )

    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # TABELAS
    # =====================================================

    st.subheader("Resultado Final")
    st.dataframe(base)

    st.subheader("Validação Quantidades")
    st.dataframe(validacao)

    # =====================================================
    # EXPORTAÇÃO
    # =====================================================

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    arquivo_saida = os.path.join(
        OUTPUT_FOLDER,
        f"auditoria_{timestamp}.xlsx",
    )

    with pd.ExcelWriter(arquivo_saida, engine="xlsxwriter") as writer:

        base.to_excel(writer, sheet_name="Resultado", index=False)
        validacao.to_excel(writer, sheet_name="Validacao", index=False)

    st.success("Processamento concluído")

    with open(arquivo_saida, "rb") as f:
        st.download_button(
            "⬇ Baixar Relatório",
            f,
            file_name=f"auditoria_{timestamp}.xlsx",
        )