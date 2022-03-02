for file in $1*
do
    echo $file
    if [ "$6" == "1" ];
    then
        python main.py -b "$file" -m $2 --num_examples $3 --num_queries $4 --tau $5 --enrich_predicates
    else
        python main.py -b "$file" -m $2 --num_examples $3 --num_queries $4 --tau $5 
    fi
done