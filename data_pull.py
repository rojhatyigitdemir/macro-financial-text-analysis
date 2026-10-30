import yfinance as yf
import pandas as pd
import numpy as np

# 1. 8 Makro Tema ve Varlık Evreni
MACRO_UNIVERSE = {
    "Crypto": ["BTC-USD", "ETH-USD"],
    "US_Tech": ["QQQ", "TSM"],
    "Bonds_RealEstate": ["TLT", "O", "BNDW"],
    "Industrial_Energy": ["CPER", "PALL", "USO"],  # Bakır, Paladyum, Petrol
    "Food_Agriculture": ["DBA", "WEAT"],           # Tarım ve Buğday
    "Defense_Security": ["ITA", "XAR"],            # Savunma ve Havacılık
    "Swiss_EU_Macro": ["EWL", "VGK"],              # İsviçre ve Avrupa
    "Turkey_Macro": ["TUR", "TRY=X"]               # Türkiye ETF ve USD/TRY
}

news_rows = []
context_rows = []

for theme, tickers in MACRO_UNIVERSE.items():
    for ticker in tickers:
        asset = yf.Ticker(ticker)
        
        # --- A. METİN VERİSİ: Haber Başlıkları ---
        recent_news = asset.news or []
        for item in recent_news:
            # yfinance yeni/eski API yapısına uyumlu başlık ve tarih çekimi
            content = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
            title = item.get("title") or content.get("title")
            pub_time = item.get("providerPublishTime") or content.get("pubDate")
            publisher = item.get("publisher") or (content.get("provider", {}) or {}).get("displayName")
            
            if title:
                news_rows.append({
                    "macro_theme": theme,
                    "symbol": ticker,
                    "created_at": pub_time,
                    "publisher": publisher,
                    "text": title.strip()
                })
        
        # --- B. BAĞLAM VERİSİ: AlphaGuard Momentum & Şok Kuralları ---
        try:
            # 1) Haftalık veriden 8-haftalık SMA (Uptrend) ve 4-haftalık Momentum
            hist_w = asset.history(period="6mo", interval="1wk")
            if len(hist_w) >= 9:
                latest_price = hist_w["Close"].iloc[-1]
                # Tamamlanmış önceki 8 haftanın ortalaması (AlphaGuard Kural 3.1)
                sma_8w = hist_w["Close"].iloc[-9:-1].mean()
                uptrend = int(latest_price > sma_8w)
                # 4 haftalık getiri % (AlphaGuard Kural 3.2)
                mom_4w = ((latest_price / hist_w["Close"].iloc[-5]) - 1) * 100
            else:
                latest_price, sma_8w, uptrend, mom_4w = np.nan, np.nan, np.nan, np.nan

            # 2) Günlük veriden 14-günlük ATR tarzı Fiyat Şoku (AlphaGuard Kural 3.4)
            hist_d = asset.history(period="1mo", interval="1d")
            if len(hist_d) >= 16:
                daily_range = (hist_d["High"] - hist_d["Low"]).iloc[-15:-1].mean()
                prev_close = hist_d["Close"].iloc[-2]
                today_high = hist_d["High"].iloc[-1]
                today_low = hist_d["Low"].iloc[-1]
                shock_up = (today_high - prev_close) > (2.5 * daily_range)
                shock_down = (prev_close - today_low) > (2.5 * daily_range)
                shock_flag = int(shock_up or shock_down)
            else:
                shock_flag = 0

            context_rows.append({
                "macro_theme": theme,
                "symbol": ticker,
                "price": round(float(latest_price), 2) if pd.notna(latest_price) else None,
                "uptrend": uptrend,             # 1 = Uptrend, 0 = Downtrend (in_government karşılığı)
                "mom_4w": round(float(mom_4w), 2) if pd.notna(mom_4w) else None,
                "shock_flag": shock_flag        # 1 = Fiyat şoku var, 0 = Yok
            })
        except Exception as e:
            print(f"Bağlam verisi hatası ({ticker}): {e}")

# 2. Tabloları oluşturma ve kaydetme
df_news = pd.DataFrame(news_rows)
df_news["created_at"] = pd.to_datetime(df_news["created_at"], errors="coerce", utc=True)
df_news = df_news.drop_duplicates(subset=["symbol", "text"]).reset_index(drop=True)
df_news["news_id"] = df_news.index + 1

df_context = pd.DataFrame(context_rows)

df_news.to_csv("makro_haberler.csv", index=False)
df_context.to_csv("makro_baglam.csv", index=False)

print(f"Tamamlandı! {len(df_news)} benzersiz haber ve {len(df_context)} varlık bağlam verisi kaydedildi.")
display(df_context)
display(df_news.head(10))
