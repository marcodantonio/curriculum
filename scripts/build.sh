#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="$ROOT_DIR/build"
DIST_ROOT="$ROOT_DIR/dist"
LANG_DIR="$ROOT_DIR/content/lang"
THEME_DIR="$ROOT_DIR/themes"

mkdir -p "$BUILD_ROOT" "$DIST_ROOT"

available_langs() {
  find "$LANG_DIR" -mindepth 1 -maxdepth 1 -type d ! -name '_template' -printf '%f\n' | sort
}

available_themes() {
  find "$THEME_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
}

build_combo() {
  local theme="$1"
  local lang="$2"
  local combo_dir="$BUILD_ROOT/$theme/$lang"
  local wrapper="$combo_dir/main-$theme-$lang.tex"
  local wrapper_base
  local dist_name="cv-$lang.pdf"

  if [[ ! -d "$THEME_DIR/$theme" ]]; then
    echo "Unknown theme: $theme" >&2
    exit 1
  fi

  for req in meta.tex labels.tex experience.tex education.tex projects.tex activities.tex skill-groups.tex languages.tex highlights.tex other-info.tex legal.tex; do
    if [[ ! -f "$LANG_DIR/$lang/$req" ]]; then
      echo "Language '$lang' is missing $req" >&2
      exit 1
    fi
  done

  mkdir -p "$combo_dir" "$DIST_ROOT/$theme"

  cat > "$wrapper" <<WRAP
\def\CVLanguage{$lang}
\def\CVTheme{$theme}
\input{$ROOT_DIR/main.tex}
WRAP

  wrapper_base="$(basename "$wrapper" .tex)"

  latexmk -lualatex -interaction=nonstopmode -halt-on-error \
    -outdir="$combo_dir" "$wrapper" \
    >"/tmp/cv-$theme-$lang.log" 2>&1 || { cat "/tmp/cv-$theme-$lang.log"; return 1; }

  cp "$combo_dir/${wrapper_base}.pdf" "$DIST_ROOT/$theme/$dist_name"
}

build_theme() {
  local theme="$1"
  local lang="${2:-all}"
  if [[ "$lang" == "all" ]]; then
    while IFS= read -r item; do
      build_combo "$theme" "$item"
    done < <(available_langs)
  else
    build_combo "$theme" "$lang"
  fi
}

build_all() {
  while IFS= read -r theme; do
    while IFS= read -r lang; do
      build_combo "$theme" "$lang"
    done < <(available_langs)
  done < <(available_themes)
}

clean_all() {
  rm -rf "$BUILD_ROOT"/* "$DIST_ROOT"/*
}

case "${1:-all}" in
  all)
    build_all
    ;;
  clean)
    clean_all
    ;;
  list)
    echo "Themes:"
    available_themes
    echo
    echo "Languages:"
    available_langs
    ;;
  list-themes)
    available_themes
    ;;
  list-languages)
    available_langs
    ;;
  *)
    build_theme "$1" "${2:-all}"
    ;;
esac
