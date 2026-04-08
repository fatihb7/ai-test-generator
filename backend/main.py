import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

app = FastAPI(title="Test Generator API", version="1.0.0")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    log.info("%s %s → %d  (%.0fms)", request.method, request.url.path, response.status_code, ms)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FetchUrlRequest(BaseModel):
    url: str


class GenerateTestRequest(BaseModel):
    html_content: str
    framework: str = "playwright"
    provider: str = "huggingface"
    api_key: str
    model: str = "moonshotai/Kimi-K2-Instruct:novita"
    page_url: str = ""


class RunTestRequest(BaseModel):
    code: str
    variables: dict = {}
    framework: str = "playwright"


class FixTestRequest(BaseModel):
    code: str
    error: str
    framework: str = "playwright"
    provider: str = "huggingface"
    api_key: str
    model: str = "moonshotai/Kimi-K2-Instruct-0905:novita"


FIX_PROMPT_TEMPLATE = """
You are an expert QA automation engineer. The following {framework} Python test code produced an error when executed. Fix the code so it runs without errors.

Code:
```python
{code}
```

Error Output:
{error}

Requirements:
1. Fix all syntax errors, import errors, and runtime errors shown above
2. Keep the same test structure and test scenarios
3. Do not change the logic of the tests, only fix the errors
4. Return ONLY the fixed Python code, no markdown fences, no explanations outside the code.
"""

PROMPT_TEMPLATE = """
You are an expert QA automation engineer. Analyze the following HTML form structure and generate a complete, production-ready {framework} test script in Python.

HTML/Form Structure:
```html
{html_content}
```
Target URL: {page_url}

Requirements:
1. Generate a complete test file with all necessary imports
2. Include at least these test cases:
   - Happy path (valid inputs, successful submission)
   - Empty/blank field validation
   - Invalid input validation (if applicable, e.g. wrong email format, short password)
   - Boundary cases for input fields
3. Use descriptive test function names in snake_case
4. Add brief comments explaining each test scenario
5. Use async/await syntax for Playwright or proper waits for Selenium
6. Use the exact Target URL above in all page.goto() / driver.get() calls — do not use any placeholder URL.
7. For any user-supplied value the test needs (e.g. credentials, emails, names), use a short snake_case placeholder string (e.g. 'valid_username', 'valid_password', 'test_email'). Do NOT hard-code real credentials.
8. On the very FIRST line of your response output this special comment (valid JSON array) listing every placeholder you used:
   # TESTVARS: [{{"key": "valid_username", "desc": "Geçerli kullanıcı adı"}}, {{"key": "valid_password", "desc": "Geçerli şifre"}}]
   - "key" must exactly match the placeholder string used in send_keys() / fill() / type() calls.
   - "desc" should be a short Turkish description so the user knows what to enter.
   - If no user-supplied values are needed, output: # TESTVARS: []
9. After that first line, output ONLY the Python code — no markdown fences, no explanations outside the code.
10. Every test MUST contain at least one real, executable assertion (e.g. assert, expect, wait_for_selector, wait_for_url). NEVER leave assertions as comments. A test without a real assertion is useless and will always pass even if the page is broken.
    - For success cases: assert a URL change, a success message selector, or a dashboard element.
    - For error/validation cases: assert an error message element is visible on the page.
    - Use page.wait_for_selector() or page.locator().wait_for() to wait for elements before asserting.
    - Do NOT write lines like "# await page.wait_for_selector(...)" — execute them for real.
"""


def _strip_fences(code: str) -> str:
    if code.startswith("```"):
        lines = code.splitlines()
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end = i
                break
        return "\n".join(lines[start:end])
    return code


TESTVARS_PREFIX = "# TESTVARS:"

