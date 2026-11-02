
import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import json
from pathlib import Path
from datetime import datetime

# ==================================
# НАСТРОЙКИ
# ==================================

st.set_page_config(
    page_title="Crypto AI Analyst 5.0",
    page_icon="₿",
    layout="wide"
)

st.title("₿ Crypto AI Analyst 5.0")
st.caption("Учебная аналитика криптовалютного рынка")

exchange = ccxt.binance({
    "enableRateLimit": True
})

PORTFOLIO_FILE = Path(__file__).resolve().parent.parent / "portfolio.json"

coins = {
    "Bitcoin": "BTC/USDT",
    "Ethereum": "ETH/USDT",
    "Solana": "SOL/USDT"
}

symbols = {
    "BTC": "BTC/USDT",
    "ETH": "ETH/USDT",
    "SOL": "SOL/USDT"
}

# ==================================
# СОХРАНЕНИЕ ДАННЫХ
# ==================================

def load_portfolio():
    if PORTFOLIO_FILE.exists():
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

            return data

        except (json.JSONDecodeError, OSError):
            st.warning("Не удалось прочитать файл портфеля.")

    return {
        "balance": 10000.0,
        "portfolio": {
            "BTC": 0.0,
            "ETH": 0.0,
            "SOL": 0.0
        },
        "history": [],
        "equity_history": []
    }


def save_portfolio():
    data = {
        "balance": st.session_state.balance,
        "portfolio": st.session_state.portfolio,
        "history": st.session_state.history,
        "equity_history": st.session_state.equity_history
    }

    temp_file = PORTFOLIO_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    temp_file.replace(PORTFOLIO_FILE)


# ==================================
# ЗАГРУЗКА ПОРТФЕЛЯ
# ==================================

saved_data = load_portfolio()

if "balance" not in st.session_state:
    st.session_state.balance = float(
        saved_data.get("balance", 10000.0)
    )

if "portfolio" not in st.session_state:
    st.session_state.portfolio = saved_data.get(
        "portfolio",
        {"BTC": 0.0, "ETH": 0.0, "SOL": 0.0}
    )

if "history" not in st.session_state:
    st.session_state.history = saved_data.get("history", [])

if "equity_history" not in st.session_state:
    st.session_state.equity_history = saved_data.get(
        "equity_history", []
    )

if "last_prices" not in st.session_state:
    st.session_state.last_prices = {}

# ==================================
# ПОЛУЧЕНИЕ ЦЕН
# ==================================

def get_price(symbol):
    ticker = exchange.fetch_ticker(symbol)
    return float(ticker["last"])


def get_prices():
    result = {}

    for ticker, symbol in symbols.items():
        result[ticker] = get_price(symbol)

    return result


# ==================================
# АНАЛИЗ РЫНКА
# ==================================

st.header("📈 Анализ рынка")

coin = st.selectbox(
    "Выбери криптовалюту",
    list(coins.keys())
)

timeframe = st.selectbox(
    "Период графика",
    ["1h", "4h", "1d"]
)

if st.button("Анализировать"):
    try:
        symbol = coins[coin]

        with st.spinner("Получаем рыночные данные..."):
            data = exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                limit=200
            )

        df = pd.DataFrame(
            data,
            columns=[
                "time", "open", "high",
                "low", "close", "volume"
            ]
        )

        df["time"] = pd.to_datetime(
            df["time"], unit="ms"
        )

        # SMA
        df["SMA20"] = df["close"].rolling(20).mean()
        df["SMA50"] = df["close"].rolling(50).mean()

        # RSI
        delta = df["close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(
            alpha=1/14,
            adjust=False
        ).mean()

        avg_loss = loss.ewm(
            alpha=1/14,
            adjust=False
        ).mean()

        rs = avg_gain / avg_loss.replace(0, 0.000001)

        df["RSI"] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df["close"].ewm(
            span=12,
            adjust=False
        ).mean()

        ema26 = df["close"].ewm(
            span=26,
            adjust=False
        ).mean()

        df["MACD"] = ema12 - ema26

        df["Signal"] = df["MACD"].ewm(
            span=9,
            adjust=False
        ).mean()

        last = df.iloc[-1]
        rsi = last["RSI"]

        # Оценка технических сигналов
        score = 0

        if last["SMA20"] > last["SMA50"]:
            score += 1
        else:
            score -= 1

        if last["MACD"] > last["Signal"]:
            score += 1
        else:
            score -= 1

        if 40 <= rsi <= 65:
            score += 1
        elif rsi < 30 or rsi > 70:
            score -= 1

        # Показатели
        st.subheader("Основные показатели")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Последняя цена",
            f"${last['close']:,.2f}"
        )

        col2.metric(
            "RSI",
            f"{rsi:.2f}"
        )

        col3.metric(
            "Индекс сигналов",
            f"{score}/3"
        )

        # График цены
        st.subheader("График цены")

        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Цена"
        ))

        fig.add_trace(go.Scatter(
            x=df["time"],
            y=df["SMA20"],
            name="SMA 20"
        ))

        fig.add_trace(go.Scatter(
            x=df["time"],
            y=df["SMA50"],
            name="SMA 50"
        ))

        fig.update_layout(
            height=500,
            xaxis_rangeslider_visible=False
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # MACD
        st.subheader("MACD")

        macd_fig = go.Figure()

        macd_fig.add_trace(go.Scatter(
            x=df["time"],
            y=df["MACD"],
            name="MACD"
        ))

        macd_fig.add_trace(go.Scatter(
            x=df["time"],
            y=df["Signal"],
            name="Signal"
        ))

        macd_fig.update_layout(height=300)

        st.plotly_chart(
            macd_fig,
            use_container_width=True
        )

        # Сканер
        st.subheader("AI Market Scanner")

        if score >= 2:
            st.success("Позитивный технический фон")
        elif score <= -2:
            st.error("Негативный технический фон")
        else:
            st.info("Нейтральный технический фон")

        if rsi > 70:
            st.warning("RSI выше 70 — зона перекупленности.")
        elif rsi < 30:
            st.warning("RSI ниже 30 — зона перепроданности.")
        else:
            st.info("RSI находится между 30 и 70.")

        if last["SMA20"] > last["SMA50"]:
            st.write("SMA 20 выше SMA 50.")
        else:
            st.write("SMA 20 ниже SMA 50.")

        if last["MACD"] > last["Signal"]:
            st.write("MACD выше сигнальной линии.")
        else:
            st.write("MACD ниже сигнальной линии.")

        st.caption(
            "Это экспериментальная оценка индикаторов, "
            "а не прогноз и не рекомендация."
        )

    except Exception as error:
        st.error(f"Ошибка анализа: {error}")


# ==================================
# ВИРТУАЛЬНЫЙ ПОРТФЕЛЬ
# ==================================

st.divider()
st.header("💼 Виртуальный портфель")

try:
    current_prices = get_prices()
    st.session_state.last_prices = current_prices

except Exception as error:
    st.warning(f"Не удалось обновить котировки: {error}")

prices = st.session_state.last_prices

portfolio_value = sum(
    st.session_state.portfolio.get(coin, 0.0)
    * prices.get(coin, 0.0)
    for coin in symbols
)

total_value = (
    st.session_state.balance + portfolio_value
)

profit = total_value - 10000.0

col1, col2, col3 = st.columns(3)

col1.metric(
    "Свободный баланс",
    f"${st.session_state.balance:,.2f}"
)

col2.metric(
    "Стоимость монет",
    f"${portfolio_value:,.2f}"
)

col3.metric(
    "Общая стоимость",
    f"${total_value:,.2f}",
    delta=f"${profit:,.2f}"
)

# ==================================
# МОИ АКТИВЫ
# ==================================

st.subheader("Мои активы")

asset_data = []

for ticker in symbols:
    quantity = st.session_state.portfolio.get(ticker, 0.0)
    price = prices.get(ticker, 0.0)

    asset_data.append({
        "Монета": ticker,
        "Количество": quantity,
        "Цена": price,
        "Стоимость": quantity * price
    })

st.dataframe(
    pd.DataFrame(asset_data),
    use_container_width=True,
    hide_index=True
)

# ==================================
# ГРАФИК КАПИТАЛА
# ==================================

st.subheader("📊 Изменение виртуального капитала")

if st.session_state.equity_history:
    equity_df = pd.DataFrame(
        st.session_state.equity_history
    )

    if not equity_df.empty:
        equity_df["Время"] = pd.to_datetime(
            equity_df["Время"]
        )

        chart = go.Figure()

        chart.add_trace(go.Scatter(
            x=equity_df["Время"],
            y=equity_df["Стоимость"],
            mode="lines+markers",
            name="Капитал"
        ))

        chart.update_layout(
            height=350,
            yaxis_title="USD",
            xaxis_title="Дата"
        )

        st.plotly_chart(
            chart,
            use_container_width=True
        )
else:
    st.info(
        "График появится после первой виртуальной операции."
    )

# ==================================
# ВИРТУАЛЬНАЯ ТОРГОВЛЯ
# ==================================

st.divider()
st.header("🧪 Симулятор виртуальных операций")

trade_coin = st.selectbox(
    "Выбери монету",
    ["BTC", "ETH", "SOL"],
    key="trade_coin"
)

trade_action = st.radio(
    "Тип операции",
    ["Купить", "Продать"],
    horizontal=True
)

trade_amount = st.number_input(
    "Количество монет",
    min_value=0.0,
    value=0.001,
    step=0.001,
    format="%.6f"
)

if st.button("Выполнить виртуальную операцию"):

    try:
        price = get_price(symbols[trade_coin])
        total = price * trade_amount

        if trade_amount <= 0:
            st.error("Количество должно быть больше нуля.")

        elif trade_action == "Купить":

            if total <= st.session_state.balance:

                st.session_state.balance -= total

                st.session_state.portfolio[trade_coin] += trade_amount

                st.session_state.history.append({
                    "Время": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Операция": "Покупка",
                    "Монета": trade_coin,
                    "Количество": trade_amount,
                    "Цена": price,
                    "Сумма": total
                })

                # Сохраняем стоимость портфеля
                new_prices = get_prices()

                new_value = st.session_state.balance + sum(
                    st.session_state.portfolio[ticker]
                    * new_prices[ticker]
                    for ticker in symbols
                )

                st.session_state.equity_history.append({
                    "Время": datetime.now().isoformat(),
                    "Стоимость": new_value
                })

                save_portfolio()

                st.success("Виртуальная покупка выполнена!")
                st.rerun()

            else:
                st.error("Недостаточно виртуальных средств.")

        else:

            if trade_amount <= st.session_state.portfolio[trade_coin]:

                st.session_state.portfolio[trade_coin] -= trade_amount

                st.session_state.balance += total

                st.session_state.history.append({
                    "Время": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Операция": "Продажа",
                    "Монета": trade_coin,
                    "Количество": trade_amount,
                    "Цена": price,
                    "Сумма": total
                })

                # Сохраняем стоимость портфеля
                new_prices = get_prices()

                new_value = st.session_state.balance + sum(
                    st.session_state.portfolio[ticker]
                    * new_prices[ticker]
                    for ticker in symbols
                )

                st.session_state.equity_history.append({
                    "Время": datetime.now().isoformat(),
                    "Стоимость": new_value
                })

                save_portfolio()

                st.success("Виртуальная продажа выполнена!")
                st.rerun()

            else:
                st.error("Недостаточно виртуальных монет.")

    except Exception as error:
        st.error(f"Ошибка операции: {error}")


# ==================================
# ИСТОРИЯ ОПЕРАЦИЙ
# ==================================

st.subheader("📜 История виртуальных операций")

if st.session_state.history:
    history_df = pd.DataFrame(
        st.session_state.history
    )

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Пока операций нет.")

st.caption(
    "Все операции виртуальные. Реальные деньги не используются. "
    "Рыночные котировки загружаются из публичных данных Binance."
)


# ==================================
# MARKET SCANNER 6.0
# ==================================

st.divider()
st.header("🔎 Market Scanner — 20 монет")

scanner_symbols = [
    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "DOGE/USDT",
    "TRX/USDT",
    "AVAX/USDT",
    "LINK/USDT",
    "DOT/USDT",
    "LTC/USDT",
    "BCH/USDT",
    "UNI/USDT",
    "ATOM/USDT",
    "ETC/USDT",
    "FIL/USDT",
    "NEAR/USDT",
    "APT/USDT",
    "ARB/USDT"
]

if st.button("🔄 Сканировать рынок"):
    results = []

    progress = st.progress(0)
    status = st.empty()

    for index, symbol in enumerate(scanner_symbols):
        try:
            status.write(f"Анализируем {symbol}...")

            candles = exchange.fetch_ohlcv(
                symbol,
                timeframe="1h",
                limit=100
            )

            df_scan = pd.DataFrame(
                candles,
                columns=[
                    "time", "open", "high",
                    "low", "close", "volume"
                ]
            )

            close = df_scan["close"]

            # RSI
            delta = close.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)

            avg_gain = gain.ewm(
                alpha=1/14,
                adjust=False
            ).mean()

            avg_loss = loss.ewm(
                alpha=1/14,
                adjust=False
            ).mean()

            rs = avg_gain / avg_loss.replace(0, 0.000001)

            rsi_value = (
                100 - (100 / (1 + rs))
            ).iloc[-1]

            # SMA
            sma20 = close.rolling(20).mean().iloc[-1]
            sma50 = close.rolling(50).mean().iloc[-1]

            # MACD
            ema12 = close.ewm(
                span=12,
                adjust=False
            ).mean()

            ema26 = close.ewm(
                span=26,
                adjust=False
            ).mean()

            macd = ema12 - ema26

            signal = macd.ewm(
                span=9,
                adjust=False
            ).mean()

            # Оценка
            score = 0

            if sma20 > sma50:
                score += 1
            else:
                score -= 1

            if macd.iloc[-1] > signal.iloc[-1]:
                score += 1
            else:
                score -= 1

            if 40 <= rsi_value <= 65:
                score += 1
            elif rsi_value < 30 or rsi_value > 70:
                score -= 1

            ticker = exchange.fetch_ticker(symbol)

            results.append({
                "Монета": symbol,
                "Цена": ticker["last"],
                "Изменение 24ч (%)": ticker.get(
                    "percentage", 0
                ),
                "RSI": round(float(rsi_value), 2),
                "Объём": ticker.get("quoteVolume", 0),
                "Оценка": score
            })

        except Exception:
            pass

        progress.progress(
            (index + 1) / len(scanner_symbols)
        )

    status.empty()
    progress.empty()

    if results:
        scanner_df = pd.DataFrame(results)

        scanner_df = scanner_df.sort_values(
            "Оценка",
            ascending=False
        )

        st.session_state.scanner_results = scanner_df

        st.success(
            f"Проверено монет: {len(results)} из "
            f"{len(scanner_symbols)}"
        )

    else:
        st.error("Не удалось получить данные рынка.")

if "scanner_results" in st.session_state:
    st.subheader("Результаты сканирования")

    st.dataframe(
        st.session_state.scanner_results,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Оценка отражает только выбранные технические индикаторы. "
        "Она не предсказывает будущую цену."
    )


# ==========================================
# CRYPTO AI ANALYST 7.0 — BACKTESTING
# ==========================================

st.divider()
st.header("🧪 Historical Backtesting")

st.write(
    "Проверка технической стратегии на исторических данных."
)

bt_coin = st.selectbox(
    "Криптовалюта для тестирования",
    ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    key="bt_coin"
)

bt_timeframe = st.selectbox(
    "Таймфрейм тестирования",
    ["1h", "4h", "1d"],
    key="bt_timeframe"
)

bt_fee = st.number_input(
    "Комиссия за одну операцию (%)",
    min_value=0.0,
    max_value=2.0,
    value=0.1,
    step=0.05
)

