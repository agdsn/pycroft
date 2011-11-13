#!/bin/bash

# Exit script if no description was entered on the commandline
if [ -z $1 ] &> /dev/null # suppress errors when $i contains spaces
then
    echo "Error: No description entered."
    echo ""
    echo "USAGE:"
    echo "Please enter a description for this migration as the first argument on the command line, like this: "
    echo ""
    echo "$0 \"Describe this migration here\""
    echo ""
    exit
fi

# Create array of the commands which this script runs, so we can list remaining 
#   commands when user cancels the script's execution.
declare -a commands=("./manage.py create_model > oldmodel.py" \
                     "./manage.py make_update_script_for_model --oldmodel=oldmodel:meta --model=pycroft.model.base:ModelBase.metadata > \"migration/versions/$filename\"" \
                     "vim migration/versions/$filename" \
                     './manage.py upgrade' \
                     'rm oldmodel.py' \
                     );

# Takes 1 argument:
#   A description of the next action the script will take if the user presses ENTER;
element=0
function press_enter
{
    echo ""
    echo "Do you want to $1?"
    echo -n "Press ENTER to say \"Yes\" and continue, or any other key to quit: "
    read response
    echo ""
    # If the user pressed Enter
    if [ -z $response ];
    then
        # remove the first command from the array
        elements=${#commands[@]}
        for (( i=0;i<$elements;i++ ));
        do
            c=${commands[${i}]}
            if [ $i -gt $element ];
            then
                c2+=($c)
            fi
            commands=$c2
        done
        ((element++))
        # continue
    else
        echo "Here are the next commands you may want to enter:"
        echo ""
        elements=${#commands[@]}
        for (( i=0;i<$elements;i++));
        do
            el_minus=$(($element-1))
            echo $el_minus
            if [ $i -gt $el_minus ];
            then
                echo ${commands[${i}]}
            fi
        done
        echo ""
        exit
    fi
}

echo "Comparing the model to the database to see what needs to change in the database..."
./manage.py compare_model_to_db pycroft.model.base:ModelBase.metadata

press_enter "create a declarative model file representing the current state of the database"
./manage.py create_model > oldmodel.py

press_enter "create an upgrade script (giving it a meaningful name)"

# Convert first argument's spaces to underscores
# TODO: Make this replace a forward slash too
description=${1// /_}
description=${description//\//_}
# Create new migration number
# Get list of files in migration directory
cd migration/versions
for i in *
do
    # Get the first 3 characters of each filename and append them to a list
    key=`echo ${i:0:3}|sed 's/^0*//'`
    numbers[$key]=$key
done
cd ../..
# Get the highest migration number and add 1 to that number, then zero-pad to three digits
new_number=`printf "%03d" ${#numbers[@]}`
filename="${new_number}_${description}.py"

./manage.py make_update_script_for_model --oldmodel=oldmodel:meta --model=pycroft.model.base:ModelBase.metadata > "migration/versions/$filename"

press_enter "edit the upgrade script in vim"
echo "Please manually edit $filename in case it does not do what you want it to do."
echo ""
vim migration/versions/$filename

press_enter "test upgrading & downgrading on an expendable copy of your database"
cp test_db.sqlite test_db.sqlite.bak
./manage.py test
# then if all went well, restore your original database
rm test_db.sqlite
mv test_db.sqlite.bak test_db.sqlite

# ------------------------------------------------------------------------------------------------------
# NOTE: !!! Start here if you're not creating a new migration, but only running a migration that another 
# developer created in order to get your database schema in sync with new code revisions you just pulled
# in via Bazaar !!!
# ------------------------------------------------------------------------------------------------------

press_enter "run the migration script to upgrade your database"
./manage.py upgrade

press_enter "remove the temporary file"
rm oldmodel.py oldmodel.pyc

echo "Done!"
