import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="http:localhost:5000", port=5000, reload=True)
