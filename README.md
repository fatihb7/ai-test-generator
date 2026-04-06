# AI Test Generator

Form HTML'ini veya JSON yapısını yapıştırın; HuggingFace ya da OpenAI modelleriyle otomatik **Playwright** veya **Selenium** Python test senaryosu üretin.

## Demo

<video src="demo.mp4" controls width="100%"></video>

> Uygulamanın temel akışını gösteren kısa bir tanıtım videosu. Form HTML'i yapıştırılıp model seçildikten sonra Playwright/Selenium test kodunun nasıl üretildiği adım adım görülebilir.

---

## Proje Yapısı

```
ErikLabsCase/
├── backend/              # Python FastAPI
│   ├── main.py
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/             # React + Vite
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── nginx.conf
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Kurulum

### 1. Backend

> **Ön koşul:** `uv` kurulu değilse önce yükleyin:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```
```bash
cd backend

# Sanal ortam oluştur ve bağımlılıkları yükle
uv sync

# Sunucuyu başlat
uv run uvicorn main:app --reload
```

Backend `http://localhost:8000` adresinde çalışmaya başlar.

---
### 2. Frontend

```bash
cd frontend

npm install
npm run dev
```

Uygulama `http://localhost:5173` adresinde açılır.

---

### 3. Docker ile Çalıştırma (Önerilen)

> **Ön koşul:** Sisteminizde [Docker](https://docs.docker.com/get-docker/) ve Docker Compose kurulu olmalıdır.

Proje kök dizininde tek komutla tüm servisleri ayağa kaldırabilirsiniz:

```bash
docker compose up --build
```

| Servis   | Adres                   |
|----------|-------------------------|
| Frontend | http://localhost:3000   |
| Backend  | http://localhost:8000   |

Servisleri arka planda (detached) çalıştırmak için:

```bash
docker compose up --build -d
```

Logları takip etmek için:

```bash
docker compose logs -f
```

Servisleri durdurmak için:

```bash
docker compose down
```

> **Not:** Frontend, production build olarak Nginx üzerinde sunulur. Backend API istekleri `/api/*` yolu üzerinden yönlendirilmez; frontend doğrudan `http://localhost:8000` adresini kullanır.

---

## Kullanım

1. **Sağlayıcı seçin** — HuggingFace veya OpenAI
2. **Model seçin** — Seçilen sağlayıcıya göre otomatik listelenir
3. **API anahtarınızı girin** — `hf_...` (HuggingFace) veya `sk-...` (OpenAI)
4. *(İsteğe bağlı)* **URL girin ve Çek butonuna tıklayın** — sayfa kaynağı otomatik olarak HTML giriş alanına doldurulur; üretilen testlerde bu URL kullanılır
5. Sol panele **form HTML'i** yapıştırın (veya **Örnek Yükle** butonunu kullanın)
6. **Framework seçin** — Playwright veya Selenium
7. **Test Üret** butonuna tıklayın
8. Sağ panelde syntax-highlighted Python test kodu görünür
9. **Kopyala** butonu ile kodu panoya alın

> API anahtarı yalnızca istek sırasında backend'e iletilir; herhangi bir yerde saklanmaz.

---

## API

### `POST /fetch-url`

Verilen URL'nin sayfa kaynağını çekip döndürür.

**Request:**
```json
{ "url": "https://example.com/login" }
```

**Response:**
```json
{ "html": "<!DOCTYPE html>...", "status_code": 200 }
```

---

### `POST /generate-test`

**Request:**
```json
{
  "html_content": "<form>...</form>",
  "framework": "playwright",
  "provider": "huggingface",
  "api_key": "hf_...",
  "model": "moonshotai/Kimi-K2-Instruct:novita",
  "page_url": "https://test.com/login"
}
```

> `page_url` opsiyoneldir. Gönderilirse üretilen testlerde bu URL kullanılır; gönderilmezse `http://localhost:3000` varsayılan olarak alınır.

**Response:**
```json
{
  "code": "import pytest\nfrom playwright...",
  "framework": "playwright"
}
```

### `GET /health`

```json
{ "status": "ok" }
```

---

## Teknolojiler

| Katman    | Teknoloji                                          |
|-----------|----------------------------------------------------|
| Backend   | Python 3.10+, FastAPI, Uvicorn, uv                 |
| LLM       | HuggingFace Inference API veya OpenAI API          |
| Modeller  | Kimi K2 Instruct (Novita), GPT-4o                  |
| Frontend  | React 18, Vite 6                                   |
| Highlight | react-syntax-highlighter (Prism / vscDarkPlus)     |
| Container | Docker, Docker Compose, Nginx (frontend prod)       |
