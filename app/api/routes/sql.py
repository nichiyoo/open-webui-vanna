from fastapi import APIRouter, HTTPException, Query, Depends
from app.models.responses import (
    SQLResponse,
    DataFrameResponse,
    PlotlyFigureResponse,
    QuestionCacheResponse,
)
from app.services.vanna_service import vanna
from app.services.cache_service import get_cache
from app.api.dependencies import requires_cache

router = APIRouter(prefix="/api", tags=["sql"])


@router.get("/generate_sql", response_model=SQLResponse)
async def generate_sql(
    question: str = Query(..., description="Question to generate SQL for")
):
    """Generate SQL query from natural language question."""
    try:
        cache = get_cache()
        id = cache.generate_id(question=question)
        sql = vanna.generate_sql(question=question, allow_llm_to_see_data=True)

        cache.set(id=id, field="question", value=question)
        cache.set(id=id, field="sql", value=sql)

        return SQLResponse(id=id, text=sql)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run_sql", response_model=DataFrameResponse)
async def run_sql(cache_data: dict = Depends(requires_cache(["sql"]))):
    """Execute SQL query and return results."""
    try:
        cache = get_cache()
        sql = cache_data["sql"]
        id = cache_data["id"]

        df = vanna.run_sql(sql=sql)
        cache.set(id=id, field="df", value=df)

        return DataFrameResponse(id=id, df=df.head(10).to_json(orient="records"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generate_plotly_figure", response_model=PlotlyFigureResponse)
async def generate_plotly_figure(
    cache_data: dict = Depends(requires_cache(["df", "question", "sql"]))
):
    """Generate Plotly visualization from query results."""
    try:
        cache = get_cache()
        df = cache_data["df"]
        question = cache_data["question"]
        sql = cache_data["sql"]
        id = cache_data["id"]

        code = vanna.generate_plotly_code(
            question=question,
            sql=sql,
            df_metadata=f"Running df.dtypes gives:\n {df.dtypes}",
        )
        fig = vanna.get_plotly_figure(plotly_code=code, df=df, dark_mode=False)
        fig_json = fig.to_json()

        cache.set(id=id, field="fig_json", value=fig_json)

        return PlotlyFigureResponse(id=id, fig=fig_json)
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load_question", response_model=QuestionCacheResponse)
async def load_question(
    cache_data: dict = Depends(
        requires_cache(["question", "sql", "df", "fig_json", "followup_questions"])
    )
):
    """Load complete question data from cache."""
    try:
        return QuestionCacheResponse(
            id=cache_data["id"],
            question=cache_data["question"],
            sql=cache_data["sql"],
            df=cache_data["df"].head(10).to_json(orient="records"),
            fig=cache_data["fig_json"],
            followup_questions=cache_data["followup_questions"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