if st.button("▶ Запустить бэктест"):

    try:
        with st.spinner("Проверяем исторические данные..."):

            candles = exchange.fetch_ohlcv(
                bt_coin,
                timeframe=bt_timeframe,
                limit=500
            )

            bt_df = pd.DataFrame(
                candles,
                columns=[
                    "time", "open", "high",
                    "low", "close", "volume"
                ]
            )

            bt_df["time"] = pd.to_datetime(
                bt_df["time"], unit="ms"
            )

            if len(bt_df) < 60:
                st.error("Недостаточно исторических данных.")
                st.stop()

            # Скользящие средние
            bt_df["SMA20"] = (
                bt_df["close"].rolling(20).mean()
            )

            bt_df["SMA50"] = (
                bt_df["close"].rolling(50).mean()
            )

            # MACD
            bt_ema12 = bt_df["close"].ewm(
                span=12, adjust=False
            ).mean()

            bt_ema26 = bt_df["close"].ewm(
                span=26, adjust=False
            ).mean()

            bt_df["MACD"] = bt_ema12 - bt_ema26

            bt_df["Signal"] = bt_df["MACD"].ewm(
                span=9, adjust=False
            ).mean()

            # Условие нахождения в виртуальной позиции
            bt_df["entry_signal"] = (
                (bt_df["SMA20"] > bt_df["SMA50"]) &
                (bt_df["MACD"] > bt_df["Signal"])
            )

            # Начальные параметры
            initial_capital = 10000.0
            cash = initial_capital
            quantity = 0.0
            entry_cost = 0.0
            entry_price = 0.0
            entry_time = None

            fee = bt_fee / 100

            in_position = False
            trades = []
            equity_values = []

            equity_values.append({
                "Время": bt_df["time"].iloc[0],
                "Капитал": initial_capital
            })

            # Проходим исторические свечи
            for i in range(1, len(bt_df)):

                row = bt_df.iloc[i]

                # Сигнал предыдущей свечи.
                # Сделка выполняется на открытии текущей.
                signal = bool(
                    bt_df["entry_signal"].iloc[i - 1]
                )

                # Виртуальная покупка
                if signal and not in_position:

                    entry_price = float(row["open"])
                    entry_time = row["time"]
                    entry_cost = cash

                    quantity = cash / (
                        entry_price * (1 + fee)
                    )

                    cash = 0.0
                    in_position = True

                # Виртуальная продажа
                elif not signal and in_position:

                    exit_price = float(row["open"])

                    cash = (
                        quantity *
                        exit_price *
                        (1 - fee)
                    )

                    trade_profit = cash - entry_cost

                    trades.append({
                        "Вход": entry_time,
                        "Выход": row["time"],
                        "Цена входа": entry_price,
                        "Цена выхода": exit_price,
                        "Результат ($)": trade_profit,
                        "Результат (%)": (
                            trade_profit / entry_cost * 100
                        )
                    })

                    quantity = 0.0
                    in_position = False

                # Закрываем оставшуюся позицию
                # на последней исторической свече
                if i == len(bt_df) - 1 and in_position:

                    exit_price = float(row["close"])

                    cash = (
                        quantity *
                        exit_price *
                        (1 - fee)
                    )

                    trade_profit = cash - entry_cost

                    trades.append({
                        "Вход": entry_time,
                        "Выход": row["time"],
                        "Цена входа": entry_price,
                        "Цена выхода": exit_price,
                        "Результат ($)": trade_profit,
                        "Результат (%)": (
                            trade_profit / entry_cost * 100
                        )
                    })

                    quantity = 0.0
                    in_position = False

                # Стоимость портфеля на закрытии свечи
                if in_position:
                    equity = (
                        quantity *
                        float(row["close"]) *
                        (1 - fee)
                    )
                else:
                    equity = cash

                equity_values.append({
                    "Время": row["time"],
                    "Капитал": equity
                })

            # Результаты стратегии
            equity_df = pd.DataFrame(equity_values)
            trades_df = pd.DataFrame(trades)

            final_capital = float(
                equity_df["Капитал"].iloc[-1]
            )

            total_return = (
                final_capital / initial_capital - 1
            ) * 100

            # Максимальная просадка
            equity_df["Peak"] = (
                equity_df["Капитал"].cummax()
            )

            equity_df["Drawdown"] = (
                equity_df["Капитал"] /
                equity_df["Peak"] - 1
            ) * 100

            max_drawdown = float(
                equity_df["Drawdown"].min()
            )

            # Процент прибыльных сделок
            if len(trades_df) > 0:
                winning_trades = (
                    trades_df["Результат ($)"] > 0
                ).sum()

                win_rate = (
                    winning_trades /
                    len(trades_df) * 100
                )
            else:
                win_rate = 0.0

            # Сравнение с удержанием актива
            first_price = float(bt_df["open"].iloc[0])
            last_price = float(bt_df["close"].iloc[-1])

            buy_hold_quantity = (
                initial_capital /
                (first_price * (1 + fee))
            )

            buy_hold_capital = (
                buy_hold_quantity *
                last_price *
                (1 - fee)
            )

            buy_hold_return = (
                buy_hold_capital /
                initial_capital - 1
            ) * 100

            # Сохраняем результаты
            st.session_state.bt_results = {
                "coin": bt_coin,
                "timeframe": bt_timeframe,
                "final_capital": final_capital,
                "total_return": total_return,
                "max_drawdown": max_drawdown,
                "win_rate": win_rate,
                "trade_count": len(trades_df),
                "buy_hold_return": buy_hold_return,
                "equity": equity_df,
                "trades": trades_df
            }

    except Exception as error:
        st.error(f"Ошибка бэктеста: {error}")


# ==========================================
# ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ
# ==========================================

if "bt_results" in st.session_state:

    result = st.session_state.bt_results

    st.subheader(
        f"Результаты: {result['coin']} ({result['timeframe']})"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Итоговый капитал",
        f"${result['final_capital']:,.2f}"
    )

    col2.metric(
        "Доходность стратегии",
        f"{result['total_return']:.2f}%"
    )

    col3.metric(
        "Максимальная просадка",
        f"{result['max_drawdown']:.2f}%"
    )

    col4, col5, col6 = st.columns(3)

    col4.metric(
        "Количество сделок",
        result["trade_count"]
    )

    col5.metric(
        "Прибыльные сделки",
        f"{result['win_rate']:.2f}%"
    )

    col6.metric(
        "Доходность удержания",
        f"{result['buy_hold_return']:.2f}%"
    )

    # График капитала
    st.subheader("📈 История виртуального капитала")

    equity_chart = go.Figure()

    equity_chart.add_trace(go.Scatter(
        x=result["equity"]["Время"],
        y=result["equity"]["Капитал"],
        mode="lines",
        name="Стратегия"
    ))

    equity_chart.update_layout(
        height=400,
        xaxis_title="Время",
        yaxis_title="Капитал (USD)"
    )

    st.plotly_chart(
        equity_chart,
        use_container_width=True
    )

    # История сделок
    st.subheader("📋 История виртуальных сделок")

    if not result["trades"].empty:

        st.dataframe(
            result["trades"],
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info(
            "За выбранный исторический период "
            "стратегия не совершила сделок."
        )

    st.caption(
        "Бэктест учитывает комиссию и использует сигнал "
        "предыдущей свечи для исполнения на следующей. "
        "Исторические результаты не гарантируют будущую доходность."
    )

# ==========================================
# CRYPTO AI ANALYST 8.0 — AI PREDICTOR
# ==========================================

import streamlit as ai_st
import ccxt as ai_ccxt
import pandas as ai_pd
import numpy as ai_np

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

ai_st.divider()
ai_st.header("🤖 Crypto AI Predictor 8.0")

ai_st.warning(
    "Экспериментальная модель для обучения и анализа. "
    "Прогнозы не гарантируют будущую цену и не являются "
    "рекомендациями по покупке или продаже."
)

ai_col1, ai_col2 = ai_st.columns(2)

with ai_col1:
    ai_symbol = ai_st.selectbox(
        "Криптовалюта",
        ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        key="ai_predict_symbol"
    )

with ai_col2:
    ai_timeframe = ai_st.selectbox(
        "Таймфрейм",
        ["1h", "4h", "1d"],
        key="ai_predict_timeframe"
    )

if ai_st.button("🧠 Обучить AI и сделать прогноз"):
    try:
        with ai_st.spinner("Загружаем данные и обучаем модель..."):

            ai_exchange = ai_ccxt.binance({
                "enableRateLimit": True
            })

            ai_raw = ai_exchange.fetch_ohlcv(
                ai_symbol,
                timeframe=ai_timeframe,
                limit=700
            )

            ai_df = ai_pd.DataFrame(
                ai_raw,
                columns=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume"
                ]
            )

            # Не используем незакрытую свечу
            ai_df = ai_df.iloc[:-1].copy()

            # Создаём признаки
            ai_df["return_1"] = ai_df["close"].pct_change(1)
            ai_df["return_3"] = ai_df["close"].pct_change(3)
            ai_df["return_6"] = ai_df["close"].pct_change(6)

            ai_df["sma_10"] = (
                ai_df["close"].rolling(10).mean()
            )

            ai_df["sma_30"] = (
                ai_df["close"].rolling(30).mean()
            )

            ai_df["sma_ratio"] = (
                ai_df["sma_10"] / ai_df["sma_30"] - 1
            )

            ai_df["volatility"] = (
                ai_df["return_1"].rolling(10).std()
            )

            ai_df["volume_change"] = (
                ai_df["volume"].pct_change()
            )

            # Цель — изменение цены на следующей свече
            ai_df["target"] = (
                ai_df["close"].shift(-1) /
                ai_df["close"] - 1
            )

            ai_features = [
                "return_1",
                "return_3",
                "return_6",
                "sma_ratio",
                "volatility",
                "volume_change"
            ]

            ai_data = ai_df.replace(
                [ai_np.inf, -ai_np.inf],
                ai_np.nan
            ).dropna(
                subset=ai_features + ["target"]
            )

            if len(ai_data) < 150:
                raise ValueError(
                    "Недостаточно исторических данных."
                )

            X = ai_data[ai_features]
            y = ai_data["target"]

            # Хронологическое разделение:
            # старые данные — обучение,
            # более новые — проверка.
            split = int(len(ai_data) * 0.8)

            X_train = X.iloc[:split]
            X_test = X.iloc[split:]

            y_train = y.iloc[:split]
            y_test = y.iloc[split:]

            ai_model = RandomForestRegressor(
                n_estimators=200,
                max_depth=6,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1
            )

            ai_model.fit(X_train, y_train)

            # Проверка на данных, которые модель не видела
            ai_test_predictions = ai_model.predict(X_test)

            ai_mae = mean_absolute_error(
                y_test,
                ai_test_predictions
            )

            ai_baseline_mae = mean_absolute_error(
                y_test,
                numpy_zeros := ai_np.zeros(len(y_test))
            )

            # Переобучаем модель на всей доступной истории
            ai_model.fit(X, y)

            # Признаки последней закрытой свечи
            ai_latest = ai_df[ai_features].replace(
                [ai_np.inf, -ai_np.inf],
                ai_np.nan
            ).dropna()

            if ai_latest.empty:
                raise ValueError(
                    "Не удалось подготовить последние данные."
                )

            ai_last_features = ai_latest.iloc[[-1]]

            ai_predicted_return = ai_model.predict(
                ai_last_features
            )[0]

            ai_last_price = float(
                ai_df.loc[ai_latest.index[-1], "close"]
            )

            ai_predicted_price = (
                ai_last_price * (1 + ai_predicted_return)
            )

        ai_st.success("Обучение модели завершено!")

        ai_st.subheader("Результат прогноза")

        c1, c2, c3 = ai_st.columns(3)

        c1.metric(
            "Последняя цена",
            f"${ai_last_price:,.4f}"
        )

        c2.metric(
            "Расчётная цена",
            f"${ai_predicted_price:,.4f}"
        )

        c3.metric(
            "Прогноз изменения",
            f"{ai_predicted_return * 100:+.3f}%"
        )

        ai_st.subheader("Проверка точности модели")

        m1, m2 = ai_st.columns(2)

        m1.metric(
            "Ошибка AI (MAE)",
            f"{ai_mae * 100:.4f}%"
        )

        m2.metric(
            "Ошибка простого прогноза",
            f"{ai_baseline_mae * 100:.4f}%"
        )

        if ai_mae < ai_baseline_mae:
            ai_st.info(
                "На этом тестовом отрезке модель показала "
                "меньшую среднюю ошибку, чем простой прогноз."
            )
        else:
            ai_st.info(
                "На этом тестовом отрезке модель не превзошла "
                "простой прогноз."
            )

        ai_st.subheader("Факт и прогноз на тестовых данных")

        ai_chart = ai_pd.DataFrame({
            "Реальное изменение (%)":
                y_test.values * 100,

            "Прогноз AI (%)":
                ai_test_predictions * 100
        })

        ai_st.line_chart(ai_chart)

        ai_st.caption(
            "Показана проверка на исторических данных. "
            "Результаты не гарантируют точность будущих прогнозов."
        )

    except Exception as ai_error:
        ai_st.error(
            f"Ошибка AI Predictor: {ai_error}"
        )

# ==========================================
# CRYPTO AI ANALYST 9.0
# NEWS + SMART ALERTS
# ==========================================

import streamlit as v9_st
import ccxt as v9_ccxt
import pandas as v9_pd
import feedparser as v9_feedparser

v9_st.divider()
v9_st.header("🚀 Crypto AI Analyst 9.0")

v9_st.warning(
    "Новости и технические оповещения предназначены "
    "для обучения и анализа. Они не являются финансовыми рекомендациями."
)

# ==========================================
# CRYPTO NEWS
# ==========================================

v9_st.subheader("📰 Crypto News")

v9_feeds = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss"
}

if "v9_news" not in v9_st.session_state:
    v9_st.session_state.v9_news = []

if v9_st.button("🔄 Обновить новости", key="v9_news_button"):
    v9_articles = []

    with v9_st.spinner("Загружаем новости..."):
        for v9_source, v9_url in v9_feeds.items():
            try:
                v9_parsed = v9_feedparser.parse(v9_url)

                for v9_entry in v9_parsed.entries[:8]:
                    v9_articles.append({
                        "source": v9_source,
                        "title": v9_entry.get(
                            "title", "Без заголовка"
                        ),
                        "link": v9_entry.get("link", ""),
                        "published": v9_entry.get(
                            "published", "Дата не указана"
                        )
                    })

            except Exception:
                continue

    v9_st.session_state.v9_news = v9_articles

if v9_st.session_state.v9_news:
    for v9_article in v9_st.session_state.v9_news:
        v9_st.write("**" + v9_article["title"] + "**")
        v9_st.caption(
            v9_article["source"] + " | " +
            v9_article["published"]
        )

        if v9_article["link"].startswith("https://"):
            v9_st.markdown(
                "[Читать оригинал](" +
                v9_article["link"] + ")"
            )

        v9_st.divider()
else:
    v9_st.info(
        "Нажми «Обновить новости», чтобы загрузить ленту."
    )

# ==========================================
# SMART ALERTS
# ==========================================

v9_st.subheader("🔔 Smart Alerts")

v9_st.write(
    "Проверяем RSI и MACD для BTC, ETH и SOL."
)

if v9_st.button(
    "🔍 Проверить рынок",
    key="v9_alert_button"
):

    v9_exchange = v9_ccxt.binance({
        "enableRateLimit": True
    })

    v9_symbols = [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT"
    ]

    v9_alert_results = []

    with v9_st.spinner("Анализируем рынок..."):

        for v9_symbol in v9_symbols:
            try:
                v9_candles = v9_exchange.fetch_ohlcv(
                    v9_symbol,
                    timeframe="1h",
                    limit=100
                )

                v9_df = v9_pd.DataFrame(
                    v9_candles,
                    columns=[
                        "timestamp",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume"
                    ]
                )

                # Используем только закрытые свечи
                v9_df = v9_df.iloc[:-1].copy()

                # RSI
                v9_delta = v9_df["close"].diff()

                v9_gain = v9_delta.clip(lower=0)
                v9_loss = -v9_delta.clip(upper=0)

                v9_avg_gain = v9_gain.ewm(
                    alpha=1/14,
                    adjust=False
                ).mean()

                v9_avg_loss = v9_loss.ewm(
                    alpha=1/14,
                    adjust=False
                ).mean()

                v9_rs = v9_avg_gain / v9_avg_loss.replace(
                    0, float("nan")
                )

                v9_df["rsi"] = (
                    100 - (100 / (1 + v9_rs))
                )

                # MACD
                v9_ema12 = v9_df["close"].ewm(
                    span=12,
                    adjust=False
                ).mean()

                v9_ema26 = v9_df["close"].ewm(
                    span=26,
                    adjust=False
                ).mean()

                v9_df["macd"] = v9_ema12 - v9_ema26

                v9_df["signal"] = v9_df["macd"].ewm(
                    span=9,
                    adjust=False
                ).mean()

                v9_last = v9_df.iloc[-1]
                v9_prev = v9_df.iloc[-2]

                v9_rsi = float(v9_last["rsi"])
                v9_macd_diff = (
                    v9_last["macd"] - v9_last["signal"]
                )
                v9_prev_diff = (
                    v9_prev["macd"] - v9_prev["signal"]
                )

                v9_alerts = []

                if v9_rsi >= 70:
                    v9_alerts.append(
                        "RSI выше 70 — высокая зона RSI"
                    )

                elif v9_rsi <= 30:
                    v9_alerts.append(
                        "RSI ниже 30 — низкая зона RSI"
                    )

                if (
                    v9_prev_diff <= 0
                    and v9_macd_diff > 0
                ):
                    v9_alerts.append(
                        "MACD пересёк сигнальную линию вверх"
                    )

                elif (
                    v9_prev_diff >= 0
                    and v9_macd_diff < 0
                ):
                    v9_alerts.append(
                        "MACD пересёк сигнальную линию вниз"
                    )

                v9_alert_results.append({
                    "symbol": v9_symbol,
                    "price": float(v9_last["close"]),
                    "rsi": v9_rsi,
                    "alerts": v9_alerts
                })

            except Exception as v9_error:
                v9_st.warning(
                    v9_symbol + ": не удалось получить данные."
                )

    for v9_result in v9_alert_results:
        v9_st.markdown(
            "### " + v9_result["symbol"]
        )

        v9_c1, v9_c2 = v9_st.columns(2)

        v9_c1.metric(
            "Цена",
            f"${v9_result['price']:,.4f}"
        )

        v9_c2.metric(
            "RSI",
            f"{v9_result['rsi']:.2f}"
        )

        if v9_result["alerts"]:
            for v9_alert in v9_result["alerts"]:
                v9_st.info("🔔 " + v9_alert)
        else:
            v9_st.success(
                "Особых условий RSI или пересечения MACD нет."
            )

        v9_st.divider()

    if not v9_alert_results:
        v9_st.error(
            "Не удалось получить данные рынка. "
            "Попробуй обновить проверку позже."
        )

