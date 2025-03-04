#!/bin/bash

INPUT_PATH=$1

if [ -z "$INPUT_PATH" ]; then
	echo "Usage: $0 INPUT_PATH"
	exit
fi

set -x

# change these variables if necessary to point to the correct folders
export NLTK_DATA=~/nltk_data
export PYTHONPATH=.

input_dir=$(dirname $INPUT_PATH)
input_file=$(basename $INPUT_PATH .txt)

token_file=$input_dir/$input_file.tok.txt
cat $INPUT_PATH | python -m ccg2lamp.en.tokenizer > $token_file

candc_xml=$input_dir/$input_file.candc.xml
candc_log=$input_dir/$input_file.candc.log
./candc-1.00/bin/candc --models candc-1.00/models --log $candc_log --candc-printer xml --input $token_file > $candc_xml

parse_xml=$input_dir/$input_file.syn.xml
python -m ccg2lamp.en.candc2transccg $token_file $candc_xml > $parse_xml

parse_html=$input_dir/${input_file}.syn.html
python -m ccg2lamp.scripts.visualize $parse_xml > $parse_html

sem_xml=$input_dir/$input_file.sem.xml
python -m ccg2lamp.scripts.semparse $parse_xml ccg2lamp/en/semantic_templates_en_emnlp2015.yaml $sem_xml --ncores=0

sem_html=$input_dir/${input_file}.sem.html
python -m ccg2lamp.scripts.visualize $sem_xml > $sem_html

entail_html=$input_dir/${input_file}.pro.html
proof_xml=$input_dir/${input_file}.pro.xml
python -m ccg2lamp.scripts.prove $sem_xml --proof $proof_xml --graph_out $entail_html

set +x