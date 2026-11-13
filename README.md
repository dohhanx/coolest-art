# Unzipping the Dawn

A surreal ukiyo-e print. On a mountain ridge, villagers haul a giant brass zipper open across the indigo night sky, and a blazing dawn pours out through the gap.

`main.py` does not draw the picture. It checks `art/unzipping-the-dawn.jpg` and copies those bytes to `/output/entry.png` (or to `$MAKEFUN_OUTPUT_DIR/entry.png` when that variable is set). The file must be a whole JPEG, at most 1 MiB, and at most 1024 by 1024 pixels.

```
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```
