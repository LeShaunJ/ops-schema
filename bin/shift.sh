#!/usr/bin/env bash

if [[ $1 =~ ^0|[1-9][0-9]*$ ]]; then
  echo "ERROR: Must specify a minimum revision number." 1>&2;
  exit 1;
fi

declare minumum=$1;
declare glob;

for index in $(seq 35 "$minumum"); do
  pad=$(printf -- '%03d' "$index");
  glob="*.${pad}.yaml";
  uprev=$(printf -- '%03d' "$((index+1))");
  # shellcheck disable=SC2207
  declare -a files_all=(`find var/lib -type f -name "*.yaml"`)
  # shellcheck disable=SC2207
  declare -a file_refs=(`
    pcre2grep -H "\\w\\.${pad}\\.yaml" "${files_all[@]}" \
      |cut -d: -f1 \
      |sort -u;
  `);
  echo "${glob}:";
  printf '%s\n' "${file_refs[@]}";
  if [ ${#file_refs[@]} -gt 0 ]; then
    perl -i.bak -pe \
      's/(?<=\.)'"$pad"'(?=\.yaml)/'"$uprev"'/g' \
      "${file_refs[@]}";
  fi
done

for index in $(seq 35 "$minumum"); do
  pad=$(printf -- '%03d' "$index");
  glob="*.${pad}.yaml";
  uprev=$(printf -- '%03d' "$((index+1))");
  # shellcheck disable=SC2207
  declare -a files=(`find var/lib -type f -name "$glob"`);
  echo "${glob}:";
  for file in "${files[@]}"; do
    mv -vf "${file}" "${file/$pad/$uprev}";
  done
  echo;
done
