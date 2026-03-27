#!/usr/bin/env bash
# =============================================================================
# migrate.sh — Script de migración de ruidaqan-main → nueva estructura
#
# Uso:
#   cd /ruta/a/tu/repo
#   bash migrate.sh
#
# El script NO borra nada: copia/mueve y luego muestra qué hacer manualmente.
# =============================================================================

set -e
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
echo "Repo: $REPO_ROOT"

# ── 1. Mover requirements a la raíz ──────────────────────────────────────────
if [ -f "src/ruidaqan/gui/requirements_python310.txt" ]; then
    mv src/ruidaqan/gui/requirements_python310.txt requirements-py310.txt
    echo "✓ requirements_python310.txt → requirements-py310.txt"
fi
if [ -f "src/ruidaqan/gui/requirements_python38.txt" ]; then
    mv src/ruidaqan/gui/requirements_python38.txt requirements-py38.txt
    echo "✓ requirements_python38.txt → requirements-py38.txt"
fi

# ── 2. Renombrar constantes/ → constants/ ─────────────────────────────────────
if [ -d "src/ruidaqan/constantes" ] && [ ! -d "src/ruidaqan/constants" ]; then
    git mv src/ruidaqan/constantes src/ruidaqan/constants
    echo "✓ constantes/ → constants/  (git mv)"
fi

# ── 3. Mover datos de transferencias a data/ ─────────────────────────────────
if [ -d "src/ruidaqan/transferencias" ]; then
    mkdir -p data
    git mv src/ruidaqan/transferencias data/transferencias
    echo "✓ src/ruidaqan/transferencias/ → data/transferencias/"
fi

# ── 4. Mover fixtures de test/ a tests/fixtures/ ─────────────────────────────
mkdir -p tests/fixtures
for ext in h5 RUI pkl; do
    for f in test/*.$ext; do
        [ -f "$f" ] || continue
        cp "$f" tests/fixtures/
        echo "✓ Copiado $f → tests/fixtures/"
    done
done

# Mover scripts de test
for f in test/test_*.py; do
    [ -f "$f" ] || continue
    git mv "$f" "tests/$(basename $f)" 2>/dev/null || cp "$f" "tests/$(basename $f)"
    echo "✓ $f → tests/"
done

# ── 5. Eliminar docs/html compilada de dentro de src/ ────────────────────────
if [ -d "src/ruidaqan/docs/html" ]; then
    rm -rf src/ruidaqan/docs/html
    echo "✓ Eliminado src/ruidaqan/docs/html/  (docs compilada no va en src)"
fi

# ── 6. Sacar dist/ del tracking de git ───────────────────────────────────────
if git ls-files --error-unmatch dist/ &>/dev/null 2>&1; then
    git rm -r --cached dist/
    echo "✓ dist/ removida del índice de git (ya está en .gitignore)"
fi

# ── 7. Eliminar setup.py redundante ──────────────────────────────────────────
if [ -f "setup.py" ]; then
    git rm setup.py
    echo "✓ setup.py eliminado (pyproject.toml lo reemplaza)"
fi

# ── 8. Crear .github/workflows/ ──────────────────────────────────────────────
mkdir -p .github/workflows
echo "✓ Directorio .github/workflows/ listo para los yamls"

echo ""
echo "============================================================"
echo "  Pasos manuales que quedan:"
echo "============================================================"
echo ""
echo "  1. Copiá los archivos .yml de workflows:"
echo "     cp /ruta/a/ci.yml      .github/workflows/"
echo "     cp /ruta/a/publish.yml .github/workflows/"
echo ""
echo "  2. Reemplazá pyproject.toml con la versión nueva."
echo ""
echo "  3. Actualizá los imports en src/ si usaban 'constantes':"
echo "     grep -r 'ruidaqan.constantes' src/ tests/"
echo "     → cambiar por 'ruidaqan.constants'"
echo ""
echo "  4. Configurá PyPI Trusted Publishing en:"
echo "     https://pypi.org/manage/project/ruidaqan/settings/publishing/"
echo "     Owner:    <tu-usuario-github>"
echo "     Repo:     ruidaqan"
echo "     Workflow: publish.yml"
echo "     Env:      pypi"
echo ""
echo "  5. Creá el entorno 'pypi' en GitHub:"
echo "     Repo → Settings → Environments → New environment → pypi"
echo ""
echo "  6. Hacé git add + commit:"
echo "     git add -A"
echo "     git commit -m 'refactor: reorganización de estructura del proyecto'"
echo ""
echo "  7. Para publicar una nueva versión:"
echo "     bumpver update --patch   (o --minor / --major)"
echo "     git push --follow-tags"
echo ""
