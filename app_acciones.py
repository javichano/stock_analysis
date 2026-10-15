"""
Analizador visual de acciones (Streamlit + yfinance).

Instalación (una sola vez):
    pip install streamlit yfinance pandas

Ejecutar:
    streamlit run app_acciones.py

Se abrirá solo en el navegador (http://localhost:8501).
Los datos vienen de Yahoo Finance y pueden faltar o ser imprecisos.
Es una herramienta de apoyo, no una recomendación de inversión.
"""

import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Analizador de acciones", layout="wide")

st.title("Analizador de acciones")
st.caption("Datos de Yahoo Finance. Herramienta de apoyo, no una recomendación de inversión.")

# ---------- Barra lateral ----------
entrada = st.sidebar.text_input("Tickers (separados por coma)", "AAPL, MSFT, NVDA, KO, JNJ")
periodo = st.sidebar.selectbox("Periodo del gráfico de precios", ["6mo", "1y", "2y", "5y"], index=2)
st.sidebar.caption("Acciones españolas: añade .MC (ej. SAN.MC, ITX.MC)")

tickers = [t.strip().upper() for t in entrada.split(",") if t.strip()]


# ---------- Funciones ----------
def porcentaje(valor):
    """Pasa 0.25 a 25.0 (si el dato existe)."""
    if valor is None:
        return None
    return valor * 100


@st.cache_data(ttl=3600)
def obtener_datos(ticker):
    """Descarga los datos de una empresa y calcula sus ratios."""
    info = yf.Ticker(ticker).info

    deuda = info.get("totalDebt")
    caja = info.get("totalCash")
    ebitda = info.get("ebitda")
    deuda_neta_ebitda = None
    if deuda is not None and caja is not None and ebitda:
        deuda_neta_ebitda = (deuda - caja) / ebitda

    peg = info.get("pegRatio") or info.get("trailingPegRatio")

    return {
        "Ticker": ticker,
        "Empresa": info.get("shortName"),
        "Sector": info.get("sector"),
        "Precio": info.get("currentPrice"),
        "PER": info.get("trailingPE"),
        "PER futuro": info.get("forwardPE"),
        "PEG": peg,
        "P/Ventas": info.get("priceToSalesTrailing12Months"),
        "P/Valor contable": info.get("priceToBook"),
        "Margen neto %": porcentaje(info.get("profitMargins")),
        "Margen operativo %": porcentaje(info.get("operatingMargins")),
        "ROE %": porcentaje(info.get("returnOnEquity")),
        "Crec. ingresos %": porcentaje(info.get("revenueGrowth")),
        "Deuda neta/EBITDA": deuda_neta_ebitda,
        "Flujo caja libre": info.get("freeCashflow"),
    }


@st.cache_data(ttl=3600)
def obtener_precios(lista_tickers, periodo):
    """Precios de cierre, todos empezando en base 100 para poder compararlos."""
    datos = yf.download(list(lista_tickers), period=periodo, auto_adjust=True, progress=False)["Close"]
    if isinstance(datos, pd.Series):
        datos = datos.to_frame(lista_tickers[0])
    datos = datos.dropna(how="all").ffill()
    return datos / datos.iloc[0] * 100


def avisos(fila):
    """Devuelve las señales de alerta en un texto."""
    lista = []

    if pd.notna(fila["PER"]) and fila["PER"] > 40:
        lista.append("PER alto (>40)")
    if pd.notna(fila["PER"]) and fila["PER"] < 0:
        lista.append("Pierde dinero")
    if pd.notna(fila["PEG"]) and fila["PEG"] > 2:
        lista.append("PEG alto (>2)")
    if pd.notna(fila["Deuda neta/EBITDA"]) and fila["Deuda neta/EBITDA"] > 4:
        lista.append("Mucha deuda (>4)")
    if pd.notna(fila["Flujo caja libre"]) and fila["Flujo caja libre"] < 0:
        lista.append("Flujo de caja negativo")
    if pd.notna(fila["Crec. ingresos %"]) and fila["Crec. ingresos %"] < 0:
        lista.append("Ingresos a la baja")

    return ", ".join(lista) if lista else "Sin alertas"


# ---------- Datos ----------
if not tickers:
    st.info("Escribe al menos un ticker en la barra lateral.")
    st.stop()

filas = []
for ticker in tickers:
    try:
        filas.append(obtener_datos(ticker))
    except Exception as error:
        st.warning(f"No se pudo obtener {ticker}: {error}")

if not filas:
    st.error("No se obtuvo ningún dato.")
    st.stop()

tabla = pd.DataFrame(filas)
tabla["Alertas"] = [avisos(fila) for _, fila in tabla.iterrows()]

# ---------- Pestañas ----------
pestana1, pestana2, pestana3, pestana4 = st.tabs(
    ["Resumen", "Valoración", "Calidad y deuda", "Evolución del precio"]
)

with pestana1:
    st.subheader("Comparativa")
    st.dataframe(tabla.drop(columns=["Flujo caja libre"]).round(2), use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar CSV",
        tabla.to_csv(index=False, encoding="utf-8-sig"),
        file_name="analisis_acciones.csv",
        mime="text/csv",
    )

with pestana2:
    st.subheader("Cuánto pagas por cada empresa (menor = más barata)")
    col1, col2 = st.columns(2)
    with col1:
        st.write("PER (precio/beneficio)")
        st.bar_chart(tabla.set_index("Ticker")["PER"])
    with col2:
        st.write("PEG (PER / crecimiento)")
        st.bar_chart(tabla.set_index("Ticker")["PEG"])
    col3, col4 = st.columns(2)
    with col3:
        st.write("Precio / Ventas")
        st.bar_chart(tabla.set_index("Ticker")["P/Ventas"])
    with col4:
        st.write("Precio / Valor contable")
        st.bar_chart(tabla.set_index("Ticker")["P/Valor contable"])

with pestana3:
    st.subheader("Rentabilidad y salud financiera")
    col1, col2 = st.columns(2)
    with col1:
        st.write("Margen neto %")
        st.bar_chart(tabla.set_index("Ticker")["Margen neto %"])
    with col2:
        st.write("ROE %")
        st.bar_chart(tabla.set_index("Ticker")["ROE %"])
    col3, col4 = st.columns(2)
    with col3:
        st.write("Crecimiento de ingresos %")
        st.bar_chart(tabla.set_index("Ticker")["Crec. ingresos %"])
    with col4:
        st.write("Deuda neta / EBITDA (más de 4 = mucha deuda)")
        st.bar_chart(tabla.set_index("Ticker")["Deuda neta/EBITDA"])

    st.subheader("Alertas")
    for _, fila in tabla.iterrows():
        st.write(f"**{fila['Ticker']}**: {fila['Alertas']}")

with pestana4:
    st.subheader(f"Evolución del precio (base 100, {periodo})")
    try:
        st.line_chart(obtener_precios(tuple(tickers), periodo))
    except Exception as error:
        st.warning(f"No se pudieron descargar los precios: {error}")
