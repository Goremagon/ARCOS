# =============================================================================
# ARCOS: AI Rule-Constrained Orchestration System - Windows Build File
# =============================================================================

PROJECT_NAME := arcos-core
VERSION      := 0.1.0
SCHEMA_DIR   := ./schemas

# executables
CARGO        := cargo
XMLLINT      := xmllint

# --- Default Target ---
.PHONY: all
all: info validate-schemas build test
	@echo [ARCOS] All-in-one build completed successfully.

# --- 1. Information ---
.PHONY: info
info:
	@echo ========================================
	@echo    ARCOS Build System v$(VERSION)
	@echo ========================================
	@echo Targets:
	@echo   make all       - Validate, build, and test everything
	@echo   make schemas   - Check XSD syntax
	@echo   make build     - Compile the Maestro binaries
	@echo   make clean     - Remove build artifacts
	@echo ========================================

# --- 2. Schema Validation ---
.PHONY: validate-schemas
validate-schemas:
	@echo [Schema] Checking XSD syntax...
	@$(XMLLINT) --noout $(SCHEMA_DIR)/arcos-core.xsd
	@echo [Schema] Core XSD syntax is good.

# --- 3. Build Core Components ---
.PHONY: build
build:
	@echo [Build] Compiling ARCOS Core...
	@$(CARGO) build --release
	@echo [Build] Compilation finished.

# --- 4. Testing ---
.PHONY: test
test:
	@echo [Test] Running unit tests...
	@$(CARGO) test
	@echo [Test] Test suite passed.

# --- 5. Cleanup ---
.PHONY: clean
clean:
	@echo [Clean] Cleaning build artifacts...
	@$(CARGO) clean
	@echo [Clean] Workspace is clean.