from dotenv import load_dotenv

# Loaded here, before any submodule reads os.environ, so every entrypoint -- the API,
# `ioe-index`, `ioe-notices` -- sees the same .env regardless of which shell started it.
load_dotenv()


def main() -> None:
    print("Hello from ioe!")
