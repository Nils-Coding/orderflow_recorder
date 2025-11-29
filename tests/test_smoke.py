def test_logger_smoke():
	from orderflow_recorder.utils.logging import setup_logging, get_logger

	setup_logging()
	log = get_logger()
	log.info("logger smoke")
	assert log is not None


