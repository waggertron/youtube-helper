from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
async def search(
    request: Request,
    q: str = Query(..., min_length=1),
    threshold: int = Query(60, ge=0, le=100),
):
    from youtube_helper.search.fuzzy import FuzzySearch

    searcher = FuzzySearch(request.app.state.db_path)
    results = searcher.search_all(q, threshold=threshold)
    return {"query": q, "results": results}