v9_st.caption(
    "Данные Binance и RSS-лент. Проверка выполняется "
    "только после нажатия кнопки."
)


# ==========================================
# CRYPTO AI ANALYST 10.0
# PROFESSIONAL DASHBOARD
# ==========================================

import streamlit as p10_st
import ccxt as p10_ccxt
import pandas as p10_pd
import numpy as p10_np

p10_st.divider()
p10_st.header("💎 Crypto AI Analyst 10.0")
p10_st.subheader("Professional Dashboard")

p10_st.warning(
    "Учебная аналитическая панель. Данные и модели "
    "не гарантируют будущих результатов."
)

p10_exchange = p10_ccxt.binance({
    "enableRateLimit": True
})

p10_symbols = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT",
    "SOL/USDT", "XRP/USDT", "ADA/USDT",
    "DOGE/USDT", "AVAX/USDT", "LINK/USDT",
    "DOT/USDT"
]

# ==========================================
# 1. MARKET DASHBOARD
# ==========================================

p10_st.subheader("📊 Обзор рынка")

if p10_st.button("🔄 Обновить рынок", key="p10_market"):

    p10_market_data = []

    with p10_st.spinner("Получаем данные рынка..."):
        for p10_symbol in p10_symbols:
            try:
                p10_ticker = p10_exchange.fetch_ticker(
                    p10_symbol
                )

                p10_market_data.append({
                    "Монета": p10_symbol,
                    "Цена": p10_ticker.get("last"),
                    "Изменение за 24ч (%)":
                        p10_ticker.get("percentage"),
                    "Объём": p10_ticker.get("quoteVolume")
                })

            except Exception:
                continue

    p10_st.session_state["p10_market_data"] = (
        p10_market_data
    )

if "p10_market_data" in p10_st.session_state:
    p10_market_df = p10_pd.DataFrame(
        p10_st.session_state["p10_market_data"]
    )

    if not p10_market_df.empty:
        p10_st.dataframe(
            p10_market_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        p10_st.info("Нет доступных данных.")

# ==========================================
# 2. PRICE CHART — LAST 7 DAYS
# ==========================================

p10_st.divider()
p10_st.subheader("📈 График за 7 дней")

p10_chart_symbol = p10_st.selectbox(
    "Выбери криптовалюту",
    p10_symbols,
    key="p10_chart_symbol"
)

if p10_st.button(
    "Показать график",
    key="p10_chart_button"
):
    try:
        with p10_st.spinner("Загружаем историю..."):
            p10_candles = p10_exchange.fetch_ohlcv(
                p10_chart_symbol,
                timeframe="1h",
                limit=168
            )

            p10_chart_df = p10_pd.DataFrame(
                p10_candles,
                columns=[
                    "timestamp", "open", "high",
                    "low", "close", "volume"
                ]
            )

            p10_chart_df["Время"] = (
                p10_pd.to_datetime(
                    p10_chart_df["timestamp"],
                    unit="ms"
                )
            )

            p10_chart_df = p10_chart_df.set_index(
                "Время"
            )

        p10_st.line_chart(
            p10_chart_df["close"],
            use_container_width=True
        )

        p10_change = (
            p10_chart_df["close"].iloc[-1] /
            p10_chart_df["close"].iloc[0] - 1
        ) * 100

        p10_st.metric(
            "Изменение за период",
            f"{p10_change:+.2f}%"
        )

    except Exception as p10_error:
        p10_st.error(f"Ошибка графика: {p10_error}")

# ==========================================
# 3. AI MODEL HISTORY
# ==========================================

p10_st.divider()
p10_st.subheader("🧠 AI: прогноз против факта")

p10_ai_symbol = p10_st.selectbox(
    "Монета для проверки модели",
    ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    key="p10_ai_symbol"
)

if p10_st.button(
    "Проверить точность AI",
    key="p10_ai_button"
):
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import mean_absolute_error

        with p10_st.spinner("Проверяем модель..."):
            p10_raw = p10_exchange.fetch_ohlcv(
                p10_ai_symbol,
                timeframe="1h",
                limit=700
            )

            p10_ai_df = p10_pd.DataFrame(
                p10_raw,
                columns=[
                    "timestamp", "open", "high",
                    "low", "close", "volume"
                ]
            )

            p10_ai_df = p10_ai_df.iloc[:-1].copy()

            p10_ai_df["r1"] = (
                p10_ai_df["close"].pct_change()
            )

            p10_ai_df["r3"] = (
                p10_ai_df["close"].pct_change(3)
            )

            p10_ai_df["r6"] = (
                p10_ai_df["close"].pct_change(6)
            )

            p10_ai_df["sma_ratio"] = (
                p10_ai_df["close"].rolling(10).mean() /
                p10_ai_df["close"].rolling(30).mean() - 1
            )

            p10_ai_df["volatility"] = (
                p10_ai_df["r1"].rolling(10).std()
            )

            p10_ai_df["target"] = (
                p10_ai_df["close"].shift(-1) /
                p10_ai_df["close"] - 1
            )

            p10_features = [
                "r1", "r3", "r6",
                "sma_ratio", "volatility"
            ]

            p10_ai_df = p10_ai_df.replace(
                [p10_np.inf, -p10_np.inf],
                p10_np.nan
            ).dropna(
                subset=p10_features + ["target"]
            )

            if len(p10_ai_df) < 150:
                raise ValueError("Недостаточно данных.")

            p10_X = p10_ai_df[p10_features]
            p10_y = p10_ai_df["target"]

            p10_split = int(len(p10_ai_df) * 0.8)

            p10_X_train = p10_X.iloc[:p10_split]
            p10_X_test = p10_X.iloc[p10_split:]

            p10_y_train = p10_y.iloc[:p10_split]
            p10_y_test = p10_y.iloc[p10_split:]

            p10_model = RandomForestRegressor(
                n_estimators=150,
                max_depth=6,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1
            )

            p10_model.fit(
                p10_X_train,
                p10_y_train
            )

            p10_predictions = p10_model.predict(
                p10_X_test
            )

            p10_mae = mean_absolute_error(
                p10_y_test,
                p10_predictions
            )

            p10_baseline = mean_absolute_error(
                p10_y_test,
                p10_np.zeros(len(p10_y_test))
            )

            p10_history = p10_pd.DataFrame({
                "Фактическое изменение (%)":
                    p10_y_test.values * 100,
                "Прогноз AI (%)":
                    p10_predictions * 100
            })

            p10_st.session_state[
                "p10_prediction_history"
            ] = p10_history

            p10_st.session_state[
                "p10_model_metrics"
            ] = {
                "mae": p10_mae,
                "baseline": p10_baseline
            }

    except Exception as p10_error:
        p10_st.error(f"Ошибка модели: {p10_error}")

if "p10_prediction_history" in p10_st.session_state:

    p10_history = p10_st.session_state[
        "p10_prediction_history"
    ]

    p10_metrics = p10_st.session_state[
        "p10_model_metrics"
    ]

    p10_a, p10_b = p10_st.columns(2)

    p10_a.metric(
        "Ошибка AI (MAE)",
        f"{p10_metrics['mae'] * 100:.4f}%"
    )

    p10_b.metric(
        "Ошибка простого прогноза",
        f"{p10_metrics['baseline'] * 100:.4f}%"
    )

    p10_st.line_chart(
        p10_history.tail(50),
        use_container_width=True
    )

    p10_st.dataframe(
        p10_history.tail(30),
        use_container_width=True
    )

# ==========================================
# 4. VIRTUAL ALERT SETTINGS
# ==========================================

p10_st.divider()
p10_st.subheader("🔔 Настройки уведомлений")

p10_alert_symbol = p10_st.selectbox(
    "Монета",
    ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    key="p10_alert_symbol"
)

p10_rsi_limit = p10_st.slider(
    "Порог высокого RSI",
    min_value=60,
    max_value=90,
    value=70,
    key="p10_rsi_limit"
)

p10_st.caption(
    "Проверка выполняется только после нажатия кнопки."
)

if p10_st.button(
    "Проверить уведомления",
    key="p10_alert_button"
):
    try:
        p10_alert_candles = p10_exchange.fetch_ohlcv(
            p10_alert_symbol,
            timeframe="1h",
            limit=100
        )

        p10_alert_df = p10_pd.DataFrame(
            p10_alert_candles,
            columns=[
                "timestamp", "open", "high",
                "low", "close", "volume"
            ]
        )

        p10_alert_df = p10_alert_df.iloc[:-1].copy()

        p10_delta = p10_alert_df["close"].diff()

        p10_gain = p10_delta.clip(lower=0).ewm(
            alpha=1/14,
            adjust=False
        ).mean()

        p10_loss = (-p10_delta.clip(upper=0)).ewm(
            alpha=1/14,
            adjust=False
        ).mean()

        p10_rs = p10_gain / p10_loss.replace(
            0, float("nan")
        )

        p10_rsi_value = (
            100 - 100 / (1 + p10_rs)
        ).iloc[-1]

        p10_st.metric(
            "Текущий RSI",
            f"{p10_rsi_value:.2f}"
        )

        if p10_rsi_value >= p10_rsi_limit:
            p10_st.warning(
                "Уведомление: RSI достиг заданного высокого порога."
            )
        elif p10_rsi_value <= 30:
            p10_st.info(
                "Уведомление: RSI находится ниже 30."
            )
        else:
            p10_st.success(
                "Заданные условия уведомления не обнаружены."
            )

    except Exception as p10_error:
        p10_st.error(
            f"Ошибка проверки: {p10_error}"
        )

# ==========================================
# 5. EXPORT TO CSV
# ==========================================

p10_st.divider()
p10_st.subheader("💾 Экспорт данных")

if "p10_market_data" in p10_st.session_state:
    p10_export_df = p10_pd.DataFrame(
        p10_st.session_state["p10_market_data"]
    )

    if not p10_export_df.empty:
        p10_csv = p10_export_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        p10_st.download_button(
            "📥 Скачать обзор рынка CSV",
            data=p10_csv,
            file_name="crypto_market_dashboard.csv",
            mime="text/csv"
        )

if "p10_prediction_history" in p10_st.session_state:
    p10_history_csv = (
        p10_st.session_state[
            "p10_prediction_history"
        ].to_csv(index=False).encode("utf-8-sig")
    )

    p10_st.download_button(
        "📥 Скачать историю AI CSV",
        data=p10_history_csv,
        file_name="crypto_ai_history.csv",
        mime="text/csv"
    )

p10_st.caption(
    "Crypto AI Analyst 10.0 | Учебный режим"
)


# ==========================================
# CRYPTO AI ANALYST 11.0
# RISK MANAGEMENT & PORTFOLIO LAB
# ==========================================

import streamlit as r11_st
import ccxt as r11_ccxt
import pandas as r11_pd
import numpy as r11_np

r11_st.divider()
r11_st.header("🛡️ Crypto AI Analyst 11.0")
r11_st.subheader("Risk Management & Portfolio Lab")

r11_st.warning(
    "Учебный симулятор. Все расчёты основаны на исторических "
    "данных и не являются рекомендацией по инвестированию."
)

r11_symbols = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT"
]

r11_st.write(
    "Анализируем исторические дневные цены за последние 180 дней."
)

if r11_st.button(
    "🔍 Запустить анализ рисков",
    key="r11_analyze"
):
    try:
        r11_exchange = r11_ccxt.binance({
            "enableRateLimit": True
        })

        r11_prices = {}

        with r11_st.spinner("Загружаем исторические данные..."):
            for r11_symbol in r11_symbols:
                try:
                    r11_candles = r11_exchange.fetch_ohlcv(
                        r11_symbol,
                        timeframe="1d",
                        limit=180
                    )

                    r11_df = r11_pd.DataFrame(
                        r11_candles,
                        columns=[
                            "timestamp", "open", "high",
                            "low", "close", "volume"
                        ]
                    )

                    # Исключаем последнюю незакрытую свечу
                    r11_df = r11_df.iloc[:-1]

                    r11_df["date"] = r11_pd.to_datetime(
                        r11_df["timestamp"],
                        unit="ms"
                    )

                    r11_prices[r11_symbol] = (
                        r11_df.set_index("date")["close"]
                    )

                except Exception:
                    continue

        if len(r11_prices) < 2:
            raise ValueError(
                "Недостаточно данных для анализа."
            )

        r11_price_df = r11_pd.DataFrame(
            r11_prices
        ).dropna()

        r11_returns = r11_price_df.pct_change().dropna()

        if len(r11_returns) < 20:
            raise ValueError(
                "Недостаточно общих исторических наблюдений."
            )

        # ==================================
        # VOLATILITY
        # ==================================

        r11_st.subheader("📉 Волатильность")

        r11_volatility = (
            r11_returns.std() * r11_np.sqrt(365) * 100
        )

        r11_vol_df = r11_pd.DataFrame({
            "Монета": r11_volatility.index,
            "Годовая волатильность (%)":
                r11_volatility.values
        }).sort_values(
            "Годовая волатильность (%)",
            ascending=False
        )

        r11_st.dataframe(
            r11_vol_df,
            use_container_width=True,
            hide_index=True
        )

        r11_st.bar_chart(
            r11_vol_df.set_index("Монета")
        )

        # ==================================
        # CORRELATION
        # ==================================

        r11_st.divider()
        r11_st.subheader("🔗 Корреляция криптовалют")

        r11_corr = r11_returns.corr()

        r11_st.dataframe(
            r11_corr.style.format("{:.2f}"),
            use_container_width=True
        )

        r11_st.caption(
            "Корреляция показывает, насколько часто "
            "исторические изменения цен происходили в одном направлении."
        )

        # ==================================
        # EQUAL WEIGHT PORTFOLIO
        # ==================================

        r11_st.divider()
        r11_st.subheader("💼 Виртуальный портфель")

        r11_equal_weights = (
            r11_np.ones(len(r11_returns.columns)) /
            len(r11_returns.columns)
        )

        r11_equal_returns = (
            r11_returns * r11_equal_weights
        ).sum(axis=1)

        r11_equal_equity = (
            1 + r11_equal_returns
        ).cumprod()

        r11_peak = r11_equal_equity.cummax()

        r11_drawdown = (
            r11_equal_equity / r11_peak - 1
        ) * 100

        r11_max_drawdown = r11_drawdown.min()

        r11_portfolio_volatility = (
            r11_equal_returns.std() *
            r11_np.sqrt(365) * 100
        )

        r11_total_return = (
            r11_equal_equity.iloc[-1] - 1
        ) * 100

        r11_c1, r11_c2, r11_c3 = r11_st.columns(3)

        r11_c1.metric(
            "Историческое изменение",
            f"{r11_total_return:+.2f}%"
        )

        r11_c2.metric(
            "Максимальная просадка",
            f"{r11_max_drawdown:.2f}%"
        )

        r11_c3.metric(
            "Годовая волатильность",
            f"{r11_portfolio_volatility:.2f}%"
        )

        r11_st.line_chart(
            r11_equal_equity,
            use_container_width=True
        )

        r11_st.caption(
            "Модель равных долей без комиссий и проскальзывания. "
            "Это историческая симуляция, а не реальная доходность."
        )

        # ==================================
        # SAVE RESULTS
        # ==================================

        r11_st.session_state["r11_prices"] = r11_price_df
        r11_st.session_state["r11_returns"] = r11_returns
        r11_st.session_state["r11_analyzed"] = True

    except Exception as r11_error:
        r11_st.error(
            f"Ошибка анализа: {r11_error}"
        )


# ==========================================
# VIRTUAL ALLOCATION SIMULATOR
# ==========================================

r11_st.divider()
r11_st.subheader("🧪 Симулятор распределения")

r11_st.write(
    "Выбери условные доли для исторической симуляции. "
    "Это не рекомендации по распределению реальных средств."
)

