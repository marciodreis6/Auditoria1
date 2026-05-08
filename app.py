import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================================================
# CONFIGURAÇÕES
# =========================================================

OUTPUT_FOLDER = "output"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="Auditoria Inteligente",
    layout="wide"
)

st.title("📦 Auditoria Inteligente de Remessas")


# =========================================================
# FUNÇÕES
# =========================================================

def ler_txt(arquivo_txt):

    dados = []

    conteudo = arquivo_txt.read().decode(
        "utf-8",
        errors="ignore"
    )

    linhas = conteudo.splitlines()

    for linha in linhas:

        partes = linha.strip().split(";")

        if len(partes) != 4:
            continue

        data = partes[0]
        hora = partes[1]
        chave_palete = partes[2]
        quantidade = partes[3]

        try:
            quantidade = float(
                str(quantidade).replace(",", ".")
            )

        except:
            quantidade = 0

        dados.append(
            {
                "data_bipagem": f"{data} {hora}",
                "chave_palete": str(chave_palete).strip(),
                "quantidade_txt": quantidade,
            }
        )

    return pd.DataFrame(dados)


def calcular_shelf_life(
    data_fabricacao,
    data_validade,
    data_embarque
):

    try:

        vida_total = (
            data_validade - data_fabricacao
        ).days

        vida_restante = (
            data_validade - data_embarque
        ).days

        if vida_total <= 0:
            return 0

        percentual = (
            vida_restante / vida_total
        ) * 100

        return round(percentual, 2)

    except:
        return 0


# =========================================================
# UPLOADS
# =========================================================

st.subheader("Upload dos Arquivos")

arquivo_fabrica = st.file_uploader(
    "Relatório Fábrica",
    type=["xlsx"]
)

arquivo_detalhamento = st.file_uploader(
    "Detalhamento Remessas",
    type=["xlsx", "csv"]
)

arquivo_bloqueados = st.file_uploader(
    "Itens Bloqueados",
    type=["xlsx"]
)

arquivo_shelf = st.file_uploader(
    "Shelf Life Clientes",
    type=["xlsx"]
)

