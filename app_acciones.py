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

# Borra el caché y vuelve a descargar los datos
if st.sidebar.button("Actualizar datos"):
    st.cache_data.clear()
    st.rerun()


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


# ---------- Glosario ----------
GLOSARIO = [
    {
        "nombre": "PER (precio/beneficio)",
        "que_es": "Cuántos años de beneficios actuales tendrías que esperar para recuperar lo que pagas por la acción. Cuanto más alto, más cara parece.",
        "formula": "PER = Precio de la acción / Beneficio por acción (BPA)",
        "ejemplo": "La acción cuesta 100 € y la empresa gana 5 € por acción al año: PER = 100 / 5 = 20.",
        "interpretacion": "Compáralo con empresas del mismo sector y con el histórico de la propia empresa. Un PER alto suele significar que el mercado espera mucho crecimiento; uno bajo, que espera poco o que hay problemas.",
        "ojo": "Si la empresa pierde dinero, el PER es negativo o no existe. Un año con beneficios extraordinarios lo distorsiona.",
    },
    {
        "nombre": "PER futuro",
        "que_es": "Lo mismo que el PER, pero usando el beneficio que los analistas esperan para los próximos 12 meses.",
        "formula": "PER futuro = Precio de la acción / Beneficio por acción estimado",
        "ejemplo": "La acción cuesta 100 € y se espera que gane 6 € por acción: PER futuro = 100 / 6 = 16,7.",
        "interpretacion": "Si es bastante menor que el PER actual, se espera que los beneficios crezcan. Si es mayor, se espera que bajen.",
        "ojo": "Se basa en previsiones, y las previsiones fallan con frecuencia.",
    },
    {
        "nombre": "PEG",
        "que_es": "El PER ajustado por crecimiento. Sirve para saber si un PER alto está justificado por lo rápido que crece la empresa.",
        "formula": "PEG = PER / Crecimiento anual esperado del beneficio (en %)",
        "ejemplo": "PER de 20 y beneficios que crecen un 10% al año: PEG = 20 / 10 = 2.",
        "interpretacion": "Alrededor de 1 se considera equilibrado, por debajo de 1 barato respecto a su crecimiento y por encima de 2 caro.",
        "ojo": "Depende de la estimación de crecimiento, que es una predicción. Úsalo como orientación, no como verdad.",
    },
    {
        "nombre": "P/Ventas (precio/ventas)",
        "que_es": "Cuánto pagas por cada euro que la empresa vende al año. Es útil cuando todavía no tiene beneficios.",
        "formula": "P/Ventas = Capitalización bursátil / Ingresos anuales",
        "ejemplo": "La empresa vale 1.000 M€ en bolsa y vende 250 M€ al año: P/Ventas = 1.000 / 250 = 4.",
        "interpretacion": "Cuanto más bajo, más barata. Compárala solo con empresas del mismo sector.",
        "ojo": "No dice si la empresa gana dinero. Un software con márgenes altos puede justificar un P/Ventas mucho mayor que un supermercado.",
    },
    {
        "nombre": "P/Valor contable (P/B)",
        "que_es": "Compara lo que vale la empresa en bolsa con lo que dicen sus libros (activos menos deudas).",
        "formula": "P/B = Precio de la acción / (Patrimonio neto / Número de acciones)",
        "ejemplo": "La acción cuesta 30 € y el valor contable por acción es 20 €: P/B = 30 / 20 = 1,5.",
        "interpretacion": "Por debajo de 1 significa que cotiza por debajo de su valor en libros. Es muy usado en bancos y empresas con muchos activos físicos.",
        "ojo": "En tecnológicas, cuyo valor está en marca, software o patentes, el P/B siempre sale alto sin que eso signifique que estén caras.",
    },
    {
        "nombre": "Margen neto %",
        "que_es": "De cada 100 € que vende la empresa, cuántos se quedan como beneficio final después de pagar todo (costes, intereses e impuestos).",
        "formula": "Margen neto = (Beneficio neto / Ingresos) x 100",
        "ejemplo": "Gana 20 M€ y vende 200 M€: margen neto = (20 / 200) x 100 = 10%.",
        "interpretacion": "Cuanto más alto, mejor. Lo importante es que se mantenga o mejore con los años.",
        "ojo": "Cada sector tiene márgenes distintos: un supermercado con 3% puede ser excelente y un software con 3% muy malo.",
    },
    {
        "nombre": "Margen operativo %",
        "que_es": "Lo mismo que el margen neto, pero antes de intereses e impuestos. Mide lo rentable que es el negocio en sí.",
        "formula": "Margen operativo = (Beneficio operativo / Ingresos) x 100",
        "ejemplo": "Beneficio operativo de 30 M€ con ventas de 200 M€: (30 / 200) x 100 = 15%.",
        "interpretacion": "Si el margen operativo es bueno pero el neto es bajo, el problema suele ser la deuda (muchos intereses) o los impuestos.",
        "ojo": "Igual que el anterior: compáralo con empresas del mismo sector.",
    },
    {
        "nombre": "ROE % (rentabilidad sobre recursos propios)",
        "que_es": "Cuánto beneficio genera la empresa con el dinero de sus accionistas.",
        "formula": "ROE = (Beneficio neto / Patrimonio neto) x 100",
        "ejemplo": "Gana 15 M€ y su patrimonio neto es 100 M€: ROE = (15 / 100) x 100 = 15%.",
        "interpretacion": "Un ROE sostenido por encima del 15% suele indicar un buen negocio.",
        "ojo": "Pedir mucha deuda puede inflar el ROE sin que el negocio sea mejor. Míralo junto con la deuda.",
    },
    {
        "nombre": "Crecimiento de ingresos %",
        "que_es": "Cuánto han crecido (o caído) las ventas de la empresa respecto al periodo anterior.",
        "formula": "Crecimiento = ((Ingresos actuales - Ingresos anteriores) / Ingresos anteriores) x 100",
        "ejemplo": "Antes vendía 200 M€ y ahora 230 M€: ((230 - 200) / 200) x 100 = 15%.",
        "interpretacion": "Crecer de forma constante es buena señal. Un crecimiento negativo significa que las ventas bajan.",
        "ojo": "Yahoo suele compararlo con el mismo trimestre del año anterior, así que un solo trimestre malo o bueno puede engañar.",
    },
    {
        "nombre": "EBITDA",
        "que_es": "Beneficio de la empresa antes de restar intereses, impuestos, depreciaciones y amortizaciones. Es una forma de medir lo que genera el negocio antes de las partidas financieras y contables.",
        "formula": "EBITDA = Beneficio operativo + Depreciaciones + Amortizaciones",
        "ejemplo": "Beneficio operativo de 30 M€ y depreciaciones y amortizaciones de 10 M€: EBITDA = 40 M€.",
        "interpretacion": "Se usa para comparar empresas con distintos niveles de deuda e inversión, y es la base del ratio Deuda neta/EBITDA.",
        "ojo": "Ignora el gasto en inversiones que la empresa necesita para seguir funcionando, así que puede verse mejor de lo que es.",
    },
    {
        "nombre": "Deuda neta / EBITDA",
        "que_es": "Cuántos años tardaría la empresa en pagar su deuda neta con lo que genera. Mide el riesgo por endeudamiento.",
        "formula": "Deuda neta / EBITDA = (Deuda total - Caja) / EBITDA",
        "ejemplo": "Deuda de 500 M€, caja de 100 M€ y EBITDA de 200 M€: (500 - 100) / 200 = 2.",
        "interpretacion": "Por debajo de 2 es cómodo, entre 2 y 4 hay que vigilarlo y por encima de 4 suele preocupar. Un valor negativo significa que tiene más caja que deuda.",
        "ojo": "Los umbrales son orientativos: sectores estables (energía, telecomunicaciones) toleran más deuda que los cíclicos.",
    },
    {
        "nombre": "Flujo de caja libre",
        "que_es": "El dinero real que le sobra a la empresa después de pagar sus gastos y las inversiones necesarias para mantener el negocio.",
        "formula": "Flujo de caja libre = Flujo de caja operativo - Inversiones en activos (capex)",
        "ejemplo": "Genera 300 M€ con su actividad e invierte 100 M€ en equipos e instalaciones: 300 - 100 = 200 M€.",
        "interpretacion": "Si es positivo y crece, la empresa puede pagar dividendos, reducir deuda o recomprar acciones. Es más difícil de maquillar que el beneficio contable.",
        "ojo": "Puede ser negativo en una empresa que invierte mucho para crecer, pero no es sostenible para siempre.",
    },
    {
        "nombre": "Alertas de esta app",
        "que_es": "Avisos automáticos cuando un ratio cruza un umbral sencillo.",
        "formula": "PER > 40, PER negativo, PEG > 2, Deuda neta/EBITDA > 4, flujo de caja libre negativo, ingresos a la baja",
        "ejemplo": "Una empresa con PER de 55 mostrará 'PER alto (>40)'.",
        "interpretacion": "Una alerta es un motivo para investigar más, no para descartar la empresa.",
        "ojo": "Los umbrales son fijos y no tienen en cuenta el sector. Una empresa de crecimiento puede merecer un PER alto.",
    },
]

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
pestana1, pestana2, pestana3, pestana4, pestana5 = st.tabs(
    ["Resumen", "Valoración", "Calidad y deuda", "Evolución del precio", "Glosario"]
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

with pestana5:
    st.subheader("Glosario: qué significa cada ratio")
    st.write(
        "Ningún ratio sirve por sí solo. Compara siempre empresas del mismo sector, "
        "mira varios ratios a la vez y consulta cómo han evolucionado con los años. "
        "Los umbrales que se mencionan son orientativos."
    )
    for item in GLOSARIO:
        with st.expander(item["nombre"]):
            st.write(item["que_es"])
            st.markdown("**Fórmula**")
            st.code(item["formula"], language="text")
            st.markdown(f"**Ejemplo:** {item['ejemplo']}")
            st.markdown(f"**Cómo interpretarlo:** {item['interpretacion']}")
            st.markdown(f"**Ojo:** {item['ojo']}")