r11_btc_weight = r11_st.slider(
    "BTC — условная доля (%)",
    0, 100, 50,
    key="r11_btc"
)

r11_eth_weight = r11_st.slider(
    "ETH — условная доля (%)",
    0, 100, 30,
    key="r11_eth"
)

r11_sol_weight = r11_st.slider(
    "SOL — условная доля (%)",
    0, 100, 20,
    key="r11_sol"
)

r11_weights = {
    "BTC/USDT": r11_btc_weight,
    "ETH/USDT": r11_eth_weight,
    "SOL/USDT": r11_sol_weight
}

r11_total_weight = sum(r11_weights.values())

if r11_total_weight == 0:
    r11_st.info(
        "Укажи хотя бы одну ненулевую долю."
    )

elif r11_st.button(
    "📊 Рассчитать виртуальный сценарий",
    key="r11_simulate"
):

    if "r11_returns" not in r11_st.session_state:
        r11_st.warning(
            "Сначала запусти анализ рисков."
        )

    else:
        r11_data = r11_st.session_state[
            "r11_returns"
        ]

        r11_available = [
            x for x in r11_weights
            if x in r11_data.columns
        ]

        if not r11_available:
            r11_st.error(
                "Нет исторических данных для выбранных монет."
            )

        else:
            r11_selected_weights = r11_np.array([
                r11_weights[x] for x in r11_available
            ], dtype=float)

            r11_selected_weights = (
                r11_selected_weights /
                r11_selected_weights.sum()
            )

            r11_selected_returns = r11_data[
                r11_available
            ]

            r11_scenario_returns = (
                r11_selected_returns *
                r11_selected_weights
            ).sum(axis=1)

            r11_scenario_equity = (
                1 + r11_scenario_returns
            ).cumprod()

            r11_scenario_peak = (
                r11_scenario_equity.cummax()
            )

            r11_scenario_dd = (
                r11_scenario_equity /
                r11_scenario_peak - 1
            ) * 100

            r11_scenario_return = (
                r11_scenario_equity.iloc[-1] - 1
            ) * 100

            r11_scenario_vol = (
                r11_scenario_returns.std() *
                r11_np.sqrt(365) * 100
            )

            r11_scenario_max_dd = (
                r11_scenario_dd.min()
            )

            r11_st.success(
                "Историческая симуляция рассчитана."
            )

            r11_x, r11_y, r11_z = r11_st.columns(3)

            r11_x.metric(
                "Изменение",
                f"{r11_scenario_return:+.2f}%"
            )

            r11_y.metric(
                "Макс. просадка",
                f"{r11_scenario_max_dd:.2f}%"
            )

            r11_z.metric(
                "Волатильность",
                f"{r11_scenario_vol:.2f}%"
            )

            r11_st.line_chart(
                r11_scenario_equity,
                use_container_width=True
            )

            r11_st.write("Условное распределение:")

            r11_allocation_df = r11_pd.DataFrame({
                "Монета": r11_available,
                "Доля (%)": r11_selected_weights * 100
            })

            r11_st.dataframe(
                r11_allocation_df,
                use_container_width=True,
                hide_index=True
            )

            r11_st.download_button(
                "📥 Скачать результаты симуляции",
                data=r11_allocation_df.to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name="virtual_allocation.csv",
                mime="text/csv"
            )

r11_st.caption(
    "Crypto AI Analyst 11.0 | Historical Risk Lab"
)


# ==========================================
# CRYPTO AI ANALYST 12.0
# ADVANCED AI INTELLIGENCE
# ==========================================

import streamlit as a12_st
import ccxt as a12_ccxt
import pandas as a12_pd
import numpy as a12_np

from sklearn.ensemble import (
    RandomForestRegressor,
    HistGradientBoostingRegressor
)
from sklearn.metrics import mean_absolute_error

a12_st.divider()
a12_st.header("🧠 Crypto AI Analyst 12.0")
a12_st.subheader("Advanced AI Intelligence")

a12_st.warning(
    "Экспериментальная аналитика. Рейтинги и прогнозы "
    "не гарантируют будущих результатов и не являются "
    "рекомендациями по покупке или продаже."
)

a12_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

a12_exchange = a12_ccxt.binance({
    "enableRateLimit": True
})

# ==========================================
# 1. MARKET REGIME DETECTION
# ==========================================

a12_st.subheader("🌐 1. Рыночные режимы")

if a12_st.button(
    "🔍 Определить состояние рынка",
    key="a12_regime_button"
):
    a12_regime_results = []

    with a12_st.spinner("Анализируем рынок..."):
        for a12_symbol in a12_symbols:
            try:
                a12_raw = a12_exchange.fetch_ohlcv(
                    a12_symbol,
                    timeframe="1d",
                    limit=100
                )

                a12_df = a12_pd.DataFrame(
                    a12_raw,
                    columns=[
                        "timestamp", "open", "high",
                        "low", "close", "volume"
                    ]
                )

                a12_df = a12_df.iloc[:-1].copy()

                if len(a12_df) < 55:
                    continue

                a12_close = a12_df["close"]
                a12_return = a12_close.pct_change()

                a12_sma20 = a12_close.rolling(20).mean()
                a12_sma50 = a12_close.rolling(50).mean()

                a12_change20 = (
                    a12_close.iloc[-1] /
                    a12_close.iloc[-21] - 1
                ) * 100

                a12_volatility = (
                    a12_return.tail(20).std() *
                    a12_np.sqrt(365) * 100
                )

                a12_current = a12_close.iloc[-1]
                a12_fast = a12_sma20.iloc[-1]
                a12_slow = a12_sma50.iloc[-1]

                if (
                    a12_current > a12_fast > a12_slow
                    and a12_change20 > 2
                ):
                    a12_regime = "Восходящий тренд"

                elif (
                    a12_current < a12_fast < a12_slow
                    and a12_change20 < -2
                ):
                    a12_regime = "Нисходящий тренд"

                else:
                    a12_regime = "Боковое / смешанное движение"

                a12_regime_results.append({
                    "Монета": a12_symbol,
                    "Цена": a12_current,
                    "Изменение за 20 дней (%)":
                        a12_change20,
                    "Волатильность (%)":
                        a12_volatility,
                    "Режим": a12_regime
                })

            except Exception:
                continue

    a12_st.session_state["a12_regimes"] = (
        a12_regime_results
    )

if "a12_regimes" in a12_st.session_state:
    a12_regime_df = a12_pd.DataFrame(
        a12_st.session_state["a12_regimes"]
    )

    if not a12_regime_df.empty:
        a12_st.dataframe(
            a12_regime_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        a12_st.info("Не удалось получить данные.")

# ==========================================
# 2. TREND ANALYSIS
# ==========================================

a12_st.divider()
a12_st.subheader("📈 2. Анализ трендов")

a12_trend_symbol = a12_st.selectbox(
    "Выбери монету для анализа",
    a12_symbols,
    key="a12_trend_symbol"
)

if a12_st.button(
    "Анализировать тренд",
    key="a12_trend_button"
):
    try:
        with a12_st.spinner("Анализируем тренд..."):
            a12_raw = a12_exchange.fetch_ohlcv(
                a12_trend_symbol,
                timeframe="1d",
                limit=120
            )

            a12_trend_df = a12_pd.DataFrame(
                a12_raw,
                columns=[
                    "timestamp", "open", "high",
                    "low", "close", "volume"
                ]
            )

            a12_trend_df = a12_trend_df.iloc[:-1].copy()

            a12_trend_df["SMA20"] = (
                a12_trend_df["close"].rolling(20).mean()
            )

            a12_trend_df["SMA50"] = (
                a12_trend_df["close"].rolling(50).mean()
            )

            a12_delta = a12_trend_df["close"].diff()

            a12_gain = a12_delta.clip(lower=0).ewm(
                alpha=1/14,
                adjust=False
            ).mean()

            a12_loss = (-a12_delta.clip(upper=0)).ewm(
                alpha=1/14,
                adjust=False
            ).mean()

            a12_rs = a12_gain / a12_loss.replace(
                0, float("nan")
            )

            a12_trend_df["RSI"] = (
                100 - 100 / (1 + a12_rs)
            )

            a12_last = a12_trend_df.iloc[-1]

            a12_score = 0

            if a12_last["close"] > a12_last["SMA20"]:
                a12_score += 1

            if a12_last["SMA20"] > a12_last["SMA50"]:
                a12_score += 1

            if a12_last["RSI"] > 50:
                a12_score += 1
            elif a12_last["RSI"] < 50:
                a12_score -= 1

            a12_st.metric(
                "Последняя цена",
                f"${a12_last['close']:,.4f}"
            )

            a12_st.metric(
                "RSI",
                f"{a12_last['RSI']:.2f}"
            )

            a12_st.metric(
                "Аналитический балл",
                f"{a12_score:+d} / 3"
            )

            if a12_score >= 2:
                a12_st.success(
                    "Преобладают положительные технические признаки."
                )
            elif a12_score <= -2:
                a12_st.warning(
                    "Преобладают отрицательные технические признаки."
                )
            else:
                a12_st.info(
                    "Сигналы смешанные или нейтральные."
                )

            a12_st.line_chart(
                a12_trend_df.set_index("timestamp")[
                    ["close", "SMA20", "SMA50"]
                ],
                use_container_width=True
            )

    except Exception as a12_error:
        a12_st.error(f"Ошибка анализа: {a12_error}")

# ==========================================
# 3. ML MODEL COMPARISON
# ==========================================

a12_st.divider()
a12_st.subheader("🔬 3. Сравнение ML-моделей")

a12_ml_symbol = a12_st.selectbox(
    "Монета для тестирования",
    a12_symbols,
    key="a12_ml_symbol"
)

if a12_st.button(
    "Сравнить модели",
    key="a12_ml_button"
):
    try:
        with a12_st.spinner("Обучаем и тестируем модели..."):

            a12_raw = a12_exchange.fetch_ohlcv(
                a12_ml_symbol,
                timeframe="1h",
                limit=700
            )

            a12_ml_df = a12_pd.DataFrame(
                a12_raw,
                columns=[
                    "timestamp", "open", "high",
                    "low", "close", "volume"
                ]
            )

            a12_ml_df = a12_ml_df.iloc[:-1].copy()

            a12_ml_df["return1"] = (
                a12_ml_df["close"].pct_change()
            )

            a12_ml_df["return3"] = (
                a12_ml_df["close"].pct_change(3)
            )

            a12_ml_df["return6"] = (
                a12_ml_df["close"].pct_change(6)
            )

            a12_ml_df["sma_ratio"] = (
                a12_ml_df["close"].rolling(10).mean() /
                a12_ml_df["close"].rolling(30).mean() - 1
            )

            a12_ml_df["volatility"] = (
                a12_ml_df["return1"].rolling(10).std()
            )

            a12_ml_df["target"] = (
                a12_ml_df["close"].shift(-1) /
                a12_ml_df["close"] - 1
            )

            a12_features = [
                "return1",
                "return3",
                "return6",
                "sma_ratio",
                "volatility"
            ]

            a12_ml_df = a12_ml_df.replace(
                [a12_np.inf, -a12_np.inf],
                a12_np.nan
            ).dropna(
                subset=a12_features + ["target"]
            )

            if len(a12_ml_df) < 150:
                raise ValueError("Недостаточно данных.")

            a12_X = a12_ml_df[a12_features]
            a12_y = a12_ml_df["target"]

            a12_split = int(len(a12_ml_df) * 0.8)

            a12_X_train = a12_X.iloc[:a12_split]
            a12_X_test = a12_X.iloc[a12_split:]

            a12_y_train = a12_y.iloc[:a12_split]
            a12_y_test = a12_y.iloc[a12_split:]

            a12_models = {
                "Random Forest": RandomForestRegressor(
                    n_estimators=150,
                    max_depth=6,
                    min_samples_leaf=5,
                    random_state=42,
                    n_jobs=-1
                ),

                "Gradient Boosting":
                    HistGradientBoostingRegressor(
                        max_iter=150,
                        max_leaf_nodes=15,
                        l2_regularization=1.0,
                        random_state=42
                    )
            }

            a12_results = []
            a12_predictions = {}

            for a12_name, a12_model in a12_models.items():

                a12_model.fit(
                    a12_X_train,
                    a12_y_train
                )

                a12_prediction = a12_model.predict(
                    a12_X_test
                )

                a12_mae = mean_absolute_error(
                    a12_y_test,
                    a12_prediction
                )

                a12_direction_accuracy = (
                    (
                        a12_np.sign(a12_prediction) ==
                        a12_np.sign(a12_y_test.values)
                    ).mean() * 100
                )

                a12_results.append({
                    "Модель": a12_name,
                    "MAE (%)": a12_mae * 100,
                    "Совпадение направления (%)":
                        a12_direction_accuracy
                })

                a12_predictions[a12_name] = (
                    a12_prediction
                )

            a12_results_df = a12_pd.DataFrame(
                a12_results
            ).sort_values("MAE (%)")

            a12_st.session_state["a12_ml_results"] = (
                a12_results_df
            )

            a12_st.session_state["a12_ml_predictions"] = (
                a12_predictions
            )

            a12_st.session_state["a12_ml_actual"] = (
                a12_y_test.values
            )

    except Exception as a12_error:
        a12_st.error(f"Ошибка ML: {a12_error}")

if "a12_ml_results" in a12_st.session_state:

    a12_st.dataframe(
        a12_st.session_state["a12_ml_results"],
        use_container_width=True,
        hide_index=True
    )

    a12_st.caption(
        "Меньшая MAE означает меньшую среднюю ошибку "
        "на выбранном историческом тестовом отрезке."
    )

    a12_predictions = a12_st.session_state[
        "a12_ml_predictions"
    ]

    a12_actual = a12_st.session_state[
        "a12_ml_actual"
    ]

    a12_plot_data = a12_pd.DataFrame({
        "Факт (%)": a12_actual * 100
    })

    for a12_name, a12_prediction in a12_predictions.items():
        a12_plot_data[a12_name + " (%)"] = (
            a12_prediction * 100
        )

    a12_st.line_chart(
        a12_plot_data.tail(50),
        use_container_width=True
    )

    a12_best = a12_st.session_state[
        "a12_ml_results"
    ].iloc[0]

    a12_st.info(
        "На этом тестовом отрезке наименьшую MAE показала модель: "
        + a12_best["Модель"]
    )

# ==========================================
# 4. MODEL AGREEMENT
# ==========================================

a12_st.divider()
a12_st.subheader("🎯 4. Согласованность моделей")

if "a12_ml_predictions" in a12_st.session_state:

    a12_predictions = a12_st.session_state[
        "a12_ml_predictions"
    ]

    a12_actual = a12_st.session_state[
        "a12_ml_actual"
    ]

    a12_model_names = list(a12_predictions.keys())

    a12_last_predictions = [
        float(a12_predictions[name][-1])
        for name in a12_model_names
    ]

    a12_st.write("Последние тестовые прогнозы:")

    for a12_name, a12_value in zip(
        a12_model_names,
        a12_last_predictions
    ):
        a12_st.write(
            f"**{a12_name}:** {a12_value * 100:+.4f}%"
        )

    if len(a12_last_predictions) >= 2:
        if (
            a12_last_predictions[0] *
            a12_last_predictions[1] > 0
        ):
            a12_st.info(
                "Модели совпали по направлению последнего "
                "исторического тестового прогноза."
            )
        else:
            a12_st.info(
                "Модели разошлись во мнениях по направлению."
            )

    a12_st.caption(
        "Согласие моделей не является вероятностью успеха "
        "и не гарантирует правильность будущих прогнозов."
    )

# ==========================================
# 5. ANALYTICAL REPORT
# ==========================================

a12_st.divider()
a12_st.subheader("📄 5. Аналитический отчёт")

a12_report_lines = [
    "CRYPTO AI ANALYST 12.0",
    "ADVANCED AI INTELLIGENCE",
    "",
    "Учебный аналитический отчёт."
]

if "a12_regimes" in a12_st.session_state:
    a12_report_lines.append("")
    a12_report_lines.append("РЫНОЧНЫЕ РЕЖИМЫ:")

    for a12_item in a12_st.session_state["a12_regimes"]:
        a12_report_lines.append(
            a12_item["Монета"] + ": " +
            a12_item["Режим"]
        )

if "a12_ml_results" in a12_st.session_state:
    a12_report_lines.append("")
    a12_report_lines.append("СРАВНЕНИЕ МОДЕЛЕЙ:")

    for _, a12_row in (
        a12_st.session_state["a12_ml_results"].iterrows()
    ):
        a12_report_lines.append(
            a12_row["Модель"] +
            " | MAE: " +
            f"{a12_row['MAE (%)']:.4f}%"
        )

a12_report_lines.append("")
a12_report_lines.append(
    "Исторические результаты не гарантируют будущих."
)

a12_report = "\n".join(a12_report_lines)

a12_st.download_button(
    "📥 Скачать отчёт TXT",
    data=a12_report,
    file_name="crypto_ai_report_12.txt",
    mime="text/plain"
)

a12_st.caption(
    "Crypto AI Analyst 12.0 | Experimental Research Lab"
)


# ==========================================
# CRYPTO AI ANALYST 13.0
# DATA CENTER — SQLITE + AI HISTORY
# ==========================================

import sqlite3 as d13_sqlite
from pathlib import Path as d13_Path
from datetime import datetime as d13_datetime, timezone as d13_timezone

import streamlit as d13_st
import ccxt as d13_ccxt
import pandas as d13_pd
import numpy as d13_np

from sklearn.ensemble import RandomForestRegressor

d13_st.divider()
d13_st.header("💾 Crypto AI Analyst 13.0")
d13_st.subheader("Data Center")

d13_st.info(
    "Здесь хранятся учебные AI-прогнозы, результаты "
    "их последующей проверки и статистика ошибок."
)

# ==========================================
# DATABASE
# ==========================================

d13_DB_PATH = (
    d13_Path(__file__).resolve().parent.parent /
    "crypto_ai_history.db"
)

def d13_connect():
    connection = d13_sqlite.connect(d13_DB_PATH)
    connection.row_factory = d13_sqlite.Row
    return connection


def d13_init_database():
    with d13_connect() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                model TEXT NOT NULL,
                base_price REAL NOT NULL,
                predicted_return REAL NOT NULL,
                predicted_price REAL NOT NULL,
                target_timestamp INTEGER NOT NULL,
                actual_price REAL,
                actual_return REAL,
                status TEXT NOT NULL DEFAULT 'Pending'
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_prediction_status
            ON predictions(status)
        """)


d13_init_database()

# ==========================================
# SETTINGS
# ==========================================

d13_exchange = d13_ccxt.binance({
    "enableRateLimit": True
})

d13_symbols = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT"
]

d13_timeframes = ["1h", "4h", "1d"]

d13_durations = {
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000
}

d13_features = [
    "return1",
    "return3",
    "return6",
    "sma_ratio",
    "volatility"
]


# ==========================================
# FEATURE ENGINEERING
# ==========================================

def d13_prepare_data(df):
    df = df.copy()

    df["return1"] = df["close"].pct_change()
    df["return3"] = df["close"].pct_change(3)
    df["return6"] = df["close"].pct_change(6)

    df["sma_ratio"] = (
        df["close"].rolling(10).mean() /
        df["close"].rolling(30).mean() - 1
    )

    df["volatility"] = (
        df["return1"].rolling(10).std()
    )

    df["target"] = (
        df["close"].shift(-1) / df["close"] - 1
    )

    df = df.replace(
        [d13_np.inf, -d13_np.inf],
        d13_np.nan
    )

    return df


# ==========================================
# CREATE A NEW FORECAST
# ==========================================

d13_st.divider()
d13_st.subheader("🧠 Сохранить новый прогноз")

d13_col1, d13_col2 = d13_st.columns(2)

with d13_col1:
    d13_symbol = d13_st.selectbox(
        "Криптовалюта",
        d13_symbols,
        key="d13_symbol"
    )

with d13_col2:
    d13_timeframe = d13_st.selectbox(
        "Таймфрейм",
        d13_timeframes,
        key="d13_timeframe"
    )

if d13_st.button(
    "🧠 Создать и сохранить прогноз",
    key="d13_create"
):
    try:
        with d13_st.spinner(
            "Обучаем модель и сохраняем прогноз..."
        ):
            d13_raw = d13_exchange.fetch_ohlcv(
                d13_symbol,
                timeframe=d13_timeframe,
                limit=700
            )

            d13_df = d13_pd.DataFrame(
                d13_raw,
                columns=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume"
                ]
            )

            # Исключаем незакрытую свечу
            d13_df = d13_df.iloc[:-1].copy()

            d13_prepared = d13_prepare_data(d13_df)

            d13_training = d13_prepared.dropna(
                subset=d13_features + ["target"]
            )

            d13_latest = d13_prepared.dropna(
                subset=d13_features
            )

            if len(d13_training) < 150:
                raise ValueError(
                    "Недостаточно исторических данных."
                )

            if d13_latest.empty:
                raise ValueError(
                    "Не удалось подготовить признаки."
                )

            d13_X = d13_training[d13_features]
            d13_y = d13_training["target"]

            d13_model = RandomForestRegressor(
                n_estimators=150,
                max_depth=6,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1
            )

            d13_model.fit(d13_X, d13_y)

            d13_last_features = d13_latest[
                d13_features
            ].iloc[[-1]]

            d13_predicted_return = float(
                d13_model.predict(
                    d13_last_features
                )[0]
            )

            d13_last_row = d13_latest.iloc[-1]

            d13_base_price = float(
                d13_last_row["close"]
            )

            d13_predicted_price = (
                d13_base_price *
                (1 + d13_predicted_return)
            )

            d13_target_timestamp = (
                int(d13_last_row["timestamp"]) +
                d13_durations[d13_timeframe]
            )

            d13_created_at = (
                d13_datetime.now(
                    d13_timezone.utc
                ).isoformat()
            )

            with d13_connect() as connection:
                connection.execute("""
                    INSERT INTO predictions (
                        created_at,
                        symbol,
                        timeframe,
                        model,
                        base_price,
                        predicted_return,
                        predicted_price,
                        target_timestamp,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    d13_created_at,
                    d13_symbol,
                    d13_timeframe,
                    "Random Forest",
                    d13_base_price,
                    d13_predicted_return,
                    d13_predicted_price,
                    d13_target_timestamp,
                    "Pending"
                ))

        d13_st.success(
            "Прогноз успешно сохранён в SQLite!"
        )

        d13_st.metric(
            "Исходная цена",
            f"${d13_base_price:,.4f}"
        )

        d13_st.metric(
            "Расчётная цена",
            f"${d13_predicted_price:,.4f}"
        )

        d13_st.metric(
            "Прогноз изменения",
            f"{d13_predicted_return * 100:+.3f}%"
        )

        d13_st.caption(
            "Это экспериментальный прогноз, а не рекомендация "
            "по совершению сделки."
        )

    except Exception as d13_error:
        d13_st.error(
            f"Ошибка создания прогноза: {d13_error}"
        )


