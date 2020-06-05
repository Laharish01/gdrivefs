
default_directory="/home/${USER}/gdrivefs-backup"

if [ $# -eq 0 ]
    then
        echo "Please exit and enter a valid directory or enter c for default directory"
        read c
        echo "Creating directory..."
        [ ! -d "${default_directory}" ] && mkdir -p "${default_directory}"
fi

rm -rf src/root

#echo ${1}
#echo ${default_directory}
#echo ${1:-${default_directory}}
python3 src/fusion.py ${1:-${default_directory}}
