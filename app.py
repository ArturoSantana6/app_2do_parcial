import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from io import BytesIO

st.set_page_config(page_title="Análisis Financiero Profesional", layout="wide")

def calcular_cagr(df, años):
    try:
        dias = 252 * años
        if len(df) < dias:
            return None
        final = df["Close"].iloc[-1]
        inicio = df["Close"].iloc[-dias]
        return (final / inicio) ** (1 / años) - 1
    except:
        return None

def validar_ticker(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1d")
        return not data.empty
    except:
        return False

def obtener_datos_basicos(ticker):
    data = yf.Ticker(ticker)
    info = data.info
    hist = data.history(period="5y")
    return info, hist

def exportar_excel(df_dict):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for sheet, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet)
    buffer.seek(0)
    return buffer

st.title("📊 Análisis Financiero Profesional")
st.markdown("Compara un activo con otros dos y el índice S&P 500. Visualiza su desempeño, riesgo, métricas y exporta los resultados.")

with st.sidebar:
    st.image("https://img.icons8.com/color/96/graph.png", width=50)
    st.header("🔎 Instrucciones")
    ticker_main = st.text_input("Ticker Principal:", value="AAPL")
    comp1 = st.text_input("Comparar con 1:", value="")
    comp2 = st.text_input("Comparar con 2:", value="")
    buscar = st.button("🔍 Analizar")

if buscar:
    tickers = []
    if ticker_main:
        tickers.append(ticker_main)
    if comp1:
        tickers.append(comp1)
    if comp2:
        tickers.append(comp2)
    tickers.append("^GSPC")

    datos = {}
    historicos = {}

    for tk in tickers:
        if validar_ticker(tk):
            info, hist = obtener_datos_basicos(tk)
            datos[tk] = info
            historicos[tk] = hist
        else:
            st.error(f"❌ El ticker '{tk}' es inválido. Por favor revisa e intenta nuevamente.")

    if ticker_main in datos:
        tabs = st.tabs(["📄 Perfil", "📈 Precios", "📊 Métricas", "📁 Exportar"])

        with tabs[0]:
            info = datos[ticker_main]
            st.subheader("🏢 Perfil de la Empresa")
            st.markdown(f"**Nombre:** {info.get('longName', 'N/A')}")
            st.markdown(f"**Sector:** {info.get('sector', 'N/A')}")
            st.markdown(f"**Descripción:** {info.get('longBusinessSummary', 'No disponible')}")

        with tabs[1]:
            st.subheader("📈 Evolución Histórica de Precios (5 años)")
            st.markdown("Los precios están normalizados para facilitar la comparación (base 100). Se incluye una línea de tendencia lineal para el activo principal.")
            fig = go.Figure()
            for tk, df in historicos.items():
                base = df["Close"].iloc[0]
                serie_normalizada = df["Close"] / base * 100
                fig.add_trace(go.Scatter(x=df.index, y=serie_normalizada, mode='lines', name=tk))
                if tk == ticker_main:
                    x_numeric = np.arange(len(df))
                    y = serie_normalizada.values
                    coef = np.polyfit(x_numeric, y, 1)
                    tendencia = coef[0] * x_numeric + coef[1]
                    fig.add_trace(go.Scatter(
                        x=df.index, y=tendencia,
                        mode='lines', name=f"Tendencia ({tk})",
                        line=dict(dash='dash', color='gray')
                    ))
            fig.update_layout(title="Comparativa de Precios (Normalizados)", xaxis_title="Fecha", yaxis_title="Índice Base 100")
            st.plotly_chart(fig, use_container_width=True)

        with tabs[2]:
            st.subheader("📊 Análisis Financiero")
            st.markdown("### 🔍 Comparativa de Rendimiento y Riesgo")
            resultados = {}
            for tk, df in historicos.items():
                cagr_1 = calcular_cagr(df, 1)
                cagr_3 = calcular_cagr(df, 3)
                cagr_5 = calcular_cagr(df, 5)
                daily_ret = df["Close"].pct_change().dropna()
                vol = np.std(daily_ret) * np.sqrt(252)
                resultados[tk] = {
                    "CAGR 1 año": f"{cagr_1*100:.2f}%" if cagr_1 else "N/A",
                    "CAGR 3 años": f"{cagr_3*100:.2f}%" if cagr_3 else "N/A",
                    "CAGR 5 años": f"{cagr_5*100:.2f}%" if cagr_5 else "N/A",
                    "Volatilidad Anualizada": f"{vol:.2%}"
                }

            st.latex(r"CAGR = \left( \frac{\text{Precio}_{\text{final}}}{\text{Precio}_{\text{inicial}}} \right)^{\frac{1}{n}} - 1")
            st.dataframe(pd.DataFrame(resultados).T)

            st.subheader("📌 Ratios Financieros Clave")
            info = datos[ticker_main]
            ratios = {
                "P/E": info.get("trailingPE", "N/A"),
                "P/B": info.get("priceToBook", "N/A"),
                "ROE": f"{info.get('returnOnEquity', 0)*100:.2f}%" if info.get("returnOnEquity") else "N/A",
                "Debt/Equity": info.get("debtToEquity", "N/A"),
                "Margen Neto": f"{info.get('netMargins', 0)*100:.2f}%" if info.get("netMargins") else "N/A"
            }
            st.dataframe(pd.DataFrame.from_dict(ratios, orient="index", columns=["Valor"]))

        with tabs[3]:
            st.subheader("📁 Exportar Resultados")
            excel_data = exportar_excel({
                "Comparativa": pd.DataFrame(resultados).T,
                "Ratios": pd.DataFrame.from_dict(ratios, orient="index", columns=["Valor"])
            })
            st.download_button("📥 Descargar Excel", data=excel_data, file_name="analisis_financiero.xlsx", mime="application/vnd.ms-excel")
