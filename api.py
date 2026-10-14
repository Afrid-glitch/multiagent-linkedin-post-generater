from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from main import generate_post


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI()


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# REQUEST MODEL
# ============================================================

class GenerateRequest(BaseModel):

    topic: str


# ============================================================
# HOME PAGE
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


# ============================================================
# GENERATE LINKEDIN POST
# ============================================================

@app.post("/generate")
async def generate(
    request: GenerateRequest
):

    topic = request.topic.strip()

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not topic:

        return {
            "success": False,
            "error": "Please enter a topic."
        }

    # --------------------------------------------------------
    # Generate post
    # --------------------------------------------------------

    try:

        result = generate_post(
            topic
        )

        return {
            "success": True,
            "draft": result["draft"],
            "approved": result["approved"],
            "attempts": result["attempts"],
            "feedback": result["feedback"]
        }

    # --------------------------------------------------------
    # Error handling
    # --------------------------------------------------------

    except Exception as e:

        print(
            f"ERROR: {str(e)}"
        )

        return {
            "success": False,
            "error": str(e)
        }
