from backend import create_app, load_config

app = create_app()

if __name__ == "__main__":
    cfg = load_config()
    app.run(debug=True, port=cfg.get("backend_port"))