# ==========================================
# EVALUATE COMPLETED FORECASTS
# ==========================================

d13_st.divider()
d13_st.subheader("🔬 Проверка сохранённых прогнозов")

d13_st.write(
    "После закрытия следующей свечи можно проверить, "
    "насколько прогноз отличался от фактической цены."
)

if d13_st.button(
    "🔍 Проверить завершённые прогнозы",
    key="d13_evaluate"
):
    d13_checked = 0
    d13_errors = 0

    with d13_connect() as connection:
        d13_pending = connection.execute("""
            SELECT *
            FROM predictions
            WHERE status = 'Pending'
            ORDER BY id ASC
        """).fetchall()

    with d13_st.spinner(
        "Проверяем исторические прогнозы..."
    ):
        for d13_record in d13_pending:
            try:
                d13_target_ts = int(
                    d13_record["target_timestamp"]
                )

                d13_duration = d13_durations[
                    d13_record["timeframe"]
                ]

                d13_now_ms = int(
                    d13_datetime.now(
                        d13_timezone.utc
                    ).timestamp() * 1000
                )

                # Проверяем только после закрытия целевой свечи
                if d13_now_ms < (
                    d13_target_ts + d13_duration
                ):
                    continue

                d13_actual_candles = (
                    d13_exchange.fetch_ohlcv(
                        d13_record["symbol"],
                        timeframe=d13_record["timeframe"],
                        since=d13_target_ts,
                        limit=5
                    )
                )

                d13_match = next(
                    (
                        candle for candle in d13_actual_candles
                        if int(candle[0]) == d13_target_ts
                    ),
                    None
                )

                if d13_match is None:
                    continue

                d13_actual_price = float(
                    d13_match[4]
                )

                d13_base = float(
                    d13_record["base_price"]
                )

                d13_actual_return = (
                    d13_actual_price / d13_base - 1
                )

                with d13_connect() as connection:
                    connection.execute("""
                        UPDATE predictions
                        SET actual_price = ?,
                            actual_return = ?,
                            status = 'Evaluated'
                        WHERE id = ?
                    """, (
                        d13_actual_price,
                        d13_actual_return,
                        d13_record["id"]
                    ))

                d13_checked += 1

            except Exception:
                d13_errors += 1

    if d13_checked:
        d13_st.success(
            f"Проверено прогнозов: {d13_checked}"
        )
    else:
        d13_st.info(
            "Пока нет прогнозов, которые можно проверить. "
            "Для этого следующая свеча должна полностью закрыться."
        )

    if d13_errors:
        d13_st.warning(
            f"Не удалось проверить некоторые записи: {d13_errors}"
        )


# ==========================================
# FORECAST HISTORY
# ==========================================

d13_st.divider()
d13_st.subheader("📚 История прогнозов")

with d13_connect() as connection:
    d13_history_rows = connection.execute("""
        SELECT *
        FROM predictions
        ORDER BY id DESC
    """).fetchall()

d13_history = d13_pd.DataFrame([
    dict(row) for row in d13_history_rows
])

if not d13_history.empty:

    d13_display = d13_history[[
        "id",
        "created_at",
        "symbol",
        "timeframe",
        "base_price",
        "predicted_price",
        "actual_price",
        "status"
    ]].copy()

    d13_display.columns = [
        "ID",
        "Дата создания",
        "Монета",
        "Таймфрейм",
        "Исходная цена",
        "Прогноз",
        "Фактическая цена",
        "Статус"
    ]

    d13_st.dataframe(
        d13_display,
        use_container_width=True,
        hide_index=True
    )

else:
    d13_st.info(
        "История пока пустая. Создай первый прогноз."
    )


# ==========================================
# MODEL ACCURACY STATISTICS
# ==========================================

d13_st.divider()
d13_st.subheader("🎯 Статистика точности")

if not d13_history.empty:

    d13_evaluated = d13_history[
        d13_history["status"] == "Evaluated"
    ].copy()

    d13_total = len(d13_history)
    d13_completed = len(d13_evaluated)
    d13_pending_count = d13_total - d13_completed

    d13_a, d13_b, d13_c = d13_st.columns(3)

    d13_a.metric(
        "Всего прогнозов",
        d13_total
    )

    d13_b.metric(
        "Проверено",
        d13_completed
    )

    d13_c.metric(
        "Ожидают проверки",
        d13_pending_count
    )

    if d13_completed > 0:

        d13_evaluated["absolute_error"] = (
            d13_evaluated["predicted_return"] -
            d13_evaluated["actual_return"]
        ).abs()

        d13_mae = (
            d13_evaluated["absolute_error"].mean() * 100
        )

        d13_direction_accuracy = (
            (
                d13_np.sign(
                    d13_evaluated["predicted_return"]
                ) ==
                d13_np.sign(
                    d13_evaluated["actual_return"]
                )
            ).mean() * 100
        )

        d13_x, d13_y = d13_st.columns(2)

        d13_x.metric(
            "Средняя ошибка изменения",
            f"{d13_mae:.4f}%"
        )

        d13_y.metric(
            "Совпадение направления",
            f"{d13_direction_accuracy:.2f}%"
        )

        d13_accuracy_chart = d13_evaluated[
            ["predicted_return", "actual_return"]
        ].copy()

        d13_accuracy_chart.columns = [
            "Прогноз (%)",
            "Факт (%)"
        ]

        d13_accuracy_chart = (
            d13_accuracy_chart * 100
        )

        d13_st.line_chart(
            d13_accuracy_chart,
            use_container_width=True
        )

        d13_st.caption(
            "Статистика рассчитывается только по проверенным "
            "записям. Небольшая выборка может давать нестабильные "
            "результаты и не доказывает способность модели "
            "предсказывать будущие цены."
        )

    else:
        d13_st.info(
            "Статистика появится после проверки первых прогнозов."
        )


# ==========================================
# CSV EXPORT
# ==========================================

d13_st.divider()
d13_st.subheader("📤 Экспорт базы данных")

if not d13_history.empty:

    d13_csv = d13_history.to_csv(
        index=False
    ).encode("utf-8-sig")

    d13_st.download_button(
        "📥 Скачать всю историю прогнозов",
        data=d13_csv,
        file_name="crypto_ai_predictions_13.csv",
        mime="text/csv"
    )

d13_st.caption(
    "База данных: crypto_ai_history.db | "
    "Crypto AI Analyst 13.0"
)


# ==========================================
# CRYPTO AI ANALYST 14.0
# AI MODEL LAB
# ==========================================

import streamlit as d14_st
import ccxt as d14_ccxt
import pandas as d14_pd
import numpy as d14_np

from sklearn.ensemble import (
    RandomForestRegressor,
    HistGradientBoostingRegressor
)
from sklearn.linear_model import LinearRegression
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

d14_st.divider()
d14_st.header("🧪 Crypto AI Analyst 14.0")
d14_st.subheader("AI Model Lab")

d14_st.write(
    "Сравнение алгоритмов машинного обучения "
    "на исторических рыночных данных."
)

d14_st.warning(
    "Экспериментальный анализ. Хорошие результаты на истории "
    "не гарантируют точности будущих прогнозов."
)

# ==========================================
# SETTINGS
# ==========================================

d14_exchange = d14_ccxt.binance({
    "enableRateLimit": True
})

d14_col1, d14_col2 = d14_st.columns(2)

with d14_col1:
    d14_symbol = d14_st.selectbox(
        "Монета",
        ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],
        key="d14_symbol"
    )

with d14_col2:
    d14_timeframe = d14_st.selectbox(
        "Таймфрейм",
        ["1h", "4h", "1d"],
        key="d14_timeframe"
    )

d14_candle_count = d14_st.slider(
    "Количество исторических свечей",
    min_value=300,
    max_value=1000,
    value=700,
    step=100,
    key="d14_candles"
)

# ==========================================
# FEATURE ENGINEERING
# ==========================================

def d14_prepare_data(df):
    df = df.copy()

    df["return1"] = df["close"].pct_change()
    df["return3"] = df["close"].pct_change(3)
    df["return6"] = df["close"].pct_change(6)

    df["sma_ratio"] = (
        df["close"].rolling(10).mean() /
        df["close"].rolling(30).mean() - 1
    )

    df["volatility"] = (
        df["return1"].rolling(10).std()
    )

    df["volume_change"] = (
        df["volume"].pct_change()
    )

    df["target"] = (
        df["close"].shift(-1) / df["close"] - 1
    )

    df = df.replace(
        [d14_np.inf, -d14_np.inf],
        d14_np.nan
    )

    return df


d14_features = [
    "return1",
    "return3",
    "return6",
    "sma_ratio",
    "volatility",
    "volume_change"
]

# ==========================================
# RUN MODEL LAB
# ==========================================

if d14_st.button(
    "🚀 Запустить сравнение моделей",
    key="d14_run"
):

    try:
        with d14_st.spinner(
            "Загружаем данные и обучаем модели..."
        ):

            d14_raw = d14_exchange.fetch_ohlcv(
                d14_symbol,
                timeframe=d14_timeframe,
                limit=d14_candle_count
            )

            d14_df = d14_pd.DataFrame(
                d14_raw,
                columns=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume"
                ]
            )

            # Исключаем незакрытую свечу
            d14_df = d14_df.iloc[:-1].copy()

            d14_df["date"] = d14_pd.to_datetime(
                d14_df["timestamp"],
                unit="ms",
                utc=True
            )

            d14_data = d14_prepare_data(d14_df)

            d14_data = d14_data.dropna(
                subset=d14_features + ["target"]
            ).copy()

            if len(d14_data) < 150:
                raise ValueError(
                    "Недостаточно данных для сравнения."
                )

            # Хронологическое разделение: первые 80% —
            # обучение, последние 20% — проверка.
            d14_split = int(len(d14_data) * 0.8)

            d14_train = d14_data.iloc[:d14_split]
            d14_test = d14_data.iloc[d14_split:]

            d14_X_train = d14_train[d14_features]
            d14_y_train = d14_train["target"]

            d14_X_test = d14_test[d14_features]
            d14_y_test = d14_test["target"]

            d14_models = {
                "Random Forest": RandomForestRegressor(
                    n_estimators=150,
                    max_depth=6,
                    min_samples_leaf=5,
                    random_state=42,
                    n_jobs=-1
                ),

                "Gradient Boosting": HistGradientBoostingRegressor(
                    max_iter=150,
                    max_leaf_nodes=15,
                    learning_rate=0.05,
                    random_state=42
                ),

                "Linear Regression": LinearRegression(),

                "Zero Return Baseline": DummyRegressor(
                    strategy="constant",
                    constant=0
                )
            }

            d14_results = []
            d14_predictions = {}

            for d14_name, d14_model in d14_models.items():

                d14_model.fit(
                    d14_X_train,
                    d14_y_train
                )

                d14_prediction = d14_model.predict(
                    d14_X_test
                )

                d14_predictions[d14_name] = d14_prediction

                d14_mae = mean_absolute_error(
                    d14_y_test,
                    d14_prediction
                )

                d14_rmse = mean_squared_error(
                    d14_y_test,
                    d14_prediction
                ) ** 0.5

                d14_direction = (
                    d14_np.sign(d14_prediction) ==
                    d14_np.sign(d14_y_test.to_numpy())
                ).mean() * 100

                d14_results.append({
                    "Модель": d14_name,
                    "MAE (%)": d14_mae * 100,
                    "RMSE (%)": d14_rmse * 100,
                    "Совпадение направления (%)": d14_direction
                })

            d14_results_df = d14_pd.DataFrame(
                d14_results
            ).sort_values("MAE (%)")

            # Сохраняем результаты в памяти Streamlit
            d14_st.session_state["d14_results"] = (
                d14_results_df
            )

            d14_st.session_state["d14_predictions"] = (
                d14_predictions
            )

            d14_st.session_state["d14_actual"] = (
                d14_y_test.to_numpy()
            )

            d14_st.session_state["d14_dates"] = (
                d14_test["date"].reset_index(drop=True)
            )

            d14_st.session_state["d14_data"] = d14_data

            d14_st.session_state["d14_features"] = d14_features

            d14_st.session_state["d14_symbol_used"] = d14_symbol

            d14_st.session_state["d14_timeframe_used"] = (
                d14_timeframe
            )

        d14_st.success(
            "Сравнение моделей завершено!"
        )

    except Exception as d14_error:
        d14_st.error(
            f"Ошибка: {d14_error}"
        )


