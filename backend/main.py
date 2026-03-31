import logging
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


class GenerateTestRequest(BaseModel):
    html_content: str
    framework: str = "playwright"
    provider: str = "huggingface"
    api_key: str
    model: str = "moonshotai/Kimi-K2-Instruct:novita"


PROMPT_TEMPLATE = """
You are an expert QA automation engineer. Analyze the following HTML form structure and generate a complete, production-ready {framework} test script in Python.

HTML/Form Structure:
```html
{html_content}
```

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
6. Make the code ready to run without modifications (use placeholder URLs like "http://localhost:3000")
7. Return ONLY the Python code, no markdown fences, no explanations outside the code.
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

    prompt = PROMPT_TEMPLATE.format(
        framework=framework,
        html_content=request.html_content.strip(),
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

        generated_code = _strip_fences(completion.choices[0].message.content.strip())
        return {"code": generated_code, "framework": framework}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok"}
