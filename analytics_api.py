"""python analytics_api.py — servicio interno candidato, un worker."""

from analytics_service.http import create_app
from analytics_service.settings import Settings


def main():
    import uvicorn
    settings = Settings.from_env()
    uvicorn.run(
        create_app(settings), host=settings.host, port=settings.port,
        workers=1, access_log=False, proxy_headers=False,
        limit_concurrency=32, timeout_keep_alive=5,
    )


if __name__ == "__main__":
    main()