# ==========================================
# RESULTS
# ==========================================

if "d14_results" in d14_st.session_state:

    d14_st.divider()
    d14_st.subheader("🏆 Результаты сравнения")

    d14_results_df = d14_st.session_state[
        "d14_results"
    ]

    d14_st.dataframe(
        d14_results_df.round(4),
        use_container_width=True,
        hide_index=True
    )

    d14_best = d14_results_df.iloc[0]

    d14_st.metric(
        "Минимальная MAE",
        f"{d14_best['MAE (%)']:.4f}%",
        help="Средняя абсолютная ошибка прогноза изменения цены."
    )

    d14_st.caption(
        f"Лучшая модель по MAE на этой проверочной выборке: "
        f"{d14_best['Модель']}. Это не означает, что она "
        f"будет лучшей на будущих данных."
    )

    # ======================================
    # MAE COMPARISON
    # ======================================

    d14_st.subheader("📊 Сравнение ошибок")

    d14_mae_chart = d14_results_df.set_index(
        "Модель"
    )[["MAE (%)", "RMSE (%)"]]

    d14_st.bar_chart(
        d14_mae_chart,
        use_container_width=True
    )

    # ======================================
    # ACTUAL VS PREDICTED
    # ======================================

    d14_st.subheader("📈 Фактические значения и прогнозы")

    d14_prediction_names = [
        name for name in d14_st.session_state[
            "d14_predictions"
        ].keys()
        if name != "Zero Return Baseline"
    ]

    d14_selected_model = d14_st.selectbox(
        "Выбери модель для графика",
        d14_prediction_names,
        key="d14_selected_model"
    )

    d14_actual = d14_st.session_state[
        "d14_actual"
    ]

    d14_predicted = d14_st.session_state[
        "d14_predictions"
    ][d14_selected_model]

    d14_dates = d14_st.session_state[
        "d14_dates"
    ]

    d14_comparison = d14_pd.DataFrame({
        "Факт (%)": d14_actual * 100,
        "Прогноз (%)": d14_predicted * 100
    }, index=d14_dates)

    d14_st.line_chart(
        d14_comparison,
        use_container_width=True
    )

    # ======================================
    # ERROR ANALYSIS
    # ======================================

    d14_st.subheader("🔍 Анализ ошибок")

    d14_error_df = d14_pd.DataFrame({
        "Дата": d14_dates,
        "Абсолютная ошибка (%)": (
            d14_np.abs(
                d14_actual - d14_predicted
            ) * 100
        ),
        "Фактическое изменение (%)": (
            d14_actual * 100
        ),
        "Прогноз (%)": (
            d14_predicted * 100
        )
    })

    d14_st.line_chart(
        d14_error_df.set_index("Дата")[
            ["Абсолютная ошибка (%)"]
        ],
        use_container_width=True
    )

    d14_st.dataframe(
        d14_error_df.tail(20).round(4),
        use_container_width=True,
        hide_index=True
    )

    # ======================================
    # FEATURE IMPORTANCE
    # ======================================

    d14_st.subheader("🧩 Важность признаков")

    d14_rf = RandomForestRegressor(
        n_estimators=150,
        max_depth=6,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1
    )

    d14_data = d14_st.session_state[
        "d14_data"
    ]

    d14_split = int(len(d14_data) * 0.8)

    d14_rf.fit(
        d14_data.iloc[:d14_split][d14_features],
        d14_data.iloc[:d14_split]["target"]
    )

    d14_importance = d14_pd.DataFrame({
        "Признак": d14_features,
        "Важность": d14_rf.feature_importances_
    }).sort_values(
        "Важность",
        ascending=False
    ).set_index("Признак")

    d14_st.bar_chart(
        d14_importance,
        use_container_width=True
    )

    d14_st.caption(
        "Важность признака показывает его вклад в работу "
        "Random Forest, но не доказывает причинно-следственную "
        "связь с движением цены."
    )

    # ======================================
    # EXPORT
    # ======================================

    d14_st.divider()
    d14_st.subheader("📤 Экспорт результатов")

    d14_export = d14_error_df.copy()

    d14_csv = d14_export.to_csv(
        index=False
    ).encode("utf-8-sig")

    d14_st.download_button(
        "📥 Скачать результаты проверки CSV",
        data=d14_csv,
        file_name="crypto_ai_model_lab_14.csv",
        mime="text/csv",
        key="d14_export"
    )

    d14_st.caption(
        "Crypto AI Analyst 14.0 | AI Model Lab"
    )


# ==========================================
# CRYPTO AI ANALYST 15.0
# AI INTELLIGENCE CENTER
# ==========================================

import streamlit as d15_st
import ccxt as d15_ccxt
import pandas as d15_pd
import numpy as d15_np
import io as d15_io

from sklearn.ensemble import IsolationForest

from reportlab.lib import colors as d15_colors
from reportlab.lib.pagesizes import A4 as d15_A4
from reportlab.lib.styles import getSampleStyleSheet as d15_styles
from reportlab.platypus import (
    SimpleDocTemplate as d15_Doc,
    Paragraph as d15_Paragraph,
    Spacer as d15_Spacer,
    Table as d15_Table,
    TableStyle as d15_TableStyle
)

d15_st.divider()
d15_st.header("🧠 Crypto AI Analyst 15.0")
d15_st.subheader("AI Intelligence Center")

d15_st.info(
    "Центр анализа рынка: аномалии, волатильность, "
    "рыночные режимы и сравнение таймфреймов."
)

d15_st.warning(
    "Это экспериментальный аналитический инструмент. "
    "Он не гарантирует точность прогнозов и не является "
    "рекомендацией покупать или продавать активы."
)

# ==========================================
# CONNECTION AND SETTINGS
# ==========================================

d15_exchange = d15_ccxt.binance({
    "enableRateLimit": True
})

d15_symbols = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT"
]

d15_timeframes = ["1h", "4h", "1d"]

d15_periods = {
    "1h": 24 * 365,
    "4h": 6 * 365,
    "1d": 365
}

d15_col1, d15_col2 = d15_st.columns(2)

with d15_col1:
    d15_symbol = d15_st.selectbox(
        "Выбери монету",
        d15_symbols,
        key="d15_symbol"
    )

with d15_col2:
    d15_timeframe = d15_st.selectbox(
        "Основной таймфрейм",
        d15_timeframes,
        key="d15_timeframe"
    )

# ==========================================
# DATA FUNCTIONS
# ==========================================

def d15_get_data(symbol, timeframe, limit=300):
    raw = d15_exchange.fetch_ohlcv(
        symbol,
        timeframe=timeframe,
        limit=limit
    )

    df = d15_pd.DataFrame(
        raw,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]
    )

    # Убираем последнюю незакрытую свечу
    df = df.iloc[:-1].copy()

    df["date"] = d15_pd.to_datetime(
        df["timestamp"],
        unit="ms",
        utc=True
    )

    return df.reset_index(drop=True)


def d15_indicators(df):
    df = df.copy()

    df["return"] = df["close"].pct_change()
    df["sma20"] = df["close"].rolling(20).mean()
    df["sma50"] = df["close"].rolling(50).mean()

    df["volatility"] = (
        df["return"].rolling(20).std()
    )

    df["volume_change"] = (
        df["volume"].pct_change()
    )

    df["change20"] = (
        df["close"].pct_change(20) * 100
    )

    return df.replace(
        [d15_np.inf, -d15_np.inf],
        d15_np.nan
    )


def d15_get_regime(row):
    if d15_pd.isna(row["sma50"]):
        return "Недостаточно данных"

    if (
        row["close"] > row["sma20"]
        and row["sma20"] > row["sma50"]
        and row["change20"] > 0
    ):
        return "Восходящий"

    if (
        row["close"] < row["sma20"]
        and row["sma20"] < row["sma50"]
        and row["change20"] < 0
    ):
        return "Нисходящий"

    return "Боковой / смешанный"


# ==========================================
# RUN ANALYSIS
# ==========================================

d15_st.divider()
d15_st.subheader("🔎 Полный анализ рынка")

if d15_st.button(
    "Запустить AI Intelligence",
    key="d15_run"
):

    try:
        d15_report = {
            "symbol": d15_symbol,
            "timeframe": d15_timeframe,
            "created": d15_pd.Timestamp.now(
                tz="UTC"
            ).strftime("%Y-%m-%d %H:%M UTC"),
            "main": {},
            "timeframes": [],
            "market": [],
            "anomaly": "Не определена"
        }

        with d15_st.spinner(
            "Анализируем рынок и загружаем данные..."
        ):

            # ----------------------------------
            # MAIN TIMEFRAME
            # ----------------------------------

            d15_raw_df = d15_get_data(
                d15_symbol,
                d15_timeframe,
                500
            )

            d15_df = d15_indicators(d15_raw_df)

            d15_last = d15_df.iloc[-1]

            d15_volatility = float(
                d15_last["volatility"] * 100
            )

            d15_annual_volatility = (
                float(d15_last["volatility"])
                * d15_np.sqrt(
                    d15_periods[d15_timeframe]
                )
                * 100
            )

            d15_regime = d15_get_regime(d15_last)

            # ----------------------------------
            # ANOMALY DETECTION
            # ----------------------------------

            d15_anomaly_features = d15_df[
                ["return", "volume_change", "volatility"]
            ].replace(
                [d15_np.inf, -d15_np.inf],
                d15_np.nan
            ).dropna()

            if len(d15_anomaly_features) >= 60:

                d15_anomaly_model = IsolationForest(
                    n_estimators=150,
                    contamination=0.03,
                    random_state=42
                )

                d15_anomaly_model.fit(
                    d15_anomaly_features
                )

                d15_latest_features = (
                    d15_anomaly_features.iloc[[-1]]
                )

                d15_anomaly_result = (
                    d15_anomaly_model.predict(
                        d15_latest_features
                    )[0]
                )

                if d15_anomaly_result == -1:
                    d15_anomaly = (
                        "Обнаружено необычное движение"
                    )
                else:
                    d15_anomaly = (
                        "Необычных признаков не обнаружено"
                    )

            else:
                d15_anomaly = (
                    "Недостаточно данных для анализа"
                )

            d15_report["anomaly"] = d15_anomaly

            d15_report["main"] = {
                "price": float(d15_last["close"]),
                "change20": float(d15_last["change20"]),
                "volatility": d15_volatility,
                "annual_volatility": d15_annual_volatility,
                "regime": d15_regime
            }

            # ----------------------------------
            # MULTI-TIMEFRAME ANALYSIS
            # ----------------------------------

            for d15_tf in d15_timeframes:

                d15_tf_raw = d15_get_data(
                    d15_symbol,
                    d15_tf,
                    200
                )

                d15_tf_df = d15_indicators(
                    d15_tf_raw
                )

                d15_tf_last = d15_tf_df.iloc[-1]

                d15_tf_regime = d15_get_regime(
                    d15_tf_last
                )

                d15_report["timeframes"].append({
                    "timeframe": d15_tf,
                    "price": float(d15_tf_last["close"]),
                    "change20": float(d15_tf_last["change20"]),
                    "regime": d15_tf_regime
                })

            # ----------------------------------
            # MARKET OVERVIEW
            # ----------------------------------

            for d15_coin in [
                "BTC/USDT",
                "ETH/USDT",
                "SOL/USDT"
            ]:

                d15_coin_df = d15_indicators(
                    d15_get_data(
                        d15_coin,
                        "1d",
                        150
                    )
                )

                d15_coin_last = d15_coin_df.iloc[-1]

                d15_report["market"].append({
                    "coin": d15_coin,
                    "price": float(d15_coin_last["close"]),
                    "change": float(d15_coin_last["change20"]),
                    "regime": d15_get_regime(
                        d15_coin_last
                    )
                })

        d15_st.session_state["d15_report"] = (
            d15_report
        )

        d15_st.session_state["d15_chart"] = (
            d15_df.tail(100).copy()
        )

        d15_st.success(
            "Анализ успешно завершён!"
        )

    except Exception as d15_error:
        d15_st.error(
            f"Ошибка анализа: {d15_error}"
        )


# ==========================================
# DISPLAY RESULTS
# ==========================================

