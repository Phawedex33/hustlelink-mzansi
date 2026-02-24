from app import create_app

print("RUN FILE IS EXECUTING")

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
