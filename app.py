import pandas as pd
import streamlit as st
import plotly.express as px

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="Auditoria Logística",
    layout="wide"
)

st.title("📦 Auditoria Inteligente - FASE 1")


# =====================================================
# FUNÇÕES
# =====================================================

def validar_colunas(
    dataframe,
    colunas_obrigatorias,
    nome_arquivo
):

    colunas_faltando = []

    for coluna in colunas_obrigatorias:

        if coluna not in dataframe.columns:
            colunas_faltando.append(coluna)

    if len(colunas_faltando) > 0:

        st.error(
            f"""
            ❌ {nome_arquivo}

            Colunas faltando:
            {colunas_faltando}
            """
        )

        return False

    st.success(f"✅ {nome_arquivo} OK")

    return True


def ler_txt(arquivo_txt):

    conteudo = arquivo_txt.read().decode(
        "utf-8",
        errors="ignore"
    )

    linhas = conteudo.splitlines()

    dados = []

    linhas_invalidas = 0

    for linha in linhas:

        partes = linha.strip().split(";")

        if len(partes) != 4:

            linhas_invalidas += 1
            continue

        data = partes[0].strip()
        hora = partes[1].strip()
        chave = partes[2].strip()
        quantidade = partes[3].strip()

        try:

            quantidade = float(
                quantidade.replace(",", ".")
            )

        except:

            linhas_invalidas += 1
            continue
        
        dados.append(
            {
                "data_bipagem": f"{data} {hora}",
                "chave_palete": chave,
                "quantidade_txt": quantidade,
            }
        )

    dataframe = pd.DataFrame(dados)

    return dataframe, linhas_invalidas


# =====================================================
# UPLOADS
# =====================================================

st.subheader("Upload dos Arquivos")

arquivo_fabrica = st.file_uploader(
    "Relatório Fábrica",
    type=["xlsx"]
)

arquivo_detalhamento = st.file_uploader(
    "Detalhamento",
    type=["xlsx", "csv"]
)

arquivo_bloqueados = st.file_uploader(
    "Bloqueados",
    type=["xlsx"]
)

arquivo_shelf = st.file_uploader(
    "Shelf Cliente",
    type=["xlsx"]
)

arquivos_txt = st.file_uploader(
    "Arquivos TXT",
    type=["txt"],
    accept_multiple_files=True
)


# =====================================================
# PROCESSAMENTO
# =====================================================

if (
    arquivo_fabrica
    and arquivo_detalhamento
    and arquivo_bloqueados
    and arquivo_shelf
    and arquivos_txt
):

    st.info("Lendo arquivos...")

    # =================================================
    # LEITURA FÁBRICA
    # =================================================

    fabrica = pd.read_excel(
        arquivo_fabrica
    )

    # =================================================
    # LEITURA DETALHAMENTO
    # =================================================

    if arquivo_detalhamento.name.endswith(".csv"):

        try:

            detalhamento = pd.read_csv(
                arquivo_detalhamento,
                sep=";",
                encoding="latin1",
                on_bad_lines="skip"
            )

        except:

            detalhamento = pd.read_csv(
                arquivo_detalhamento,
                sep=",",
                encoding="utf-8",
                on_bad_lines="skip"
            )

    else:

        detalhamento = pd.read_excel(
            arquivo_detalhamento
        )

    # =================================================
    # LEITURA BLOQUEADOS
    # =================================================

    bloqueados = pd.read_excel(
        arquivo_bloqueados
    )

    # =================================================
    # LEITURA SHELF
    # =================================================

    shelf = pd.read_excel(
        arquivo_shelf
    )
    # =================================================
# PROCESSAMENTO TXT
# =================================================

st.write("## Resultado TXT")

lista_txt = []

total_invalidas = 0

for arquivo in arquivos_txt:

    df_txt, invalidas = ler_txt(arquivo)

    total_invalidas += invalidas

    lista_txt.append(df_txt)

    st.write(
        f"""
        📄 {arquivo.name}

        ✅ Registros válidos:
        {len(df_txt)}

        ❌ Registros inválidos:
        {invalidas}
        """
    )

