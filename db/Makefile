# Database only portion of the Master makefile for Elko server and applications
#
# Make operations are all in reference to a configured set of applications and
# components.  These components are listed by name in the file 'components' or
# by defining COMPONENTS as an environment variable or on the make command
# line.  Also, regardless how the set of components is configured externally,
# the components will always includes the core server itself.
#
# Instructions:
# make db            - Make MongoDB setup scripts

# JSON static files to load 
TELEPORTDB = ./db-teleports.json

DATABASE_OBJECTS = $(TELEPORTDB)

# JSON object definitions supplied by the various components
MONGODB_OBJECTS = $(shell find . -name '*.json') $(DATABASE_OBJECTS)

# The file that actually gets produced by "make db"
DBINIT_SCRIPT = ./dbinit.sh

NEOHABITAT_MONGO_HOST ?= "127.0.0.1"

clean: nuke all help

help:
	@echo ""
	@echo "Valid 'make' targets are 'teleports', 'regions', 'all', 'clean', or JSONFILENAME.o . Default is 'clean'"
	@echo "Mongo output is in .errs"
	@echo ""

regions:
	@echo "Building Regions, Avatars, and Objects"
	@rm -f $(DBINIT_SCRIPT)
	@echo '#!/bin/bash' > $(DBINIT_SCRIPT)
	@cp dbinitpre.js $(DBINIT_SCRIPT)
	@$(foreach F,$(MONGODB_OBJECTS), echo "eupdate(" >> $(DBINIT_SCRIPT); cat $F >> $(DBINIT_SCRIPT); echo ")" >>$(DBINIT_SCRIPT);)
	@cat dbinitpost.js >> $(DBINIT_SCRIPT)
	@cat $(DBINIT_SCRIPT) | mongo $(NEOHABITAT_MONGO_HOST)/elko --verbose --shell mongohelper.js >>.errs 2>&1

teleports:
	@echo "Building Teleport Directory"
	@rm -f $(TELEPORTDB)
	@echo '{ "ref" : "teleports", "type" : "map", "map" : {' > $(TELEPORTDB)
	@$(foreach F,$(MONGODB_OBJECTS), node dumpTeleportEntries.js < $(F) >> $(TELEPORTDB);)
	@echo ' " End Of Directory": "eod" } }' >> $(TELEPORTDB)
	@cp dbinitpre.js $(DBINIT_SCRIPT)
	@echo "eupdate(" >> $(DBINIT_SCRIPT); cat $(TELEPORTDB) >> $(DBINIT_SCRIPT); echo ")" >>$(DBINIT_SCRIPT)
	@cat dbinitpost.js >> $(DBINIT_SCRIPT)
	@cat $(DBINIT_SCRIPT) | mongo $(NEOHABITAT_MONGO_HOST)/elko --verbose --shell mongohelper.js >> .errs 2>&1

%.o: %.json
	@echo "Updating" $*.json "in the database"
	@cp dbinitpre.js $(DBINIT_SCRIPT)
	@echo "eupdate(" >> $(DBINIT_SCRIPT); cat $*.json >> $(DBINIT_SCRIPT); echo ")" >>$(DBINIT_SCRIPT)
	@cat dbinitpost.js >> $(DBINIT_SCRIPT)
	@cat $(DBINIT_SCRIPT) | mongo $(NEOHABITAT_MONGO_HOST)/elko --verbose --shell mongohelper.js >> .errs 2>&1
	@tail -3 .errs

nuke:
	@echo "Nuking database"
	@rm -f  $(DATABASE_OBJECTS) .errs	
	@echo 'db.odb.remove({});' | mongo $(NEOHABITAT_MONGO_HOST)/elko --verbose --shell mongohelper.js >> .errs 2>&1

all: teleports regions

deletables:
	$(foreach F,$(MONGODB_OBJECTS), if grep -q "deletable" $(F); then grep -v "deletable" <$(F) > tmp; mv tmp $(F); fi;)