if "d15_report" in d15_st.session_state:

    d15_report = d15_st.session_state[
        "d15_report"
    ]

    d15_main = d15_report["main"]

    d15_st.divider()
    d15_st.subheader("📊 Основные показатели")

    d15_a, d15_b, d15_c = d15_st.columns(3)

    d15_a.metric(
        "Текущая цена",
        f"${d15_main['price']:,.4f}"
    )

    d15_b.metric(
        "Изменение за 20 свечей",
        f"{d15_main['change20']:+.2f}%"
    )

    d15_c.metric(
        "Волатильность",
        f"{d15_main['volatility']:.3f}%"
    )

    d15_st.metric(
        "Расчётная годовая волатильность",
        f"{d15_main['annual_volatility']:.2f}%"
    )

    d15_st.caption(
        "Годовая волатильность — статистическая оценка, "
        "полученная масштабированием исторической волатильности."
    )

    # --------------------------------------
    # MARKET REGIME
    # --------------------------------------

    d15_st.divider()
    d15_st.subheader("🌐 Рыночный режим")

    d15_st.write(
        f"**{d15_report['symbol']}**: "
        f"{d15_main['regime']}"
    )

    # --------------------------------------
    # ANOMALY
    # --------------------------------------

    d15_st.subheader("🚨 Обнаружение аномалий")

    d15_st.write(
        d15_report["anomaly"]
    )

    d15_st.caption(
        "Аномалия означает необычное сочетание исторических "
        "изменений цены, объёма и волатильности. Это не "
        "обязательно ошибка данных или начало нового тренда."
    )

    # --------------------------------------
    # MULTI-TIMEFRAME
    # --------------------------------------

    d15_st.divider()
    d15_st.subheader("⏱ Сравнение таймфреймов")

    d15_tf_df = d15_pd.DataFrame(
        d15_report["timeframes"]
    )

    d15_tf_df.columns = [
        "Таймфрейм",
        "Цена",
        "Изменение за 20 свечей (%)",
        "Режим"
    ]

    d15_st.dataframe(
        d15_tf_df.round(4),
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------
    # MARKET OVERVIEW
    # --------------------------------------

    d15_st.divider()
    d15_st.subheader("🌍 Обзор основных монет")

    d15_market_df = d15_pd.DataFrame(
        d15_report["market"]
    )

    d15_market_df.columns = [
        "Монета",
        "Цена",
        "Изменение за 20 дней (%)",
        "Режим"
    ]

    d15_st.dataframe(
        d15_market_df.round(4),
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------
    # PRICE AND VOLATILITY CHART
    # --------------------------------------

    d15_st.divider()
    d15_st.subheader("📈 График цены")

    d15_chart = d15_st.session_state[
        "d15_chart"
    ]

    d15_st.line_chart(
        d15_chart.set_index("date")[
            ["close", "sma20", "sma50"]
        ],
        use_container_width=True
    )

    d15_st.subheader("📉 Историческая волатильность")

    d15_st.line_chart(
        d15_chart.set_index("date")[
            ["volatility"]
        ] * 100,
        use_container_width=True
    )

    # ======================================
    # PDF REPORT
    # ======================================

    d15_st.divider()
    d15_st.subheader("📄 PDF-отчёт")

    def d15_create_pdf(report):

        d15_buffer = d15_io.BytesIO()

        d15_doc = d15_Doc(
            d15_buffer,
            pagesize=d15_A4
        )

        d15_stylesheet = d15_styles()

        d15_story = []

        d15_story.append(
            d15_Paragraph(
                "Crypto AI Analyst 15.0",
                d15_stylesheet["Title"]
            )
        )

        d15_story.append(
            d15_Paragraph(
                "AI Intelligence Center — Market Report",
                d15_stylesheet["Heading2"]
            )
        )

        d15_story.append(
            d15_Paragraph(
                f"Дата отчёта: {report['created']}",
                d15_stylesheet["Normal"]
            )
        )

        d15_story.append(d15_Spacer(1, 15))

        d15_story.append(
            d15_Paragraph(
                "Основной анализ",
                d15_stylesheet["Heading2"]
            )
        )

        d15_main_data = [
            ["Показатель", "Значение"],
            ["Монета", report["symbol"]],
            ["Таймфрейм", report["timeframe"]],
            ["Цена", f"${report['main']['price']:,.4f}"],
            ["Рыночный режим", report["main"]["regime"]],
            ["Изменение", f"{report['main']['change20']:.3f}%"],
            ["Волатильность", f"{report['main']['volatility']:.4f}%"],
            ["Годовая волатильность",
             f"{report['main']['annual_volatility']:.2f}%"],
            ["Аномалии", report["anomaly"]]
        ]

        d15_table = d15_Table(
            d15_main_data,
            colWidths=[220, 250]
        )

        d15_table.setStyle(
            d15_TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), d15_colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, d15_colors.grey),
                ("PADDING", (0, 0), (-1, -1), 7)
            ])
        )

        d15_story.append(d15_table)
        d15_story.append(d15_Spacer(1, 18))

        d15_story.append(
            d15_Paragraph(
                "Сравнение таймфреймов",
                d15_stylesheet["Heading2"]
            )
        )

        d15_tf_data = [
            ["Таймфрейм", "Цена", "Изменение", "Режим"]
        ]

        for item in report["timeframes"]:
            d15_tf_data.append([
                item["timeframe"],
                f"${item['price']:,.4f}",
                f"{item['change20']:.2f}%",
                item["regime"]
            ])

        d15_tf_table = d15_Table(
            d15_tf_data,
            colWidths=[75, 120, 100, 150]
        )

        d15_tf_table.setStyle(
            d15_TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), d15_colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, d15_colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6)
            ])
        )

        d15_story.append(d15_tf_table)
        d15_story.append(d15_Spacer(1, 18))

        d15_story.append(
            d15_Paragraph(
                "Обзор рынка",
                d15_stylesheet["Heading2"]
            )
        )

        d15_market_data = [
            ["Монета", "Цена", "Изменение", "Режим"]
        ]

        for item in report["market"]:
            d15_market_data.append([
                item["coin"],
                f"${item['price']:,.4f}",
                f"{item['change']:.2f}%",
                item["regime"]
            ])

        d15_market_table = d15_Table(
            d15_market_data,
            colWidths=[85, 120, 100, 140]
        )

        d15_market_table.setStyle(
            d15_TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), d15_colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, d15_colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6)
            ])
        )

        d15_story.append(d15_market_table)
        d15_story.append(d15_Spacer(1, 20))

        d15_story.append(
            d15_Paragraph(
                "Отчёт предназначен для образовательного "
                "анализа исторических рыночных данных. "
                "Показатели не гарантируют будущих результатов "
                "и не являются финансовой рекомендацией.",
                d15_stylesheet["Normal"]
            )
        )

        d15_doc.build(d15_story)

        return d15_buffer.getvalue()

    try:
        d15_pdf = d15_create_pdf(d15_report)

        d15_st.download_button(
            "📥 Скачать PDF-отчёт",
            data=d15_pdf,
            file_name="crypto_ai_intelligence_15.pdf",
            mime="application/pdf",
            key="d15_pdf"
        )

    except Exception as d15_pdf_error:
        d15_st.error(
            f"Ошибка создания PDF: {d15_pdf_error}"
        )

d15_st.caption(
    "Crypto AI Analyst 15.0 | AI Intelligence Center"
)


# ==========================================
# CRYPTO AI ANALYST 16.0
# AI RESEARCH CENTER=
# ==========================================

import io as d16_io
import streamlit as d16_st
import ccxt as d16_ccxt
import pandas as d16_pd
import numpy as d16_np

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

d16_st.divider()
d16_st.header("🔬 Crypto AI Analyst 16.0")
d16_st.subheader("AI Research Center")

d16_st.info(
    "Исследовательский центр для изучения исторических "
    "циклов, корреляций, кластеров и рыночных стрессов."
)

d16_st.warning(
    "Все результаты основаны на исторических данных. "
    "Они не гарантируют будущих изменений рынка."
)

# ==========================================
# SETTINGS
# ==========================================

d16_exchange = d16_ccxt.binance({
    "enableRateLimit": True
})

d16_symbols = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT"
]

d16_col1, d16_col2 = d16_st.columns(2)

with d16_col1:
    d16_days = d16_st.selectbox(
        "Исторический период",
        [180, 365, 500],
        index=1,
        key="d16_days"
    )

with d16_col2:
    d16_clusters = d16_st.slider(
        "Количество кластеров",
        min_value=2,
        max_value=4,
        value=3,
        key="d16_clusters"
    )

# ==========================================
# DATA LOADING
# ==========================================

def d16_load_coin(symbol, limit):
    raw = d16_exchange.fetch_ohlcv(
        symbol,
        timeframe="1d",
        limit=limit
    )

    df = d16_pd.DataFrame(
        raw,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]
    )

    # Последняя дневная свеча может быть незакрытой
    df = df.iloc[:-1].copy()

    df["date"] = d16_pd.to_datetime(
        df["timestamp"],
        unit="ms",
        utc=True
    )

    df = df[["date", "close", "volume"]]

    df = df.rename(columns={
        "close": symbol,
        "volume": symbol + "_volume"
    })

    return df


# ==========================================
# RESEARCH FUNCTIONS
# ==========================================

def d16_cycle_analysis(btc):
    df = btc.copy()

    df["sma30"] = df["BTC/USDT"].rolling(30).mean()
    df["sma90"] = df["BTC/USDT"].rolling(90).mean()

    df["return30"] = (
        df["BTC/USDT"].pct_change(30) * 100
    )

    df["rolling_high"] = (
        df["BTC/USDT"].rolling(180).max()
    )

    df["drawdown"] = (
        df["BTC/USDT"] / df["rolling_high"] - 1
    ) * 100

    conditions = [
        (
            (df["BTC/USDT"] > df["sma30"]) &
            (df["sma30"] > df["sma90"])
        ),
        (
            (df["BTC/USDT"] < df["sma30"]) &
            (df["sma30"] < df["sma90"])
        )
    ]

    choices = [
        "Восходящая фаза",
        "Нисходящая фаза"
    ]

    df["phase"] = d16_np.select(
        conditions,
        choices,
        default="Переходная фаза"
    )

    return df


def d16_cluster_analysis(returns, cluster_count):
    rows = []

    for coin in returns.columns:
        series = returns[coin].dropna()

        rows.append({
            "Монета": coin,
            "Средняя доходность (%)": series.mean() * 100,
            "Волатильность (%)": series.std() * 100,
            "Доля положительных дней (%)": (
                series > 0
            ).mean() * 100
        })

    features = d16_pd.DataFrame(rows)

    feature_columns = [
        "Средняя доходность (%)",
        "Волатильность (%)",
        "Доля положительных дней (%)"
    ]

    scaler = StandardScaler()

    scaled = scaler.fit_transform(
        features[feature_columns]
    )

    model = KMeans(
        n_clusters=cluster_count,
        random_state=42,
        n_init=10
    )

    features["Кластер"] = model.fit_predict(
        scaled
    ) + 1

    return features


def d16_find_similar_periods(btc):
    df = btc.copy()

    df["daily_return"] = df["BTC/USDT"].pct_change()

    window = 7

    rows = []

    for i in range(window, len(df) + 1):
        segment = df["daily_return"].iloc[
            i - window:i
        ].dropna()

        if len(segment) != window:
            continue

        cumulative_return = (
            (1 + segment).prod() - 1
        ) * 100

        volatility = segment.std() * 100

        positive_days = (
            segment > 0
        ).mean() * 100

        rows.append({
            "date": df["date"].iloc[i - 1],
            "return": cumulative_return,
            "volatility": volatility,
            "positive_days": positive_days
        })

    history = d16_pd.DataFrame(rows)

    if len(history) < 40:
        return d16_pd.DataFrame()

    feature_cols = [
        "return",
        "volatility",
        "positive_days"
    ]

    # Последние 7 дней — текущий исследуемый период.
    current = history.iloc[-1]

    # Исключаем последние 30 дней, чтобы не выбирать
    # практически совпадающие окна.
    candidates = history.iloc[:-30].copy()

    if len(candidates) < 5:
        return d16_pd.DataFrame()

    scaler = StandardScaler()

    combined = d16_pd.concat([
        candidates[feature_cols],
        history.tail(1)[feature_cols]
    ], ignore_index=True)

    scaled = scaler.fit_transform(combined)

    candidate_scaled = scaled[:-1]
    current_scaled = scaled[-1]

    distances = d16_np.sqrt(
        ((candidate_scaled - current_scaled) ** 2).sum(axis=1)
    )

    candidates["Сходство"] = distances

    candidates = candidates.sort_values(
        "Сходство"
    ).head(5)

    candidates["Период"] = candidates["date"].dt.strftime(
        "%Y-%m-%d"
    )

    candidates = candidates.rename(columns={
        "return": "Изменение за 7 дней (%)",
        "volatility": "Волатильность (%)",
        "positive_days": "Положительные дни (%)"
    })

    return candidates[[
        "Период",
        "Изменение за 7 дней (%)",
        "Волатильность (%)",
        "Положительные дни (%)",
        "Сходство"
    ]]


def d16_stress_analysis(btc):
    df = btc.copy()

    df["daily_return"] = df["BTC/USDT"].pct_change() * 100

    df["volatility7"] = (
        df["daily_return"].rolling(7).std()
    )

    return_threshold = df["daily_return"].quantile(0.05)
    volatility_threshold = df["volatility7"].quantile(0.90)

    df["stress"] = (
        (df["daily_return"] <= return_threshold) |
        (df["volatility7"] >= volatility_threshold)
    )

    events = df[df["stress"]].copy()

    events["Тип события"] = d16_np.where(
        events["daily_return"] <= return_threshold,
        "Сильное дневное снижение",
        "Высокая волатильность"
    )

    events = events.sort_values(
        "date",
        ascending=False
    ).head(20)

    return events[[
        "date",
        "BTC/USDT",
        "daily_return",
        "volatility7",
        "Тип события"
    ]].rename(columns={
        "date": "Дата",
        "BTC/USDT": "Цена BTC",
        "daily_return": "Изменение за день (%)",
        "volatility7": "Волатильность за 7 дней (%)"
    })


# ==========================================
# RUN RESEARCH
# ==========================================

d16_st.divider()
d16_st.subheader("🚀 Запуск исследования")

if d16_st.button(
    "Запустить AI Research Center",
    key="d16_run"
):

    try:
        with d16_st.spinner(
            "Загружаем исторические данные..."
        ):

            d16_coin_frames = {}

            for symbol in d16_symbols:
                d16_coin_frames[symbol] = d16_load_coin(
                    symbol,
                    d16_days
                )

            d16_prices = None

            for symbol, frame in d16_coin_frames.items():

                if d16_prices is None:
                    d16_prices = frame[
                        ["date", symbol]
                    ].copy()
                else:
                    d16_prices = d16_prices.merge(
                        frame[["date", symbol]],
                        on="date",
                        how="inner"
                    )

            d16_prices = d16_prices.sort_values(
                "date"
            ).reset_index(drop=True)

            if len(d16_prices) < 100:
                raise ValueError(
                    "Недостаточно общих исторических данных."
                )

            d16_returns = d16_prices[
                d16_symbols
            ].pct_change().dropna()

            # 1. Корреляция
            d16_correlation = d16_returns.corr()

            # 2. Кластеры
            d16_cluster_result = d16_cluster_analysis(
                d16_returns,
                d16_clusters
            )

            # 3. BTC cycle
            d16_btc = d16_prices[
                ["date", "BTC/USDT"]
            ].copy()

            d16_cycles = d16_cycle_analysis(
                d16_btc
            )

            # 4. Similar historical periods
            d16_similar = d16_find_similar_periods(
                d16_btc
            )

            # 5. Stress periods
            d16_stress = d16_stress_analysis(
                d16_btc
            )

            d16_result = {
                "prices": d16_prices,
                "returns": d16_returns,
                "correlation": d16_correlation,
                "clusters": d16_cluster_result,
                "cycles": d16_cycles,
                "similar": d16_similar,
                "stress": d16_stress,
                "created": d16_pd.Timestamp.now(
                    tz="UTC"
                ).strftime("%Y-%m-%d %H:%M UTC")
            }

            d16_st.session_state["d16_result"] = d16_result

        d16_st.success(
            "Исследование успешно завершено!"
        )

    except Exception as d16_error:
        d16_st.error(
            f"Ошибка исследования: {d16_error}"
        )


# ==========================================
# DISPLAY RESULTS
# ==========================================

