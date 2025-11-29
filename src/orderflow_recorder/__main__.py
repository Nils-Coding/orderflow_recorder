from .utils.logging import setup_logging, get_logger


def main() -> None:
	setup_logging()
	log = get_logger()
	log.info("orderflow-recorder skeleton ready.")


if __name__ == "__main__":
	main()


