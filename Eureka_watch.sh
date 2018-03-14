#!/bin/sh
 
if (ps ax | grep -v grep | grep -q TwitterBotEureka); then
  LIVE=1
else
  LIVE=0
  source /home/ec2-user/gmot/bin/activate
  nohup python /home/ec2-user/git/eurekabot/TwitterBotEureka.py &
fi

aws cloudwatch put-metric-data --metric-name ProcessMonitoring --namespace Processes --value ${LIVE} --dimensions "Processes=TwitterBotEureka"