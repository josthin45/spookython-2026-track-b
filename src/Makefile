# sam build corre este archivo dentro de src/ y pasa ARTIFACTS_DIR.
build-OrchestratorFunction build-SimulatorFunction build-AggregatorFunction:
	mkdir -p "$(ARTIFACTS_DIR)"
	python -m pip install -r requirements-lambda.txt -t "$(ARTIFACTS_DIR)"
	cp -r engine lambdas "$(ARTIFACTS_DIR)/"
