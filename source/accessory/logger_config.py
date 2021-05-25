import logging

def init_logger():
		
	logger = logging.getLogger("BLELogger")
	logger.setLevel(logging.DEBUG)

	# fh = logging.FileHandler("BLELog.log")
	# fh.setLevel(logging.WARN)
	sh = logging.StreamHandler(stream=None)
	sh.setLevel(logging.DEBUG)

	fmt = "%(asctime)s **%(levelname)s** %(filename)s-%(lineno)d-%(threadName)s:\n  %(message)s"
	datefmt = "%H:%M:%S"
	formatter = logging.Formatter(fmt, datefmt)

	# fh.setFormatter(formatter)
	sh.setFormatter(formatter)
	# logger.addHandler(fh)
	logger.addHandler(sh)

	# logger.debug('debug message')
	# logger.info('info message')
	# logger.warning('warn message')
	# logger.error('error message')
	# logger.critical('critical message')