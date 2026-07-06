# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?= -c .
SPHINXBUILD   ?= sphinx-build
PYTHON        ?= python3
SOURCEDIR     = source
BUILDDIR      = build
IMAGEDIR      = source/images

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile markdown spelling html-multiversion html-multiversion-preview

# Add custom markdown build command
md:
	@$(SPHINXBUILD) -b markdown "$(SOURCEDIR)" "$(BUILDDIR)/markdown" $(SPHINXOPTS) $(O)
	@echo "Copying images..."
	@mkdir -p "$(BUILDDIR)/markdown/_images"
	@cp -r "$(IMAGEDIR)"/* "$(BUILDDIR)/markdown/_images"
	@echo "Copying stylesheets..."
	@mkdir -p "$(BUILDDIR)/markdown/_static"
	@cp -r "$(SOURCEDIR)/_static"/* "$(BUILDDIR)/markdown/_static"
	@echo "Build finished. The markdown files are in $(BUILDDIR)/markdown."

# Add explicit spelling target (fails if any misspelled words are found)
spelling:
	@bash "$(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../scripts/ci/docs_spelling_check.sh"

# Build versioned docs without sphinx-multiversion.
html-multiversion:
	@./scripts/build_versioned_docs.sh

# Local preview build including all local branches.
html-multiversion-preview:
	@./scripts/build_versioned_docs.sh --preview

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
