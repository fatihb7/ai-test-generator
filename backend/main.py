import os
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Test Generator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set. Please check your .env file.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")


class GenerateTestRequest(BaseModel):
    html_content: str
    framework: str = "playwright"


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


@app.post("/generate-test")
async def generate_test(request: GenerateTestRequest):
    if not request.html_content.strip():
        raise HTTPException(status_code=400, detail="html_content cannot be empty.")

    framework = request.framework.lower()
    if framework not in ("playwright", "selenium"):
        raise HTTPException(status_code=400, detail="framework must be 'playwright' or 'selenium'.")

    prompt = PROMPT_TEMPLATE.format(
        framework=framework,
        html_content=request.html_content.strip(),
    )

    try:
        response = model.generate_content(prompt)
        generated_code = response.text.strip()

        if generated_code.startswith("```"):
            lines = generated_code.splitlines()
            start = 1
            end = len(lines)
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() == "```":
                    end = i
                    break
            generated_code = "\n".join(lines[start:end])

        return {"code": generated_code, "framework": framework}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok"}
