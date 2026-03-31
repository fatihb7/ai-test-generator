# AI Test Generator

Form HTML'ini yapıştırın, Gemini AI ile otomatik Playwright veya Selenium test senaryosu üretin.

## Proje Yapısı

```
ErikLabsCase/
├── backend/          # Python FastAPI
│   ├── main.py
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── .env.example
├── frontend/         # React + Vite
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   └── package.json
└── README.md
```

## Kurulum

### 1. Gemini API Anahtarı Alın

[Google AI Studio](https://aistudio.google.com/app/apikey) adresinden **ücretsiz** bir API anahtarı oluşturun.

---

### 2. Backend Kurulumu

> **Ön koşul:** `uv` kurulu değilse önce yükleyin:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

```bash
cd backend

# Sanal ortam oluştur ve bağımlılıkları yükle (tek komut)
uv sync

# .env dosyası oluştur
cp .env.example .env
```

`.env` dosyasını açıp API anahtarınızı yazın:

```env
GEMINI_API_KEY=your_api_key_here
```

Sunucuyu başlatın:

```bash
uv run uvicorn main:app --reload
```

Backend `http://localhost:8000` adresinde çalışmaya başlar.

---

### 3. Frontend Kurulumu

```bash
cd frontend

# Bağımlılıkları yükle
npm install

# Geliştirme sunucusunu başlat
npm run dev
```

Uygulama `http://localhost:5173` adresinde açılır.

---

## Kullanım

1. Sol panele bir form HTML'i yapıştırın (veya **Örnek Yükle** butonuna tıklayın)
2. **Playwright** veya **Selenium** arasından framework seçin
3. **Test Üret** butonuna tıklayın
4. Sağ panelde syntax-highlighted Python test kodu görünür
5. **Kopyala** butonu ile kodu panoya alın

## API

### `POST /generate-test`

**Request:**
```json
{
  "html_content": "<form>...</form>",
  "framework": "playwright"
}
```

**Response:**
```json
{
  "code": "import pytest\nfrom playwright...",
  "framework": "playwright"
}
```

## Teknolojiler

| Katman    | Teknoloji                        |
|-----------|----------------------------------|
| Backend   | Python, FastAPI, Uvicorn, uv     |
| LLM       | Google Gemini 1.5 Flash (Ücretsiz) |
| Frontend  | React 18, Vite                   |
| Highlight | react-syntax-highlighter (Prism) |
