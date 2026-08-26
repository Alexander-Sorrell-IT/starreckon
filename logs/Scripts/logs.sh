#! /bin/bash

destination_folder="Desktop\logs"
other_logs="/TSC/TSC/Naomi/wistron_logs/"
vulcan_logs="/TSC/TSC/Naomi/Vulcan/log/"
host=sbg01@10.48.161.78
pass=WistronSBG

if ! [ -d ${destination_folder} ]
then
	mkdir ${destination_folder}
fi

echo "What Model are you looking for?"
echo "1. Vulcan"
echo "2. Other"

while true
do
	read -e unit_model
	if [[ $unit_model =~ ^[1-2]{1}$ ]]
	then
		break
	else
		echo "Invalid selection. Try again."
	fi
done

if [ $unit_model -eq 1 ]
then
	log_directory=$vulcan_logs
elif [ $unit_model -eq 2 ]
then
	log_directory=$other_logs
fi

echo "Scan unit barcode"

while true
do
	read -e unit_sn
	if [[ $unit_sn =~ ^[0-9]{13}$ ]]
	then
		break
	else
		echo "Invalid SN. Re-scan barcode."
	fi
done

log_list=($(sshpass -p $pass ssh $host ls $log_directory | grep "${unit_sn}"))
wait
log_count=${#log_list[@]}

if [ $log_count -lt 1 ]
then
	echo "There are no logs for this unit."
	exit 0
elif [ $log_count -eq 1 ]
then
	echo "There is 1 log for this unit."
elif [ $log_count -gt 1 ]
then
	echo "There are $log_count logs for this unit."
fi

echo "Enter the selections to download. [0-$log_count]"

count=0
options=""
for log in ${log_list[@]}
do
	echo $count $log
	options+="$count|"
	(( count++ ))
done
echo "$log_count Do not download any more files."

selected_logs=""

while true
do
	read -e file_selection
	if [ $file_selection -eq $log_count ]
	then
		break
	elif [[ $file_selection =~ ^($options)$ ]]
	then
		if ! [[ ${log_list[file_selection]} =~ ^($selected_logs)$ ]]
		then
			selected_logs+="${log_list[$file_selection]}|"
		fi
	else
		echo "Invalid selection. Choose another option."
	fi
done

selected_logs_list=$(echo $selected_logs | tr '|' '\n')

if [[ $selected_logs_list == "" ]]
then
	echo "No files will be downloaded."
	exit 0
else
	echo "Downloading the following selections:"
	echo "${selected_logs_list[@]}"
	echo "-----------------------------------------------------------------------"
fi

for selected_log in ${selected_logs_list[@]}
do
	log_name="${selected_log%.zip}"
	scp -r ${host}:${log_directory}${selected_log} ${destination_folder}
	wait
	if ! [ -d ${destination_folder}\\${log_name} ]
	then
		mkdir ${destination_folder}\\${log_name}
	fi
	unzip -q ${destination_folder}\\${selected_log} -d ${destination_folder}\\${log_name}
	rm ${destination_folder}\\${selected_log}
done

echo "Download complete."
exit 0
