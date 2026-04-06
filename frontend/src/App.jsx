import { useState, useCallback, useEffect } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

const API_URL = "http://localhost:8000";

const MODEL_PRESETS = {
  huggingface: [
    { value: "moonshotai/Kimi-K2-Instruct-0905:novita", label: "Kimi K2 Instruct (Novita)" },
  ],
  openai: [
    { value: "gpt-4o", label: "GPT-4o" },
  ],
};

const PROVIDER_LABELS = {
  huggingface: "HuggingFace",
  openai: "OpenAI",
};

const EXAMPLE_HTML = `<form id="login-form" action="/login" method="POST">
  <h2>Giriş Yap</h2>

  <div class="form-group">
    <label for="email">E-posta</label>
    <input
      type="email"
      id="email"
      name="email"
      placeholder="ornek@email.com"
      required
    />
  </div>

  <div class="form-group">
    <label for="password">Şifre</label>
    <input
      type="password"
      id="password"
      name="password"
      placeholder="En az 8 karakter"
      minlength="8"
      required
    />
  </div>

  <div class="form-group">
    <label>
      <input type="checkbox" name="remember" />
      Beni Hatırla
    </label>
  </div>

  <button type="submit" class="btn-primary">Giriş Yap</button>

  <a href="/forgot-password">Şifremi Unuttum</a>
</form>`;

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }, [text]);

  return (
    <button className="copy-btn" onClick={handleCopy} title="Kodu kopyala">
      {copied ? (
        <>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          Kopyalandı
        </>
      ) : (
        <>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
          </svg>
          Kopyala
        </>
      )}
    </button>
  );
}

