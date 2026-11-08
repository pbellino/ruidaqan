# tests/fixtures/

> Los tests de `tests/test_sintetico.py` no necesitan estos archivos: generan
> mediciones sintéticas de espectro conocido (ver `tests/sintetico.py`) y
> corren en el CI. Los archivos de abajo sólo hacen falta para los tests con
> mediciones reales.

Este directorio contiene archivos de datos reales usados por los tests.
**No están versionados** (ver `.gitignore`).

## Archivos necesarios

| Archivo                        | Formato | Descripción                          |
|-------------------------------|---------|--------------------------------------|
| `S001-N2-1.h5`                | HDF5    | Medición adquirida con RuiDAQAn      |
| `S31-N3-1.RUI`                | RUI     | Medición del FERCIN-3                |
| `S001-resultados_ajustes.pkl` | Pickle  | Resultados de ajuste previos         |

## Cómo obtenerlos

Copiá los archivos originales desde `test/` del repo viejo:

```bash
cp /ruta/al/repo/viejo/test/*.h5  tests/fixtures/
cp /ruta/al/repo/viejo/test/*.RUI tests/fixtures/
cp /ruta/al/repo/viejo/test/*.pkl tests/fixtures/
```

Los tests que requieran estos archivos se saltearán automáticamente
(`pytest.skip`) si no los encontrás en este directorio.
