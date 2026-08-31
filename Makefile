install:
	./scripts/install.sh

test:
	./scripts/test.sh

benchmark-smoke:
	. .venv/bin/activate && politybench benchmark-smoke --fidelity F0 --seeds 2

calibrate-smoke:
	. .venv/bin/activate && politybench calibrate-smoke

dev:
	. .venv/bin/activate && politybench serve

build:
	cd packages/demo/web && npm install && npm run build

.PHONY: install test benchmark-smoke calibrate-smoke dev build
