#!/usr/bin/env zsh
(
	declare DIR=lib;
	cd $DIR || exit 1;
	# shellcheck disable=SC2207
	declare -a REVS=(`
		find . -mindepth 2 -maxdepth 2 -type f -name 'rev.*.yaml' \
			|rev \
			|cut -d'/' -f1 \
			|rev \
			|sort -u
	`);

	for (( I=0; I<${#REVS[@]}; I++ )); do
		declare FST="${REVS[1]}";
		declare REV="${REVS[$((I+1))]}";
		declare -a CUR=("${REVS[@]:1:$I}");
		# shellcheck disable=SC2207
		declare -a PROPS=(`
			eval "find . -mindepth 2 -maxdepth 2 -type f \( -name $FST ${CUR[@]//#/-o -name } \)" \
				|sort -r \
				|awk -F'/' 'BEGIN{L="";}{if($2!=L){print $0;};L=$2;}' \
				|sort`);

		cat >$REV <<-EOF
		# yaml-language-server: \$schema=https://json-schema.org/draft-07/schema
		\$schema: https://json-schema.org/draft-07/schema
		\$id: https://github.com/LeShaunJ/ops-schema/blob/main/$DIR/$REV
		allOf:
		  - \$ref: './meta.001.yaml'
		  - properties:$(
				declare PROP;
				for PATH in "${PROPS[@]}"; do
					PROP=$(/usr/bin/cut -d'/' -f2 <<<"$PATH");
					printf -- "\n%-6s%s:\n%-8s\$ref: '%s'" "" "$PROP" "" "$PATH";
				done
			)
		EOF
	done;
)