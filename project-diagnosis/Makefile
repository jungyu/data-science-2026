# =========================================================
# TCM Diagnostic RAG — Makefile
# =========================================================
# Required environment:
#   DATABASE_URL      postgresql connection string
#   OPENAI_API_KEY    required for embed / query routes
# =========================================================

PYTHON ?= python3
PSQL   ?= psql

SCHEMA_SQL := sql/tcm-rag.schema.sql
SEED_SQL   := sql/tcm-rag.seed.sql

.PHONY: help install schema seed reset embed scrape parse query sample eval mcp mcp-install check-env

help:
	@echo "Targets:"
	@echo "  install   Install Python dependencies"
	@echo "  schema    Apply schema.sql to DATABASE_URL"
	@echo "  seed      Apply seed.sql to DATABASE_URL"
	@echo "  reset     Drop schema objects and re-apply schema + seed (DESTRUCTIVE)"
	@echo "  scrape    Crawl 醫砭 directory into source_documents"
	@echo "  parse     Parse source_documents into knowledge_atoms"
	@echo "  embed     Generate embeddings for atoms missing them"
	@echo "  query Q='…'  Run end-to-end query pipeline"
	@echo "  sample    Run the first sample query from docs/examples/sample-queries.md"
	@echo "  eval      Run assertion harness against tests/cases.yaml"
	@echo "  mcp       Start MCP server on port 3000 (Claude Desktop + REST)"
	@echo "  mcp-install  Install MCP server dependencies"

check-env:
	@test -n "$$DATABASE_URL" || (echo "ERROR: DATABASE_URL is not set" && exit 1)

install:
	$(PYTHON) -m pip install -r requirements.txt

schema: check-env
	$(PSQL) "$$DATABASE_URL" -v ON_ERROR_STOP=1 -f $(SCHEMA_SQL)

seed: check-env
	$(PSQL) "$$DATABASE_URL" -v ON_ERROR_STOP=1 -f $(SEED_SQL)

reset: check-env
	@echo "⚠️  This will DROP TCM schema objects in the target database."
	@read -p "Type 'yes' to continue: " confirm && test "$$confirm" = "yes"
	$(PSQL) "$$DATABASE_URL" -v ON_ERROR_STOP=1 -c "\
	  DROP TABLE IF EXISTS public.retrieval_logs, public.query_logs, \
	  public.diagnostic_rules, public.atom_relations, public.knowledge_atoms, \
	  public.source_documents CASCADE;"
	$(MAKE) schema
	$(MAKE) seed

scrape: check-env
	$(PYTHON) scripts/scrape_yibian.py

parse: check-env
	$(PYTHON) scripts/parse_to_atoms.py

embed: check-env
	$(PYTHON) scripts/embed_atoms.py

query: check-env
	@test -n "$(Q)" || (echo "ERROR: pass Q='your query'" && exit 1)
	$(PYTHON) scripts/answer_query.py "$(Q)"

sample: check-env
	$(PYTHON) scripts/answer_query.py "最近下午容易潮熱，晚上盜汗，口乾，舌紅少苔"

eval: check-env
	$(PYTHON) scripts/eval_queries.py

mcp-install:
	$(PYTHON) -m pip install -r mcp-server/requirements.txt

mcp: check-env
	$(PYTHON) mcp-server/server.py
