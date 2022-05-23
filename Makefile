NAME="joinspartan/serverless:1.3"

.PHONY : all shell

all : shell

shell :
	docker run --rm -it \
	-v `pwd`:/code \
	--env-file .env \
	$(NAME) bash
