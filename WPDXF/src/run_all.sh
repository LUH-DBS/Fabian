for file in $1*
do
    echo $file
    python main.py -b "$file" -m $2 -num_examples $3 -num_queries $4
done