arquivos_txt = st.file_uploader(
    "Arquivos TXT",
    type=["txt"],
    accept_multiple_files=True
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
    # LEITURA ARQUIVOS
    # =====================================================

    relatorio_fabrica = pd.read_excel(
        arquivo_fabrica
    )

    bloqueados = pd.read_excel(
        arquivo_bloqueados
    )

    shelf_cliente = pd.read_excel(
        arquivo_shelf
    )

    # =====================================================
    # DETALHAMENTO
    # =====================================================

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

    # =====================================================
    # CONCATENAR TXT
    # =====================================================

    lista_txt = []

    for arquivo in arquivos_txt:

        df_txt = ler_txt(arquivo)

        lista_txt.append(df_txt)

    txt_final = pd.concat(
        lista_txt,
        ignore_index=True
    )

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

    relatorio_fabrica["Material"] = (
        relatorio_fabrica["Material"]
        .astype(str)
        .str.strip()
    )

    relatorio_fabrica["Lote"] = (
        relatorio_fabrica["Lote"]
        .astype(str)
        .str.strip()
    )

    bloqueados["Lote"] = (
        bloqueados["Lote"]
        .astype(str)
        .str.strip()
    )

    detalhamento["ITEM"] = (
        detalhamento["ITEM"]
        .astype(str)
        .str.strip()
    )

    detalhamento["QTD_EMBALA"] = pd.to_numeric(
        detalhamento["QTD_EMBALA"],
        errors="coerce"
    ).fillna(0)

    shelf_cliente["Destino"] = (
        shelf_cliente["Destino"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    shelf_cliente["Shelf"] = pd.to_numeric(
        shelf_cliente["Shelf"],
        errors="coerce"
    )

    # =====================================================
    # CRUZAMENTO TXT X FÁBRICA
    # =====================================================

    base = txt_final.merge(
        relatorio_fabrica,
        left_on="chave_palete",
        right_on="Chave Pallet",
        how="left",
    )

    # =====================================================
    # VALIDAÇÃO CHAVE PALLET
    # =====================================================

    base["status_chave"] = base[
        "Chave Pallet"
    ].apply(
        lambda x:
            "LOCALIZADA"
            if pd.notna(x)
            else "NÃO LOCALIZADA"
    )

    # =====================================================
    # VALIDAÇÃO LOTE BLOQUEADO
    # =====================================================

    base["status_lote"] = base["Lote"].isin(
        bloqueados["Lote"]
    )

    base["status_lote"] = (
        base["status_lote"]
        .apply(
            lambda x:
                "BLOQUEADO"
                if x
                else "LIBERADO"
        )
    )

    # =====================================================
    # PREPARAÇÃO ITEM
    # =====================================================

    base["ITEM"] = (
        base["Material"]
        .astype(str)
        .str.strip()
    )

    # =====================================================
    # VALIDAÇÃO QUANTIDADES
    # =====================================================

    txt_consolidado = (
        base.groupby("ITEM")["quantidade_txt"]
        .sum()
        .reset_index()
    )

    txt_consolidado.rename(
        columns={
            "quantidade_txt": "QTD_TXT"
        },
        inplace=True,
    )

    detalhamento_consolidado = (
        detalhamento.groupby("ITEM")[
            "QTD_EMBALA"
        ]
        .sum()
        .reset_index()
    )

    validacao = txt_consolidado.merge(
        detalhamento_consolidado,
        on="ITEM",
        how="left",
    )

    validacao["QTD_EMBALA"] = (
        validacao["QTD_EMBALA"]
        .fillna(0)
    )

    validacao["divergencia"] = (
        validacao["QTD_TXT"]
        - validacao["QTD_EMBALA"]
    )

    validacao["status_quantidade"] = (
        validacao["divergencia"]
        .apply(
            lambda x:
                "OK"
                if x == 0
                else "DIVERGENTE"
        )
    )

    # =====================================================
    # TRAZER STATUS QUANTIDADE PARA BASE
    # =====================================================

    base = base.merge(
        validacao[
            [
                "ITEM",
                "status_quantidade",
                "divergencia",
            ]
        ],
        on="ITEM",
        how="left",
    )

    # =====================================================
    # TRAZER CLIENTE
    # =====================================================

    base = base.merge(
        detalhamento[
            [
                "ITEM",
                "NOME",
            ]
        ],
        on="ITEM",
        how="left",
    )

    base["NOME"] = (
        base["NOME"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # =====================================================
    # CRUZAMENTO SHELF
    # =====================================================

    base = base.merge(
        shelf_cliente,
        left_on="NOME",
        right_on="Destino",
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
    # CÁLCULO SHELF LIFE
    # =====================================================

    base["shelf_calculado"] = base.apply(
        lambda row: calcular_shelf_life(
            row["Data de produção"],
            row["Data do vencimento"],
            row["data_embarque"],
        ),
        axis=1,
    )

    base["status_shelf"] = "FORA SHELF"

    base.loc[
        base["shelf_calculado"] >= base["Shelf"],
        "status_shelf"
    ] = "OK"

    # =====================================================
    # STATUS FINAL
    # =====================================================

    def definir_status(row):

        if row["status_chave"] == "NÃO LOCALIZADA":
            return "REPROVADO"

        if row["status_lote"] == "BLOQUEADO":
            return "REPROVADO"

        if row["status_quantidade"] == "DIVERGENTE":
            return "REPROVADO"

        if row["status_shelf"] == "FORA SHELF":
            return "REPROVADO"

        return "APROVADO"

    base["status_final"] = base.apply(
        definir_status,
        axis=1
    )

    # =====================================================
    # MÉTRICAS
    # =====================================================

    total = len(base)

    aprovados = len(
        base[
            base["status_final"] == "APROVADO"
        ]
    )

    reprovados = len(
        base[
            base["status_final"] == "REPROVADO"
        ]
    )

    bloqueados_total = len(
        base[
            base["status_lote"] == "BLOQUEADO"
        ]
    )

    shelf_problema = len(
        base[
            base["status_shelf"] == "FORA SHELF"
        ]
    )

    divergentes = len(
        base[
            base["status_quantidade"]
            == "DIVERGENTE"
        ]
    )

    percentual_conformidade = (
        round((aprovados / total) * 100, 2)
        if total > 0
        else 0
    )

    percentual_divergencia = (
        round((reprovados / total) * 100, 2)
        if total > 0
        else 0
    )

    # =====================================================
    # DASHBOARD
    # =====================================================

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total",
        total
    )

    col2.metric(
        "Conformes",
        aprovados
    )

    col3.metric(
        "Divergências",
        reprovados
    )

    col4.metric(
        "Lotes Bloqueados",
        bloqueados_total
    )

    col5.metric(
        "Problemas Shelf",
        shelf_problema
    )

    grafico_status = pd.DataFrame(
        {
            "Status": [
                "Conformes",
                "Divergentes"
            ],
            "Quantidade": [
                aprovados,
                reprovados
            ],
        }
    )

    fig1 = px.pie(
        grafico_status,
        names="Status",
        values="Quantidade",
        title="Percentual Conformidade",
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    grafico_divergencias = pd.DataFrame(
        {
            "Categoria": [
                "Bloqueados",
                "Shelf",
                "Quantidade"
            ],
            "Quantidade": [
                bloqueados_total,
                shelf_problema,
                divergentes,
            ],
        }
    )

    fig2 = px.bar(
        grafico_divergencias,
        x="Categoria",
        y="Quantidade",
        title="Divergências Encontradas",
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # =====================================================
    # TABELAS
    # =====================================================
    
    # REMOVE COLUNAS DUPLICADAS
    base = base.loc[:, ~base.columns.duplicated()]

    # REMOVE ESPAÇOS DOS NOMES DAS COLUNAS
    base.columns = base.columns.str.strip()

    # =====================================================
    # RESULTADO FINAL LIMPO
    # =====================================================

    colunas_resultado = [
        "chave_palete",
        "quantidade_txt",
        "data_embarque",
        "status_chave",
        "status_lote",
        "status_shelf",
        "status_final",
    ]

    resultado_final = base.filter(
        items=colunas_resultado
    ).copy()

    resultado_final.rename(
        columns={
            "chave_palete": "CHAVE_PALETE",
            "quantidade_txt": "QUANTIDADE_TXT",
            "data_embarque": "DATA_EMBARQUE",
            "status_chave": "STATUS_CHAVE",
            "status_lote": "STATUS_LOTE",
            "status_shelf": "STATUS_SHELF",
            "status_final": "STATUS_FINAL",
        },
        inplace=True,
    )

    # =====================================================
    # TABELAS
    # =====================================================

    st.subheader("Resultado Final")

    st.dataframe(resultado_final)

    st.subheader("Validação Quantidades")

    st.dataframe(validacao)

    # =====================================================
    # EXPORTAÇÃO XLSX
    # =====================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    arquivo_saida = os.path.join(
        OUTPUT_FOLDER,
        f"auditoria_{timestamp}.xlsx",
    )

    with pd.ExcelWriter(
        arquivo_saida,
        engine="xlsxwriter"
    ) as writer:

        resultado_final.to_excel(
            writer,
            sheet_name="Resultado_Final",
            index=False,
        )

        validacao.to_excel(
            writer,
            sheet_name="Validacao_Quantidades",
            index=False,
        )

    st.success(
        "Processamento concluído com sucesso"
    )

    with open(arquivo_saida, "rb") as f:

        st.download_button(
            "⬇ Baixar Relatório XLSX",
            f,
            file_name=f"auditoria_{timestamp}.xlsx",
        )
