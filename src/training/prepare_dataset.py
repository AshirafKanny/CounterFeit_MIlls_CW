from pathlib import Path


def main() -> None:
    root = Path("data")
    genuine = root / "genuine"
    counterfeit = root / "counterfeit"

    genuine.mkdir(parents=True, exist_ok=True)
    counterfeit.mkdir(parents=True, exist_ok=True)

    print("Dataset folders are ready:")
    print(f"- {genuine}")
    print(f"- {counterfeit}")
    print("Add note images into these folders for future model training.")


if __name__ == "__main__":
    main()
