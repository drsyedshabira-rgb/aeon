"""
Local mock FDA authority server for testing the submission pipeline
end-to-end without depending on a fake external domain.

Behavior (controllable via query param, so you can test both paths):
  POST /submit           -> 200 OK  (happy path: report ends up "submitted")
  POST /submit?fail=500  -> 500     (tests the retry loop)
  POST /submit?fail=400  -> 400     (tests permanent-failure / no-retry path)
"""
from fastapi import FastAPI, Request, Response

app = FastAPI(title="Mock FDA Authority")


@app.post("/submit")
async def submit(request: Request):
    fail_mode = request.query_params.get("fail")
    body = await request.body()

    if fail_mode == "500":
        return Response(content="simulated server error", status_code=500)
    if fail_mode == "400":
        return Response(content="simulated bad request", status_code=400)

    return Response(
        content=f"<ack><status>ACCEPTED</status><received_bytes>{len(body)}</received_bytes></ack>",
        media_type="application/xml",
        status_code=200,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