if "d16_result" in d16_st.session_state:

    d16_result = d16_st.session_state[
        "d16_result"
    ]

    d16_st.divider()
    d16_st.subheader("📊 1. Корреляция криптовалют")

    d16_st.write(
        "Корреляция показывает, насколько согласованно "
        "изменялись дневные доходности двух монет."
    )

    d16_st.dataframe(
        d16_result["correlation"].round(3),
        use_container_width=True
    )

    d16_st.caption(
        "Значение около +1 означает сильную положительную "
        "связь, около -1 — отрицательную, около 0 — слабую."
    )

    d16_st.subheader("📈 Корреляционная карта")

    d16_st.bar_chart(
        d16_result["correlation"],
        use_container_width=True
    )

    # --------------------------------------
    # CLUSTERING
    # --------------------------------------

    d16_st.divider()
    d16_st.subheader("🧩 2. Кластеризация монет")

    d16_st.write(
        "Монеты группируются по средней доходности, "
        "волатильности и доле положительных дней."
    )

    d16_st.dataframe(
        d16_result["clusters"].round(3),
        use_container_width=True,
        hide_index=True
    )

    d16_st.caption(
        "Номер кластера условный. Кластеры не являются "
        "рейтингом качества или прогнозом цены."
    )

    # --------------------------------------
    # BTC CYCLES
    # --------------------------------------

    d16_st.divider()
    d16_st.subheader("🔄 3. Исторические циклы BTC")

    d16_cycles = d16_result["cycles"]

    d16_latest_cycle = d16_cycles.iloc[-1]

    d16_st.metric(
        "Текущая историческая фаза",
        d16_latest_cycle["phase"]
    )

    d16_st.metric(
        "Отклонение от 180-дневного максимума",
        f"{d16_latest_cycle['drawdown']:.2f}%"
    )

    d16_st.line_chart(
        d16_cycles.set_index("date")[
            ["BTC/USDT", "sma30", "sma90"]
        ],
        use_container_width=True
    )

    d16_st.subheader("Историческая просадка BTC")

    d16_st.line_chart(
        d16_cycles.set_index("date")[
            ["drawdown"]
        ],
        use_container_width=True
    )

    # --------------------------------------
    # SIMILAR PERIODS
    # --------------------------------------

    d16_st.divider()
    d16_st.subheader("🔍 4. Похожие исторические периоды")

    d16_st.write(
        "Сравниваются последние 7 дней с предыдущими "
        "семидневными периодами по доходности, волатильности "
        "и доле положительных дней."
    )

    if not d16_result["similar"].empty:

        d16_st.dataframe(
            d16_result["similar"].round(4),
            use_container_width=True,
            hide_index=True
        )

    else:
        d16_st.info(
            "Недостаточно данных для поиска похожих периодов."
        )

    # --------------------------------------
    # STRESS ANALYSIS
    # --------------------------------------

    d16_st.divider()
    d16_st.subheader("⚠️ 5. Рыночные стресс-периоды BTC")

    d16_st.write(
        "Показываются дни с сильным снижением или высокой "
        "волатильностью относительно выбранной истории."
    )

    d16_st.dataframe(
        d16_result["stress"].round(4),
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------
    # SUMMARY
    # --------------------------------------

    d16_st.divider()
    d16_st.subheader("📋 6. Исследовательский отчёт")

    d16_st.write(
        f"Дата исследования: {d16_result['created']}"
    )

    d16_st.write(
        f"Количество общих дневных наблюдений: "
        f"{len(d16_result['prices'])}"
    )

    d16_st.write(
        f"Количество монет: {len(d16_symbols)}"
    )

    d16_st.write(
        f"Количество найденных стресс-дней: "
        f"{len(d16_result['stress'])}"
    )

    # --------------------------------------
    # CSV EXPORT
    # --------------------------------------

    d16_st.divider()
    d16_st.subheader("📥 Скачать исследование")

    def d16_excel_safe(d16_frame):
        """Подготавливает таблицу к Excel, удаляя часовой пояс у дат."""
        d16_frame = d16_frame.copy()

        for d16_column in d16_frame.columns:
            d16_dtype = d16_frame[d16_column].dtype
            if isinstance(d16_dtype, d16_pd.DatetimeTZDtype):
                d16_frame[d16_column] = (
                    d16_frame[d16_column].dt.tz_localize(None)
                )

        if (
            isinstance(d16_frame.index, d16_pd.DatetimeIndex)
            and d16_frame.index.tz is not None
        ):
            d16_frame.index = d16_frame.index.tz_localize(None)

        return d16_frame

    d16_buffer = d16_io.BytesIO()

    with d16_pd.ExcelWriter(
        d16_buffer,
        engine="xlsxwriter"
    ) as d16_writer:

        d16_excel_safe(d16_result["prices"]).to_excel(
            d16_writer,
            sheet_name="Prices",
            index=False
        )

        d16_excel_safe(d16_result["returns"]).to_excel(
            d16_writer,
            sheet_name="Returns"
        )

        d16_excel_safe(d16_result["correlation"]).to_excel(
            d16_writer,
            sheet_name="Correlation"
        )

        d16_excel_safe(d16_result["clusters"]).to_excel(
            d16_writer,
            sheet_name="Clusters",
            index=False
        )

        d16_excel_safe(d16_result["cycles"]).to_excel(
            d16_writer,
            sheet_name="BTC Cycles",
            index=False
        )

        d16_excel_safe(d16_result["similar"]).to_excel(
            d16_writer,
            sheet_name="Similar Periods",
            index=False
        )

        d16_excel_safe(d16_result["stress"]).to_excel(
            d16_writer,
            sheet_name="Stress",
            index=False
        )

    d16_st.download_button(
        "📊 Скачать полный отчёт Excel",
        data=d16_buffer.getvalue(),
        file_name="crypto_ai_research_16.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="d16_export"
    )

d16_st.caption(
    "Crypto AI Analyst 16.0 | AI Research Center"
)

# ============================================================
# CRYPTO AI ANALYST 17.0
# AI PORTFOLIO INTELLIGENCE
# ============================================================

import streamlit as v17_st
import pandas as v17_pd
import numpy as v17_np
import plotly.graph_objects as v17_go
import ccxt as v17_ccxt
from datetime import datetime as v17_datetime

v17_st.divider()

v17_st.title("🧠 AI Portfolio Intelligence 17.0")

v17_st.caption(
    "Исторический анализ и виртуальное моделирование портфеля"
)

v17_exchange = v17_ccxt.binance({
    "enableRateLimit": True
})

v17_coins = {
    "BTC": "BTC/USDT",
    "ETH": "ETH/USDT",
    "SOL": "SOL/USDT",
    "BNB": "BNB/USDT",
    "XRP": "XRP/USDT"
}

v17_st.subheader("⚙️ Настройки анализа")

v17_days = v17_st.selectbox(
    "Период анализа",
    [30, 60, 90, 180, 365],
    index=3
)

v17_capital = v17_st.number_input(
    "Начальный виртуальный капитал ($)",
    min_value=100.0,
    max_value=1000000.0,
    value=10000.0,
    step=500.0
)

v17_st.write(
    "Выбери распределение виртуального капитала:"
)

v17_col1, v17_col2, v17_col3 = v17_st.columns(3)

with v17_col1:
    v17_btc = v17_st.slider(
        "BTC (%)", 0, 100, 40
    )

with v17_col2:
    v17_eth = v17_st.slider(
        "ETH (%)", 0, 100, 25
    )

with v17_col3:
    v17_sol = v17_st.slider(
        "SOL (%)", 0, 100, 15
    )

v17_col4, v17_col5 = v17_st.columns(2)

with v17_col4:
    v17_bnb = v17_st.slider(
        "BNB (%)", 0, 100, 10
    )

with v17_col5:
    v17_xrp = v17_st.slider(
        "XRP (%)", 0, 100, 10
    )

v17_total_weight = (
    v17_btc + v17_eth + v17_sol + v17_bnb + v17_xrp
)

v17_st.write(
    f"Сумма распределения: **{v17_total_weight}%**"
)

if v17_total_weight != 100:
    v17_st.warning(
        "Сумма распределения должна составлять ровно 100%."
    )

v17_allocations = {
    "BTC": v17_btc,
    "ETH": v17_eth,
    "SOL": v17_sol,
    "BNB": v17_bnb,
    "XRP": v17_xrp
}

v17_st.caption(
    "Результаты будут основаны на исторических данных. "
    "Прошлая доходность не гарантирует будущих результатов."
)
# ============================================================
# 17.0 — ЗАГРУЗКА ИСТОРИЧЕСКИХ ДАННЫХ
# ============================================================

def v17_load_history(symbol, days):
    candles = v17_exchange.fetch_ohlcv(
        symbol,
        timeframe="1d",
        limit=days
    )

    frame = v17_pd.DataFrame(
        candles,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]
    )

    frame["date"] = v17_pd.to_datetime(
        frame["timestamp"],
        unit="ms",
        utc=True
    )

    frame = frame.set_index("date")

    return frame["close"].astype(float)


# ============================================================
# 17.0 — ЗАПУСК АНАЛИЗА
# ============================================================

v17_st.divider()

if v17_st.button(
    "🚀 Запустить AI Portfolio Analysis 17.0",
    use_container_width=True
):

    if v17_total_weight != 100:
        v17_st.error(
            "Сначала установи сумму распределения на 100%."
        )

    else:

        try:
            v17_price_data = {}

            v17_progress = v17_st.progress(0)
            v17_status = v17_st.empty()

            v17_coin_list = list(v17_coins.items())

            for v17_i, (v17_ticker, v17_symbol) in enumerate(
                v17_coin_list
            ):

                v17_status.write(
                    f"Загружаем данные {v17_ticker}..."
                )

                v17_price_data[v17_ticker] = (
                    v17_load_history(
                        v17_symbol,
                        v17_days
                    )
                )

                v17_progress.progress(
                    (v17_i + 1) / len(v17_coin_list)
                )

            v17_status.success(
                "Исторические данные загружены."
            )

            # Объединяем цены
            v17_prices = v17_pd.DataFrame(
                v17_price_data
            ).dropna()

            if len(v17_prices) < 10:
                raise ValueError(
                    "Недостаточно исторических данных."
                )

            # Доходность активов
            v17_returns = v17_prices.pct_change().dropna()

            # Веса портфеля
            v17_weights = v17_pd.Series({
                key: value / 100
                for key, value in v17_allocations.items()
            })

            # Доходность виртуального портфеля
            v17_portfolio_returns = (
                v17_returns * v17_weights
            ).sum(axis=1)

            # Кривая капитала
            v17_equity = (
                1 + v17_portfolio_returns
            ).cumprod() * v17_capital

            # Buy and hold для каждого актива
            v17_asset_results = {}

            for v17_asset in v17_prices.columns:

                v17_asset_return = (
                    v17_prices[v17_asset].iloc[-1]
                    / v17_prices[v17_asset].iloc[0]
                    - 1
                ) * 100

                v17_asset_results[v17_asset] = (
                    v17_asset_return
                )

            # Общие показатели
            v17_final_capital = float(
                v17_equity.iloc[-1]
            )

            v17_total_return = (
                v17_final_capital
                / v17_capital - 1
            ) * 100

            # Максимальная просадка
            v17_peak = v17_equity.cummax()

            v17_drawdown = (
                v17_equity / v17_peak - 1
            ) * 100

            v17_max_drawdown = float(
                v17_drawdown.min()
            )

            # Волатильность
            v17_volatility = float(
                v17_portfolio_returns.std()
                * (365 ** 0.5)
                * 100
            )

            # Sharpe Ratio — без учёта безрисковой ставки
            v17_std = v17_portfolio_returns.std()

            if v17_std > 0:
                v17_sharpe = float(
                    v17_portfolio_returns.mean()
                    / v17_std
                    * (365 ** 0.5)
                )
            else:
                v17_sharpe = 0.0

            # Сохраняем результаты
            v17_st.session_state["v17_equity"] = (
                v17_equity
            )

            v17_st.session_state["v17_returns"] = (
                v17_portfolio_returns
            )

            v17_st.session_state["v17_prices"] = (
                v17_prices
            )

            v17_st.session_state["v17_results"] = {
                "initial": v17_capital,
                "final": v17_final_capital,
                "return": v17_total_return,
                "drawdown": v17_max_drawdown,
                "volatility": v17_volatility,
                "sharpe": v17_sharpe
            }

            v17_st.session_state["v17_asset_results"] = (
                v17_asset_results
            )

            v17_st.success(
                "Анализ успешно завершён!"
            )

        except Exception as v17_error:

            v17_st.error(
                f"Ошибка анализа: {v17_error}"
            )
            # ============================================================
# 17.0 — РЕЗУЛЬТАТЫ АНАЛИЗА
# ============================================================

v17_st.divider()
v17_st.header("📊 Результаты AI Portfolio Intelligence")

if "v17_results" in v17_st.session_state:

    v17_result = v17_st.session_state["v17_results"]

    # Основные показатели
    v17_c1, v17_c2, v17_c3 = v17_st.columns(3)

    v17_c1.metric(
        "Начальный капитал",
        f"${v17_result['initial']:,.2f}"
    )

    v17_c2.metric(
        "Итоговый капитал",
        f"${v17_result['final']:,.2f}",
        f"{v17_result['return']:+.2f}%"
    )

    v17_c3.metric(
        "Максимальная просадка",
        f"{v17_result['drawdown']:.2f}%"
    )

    v17_c4, v17_c5, v17_c6 = v17_st.columns(3)

    v17_c4.metric(
        "Годовая волатильность",
        f"{v17_result['volatility']:.2f}%"
    )

    v17_c5.metric(
        "Коэффициент Sharpe",
        f"{v17_result['sharpe']:.2f}"
    )

    v17_c6.metric(
        "Изменение капитала",
        f"${v17_result['final'] - v17_result['initial']:+,.2f}"
    )

    # График капитала
    v17_st.subheader("📈 Историческая кривая капитала")

    v17_equity_chart = v17_go.Figure()

    v17_equity_chart.add_trace(
        v17_go.Scatter(
            x=v17_st.session_state["v17_equity"].index,
            y=v17_st.session_state["v17_equity"].values,
            mode="lines",
            name="Виртуальный портфель",
            fill="tozeroy"
        )
    )

    v17_equity_chart.update_layout(
        height=450,
        xaxis_title="Дата",
        yaxis_title="Стоимость ($)",
        hovermode="x unified"
    )

    v17_st.plotly_chart(
        v17_equity_chart,
        use_container_width=True
    )

    # Доходность отдельных активов
    v17_st.subheader("🪙 Сравнение активов")

    v17_asset_data = (
        v17_st.session_state["v17_asset_results"]
    )

    v17_asset_df = v17_pd.DataFrame(
        list(v17_asset_data.items()),
        columns=["Криптовалюта", "Доходность (%)"]
    )

    v17_asset_df = v17_asset_df.sort_values(
        "Доходность (%)",
        ascending=False
    )

    v17_st.dataframe(
        v17_asset_df.style.format({
            "Доходность (%)": "{:+.2f}%"
        }),
        use_container_width=True,
        hide_index=True
    )

    v17_asset_chart = v17_go.Figure()

    v17_asset_chart.add_trace(
        v17_go.Bar(
            x=v17_asset_df["Криптовалюта"],
            y=v17_asset_df["Доходность (%)"],
            text=[
                f"{value:+.2f}%"
                for value in v17_asset_df["Доходность (%)"]
            ],
            textposition="outside"
        )
    )

    v17_asset_chart.update_layout(
        title="Историческая доходность активов",
        height=400,
        yaxis_title="Доходность (%)"
    )

    v17_st.plotly_chart(
        v17_asset_chart,
        use_container_width=True
    )

    # Просадка
    v17_st.subheader("📉 Историческая просадка")

    v17_drawdown_chart = v17_go.Figure()

    v17_drawdown_chart.add_trace(
        v17_go.Scatter(
            x=v17_st.session_state["v17_equity"].index,
            y=(
                v17_st.session_state["v17_equity"]
                / v17_st.session_state["v17_equity"].cummax()
                - 1
            ) * 100,
            mode="lines",
            name="Просадка",
            fill="tozeroy"
        )
    )

    v17_drawdown_chart.update_layout(
        height=350,
        yaxis_title="Просадка (%)"
    )

    v17_st.plotly_chart(
        v17_drawdown_chart,
        use_container_width=True
    )

else:

    v17_st.info(
        "Сначала запусти AI Portfolio Analysis 17.0."
    )
    # ============================================================
# 17.0 — ЭКСПОРТ ОТЧЁТА
# ============================================================

v17_st.divider()
v17_st.header("📥 Экспорт AI Portfolio Intelligence")

if "v17_results" in v17_st.session_state:

    v17_result = v17_st.session_state["v17_results"]
    v17_equity = v17_st.session_state["v17_equity"]
    v17_returns = v17_st.session_state["v17_returns"]
    v17_prices = v17_st.session_state["v17_prices"]

    # Таблица исторических результатов
    v17_export_df = v17_pd.DataFrame({
        "Date": v17_equity.index,
        "Portfolio Value": v17_equity.values,
        "Daily Return (%)": v17_returns.values * 100,
        "Drawdown (%)": (
            v17_equity / v17_equity.cummax() - 1
        ).values * 100
    })

    # CSV
    v17_csv = v17_export_df.to_csv(
        index=False
    ).encode("utf-8-sig")

    v17_st.download_button(
        label="📊 Скачать историю портфеля CSV",
        data=v17_csv,
        file_name="crypto_ai_portfolio_17.csv",
        mime="text/csv",
        use_container_width=True
    )

    # Текстовый отчёт
    v17_report = f"""
CRYPTO AI ANALYST 17.0
AI PORTFOLIO INTELLIGENCE

Дата создания:
{v17_datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}

ПАРАМЕТРЫ

Период анализа: {v17_days} дней
Начальный капитал: ${v17_result['initial']:.2f}
Итоговый капитал: ${v17_result['final']:.2f}

РЕЗУЛЬТАТЫ

Доходность: {v17_result['return']:.2f}%
Максимальная просадка: {v17_result['drawdown']:.2f}%
Годовая волатильность: {v17_result['volatility']:.2f}%
Коэффициент Sharpe: {v17_result['sharpe']:.2f}

РАСПРЕДЕЛЕНИЕ ПОРТФЕЛЯ

BTC: {v17_btc}%
ETH: {v17_eth}%
SOL: {v17_sol}%
BNB: {v17_bnb}%
XRP: {v17_xrp}%

ИСТОРИЧЕСКАЯ ДОХОДНОСТЬ АКТИВОВ

"""

    for v17_asset, v17_return in (
        v17_st.session_state["v17_asset_results"].items()
    ):
        v17_report += (
            f"{v17_asset}: {v17_return:+.2f}%\n"
        )

    v17_report += """

ВАЖНО

Отчёт основан на исторических рыночных данных.
Результаты виртуального моделирования не гарантируют
аналогичную доходность в будущем.
Это не инвестиционная рекомендация.
"""

    v17_st.download_button(
        label="📄 Скачать полный TXT-отчёт",
        data=v17_report.encode("utf-8"),
        file_name="crypto_ai_report_17.txt",
        mime="text/plain",
        use_container_width=True
    )

    # Таблица распределения
    v17_st.subheader("Распределение виртуального капитала")

    v17_allocation_df = v17_pd.DataFrame({
        "Актив": list(v17_allocations.keys()),
        "Доля (%)": list(v17_allocations.values()),
        "Виртуальная сумма ($)": [
            v17_capital * value / 100
            for value in v17_allocations.values()
        ]
    })

    v17_st.dataframe(
        v17_allocation_df,
        use_container_width=True,
        hide_index=True
    )

else:

    v17_st.info(
        "Сначала запусти анализ, чтобы сформировать отчёт."
    )


# ============================================================
# КОНЕЦ CRYPTO AI ANALYST 17.0
# ============================================================

v17_st.divider()

v17_st.success(
    "AI Portfolio Intelligence 17.0 загружен."
)

v17_st.caption(
    "Модуль предназначен для исторического анализа "
    "и виртуального моделирования."
)