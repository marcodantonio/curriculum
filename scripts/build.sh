#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="$ROOT_DIR/build"
DIST_ROOT="$ROOT_DIR/dist"
LANG_DIR="$ROOT_DIR/content/lang"
THEME_DIR="$ROOT_DIR/themes"

mkdir -p "$BUILD_ROOT" "$DIST_ROOT"
cd "$ROOT_DIR"

available_langs() {
  find "$LANG_DIR" -mindepth 1 -maxdepth 1 -type d ! -name '_template' -exec basename {} \; | sort
}

available_themes() {
  find "$THEME_DIR" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort
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

  local preview
  preview="$(python3 "$ROOT_DIR/scripts/sync-preview.py" "$lang" --theme "$theme")"
  mkdir -p "$combo_dir" "$DIST_ROOT/$theme"

  cat > "$wrapper" <<WRAP
\def\CVLanguage{$lang}
\def\CVTheme{$theme}
\input{$ROOT_DIR/main.tex}
WRAP

  wrapper_base="$(basename "$wrapper" .tex)"

  if command -v latexmk >/dev/null 2>&1; then
    latexmk -lualatex -interaction=nonstopmode -halt-on-error \
      -outdir="$combo_dir" "$wrapper" \
      >"$combo_dir/build.log" 2>&1 || { cat "$combo_dir/build.log"; return 1; }
    cp "$combo_dir/${wrapper_base}.pdf" "$DIST_ROOT/$theme/$dist_name"
  else
    local tectonic_bin="${CV_TECTONIC_BIN:-}"
    if [[ -z "$tectonic_bin" ]] && command -v tectonic >/dev/null 2>&1; then
      tectonic_bin="$(command -v tectonic)"
    fi
    if [[ -z "$tectonic_bin" && -x "/Applications/ChatGPT.app/Contents/Resources/tectonic/tectonic" ]]; then
      tectonic_bin="/Applications/ChatGPT.app/Contents/Resources/tectonic/tectonic"
    fi
    if [[ -z "$tectonic_bin" || ! -x "$tectonic_bin" ]]; then
      echo "No compiler found. Use latexmk/LuaLaTeX or set CV_TECTONIC_BIN to an existing Tectonic executable." >&2
      return 1
    fi
    "$tectonic_bin" --outdir "$combo_dir" --keep-logs "$preview" \
      >"$combo_dir/build.log" 2>&1 || { cat "$combo_dir/build.log"; return 1; }
    cp "$combo_dir/$dist_name" "$DIST_ROOT/$theme/$dist_name"
  fi
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
  # Import pending editor edits first. Keep editable previews and their sync state.
  for preview in "$BUILD_ROOT"/review-*/cv-*.tex; do
    [[ -f "$preview" ]] || continue
    local preview_theme="$(basename "$(dirname "$preview")")"
    local preview_lang="$(basename "$preview" .tex)"
    case "$preview_lang" in cv-it|cv-en) ;; *) continue ;; esac
    python3 "$ROOT_DIR/scripts/sync-preview.py" "${preview_lang#cv-}" --theme "${preview_theme#review-}" >/dev/null
  done
  for generated in "$BUILD_ROOT"/*; do
    [[ -e "$generated" ]] || continue
    case "$(basename "$generated")" in review-*) continue ;; esac
    rm -rf -- "$generated"
  done
  rm -rf "$DIST_ROOT"/*
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