function EyeIcon({ open }) {
  return open ? (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ) : (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

export default function App() {
  const [htmlInput, setHtmlInput] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [isFetchingUrl, setIsFetchingUrl] = useState(false);
  const [urlError, setUrlError] = useState("");
  const [framework, setFramework] = useState("playwright");
  const [provider, setProvider] = useState("huggingface");
  const [model, setModel] = useState(MODEL_PRESETS.huggingface[0].value);
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [generatedCode, setGeneratedCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setModel(MODEL_PRESETS[provider][0].value);
  }, [provider]);

  const handleGenerate = useCallback(async () => {
    if (!htmlInput.trim()) {
      setError("Lütfen HTML veya JSON içeriği yapıştırın.");
      return;
    }
    if (!apiKey.trim()) {
      setError("Lütfen API anahtarınızı girin.");
      return;
    }

    setIsLoading(true);
    setError("");
    setGeneratedCode("");

    try {
      const response = await fetch(`${API_URL}/generate-test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          html_content: htmlInput,
          framework,
          provider,
          api_key: apiKey,
          model,
          page_url: urlInput.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Sunucu hatası oluştu.");
      }

      setGeneratedCode(data.code);
    } catch (err) {
      setError(err.message || "Bağlantı hatası. Backend'in çalıştığından emin olun.");
    } finally {
      setIsLoading(false);
    }
  }, [htmlInput, framework, provider, apiKey, model]);

  const handleLoadExample = useCallback(() => {
    setHtmlInput(EXAMPLE_HTML);
    setError("");
  }, []);

  const handleClear = useCallback(() => {
    setHtmlInput("");
    setGeneratedCode("");
    setError("");
  }, []);

  const handleFetchUrl = useCallback(async () => {
    const url = urlInput.trim();
    if (!url) {
      setUrlError("Lütfen bir URL girin.");
      return;
    }
    setIsFetchingUrl(true);
    setUrlError("");
    try {
      const response = await fetch(`${API_URL}/fetch-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "URL çekilemedi.");
      }
      setHtmlInput(data.html);
      setError("");
    } catch (err) {
      setUrlError(err.message || "URL çekilirken hata oluştu.");
    } finally {
      setIsFetchingUrl(false);
    }
  }, [urlInput]);

  const providerLabel = PROVIDER_LABELS[provider];
  const loadingText = `${providerLabel} test senaryoları üretiyor...`;

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <div className="logo-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
            </div>
            <span className="logo-text">AI Test Generator</span>
          </div>
          <div className="header-badge">Powered by {providerLabel}</div>
        </div>
      </header>

      {/* Main */}
      <main className="main">
        <div className="panels">
          {/* LEFT PANEL */}
          <section className="panel panel-left">
            <div className="panel-header">
              <div className="panel-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="16 18 22 12 16 6" />
                  <polyline points="8 6 2 12 8 18" />
                </svg>
                HTML / JSON Girdisi
              </div>
              <div className="header-actions">
                <button className="action-btn" onClick={handleLoadExample} title="Örnek formu yükle">
                  Örnek Yükle
                </button>
                <button className="action-btn action-btn-ghost" onClick={handleClear} title="Temizle">
                  Temizle
                </button>
              </div>
            </div>

            {/* AI Settings Bar */}
            <div className="settings-bar">
              <div className="settings-row">
                <div className="settings-group">
                  <span className="settings-label">Sağlayıcı</span>
                  <div className="toggle-group">
                    <button
                      className={`toggle-btn ${provider === "huggingface" ? "active" : ""}`}
                      onClick={() => setProvider("huggingface")}
                    >
                      HuggingFace
                    </button>
                    <button
                      className={`toggle-btn ${provider === "openai" ? "active" : ""}`}
                      onClick={() => setProvider("openai")}
                    >
                      OpenAI
                    </button>
                  </div>
                </div>

                <div className="settings-group settings-group-model">
                  <span className="settings-label">Model</span>
                  <select
                    className="model-select"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                  >
                    {MODEL_PRESETS[provider].map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="settings-row">
                <div className="settings-group settings-group-key">
                  <span className="settings-label">
                    {provider === "huggingface" ? "HF Token" : "API Key"}
                  </span>
                  <div className="key-input-wrapper">
                    <input
                      className="settings-input"
                      type={showKey ? "text" : "password"}
                      value={apiKey}
                      onChange={(e) => {
                        setApiKey(e.target.value);
                        if (error) setError("");
                      }}
                      placeholder={
                        provider === "huggingface"
                          ? "HuggingFace Inference Token (hf_...)"
                          : "OpenAI Inference Token (sk-...)"
                      }
                      spellCheck={false}
                      autoComplete="off"
                    />
                    <button
                      className="key-toggle-btn"
                      onClick={() => setShowKey((v) => !v)}
                      title={showKey ? "Gizle" : "Göster"}
                      type="button"
                    >
                      <EyeIcon open={showKey} />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* URL Fetch Bar */}
            <div className="url-fetch-bar">
              <div className="url-input-wrapper">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="url-icon">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="2" y1="12" x2="22" y2="12" />
                  <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
                </svg>
                <input
                  className="url-input"
                  type="url"
                  value={urlInput}
                  onChange={(e) => {
                    setUrlInput(e.target.value);
                    if (urlError) setUrlError("");
                  }}
                  onKeyDown={(e) => e.key === "Enter" && handleFetchUrl()}
                  placeholder="https://example.com — sayfa kaynağını çek"
                  spellCheck={false}
                  autoComplete="off"
                />
              </div>
              <button
                className={`fetch-url-btn ${isFetchingUrl ? "loading" : ""}`}
                onClick={handleFetchUrl}
                disabled={isFetchingUrl}
                title="Sayfa kaynağını çek"
              >
                {isFetchingUrl ? (
                  <>
                    <span className="spinner spinner-sm" />
                    Çekiliyor...
                  </>
                ) : (
                  <>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <polyline points="1 4 1 10 7 10" />
                      <path d="M3.51 15a9 9 0 102.13-9.36L1 10" />
                    </svg>
                    Çek
                  </>
                )}
              </button>
            </div>
            {urlError && (
              <div className="url-error">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                {urlError}
              </div>
            )}

            <textarea
              className="code-textarea"
              value={htmlInput}
              onChange={(e) => {
                setHtmlInput(e.target.value);
                if (error) setError("");
              }}
              placeholder="Form HTML'ini veya JSON yapısını buraya yapıştırın..."
              spellCheck={false}
            />

            <div className="panel-footer">
              <div className="framework-selector">
                <span className="selector-label">Framework:</span>
                <div className="toggle-group">
                  <button
                    className={`toggle-btn ${framework === "playwright" ? "active" : ""}`}
                    onClick={() => setFramework("playwright")}
                  >
                    Playwright
                  </button>
                  <button
                    className={`toggle-btn ${framework === "selenium" ? "active" : ""}`}
                    onClick={() => setFramework("selenium")}
                  >
                    Selenium
                  </button>
                </div>
              </div>

              <button
                className={`generate-btn ${isLoading ? "loading" : ""}`}
                onClick={handleGenerate}
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="spinner" />
                    Üretiliyor...
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    Test Üret
                  </>
                )}
              </button>
            </div>

            {error && (
              <div className="error-banner">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                {error}
              </div>
            )}
          </section>

          {/* DIVIDER */}
          <div className="divider" />

          {/* RIGHT PANEL */}
          <section className="panel panel-right">
            <div className="panel-header">
              <div className="panel-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
                Üretilen Test Kodu
                {generatedCode && (
                  <span className="framework-tag">{framework}</span>
                )}
              </div>
              {generatedCode && <CopyButton text={generatedCode} />}
            </div>

            <div className="output-area">
              {isLoading && (
                <div className="placeholder loading-placeholder">
                  <div className="pulse-container">
                    <div className="pulse-dot" />
                    <p>{loadingText}</p>
                  </div>
                  <div className="skeleton-lines">
                    {Array.from({ length: 12 }).map((_, i) => (
                      <div
                        key={i}
                        className="skeleton-line"
                        style={{ width: `${40 + Math.random() * 50}%`, animationDelay: `${i * 0.08}s` }}
                      />
                    ))}
                  </div>
                </div>
              )}

              {!isLoading && !generatedCode && (
                <div className="placeholder empty-placeholder">
                  <div className="placeholder-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
                      <polyline points="16 18 22 12 16 6" />
                      <polyline points="8 6 2 12 8 18" />
                    </svg>
                  </div>
                  <p className="placeholder-title">Henüz kod üretilmedi</p>
                  <p className="placeholder-subtitle">
                    Sol tarafa HTML formunu yapıştırın ve <strong>Test Üret</strong> butonuna tıklayın.
                  </p>
                </div>
              )}

              {!isLoading && generatedCode && (
                <SyntaxHighlighter
                  language="python"
                  style={vscDarkPlus}
                  showLineNumbers
                  wrapLongLines={false}
                  customStyle={{
                    margin: 0,
                    borderRadius: 0,
                    background: "#0d1117",
                    fontSize: "13px",
                    lineHeight: "1.6",
                    height: "100%",
                    flex: 1,
                  }}
                  lineNumberStyle={{
                    color: "#3d4450",
                    minWidth: "2.5em",
                    paddingRight: "1em",
                    userSelect: "none",
                  }}
                >
                  {generatedCode}
                </SyntaxHighlighter>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
