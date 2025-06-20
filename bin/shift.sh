#!/usr/bin/env bash

function usage() {
  [ -n "${1}" ] && >&2 echo "${1}"
  >&2 echo "${0} <revision> <node_path>[ <node_path> ...]" 
}

# Allows or prevents destructive commands from running.
export EXEC=''

# Parse parameters
declare -a positional=()
while [ ${#} -gt 0 ]; do
  case "${1}" in
    --dry-run|-n)
      export EXEC=':' ;;
    *) positional+=("${1}")
  esac
  shift
done
set -- "${positional[@]}"

# Ensure revision
if [[ ! "${1}" =~ ^(0|[1-9][0-9]*)$ ]]; then
  usage "ERROR: Must specify a valid minimum revision number."
  exit 1
fi
declare revision=$((${1}))
shift

# Ensure node path(s)
if [ ${#} -eq 0 ]; then
  usage "ERROR: Must specify at least one node path."
  exit 1
fi
declare -a node_paths=("${@}")
declare -a files

function format() {
  printf -- '%03d' "${1?'Must specify a revision number.'}"
}
function name() {
  echo "rev.$(format "${1}").yaml"
}
function previous() {
  local root
  local path=${1?'Must specify a path'}
  root=$(dirname "${path}")
  ( echo "${path}"; find "${root}" -maxdepth 1 -type f ) \
  |sort -u \
  |grep -B1 "${path}" \
  |grep -v "${path}"
}
function truncate() {
  echo -n './'
  rev <<<"${1#"${ROOT}/"}" |cut -d'/' -f-2 |rev
}
function patternize() {
  local path
  path=$(truncate "${1?'Must specify a path'}")
  awk -F\. '{printf "(?<=.%s.)%s(?=.%s)",$2,$3,$4}' <<<"${path}" \
  |perl -pe 's/(?<!\\)(?=[.\/])/\\/g'
}
function retrieve() {
  find -s "${ROOT}" -type f -name "${1:-"*.yaml"}" "${@:2}"
}
function rgxor() {
  local patterns
  patterns="($(printf -- '%s\n' "${@}" |paste -sd\| -))"
  echo "${patterns}"
}
function refers_to() {
  local pattern=${1?'Must specify a pattern'}
  pcre2grep -m 1 -H "${pattern}" "${files[@]}" \
  |cut -d: -f1
}
function create() {
  local path=${1?'Must specify a path'}
  mkdir -p "$(dirname "${path}")" || return 2
  local prev
  prev=$(previous "${path}")
  if [ -f "${prev}" ]; then
    ${EXEC} cp -fa "${prev}" "${path}" || return 3
    ${EXEC} perl -i -pe '
      s/'"${prev_pattern}"'/'"${next_rev}"'/g;
      s/(https:\S+?\/\w+\.)\d+(?=\.yaml)/'"\${1}${next_rev}"'/g;
    ' "${path}"
  else
    printf -- '%s\n' \
      "# yaml-language-server: \$schema=https://json-schema.org/draft-07/schema" \
      "\$schema: https://json-schema.org/draft-07/schema" \
      "\$id: ${REMOTE%.git}/blob/main/${path}" \
      "" \
      > "${path}" || return 3
  fi
}

# Root directory
export ROOT='var/lib'

# Path reference patterns for the preceding `revision`
declare -a prev_rgxs=()
# Path to be created for `revision`
declare -a next_paths=()

# Determine prev & next paths
for path in "${node_paths[@]}"; do
  declare prev_name next_name
  path="${ROOT}/${path}"
  next_name="$(name "${revision}")"

  prev_name="$(name "$((revision-1))")"
  # ...
  while true; do
    declare prev_file
    prev_file=$(previous "${path}/${prev_name}")
    if [ -f "${prev_file}" ]; then
      prev_rgxs+=("$(patternize "${prev_file}")")
    fi
    # ...
    next_paths+=("${path}/${next_name}")
    # ...
    [[ "${path}" == "${ROOT}" ]] && break
    path=$(dirname "${path}")
  done
done

declare latest glob
latest=$(find -s var/lib -maxdepth 1 -type f -name 'rev.*.yaml' | tail -1 | awk -F. '{printf "%d",$2}')
# shellcheck disable=SC2207
files=(`retrieve "*.yaml"`)

# Shift references from <revision> onwards
for index in $(seq $((latest)) $((revision))); do
  pad=$(format "${index}")
  glob="*.${pad}.yaml"
  uprev=$(format "$((index+1))")
  # shellcheck disable=SC2207
  declare -a refs=(`refers_to '\w+\.'"${pad}"'\.yaml'`)
  echo "[\$ref: ${glob}]"
  if [ ${#refs[@]} -gt 0 ]; then
    ${EXEC} perl -i -pe \
      's/(?<=\.)'"${pad}"'(?=\.yaml)/'"${uprev}"'/g' \
      "${refs[@]}" &&
    printf "Shifted *.${pad}.yaml ref(s) in %s\n" "${refs[@]}"
  fi
  echo
done

declare prev_pattern next_rev
prev_pattern=$(rgxor "${prev_rgxs[@]}")
next_rev=$(format "$((revision))")
glob="*.$(format "$((revision-1))").yaml"
# Shift proceeding refrences to previous revision
echo "[\$ref: ${glob}]"
while read -r path; do
  declare name rev
  name=$(basename "${path}")
  rev=$(cut -d. -f2 <<<"${name}")
  # ...
  if [ $((10#${rev})) -ge ${revision} ]; then
    ${EXEC} perl -i -pe \
      's/'"${prev_pattern}"'/'"${next_rev}"'/g' \
      "${path}" &&
    echo "Shifted ${glob} ref(s) in ${path}"
  fi
done < <(refers_to "${prev_pattern}")
echo
echo

# Shift filenames
for index in $(seq $((latest)) $((revision))); do
  pad=$(format "${index}")
  glob="*.${pad}.yaml"
  uprev=$(format "$((index+1))")
  # shellcheck disable=SC2207
  declare -a files=(`retrieve "${glob}"`)
  echo "[file: ${glob}]";
  for file in "${files[@]}"; do
    declare location
    location="${file/${pad}/${uprev}}"
    ${EXEC} mv -f "${file}" "${location}" &&
    echo "Moved ${file} -> ${location}"
  done
  echo
done

# Insert shifting revision files
for path in "${next_paths[@]}"; do
  create "${path}" &&
  echo "Created ${path}"
done
echo
