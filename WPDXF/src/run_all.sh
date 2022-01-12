for file in $1*
do
    echo $file
    python main.py -b "$file" -m $2
done