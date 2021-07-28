cd /home/zhangchunle/Paddle-bot/webservice/buildLog; 
rm -rf *todayDuty*
wget https://paddle-docker-tar.cdn.bcebos.com/buildLog/Paddle_todayDuty-`date +%Y-%m-%d`.log
cp Paddle_todayDuty-`date +%Y-%m-%d`.log book_todayDuty-`date +%Y-%m-%d`.log 
cp Paddle_todayDuty-`date +%Y-%m-%d`.log models_todayDuty-`date +%Y-%m-%d`.log 
wget https://paddle-docker-tar.cdn.bcebos.com/buildLog/Paddle-Lite_todayDuty-`date +%Y-%m-%d`.log