def _parse_testvars(code: str) -> tuple[str, list]:
    """Extract the leading '# TESTVARS: [...]' line from LLM output.

    Returns (cleaned_code, required_vars_list).
    required_vars_list items: {"key": str, "desc": str}
    """
    lines = code.splitlines()
    required_vars: list = []

    # The TESTVARS line might be the very first non-empty line
    insert_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(TESTVARS_PREFIX):
            json_part = stripped[len(TESTVARS_PREFIX):].strip()
            try:
                parsed = json.loads(json_part)
                if isinstance(parsed, list):
                    required_vars = parsed
            except Exception:
                log.warning("Failed to parse TESTVARS JSON: %s", json_part)
            insert_idx = i + 1
        break  # only check the first non-empty line

    cleaned = "\n".join(lines[insert_idx:]).lstrip("\n")
    return cleaned, required_vars


def _selenium_fetch(url: str) -> str:
    """Selenium headless Chrome ile sayfayı tam render edip HTML kaynağını döndürür."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)
        return driver.page_source
    finally:
        driver.quit()


def _extract_form_elements(html: str) -> str:
    """HTML'den sadece form/input elementlerini çıkarır, gereksiz tag ve attribute'ları siler.

    Bu fonksiyon LLM'e gönderilecek token sayısını önemli ölçüde azaltır.
    Aynı zamanda sadece test yazımı için gerekli yapıyı korur.
    """
    from bs4 import BeautifulSoup, Comment

    soup = BeautifulSoup(html, "lxml")

    # Test yazımıyla ilgisi olmayan tag'leri tamamen sil
    for tag in soup(["script", "style", "svg", "img", "video", "audio",
                      "iframe", "noscript", "link", "meta", "head",
                      "canvas", "picture", "source"]):
        tag.decompose()

    # HTML yorumlarını kaldır
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Sadece test için anlamlı attribute'ları tut
    KEEP_ATTRS = {
        "id", "name", "type", "placeholder", "class", "required",
        "href", "action", "method", "value", "for", "aria-label",
        "data-testid", "role", "autocomplete", "min", "max",
        "pattern", "minlength", "maxlength", "multiple",
        "checked", "selected", "disabled", "readonly",
    }
    for element in soup.find_all(True):
        for attr in [a for a in list(element.attrs) if a not in KEEP_ATTRS]:
            del element[attr]

    # Önce <form> elementlerine bak
    forms = soup.find_all("form")
    if forms:
        result = "\n\n".join(str(f) for f in forms)
        log.info("_extract_form_elements → %d form bulundu, %d chars", len(forms), len(result))
        return result

    # Form yoksa input/select/textarea içeren parent'ları topla
    inputs = soup.find_all(["input", "select", "textarea", "button"])
    if inputs:
        seen = set()
        parts = []
        for inp in inputs:
            parent = inp.parent
            pid = id(parent) if parent else None
            if pid and pid not in seen:
                seen.add(pid)
                parts.append(str(parent))
        result = "\n\n".join(parts)
        log.info("_extract_form_elements → form yok, %d parent blok, %d chars", len(parts), len(result))
        return result

    # Fallback: body'nin ilk 15000 karakteri
    body = soup.find("body")
    content = str(body) if body else str(soup)
    log.warning("_extract_form_elements → form/input bulunamadı, fallback %d chars", len(content))
    return content[:15000]


@app.post("/fetch-url")
async def fetch_url(request: FetchUrlRequest):
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url cannot be empty.")

    try:
        raw_html = await asyncio.to_thread(_selenium_fetch, url)
        compressed = _extract_form_elements(raw_html)
        log.info("fetch-url → url=%s  raw_chars=%d  compressed_chars=%d",
                 url, len(raw_html), len(compressed))
        return {"html": compressed, "status_code": 200}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Selenium fetch failed: {str(e)}")


@app.post("/generate-test")
async def generate_test(request: GenerateTestRequest):
    if not request.html_content.strip():
        raise HTTPException(status_code=400, detail="html_content cannot be empty.")

    framework = request.framework.lower()
    if framework not in ("playwright", "selenium"):
        raise HTTPException(status_code=400, detail="framework must be 'playwright' or 'selenium'.")

    provider = request.provider.lower()
    if provider not in ("openai", "huggingface"):
        raise HTTPException(status_code=400, detail="provider must be 'openai' or 'huggingface'.")

    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    page_url = request.page_url.strip() or "http://localhost:3000"
    prompt = PROMPT_TEMPLATE.format(
        framework=framework,
        html_content=request.html_content.strip(),
        page_url=page_url,
    )
    messages = [{"role": "user", "content": prompt}]
    log.info("Request → provider=%s  model=%s  framework=%s  html_chars=%d",
             provider, request.model, framework, len(request.html_content.strip()))

    try:
        t0 = time.perf_counter()
        if provider == "huggingface":
            from huggingface_hub import InferenceClient
            # "model/name:inference-provider" formatını destekle
            if ":" in request.model:
                hf_model, hf_provider = request.model.rsplit(":", 1)
            else:
                hf_model, hf_provider = request.model, None
            client = InferenceClient(
                provider=hf_provider,
                api_key=request.api_key,
            )
            completion = client.chat.completions.create(
                model=hf_model,
                messages=messages,
            )
        else:
            from openai import OpenAI
            client = OpenAI(api_key=request.api_key)
            completion = client.chat.completions.create(
                model=request.model,
                messages=messages,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        usage = getattr(completion, "usage", None)
        if usage:
            log.info("Tokens → prompt=%s  completion=%s  total=%s  (%.0fms)",
                     usage.prompt_tokens, usage.completion_tokens, usage.total_tokens, elapsed)
        else:
            log.info("LLM response received (%.0fms, no token info)", elapsed)

        raw = _strip_fences(completion.choices[0].message.content.strip())
        generated_code, required_vars = _parse_testvars(raw)
        log.info("TESTVARS detected: %s", [v.get("key") for v in required_vars])
        return {"code": generated_code, "framework": framework, "required_vars": required_vars}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")


@app.post("/run-test")
async def run_test(request: RunTestRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="code cannot be empty.")

    code = request.code
    for placeholder, value in request.variables.items():
        if value:
            code = code.replace(f"'{placeholder}'", f"'{value}'")
            code = code.replace(f'"{placeholder}"', f'"{value}"')

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        cmd = [
            sys.executable, "-m", "pytest", tmp_path,
            "-v", "-s", "--tb=short", "--no-header",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        log.info(
            "run-test → returncode=%d  stdout=%d chars  stderr=%d chars",
            result.returncode,
            len(result.stdout),
            len(result.stderr),
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Test zaman aşımına uğradı (120 saniye).",
            "returncode": -1,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.post("/fix-test")
async def fix_test(request: FixTestRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="code cannot be empty.")
    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key cannot be empty.")

    framework = request.framework.lower()
    provider = request.provider.lower()

    if provider not in ("openai", "huggingface"):
        raise HTTPException(status_code=400, detail="provider must be 'openai' or 'huggingface'.")

    prompt = FIX_PROMPT_TEMPLATE.format(
        framework=framework,
        code=request.code.strip(),
        error=request.error.strip(),
    )
    messages = [{"role": "user", "content": prompt}]
    log.info("fix-test → provider=%s  model=%s  framework=%s", provider, request.model, framework)

    try:
        t0 = time.perf_counter()
        if provider == "huggingface":
            from huggingface_hub import InferenceClient
            if ":" in request.model:
                hf_model, hf_provider = request.model.rsplit(":", 1)
            else:
                hf_model, hf_provider = request.model, None
            client = InferenceClient(provider=hf_provider, api_key=request.api_key)
            completion = client.chat.completions.create(model=hf_model, messages=messages)
        else:
            from openai import OpenAI
            client = OpenAI(api_key=request.api_key)
            completion = client.chat.completions.create(model=request.model, messages=messages)

        elapsed = (time.perf_counter() - t0) * 1000
        log.info("fix-test LLM response (%.0fms)", elapsed)

        fixed_code = _strip_fences(completion.choices[0].message.content.strip())
        return {"code": fixed_code, "framework": framework}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM fix failed: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok"}
