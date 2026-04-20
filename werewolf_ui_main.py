import argparse

from interfaces.web.app import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Werewolf web UI server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, config_dir=args.config_dir)


if __name__ == "__main__":
    main()