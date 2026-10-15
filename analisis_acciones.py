"""
Analizador de acciones: compara ratios de valoración de varias empresas.

Instalación (una sola vez):
    pip install yfinance pandas

Uso:
    python analisis_acciones.py
    python analisis_acciones.py AAPL MSFT KO     (tickers por línea de comandos)

Los datos vienen de Yahoo Finance (vía yfinance). Pueden faltar o ser
imprecisos, así que contrástalos siempre con otra fuente antes de invertir.
Esto es una herramienta de apoyo, no una recomendación de inversión.
"""

import sys
import yfinance as yf
import pandas as pd

# Cambia esta lista por las empresas que quieras analizar
TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "JNJ", "KO"]


def obtener_datos(ticker):
    """Descarga los datos de una empresa y calcula sus ratios."""
    info = yf.Ticker(ticker).info

    # Deuda neta / EBITDA (lo calculamos nosotros)
    deuda = info.get("totalDebt")
    caja = info.get("totalCash")
    ebitda = info.get("ebitda")
    deuda_neta_ebitda = None
    if deuda is not None and caja is not None and ebitda:
        deuda_neta_ebitda = (deuda - caja) / ebitda

    # Yahoo a veces llama de forma distinta al PEG
    peg = info.get("pegRatio") or info.get("trailingPegRatio")

    return {
        "Ticker": ticker,
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


def porcentaje(valor):
    """Pasa 0.25 a 25.0 (si el dato existe)."""
    if valor is None:
        return None
    return valor * 100


def avisos(fila):
    """Devuelve una lista de señales de alerta sencillas."""
    lista = []

    per = fila["PER"]
    if per is not None and per > 40:
        lista.append("PER alto (>40)")
    if per is not None and per < 0:
        lista.append("Pierde dinero")

    peg = fila["PEG"]
    if peg is not None and peg > 2:
        lista.append("PEG alto (>2)")

    deuda = fila["Deuda neta/EBITDA"]
    if deuda is not None and deuda > 4:
        lista.append("Mucha deuda (>4)")

    fcf = fila["Flujo caja libre"]
    if fcf is not None and fcf < 0:
        lista.append("Flujo de caja negativo")

    crecimiento = fila["Crec. ingresos %"]
    if crecimiento is not None and crecimiento < 0:
        lista.append("Ingresos a la baja")

    if not lista:
        return "Sin alertas"
    return ", ".join(lista)


def main():
    # Si pasas tickers por consola, se usan esos
    tickers = sys.argv[1:] if len(sys.argv) > 1 else TICKERS

    filas = []
    for ticker in tickers:
        try:
            print(f"Descargando {ticker}...")
            filas.append(obtener_datos(ticker.upper()))
        except Exception as error:
            print(f"  No se pudo obtener {ticker}: {error}")

    if not filas:
        print("No se obtuvo ningún dato.")
        return

    tabla = pd.DataFrame(filas)
    tabla["Alertas"] = [avisos(fila) for _, fila in tabla.iterrows()]

    # Mostrar todas las columnas con 2 decimales
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 250)
    pd.options.display.float_format = "{:,.2f}".format

    print("\n=== COMPARATIVA ===")
    print(tabla.drop(columns=["Flujo caja libre"]).to_string(index=False))

    # Guardar en CSV para abrirlo en Excel
    tabla.to_csv("analisis_acciones.csv", index=False, encoding="utf-8-sig")
    print("\nGuardado en analisis_acciones.csv")


if __name__ == "__main__":
    main()