# =================================================
# CONCATENA TODOS OS TXTS
# =================================================

    txt_final = pd.concat(
        lista_txt,
        ignore_index=True
    )

    # =================================================
    # NORMALIZAÇÃO
    # =================================================

    txt_final["chave_palete"] = (
        txt_final["chave_palete"]
        .astype(str)
        .str.strip()
    )

    txt_final["quantidade_txt"] = pd.to_numeric(
        txt_final["quantidade_txt"],
        errors="coerce"
    )

    txt_final["data_bipagem"] = pd.to_datetime(
        txt_final["data_bipagem"],
        errors="coerce",
        dayfirst=True
    )

    # =================================================
    # MÉTRICAS
    # =================================================

    st.subheader("Métricas TXT")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Linhas",
        len(txt_final)
    )

    col2.metric(
        "Pallets únicos",
        txt_final["chave_palete"].nunique()
    )

    col3.metric(
        "Quantidade total",
        round(
            txt_final["quantidade_txt"].sum(),
            2
        )
    )

    col4.metric(
        "Linhas inválidas",
        total_invalidas
    )

    # =================================================
    # PREVIEW
    # =================================================

    st.subheader("Preview TXT Consolidado")

    st.dataframe(txt_final)

    st.success(
        "FASE 2 concluída com sucesso"
    )
    
    # =================================================
    # FASE 3
    # CRUZAMENTO TXT X FÁBRICA
    # =================================================

    st.header("FASE 3 - Cruzamento TXT x Fábrica")

    # =================================================
    # NORMALIZAÇÃO
    # =================================================

    fabrica["Chave Pallet"] = (
        fabrica["Chave Pallet"]
        .astype(str)
        .str.strip()
    )

    fabrica["Qtd.  UM registro"] = pd.to_numeric(
        fabrica["Qtd.  UM registro"],
        errors="coerce"
    )

    # =================================================
    # MERGE
    # =================================================

    base = txt_final.merge(
        fabrica,
        left_on="chave_palete",
        right_on="Chave Pallet",
        how="left"
    )

    # =================================================
    # RENOMEIA COLUNAS
    # =================================================

    base.rename(
        columns={
            "Qtd.  UM registro": "quantidade_fabrica",
            "Material": "material",
            "Lote": "lote",
            "Data do vencimento": "validade",
            "Data de produção": "producao",
            "Status Chave Pallet": "status_pallet"
        },
        inplace=True
    )

    # =================================================
    # VALIDA EXISTÊNCIA PALLET
    # =================================================

    base["pallet_encontrado"] = (
        base["material"]
        .notna()
    )

    base["status_pallet_encontrado"] = base[
        "pallet_encontrado"
    ].apply(
        lambda x: (
            "ENCONTRADO"
            if x
            else "NÃO ENCONTRADO"
        )
    )

    # =================================================
    # COMPARA QUANTIDADES
    # =================================================

    base["quantidade_fabrica"] = pd.to_numeric(
        base["quantidade_fabrica"],
        errors="coerce"
    )

    base["divergencia_quantidade"] = (
        base["quantidade_txt"]
        - base["quantidade_fabrica"]
    )

    base["status_quantidade"] = base[
        "divergencia_quantidade"
    ].apply(
        lambda x: (
            "OK"
            if x == 0
            else "DIVERGENTE"
        )
    )

    # =================================================
    # RESULTADO
    # =================================================

    resultado_fase3 = base[
        [
            "chave_palete",
            "quantidade_txt",
            "quantidade_fabrica",
            "material",
            "lote",
            "validade",
            "producao",
            "status_pallet",
            "status_pallet_encontrado",
            "status_quantidade",
        ]
    ]

    # =================================================
    # MÉTRICAS
    # =================================================

    total = len(resultado_fase3)

    encontrados = len(
        resultado_fase3[
            resultado_fase3[
                "status_pallet_encontrado"
            ] == "ENCONTRADO"
        ]
    )

    divergentes = len(
        resultado_fase3[
            resultado_fase3[
                "status_quantidade"
            ] == "DIVERGENTE"
        ]
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Pallets",
        total
    )

    col2.metric(
        "Pallets Encontrados",
        encontrados
    )

    col3.metric(
        "Divergências",
        divergentes
    )

    # =================================================
    # PREVIEW
    # =================================================

    st.subheader(
        "Resultado Cruzamento"
    )

    st.dataframe(resultado_fase3)

    st.success(
        "FASE 3 concluída com sucesso"
    )
    # =================================================
    # FASE 4
    # VALIDAÇÃO LOTES BLOQUEADOS
    # =================================================

    st.header("FASE 4 - Validação Lotes")

    # =================================================
    # NORMALIZAÇÃO
    # =================================================

    bloqueados["Lote"] = (
        bloqueados["Lote"]
        .astype(str)
        .str.strip()
    )

    resultado_fase3["lote"] = (
        resultado_fase3["lote"]
        .astype(str)
        .str.strip()
    )

    # =================================================
    # MERGE LOTES
    # =================================================

    resultado_fase4 = resultado_fase3.merge(
        bloqueados[["Lote"]],
        left_on="lote",
        right_on="Lote",
        how="left",
        indicator=True
    )

    # =================================================
    # STATUS LOTE
    # =================================================

    resultado_fase4["status_lote"] = (
        resultado_fase4["_merge"]
        .apply(
            lambda x: (
                "BLOQUEADO"
                if x == "both"
                else "LIBERADO"
            )
        )
    )

    # =================================================
    # REMOVE COLUNAS AUXILIARES
    # =================================================

    resultado_fase4.drop(
        columns=[
            "_merge",
            "Lote"
        ],
        inplace=True
    )

    # =================================================
    # MÉTRICAS
    # =================================================

    bloqueados_total = len(
        resultado_fase4[
            resultado_fase4[
                "status_lote"
            ] == "BLOQUEADO"
        ]
    )

    liberados_total = len(
        resultado_fase4[
            resultado_fase4[
                "status_lote"
            ] == "LIBERADO"
        ]
    )

    col1, col2 = st.columns(2)

    col1.metric(
        "Lotes Bloqueados",
        bloqueados_total
    )

    col2.metric(
        "Lotes Liberados",
        liberados_total
    )

    # =================================================
    # PREVIEW
    # =================================================

    st.subheader(
        "Resultado Lotes"
    )

    st.dataframe(
        resultado_fase4
    )

    st.success(
        "FASE 4 concluída com sucesso"
    )
    
    # =================================================
    # FASE 5
    # SHELF LIFE
    # =================================================

    st.header("FASE 5 - Shelf Life")

    # =================================================
    # NORMALIZAÇÃO MATERIAL
    # =================================================

    resultado_fase4["material"] = (
        resultado_fase4["material"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    detalhamento["ITEM"] = (
        detalhamento["ITEM"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    # =================================================
    # NORMALIZAÇÃO CLIENTE
    # =================================================

    detalhamento["CNPJ"] = (
        detalhamento["CNPJ"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    shelf["Destino"] = (
        shelf["Destino"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # =================================================
    # DATAS
    # =================================================

    resultado_fase4["validade"] = pd.to_datetime(
        resultado_fase4["validade"],
        errors="coerce",
        dayfirst=True
    )

    resultado_fase4["producao"] = pd.to_datetime(
        resultado_fase4["producao"],
        errors="coerce",
        dayfirst=True
    )

    base["data_bipagem"] = pd.to_datetime(
        base["data_bipagem"],
        errors="coerce",
        dayfirst=True
    )

    # =================================================
    # CÁLCULO SHELF
    # =================================================

    def calcular_shelf(
    data_fabricacao,
    data_validade,
    data_embarque
    ):

        try:

            # validações básicas
            if pd.isna(data_fabricacao):
                return None

            if pd.isna(data_validade):
                return None

            if pd.isna(data_embarque):
                return None

            # embarque antes da fabricação
            if data_embarque < data_fabricacao:
                return None

            vida_total = (
                data_validade - data_fabricacao
            ).days

            vida_restante = (
                data_validade - data_embarque
            ).days

            # validade inválida
            if vida_total <= 0:
                return None

            shelf = (
                vida_restante / vida_total
            ) * 100

            # trava anti-dados absurdos
            if shelf < 0:
                return None

            if shelf > 100:
                return None

            return round(shelf, 2)

        except:

            return None

    resultado_fase4["data_bipagem"] = (
    base["data_bipagem"]
)

    resultado_fase4["shelf_calculado"] = (
        resultado_fase4.apply(
            lambda row: calcular_shelf(
                row["producao"],
                row["validade"],
                row["data_bipagem"]
            ),
            axis=1
        )
    )
    

    # =================================================
    # TRAZ CLIENTE PELO ITEM
    # =================================================

    cliente_item = detalhamento[
        [
            "ITEM",
            "CNPJ",
            "NOME"
        ]
    ].drop_duplicates()

    resultado_fase5 = resultado_fase4.merge(
        cliente_item,
        left_on="material",
        right_on="ITEM",
        how="left"
    )

    # =================================================
    # TRAZ REGRA SHELF
    # =================================================

    shelf_base = shelf[
        [
            "Destino",
            "Shelf"
        ]
    ].drop_duplicates()

    resultado_fase5 = resultado_fase5.merge(
        shelf_base,
        left_on="CNPJ",
        right_on="Destino",
        how="left"
    )

    # =================================================
    # CONVERSÃO SHELF
    # =================================================

    resultado_fase5["Shelf"] = pd.to_numeric(
        resultado_fase5["Shelf"],
        errors="coerce"
    )

    resultado_fase5["shelf_calculado"] = pd.to_numeric(
        resultado_fase5["shelf_calculado"],
        errors="coerce"
    )

    # =================================================
    # STATUS SHELF
    # =================================================

    resultado_fase5["Shelf"] = (
    pd.to_numeric(
        resultado_fase5["Shelf"],
        errors="coerce"
    ) * 100
)

    resultado_fase5["status_shelf"] = (
        "SEM DADOS"
    )

    resultado_fase5.loc[
        (
            pd.notna(
                resultado_fase5["shelf_calculado"]
            )
        )
        &
        (
            pd.notna(
                resultado_fase5["Shelf"]
            )
        )
        &
        (
            resultado_fase5["shelf_calculado"]
            >=
            resultado_fase5["Shelf"]
        ),
        "status_shelf"
    ] = "OK"

    resultado_fase5.loc[
        (
            pd.notna(
                resultado_fase5["shelf_calculado"]
            )
        )
        &
        (
            pd.notna(
                resultado_fase5["Shelf"]
            )
        )
        &
        (
            resultado_fase5["shelf_calculado"]
            <
            resultado_fase5["Shelf"]
        ),
        "status_shelf"
    ] = "FORA SHELF"

    # =================================================
    # MÉTRICAS
    # =================================================

    ok_shelf = len(
        resultado_fase5[
            resultado_fase5[
                "status_shelf"
            ] == "OK"
        ]
    )

    fora_shelf = len(
        resultado_fase5[
            resultado_fase5[
                "status_shelf"
            ] == "FORA SHELF"
        ]
    )

    col1, col2 = st.columns(2)

    col1.metric(
        "Shelf OK",
        ok_shelf
    )

    col2.metric(
        "Fora Shelf",
        fora_shelf
    )

    # =================================================
    # PREVIEW
    # =================================================

    preview_shelf = resultado_fase5[
        [
            "chave_palete",
            "material",
            "CNPJ",
            "NOME",
            "shelf_calculado",
            "Shelf",
            "status_shelf"
        ]
    ]

    st.subheader(
        "Resultado Shelf"
    )

    st.dataframe(
        preview_shelf
    )

    st.success(
        "FASE 5 concluída com sucesso"
    )     
    # =====================================================
    # FASE 6 — VALIDAÇÃO QUANTIDADES
    # =====================================================

    st.header("FASE 6 — Validação Quantidades")

    # =====================================================
    # NORMALIZAÇÃO
    # =====================================================

    resultado_fase5["material"] = (
        resultado_fase5["material"]
        .astype(str)
        .str.strip()
    )

    detalhamento["ITEM"] = (
        detalhamento["ITEM"]
        .astype(str)
        .str.strip()
    )

    # =====================================================
    # QUANTIDADE TXT
    # =====================================================

    txt_consolidado = (
        resultado_fase5.groupby(
            "material",
            dropna=False
        )["quantidade_txt"]
        .sum()
        .reset_index()
    )

    txt_consolidado.rename(
        columns={
            "material": "ITEM",
            "quantidade_txt": "QTD_TXT"
        },
        inplace=True
    )

    # =====================================================
    # QUANTIDADE DETALHAMENTO
    # =====================================================

    detalhamento["QTD_EMBALA"] = pd.to_numeric(
        detalhamento["QTD_EMBALA"],
        errors="coerce"
    )

    detalhamento_consolidado = (
        detalhamento.groupby(
            "ITEM",
            dropna=False
        )["QTD_EMBALA"]
        .sum()
        .reset_index()
    )

    detalhamento_consolidado.rename(
        columns={
            "QTD_EMBALA": "QTD_DETALHAMENTO"
        },
        inplace=True
    )

    # =====================================================
    # MERGE
    # =====================================================

    validacao_quantidade = (
        txt_consolidado.merge(
            detalhamento_consolidado,
            on="ITEM",
            how="outer"
        )
    )

    # =====================================================
    # TRATAMENTO
    # =====================================================

    validacao_quantidade["QTD_TXT"] = (
        pd.to_numeric(
            validacao_quantidade["QTD_TXT"],
            errors="coerce"
        ).fillna(0)
    )

    validacao_quantidade["QTD_DETALHAMENTO"] = (
        pd.to_numeric(
            validacao_quantidade["QTD_DETALHAMENTO"],
            errors="coerce"
        ).fillna(0)
    )

    # =====================================================
    # DIVERGÊNCIA
    # =====================================================

    validacao_quantidade["DIVERGENCIA"] = (
        validacao_quantidade["QTD_TXT"]
        -
        validacao_quantidade["QTD_DETALHAMENTO"]
    )

    # =====================================================
    # STATUS
    # =====================================================

    validacao_quantidade["STATUS"] = (
        validacao_quantidade["DIVERGENCIA"]
        .apply(
            lambda x:
                "OK"
                if x == 0
                else "DIVERGENTE"
        )
    )

    # =====================================================
    # RESULTADO
    # =====================================================

    st.subheader("Validação Quantidades")

    st.dataframe(
        validacao_quantidade
    )

    # =====================================================
    # MÉTRICAS
    # =====================================================

    total_itens = len(
        validacao_quantidade
    )

    itens_ok = len(
        validacao_quantidade[
            validacao_quantidade["STATUS"] == "OK"
        ]
    )

    itens_divergentes = len(
        validacao_quantidade[
            validacao_quantidade["STATUS"]
            == "DIVERGENTE"
        ]
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Itens",
        total_itens
    )

    col2.metric(
        "OK",
        itens_ok
    )

    col3.metric(
        "Divergentes",
        itens_divergentes
    )

    st.success(
        "FASE 6 concluída"
    )
    # =====================================================
    # FASE 7 — STATUS FINAL
    # =====================================================

    st.header("FASE 7 — Status Final")

    # =====================================================
    # MAPA DE DIVERGÊNCIA
    # =====================================================

    mapa_divergencia = (
        validacao_quantidade[
            ["ITEM", "STATUS"]
        ]
        .rename(
            columns={
                "STATUS": "status_quantidade"
            }
        )
    )

    # =====================================================
    # NORMALIZA MATERIAL
    # =====================================================

    resultado_fase5["material"] = (
        resultado_fase5["material"]
        .astype(str)
        .str.strip()
    )

    mapa_divergencia["ITEM"] = (
        mapa_divergencia["ITEM"]
        .astype(str)
        .str.strip()
    )

    # =====================================================
    # MERGE STATUS QUANTIDADE
    # =====================================================

    resultado_fase7 = (
    resultado_fase5.merge(
        mapa_divergencia,
        left_on="material",
        right_on="ITEM",
        how="left"
    )
    )

    # REMOVE COLUNA DUPLICADA
    resultado_fase7 = (
        resultado_fase7.loc[
            :,
            ~resultado_fase7.columns.duplicated()
        ]
    )

    # SE NÃO EXISTIR STATUS
    # PREENCHE COMO OK

    if "status_quantidade" not in resultado_fase7.columns:

        resultado_fase7["status_quantidade"] = "OK"

    # =====================================================
    # FUNÇÃO STATUS FINAL
    # =====================================================

    def definir_status_final(row):

        # pallet não encontrado
        if (
            row["status_pallet_encontrado"]
            !=
            "ENCONTRADO"
        ):

            return "REPROVADO"

        # lote bloqueado
        if (
            row["status_lote"]
            ==
            "BLOQUEADO"
        ):

            return "REPROVADO"

        # shelf inválido
        if (
            row["status_shelf"]
            ==
            "FORA SHELF"
        ):

            return "REPROVADO"

        # quantidade divergente
        if (
            row["status_quantidade"]
            ==
            "DIVERGENTE"
        ):

            return "REPROVADO"

        # sem dados shelf
        if (
            row["status_shelf"]
            ==
            "SEM DADOS"
        ):

            return "APROVADO COM ALERTA"

        return "APROVADO"

    # =====================================================
    # STATUS FINAL
    # =====================================================

    resultado_fase7["status_final"] = (
        resultado_fase7.apply(
            definir_status_final,
            axis=1
        )
    )

    # =====================================================
    # RESULTADO
    # =====================================================

    st.subheader("Resultado Final")

    st.dataframe(
        resultado_fase7
    )

    # =====================================================
    # MÉTRICAS
    # =====================================================

    total = len(resultado_fase7)

    aprovados = len(
        resultado_fase7[
            resultado_fase7["status_final"]
            ==
            "APROVADO"
        ]
    )

    reprovados = len(
        resultado_fase7[
            resultado_fase7["status_final"]
            ==
            "REPROVADO"
        ]
    )

    alerta = len(
        resultado_fase7[
            resultado_fase7["status_final"]
            ==
            "APROVADO COM ALERTA"
        ]
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total",
        total
    )

    col2.metric(
        "Aprovados",
        aprovados
    )

    col3.metric(
        "Reprovados",
        reprovados
    )

    col4.metric(
        "Alertas",
        alerta
    )

    st.success(
        "FASE 7 concluída"
    )
    # =====================================================
    # FASE 8 — DASHBOARD
    # =====================================================

    st.header("FASE 8 — Dashboard")

    # =====================================================
    # MÉTRICAS GERAIS
    # =====================================================

    total = len(resultado_fase7)

    aprovados = len(
        resultado_fase7[
            resultado_fase7["status_final"]
            ==
            "APROVADO"
        ]
    )

    reprovados = len(
        resultado_fase7[
            resultado_fase7["status_final"]
            ==
            "REPROVADO"
        ]
    )

    alertas = len(
        resultado_fase7[
            resultado_fase7["status_final"]
            ==
            "APROVADO COM ALERTA"
        ]
    )

    percentual = round(
        (aprovados / total) * 100,
        2
    ) if total > 0 else 0

    # =====================================================
    # OUTRAS MÉTRICAS
    # =====================================================

    bloqueados = len(
        resultado_fase7[
            resultado_fase7["status_lote"]
            ==
            "BLOQUEADO"
        ]
    )

    fora_shelf = len(
        resultado_fase7[
            resultado_fase7["status_shelf"]
            ==
            "FORA SHELF"
        ]
    )

    divergentes = len(
        resultado_fase7[
            resultado_fase7["status_quantidade"]
            ==
            "DIVERGENTE"
        ]
    )

    nao_encontrados = len(
        resultado_fase7[
            resultado_fase7["status_pallet_encontrado"]
            !=
            "ENCONTRADO"
        ]
    )

    # =====================================================
    # CARDS
    # =====================================================

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Pallets",
        total
    )

    col2.metric(
        "Aprovados",
        aprovados
    )

    col3.metric(
        "% Conformidade",
        f"{percentual}%"
    )

    col4, col5, col6 = st.columns(3)

    col4.metric(
        "Lotes Bloqueados",
        bloqueados
    )

    col5.metric(
        "Fora Shelf",
        fora_shelf
    )

    col6.metric(
        "Divergências",
        divergentes
    )

    # =====================================================
    # GRÁFICO STATUS FINAL
    # =====================================================

    grafico_status = (
        resultado_fase7[
            "status_final"
        ]
        .value_counts()
        .reset_index()
    )

    grafico_status.columns = [
        "Status",
        "Quantidade"
    ]

    fig1 = px.pie(
        grafico_status,
        names="Status",
        values="Quantidade",
        title="Status Final"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    # =====================================================
    # GRÁFICO LOTES
    # =====================================================

    grafico_lotes = (
        resultado_fase7[
            "status_lote"
        ]
        .value_counts()
        .reset_index()
    )

    grafico_lotes.columns = [
        "Status",
        "Quantidade"
    ]

    fig2 = px.bar(
        grafico_lotes,
        x="Status",
        y="Quantidade",
        title="Lotes Bloqueados"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # =====================================================
    # GRÁFICO SHELF
    # =====================================================

    grafico_shelf = (
        resultado_fase7[
            "status_shelf"
        ]
        .value_counts()
        .reset_index()
    )

    grafico_shelf.columns = [
        "Status",
        "Quantidade"
    ]

    fig3 = px.bar(
        grafico_shelf,
        x="Status",
        y="Quantidade",
        title="Shelf Life"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

    # =====================================================
    # GRÁFICO QUANTIDADE
    # =====================================================

    grafico_qtd = (
        validacao_quantidade[
            "STATUS"
        ]
        .value_counts()
        .reset_index()
    )

    grafico_qtd.columns = [
        "Status",
        "Quantidade"
    ]

    fig4 = px.pie(
        grafico_qtd,
        names="Status",
        values="Quantidade",
        title="Divergência Quantidade"
    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )

    st.success(
        "FASE 8 concluída"
    )
