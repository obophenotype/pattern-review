# This makefile is purely for running tests on the complete ontology-development-kit package on travis;
# users should not need to use this

# command used in make test.
# this can be changed to seed-via-docker.sh;
# but this should NOT be the default for environments like travis which
# run in a docker container anyway

# Building docker image
VERSION = "v0.1.0" 
IM=obolibrary/patternreview

build:
	@docker build --no-cache -t $(IM):$(VERSION) . \
	&& docker tag $(IM):$(VERSION) $(IM):latest
	
build-use-cache:
	@docker build -t $(IM):$(VERSION) . \
	&& docker tag $(IM):$(VERSION) $(IM):latest

rb: build-use-cache
	docker run -p 8050:8050 --env-file ./env.list $(IM)
		
run:
	docker run -p 8050:8050 --env-file ./env.list $(IM)

docker-clean:
	docker kill $(IM) || echo not running ;
	docker rm $(IM) || echo not made 

publish-no-build:
	@docker push $(IM):$(VERSION) \
	&& docker push $(IM):latest
	
publish: build
	@docker push $(IM):$(VERSION) \
	&& docker push $(IM):latest