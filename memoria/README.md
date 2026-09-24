# Memoria (LaTeX)

Plantilla de la memoria del TFM. **Respeta el límite de 20 caras** del máster: el cuerpo (de la sección 1 a
las conclusiones) debe caber en 20 páginas; portada, resumen, índice, bibliografía (media cara) y anexos no
cuentan según la guía. Cada sección lleva en comentario el número de caras orientativo y qué contar.

## Compilar
```bash
latexmk -pdf memoria.tex        # encadena pdflatex + bibtex + pdflatex + pdflatex
# o manualmente:
pdflatex memoria ; bibtex memoria ; pdflatex memoria ; pdflatex memoria
```

## Figuras
Exporta a `figuras/` y descomenta los `\includegraphics`:
- `figuras/dfd.png`  <- `../docs/threat-model/dfd.mmd` (Mermaid; usa mermaid.live o `mmdc`)
- `figuras/asr.png`  <- `../results/asr.png` (lo genera `make report`)

## Tablas de resultados
Rellena la tabla \ref{tab:asr} con `../results/asr.csv`.

## Bibliografía
BibTeX clásico (`referencias.bib`, estilo `unsrt`). Para cambiar a biblatex+biber, ver el bloque comentado
en el preámbulo de `memoria.tex`.
