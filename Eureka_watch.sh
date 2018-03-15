#!/bin/sh
 
if (ps ax | grep -v grep | grep -q TwitterBotEureka); then
  LIVE=1
else
  LIVE=0
  echo 'try restart'
  source ~/gmot/bin/activate
  cd ~/git/eurekabot
  nohup python ~/git/eurekabot/TwitterBotEureka.py &
fi

aws cloudwatch put-metric-data --metric-name ProcessMonitoring --namespace Processes --value ${LIVE} --dimensions "Processes=TwitterBotEureka"